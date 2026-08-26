#!/usr/bin/env python3
"""bib_doctor.py — hygiene audit for bib/references.bib: dedupe, required fields, DOI syntax, keys.

Checks (report-only by default; --fix rewrites the file for safe fixes):
  * duplicates: same DOI, or normalized-title similarity ≥ 95
  * required fields per entry type (article: author/title/journal/year; book: author/title/
    publisher/year; inproceedings: author/title/booktitle/year; misc/online: title/url|doi)
  * DOI syntax (10.NNNN/suffix) and https://doi.org/ prefixes embedded in the doi field
  * key normalization: surname+year+word, ascii-only (report; renames are NOT auto-applied
    because in-text keys would break — cite_audit.py catches that)
  * entries missing verified={true} (i.e., not produced by doi2bib.py)

`--retract KEY` is the sanctioned DELETION path, and it exists because the kit
previously had none. `references.bib` is script-owned (Invariant 6) and its two
sanctioned writers could only ever grow it: `doi2bib.py --append` adds, `--fix`
rewrites in place. So the one workflow that most needs to remove an entry — a
citation the verifier just identified as FABRICATED or RETRACTED — dead-ended on
the kit's own guard, and `/verify-citations` told the user to "update manually",
which `protect_data_files.py` refuses. Removal has to be a script for the same
reason addition is: a hand-edit is unrecorded, and the file has no history of
its own.

Usage:
  python scripts/bib_doctor.py --bib bib/references.bib [--fix] [--json]
  python scripts/bib_doctor.py --retract smith2020ethics [--drafts drafts] [--force]
Exit codes: 0 clean · 1 error · 2 problems found.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (DOI_RE, clean_doi, die, emit, file_lock, normalize_title, parse_bibtex,
                        require_within_cwd, serialize_bibtex, warn_missing_rapidfuzz,
                        write_text_atomic)

# Named, numeric and hex entities. Deliberately not a bare "&" match: a
# correctly-decoded field legitimately contains one.
_HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]{1,31}|#\d{1,7}|#[xX][0-9A-Fa-f]{1,6});")


REQUIRED = {
    "article": ["author", "title", "journal", "year"],
    "book": ["author", "title", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "incollection": ["author", "title", "booktitle", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "misc": ["title"],
    "online": ["title"],  # url-or-doi enforced separately below, not both required
}
KEY_RE = re.compile(r"^[a-z][a-z0-9]*$")

# Preprint servers register DOIs that doi.org content-negotiation types as
# @article, yet a preprint has no peer-reviewed journal — demanding a "journal"
# field on them produces a false "missing-field" flag on a perfectly valid,
# authoritatively-fetched entry. Detect the preprint case and require a locator
# (doi|url) instead of a journal, exactly like @misc/@online.
_PREPRINT_HOSTS = ("arxiv", "biorxiv", "medrxiv", "chemrxiv", "techrxiv",
                   "ssrn", "researchsquare", "research square", "preprints.org",
                   "osf", "hal", "zenodo", "preprint")


def _is_preprint(fields: dict) -> bool:
    doi = clean_doi(fields.get("doi", "") or "").lower()
    if doi.startswith("10.48550/arxiv") or doi.startswith("10.26434/chemrxiv") \
            or doi.startswith("10.1101/"):  # 10.1101 = Cold Spring Harbor (bioRxiv/medRxiv)
        return True
    for f in ("archiveprefix", "eprint", "primaryclass"):
        if fields.get(f):
            return True
    hay = " ".join(str(fields.get(k, "")) for k in
                   ("journal", "publisher", "note", "howpublished", "series")).lower()
    return any(h in hay for h in _PREPRINT_HOSTS)


def audit(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    problems, fixed_entries = [], []
    seen_dois: dict[str, str] = {}
    seen_titles: list[tuple[str, str]] = []
    try:
        from rapidfuzz import fuzz
        sim = lambda a, b: fuzz.token_sort_ratio(a, b)
    except ImportError:  # pragma: no cover
        warn_missing_rapidfuzz()
        sim = lambda a, b: 100 if a == b else 0

    for e in entries:
        key, fields = e["key"], dict(e["fields"])
        entry_problems = []

        # HTML entities deposited by publishers. doi2bib.py now decodes at fetch
        # time, but an entry fetched before that lands here already carrying
        # "&amp;" — and it prints that way in the finished reference list, which
        # is where it is finally noticed. Journal names with "&" are common
        # enough ("Diabetes Technology & Therapeutics", "Science & Justice")
        # that the repair is worth having on the existing-file path too.
        for fname, fvalue in list(fields.items()):
            if isinstance(fvalue, str) and _HTML_ENTITY_RE.search(fvalue):
                decoded = html.unescape(fvalue)
                if decoded != fvalue:
                    entry_problems.append({
                        "kind": "html-entity", "fix": decoded,
                        "msg": f"{fname} field carries an HTML entity — "
                               f"decode to '{decoded[:60]}'"})
                    fields[fname] = decoded

        doi = fields.get("doi", "").strip()
        if doi:
            clean = clean_doi(doi)
            if clean != doi:
                entry_problems.append({"kind": "doi-prefix", "fix": clean,
                                       "msg": f"doi field contains URL prefix — normalize to '{clean}'"})
                fields["doi"] = clean
                doi = clean
            if not DOI_RE.match(doi):
                entry_problems.append({"kind": "doi-syntax",
                                       "msg": f"'{doi}' does not match 10.NNNN/suffix"})
            if doi.lower() in seen_dois:
                entry_problems.append({"kind": "duplicate-doi",
                                       "msg": f"same DOI as entry '{seen_dois[doi.lower()]}'"})
            else:
                seen_dois[doi.lower()] = key

        ntitle = normalize_title(fields.get("title", ""))
        for other_key, other_title in seen_titles:
            if ntitle and sim(ntitle, other_title) >= 95:
                entry_problems.append({"kind": "duplicate-title",
                                       "msg": f"title ≥95% similar to entry '{other_key}'"})
                break
        if ntitle:
            seen_titles.append((key, ntitle))

        req = REQUIRED.get(e["type"], ["title"])
        is_preprint = e["type"] == "article" and _is_preprint(fields)
        if is_preprint:
            req = ["author", "title", "year"]  # no journal for a preprint
        missing = [f for f in req if not fields.get(f)]
        if (e["type"] in ("misc", "online") or is_preprint) \
                and not fields.get("url") and not fields.get("doi"):
            missing.append("url|doi")
        for f in missing:
            entry_problems.append({"kind": "missing-field",
                                   "msg": f"field '{f}' missing in {key} — run doi2bib.py --title-search or mark verified:false"})

        if not KEY_RE.match(key):
            entry_problems.append({"kind": "key-style",
                                   "msg": f"key '{key}' not normalized (want surname+year+word, ascii lowercase) — rename manually, then re-run cite_audit.py"})

        if fields.get("verified", "").lower() != "true":
            entry_problems.append({"kind": "unverified",
                                   "msg": "entry lacks verified={true} — not produced by doi2bib.py; verify or replace"})

        if entry_problems:
            problems.append({"key": key, "issues": entry_problems})
        fixed_entries.append({"type": e["type"], "key": key, "fields": fields})
    return problems, fixed_entries


def _still_cited(key: str, drafts_dir: Path) -> list[str]:
    """Draft files that still cite `key`.

    Delegates extraction to cite_audit.extract_citations rather than running a
    second regex here: a looser local pattern would disagree with the citation
    gate about what counts as a citation (fenced blocks, inline code, emails),
    and the two guards drifting apart is precisely how a retraction ends up
    looking safe to this script and missing to the gate.
    """
    from cite_audit import extract_citations
    if not drafts_dir.is_dir():
        return []
    hits = []
    for f in sorted(drafts_dir.glob("**/*.md")):
        if f.name == "STATUS.md":
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - unreadable file mid-scan
            continue
        if key in extract_citations(text):
            hits.append(f.as_posix())
    return hits


def retract(p: Path, key: str, drafts_dir: Path, force: bool) -> dict:
    """Remove every entry keyed `key` from the bib file. Caller holds the lock.

    Refuses by default while the key is still cited. That is not timidity: the
    in-text citation and the bib entry are one fact in two places, and deleting
    only the second converts a citation that is *wrong* into a citation that is
    *missing* — which cite_audit.py then blocks at finalization, one stage later
    and further from the decision that caused it. Fix the prose first. `--force`
    is for the author who deliberately wants the reverse order, and the return
    payload records that they took it.
    """
    text = p.read_text(encoding="utf-8")
    entries = parse_bibtex(text)
    if not entries and text.strip():
        die(f"{p} is non-empty but 0 entries were parsed — "
            f"malformed BibTeX (check for a missing comma/brace after an @type{{key)")
    removed = [e for e in entries if e["key"] == key]
    if not removed:
        die(f"no entry with key '{key}' in {p} — nothing to retract. Keys are "
            f"case-sensitive; `bib_doctor.py --json` lists what is actually there.")
    kept = [e for e in entries if e["key"] != key]
    cited_in = _still_cited(key, drafts_dir)
    if cited_in and not force:
        die(f"'{key}' is still cited in {', '.join(cited_in)} — remove or replace the "
            f"in-text citation first, then retract. Retracting now would turn a wrong "
            f"citation into a missing one, which cite_audit.py blocks at finalization. "
            f"Pass --force to retract anyway.")
    write_text_atomic(p, "".join(serialize_bibtex(e) + "\n\n" for e in kept))
    return {
        "action": "retract",
        "key": key,
        "removed": len(removed),
        "remaining": len(kept),
        "still_cited_in": cited_in,
        "forced": bool(cited_in and force),
        # The audit trail, and the reason this is a dict field rather than a log
        # line: references.bib is script-owned and carries no history of its
        # own, so once the entry is gone the only surviving record of what it
        # said is what this call hands back. /verify-citations writes it into
        # reviews/verify-round-N.md next to the reason for the retraction.
        "removed_bibtex": "".join(serialize_bibtex(e) for e in removed),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--fix", action="store_true", help="rewrite file applying safe fixes (doi prefix strip)")
    ap.add_argument("--retract", metavar="KEY",
                    help="remove one entry — the sanctioned deletion path for a fabricated "
                         "or retracted source; refuses while the key is still cited")
    ap.add_argument("--drafts", default="drafts",
                    help="where --retract looks for surviving in-text citations")
    ap.add_argument("--force", action="store_true",
                    help="with --retract: remove even though the key is still cited in drafts/")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    if args.retract and args.fix:
        die("--retract and --fix both rewrite the bib file for different reasons — "
            "run them one at a time so each rewrite has one cause.")
    if args.force and not args.retract:
        die("--force only means anything with --retract")
    require_within_cwd(args.bib, "--bib")
    p = Path(args.bib)
    if not p.exists():
        die(f"{args.bib} does not exist")
    if args.retract:
        require_within_cwd(args.drafts, "--drafts")
        if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
            die(f"--drafts {args.drafts} is not a directory")
        # Same whole-cycle lock as --fix below, for the same TOCTOU reason: a
        # concurrent doi2bib.py --append between our read and our write would be
        # erased by a rewrite computed from stale entries.
        with file_lock(p):
            payload = retract(p, args.retract, Path(args.drafts), args.force)
        emit(payload, True)
        sys.exit(0)
    if args.fix:
        # The ENTIRE read -> audit -> write cycle must be inside the lock, not
        # just the write: a lock around the write alone still lets a concurrent
        # doi2bib.py --append interleave between our unlocked read and our
        # locked write, so our write silently overwrites the file with a copy
        # computed from data that's already stale (a classic TOCTOU) —
        # reproduced live (10 concurrent appends racing one --fix lost entries).
        with file_lock(p):
            text = p.read_text(encoding="utf-8")
            entries = parse_bibtex(text)
            if not entries and text.strip():
                die(f"{args.bib} is non-empty but 0 entries were parsed — "
                    f"malformed BibTeX (check for a missing comma/brace after an @type{{key)")
            problems, fixed = audit(entries)
            if problems:
                write_text_atomic(p, "".join(serialize_bibtex(e) + "\n\n" for e in fixed))
    else:
        text = p.read_text(encoding="utf-8")
        entries = parse_bibtex(text)
        if not entries and text.strip():
            die(f"{args.bib} is non-empty but 0 entries were parsed — "
                f"malformed BibTeX (check for a missing comma/brace after an @type{{key)")
        problems, fixed = audit(entries)
    emit({"entries": len(entries), "problem_entries": len(problems),
          "fixed_in_place": bool(args.fix and problems), "problems": problems}, True)
    sys.exit(2 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the bib-file lock — {e}")
    except OSError as e:
        die(f"failed to write the bib file — {e}")
    except UnicodeDecodeError as e:
        die(f"bib file is not valid UTF-8 — {e}")
