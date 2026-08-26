#!/usr/bin/env python3
"""library_import.py — bring an existing reference library in, without importing its claims.

WHY THIS EXISTS
Every prospective user of this kit already has a library: a Zotero collection, a
Mendeley folder, an EndNote export, the `.bib` a previous paper was written from.
Until now the only way in was `registry_db.py add`, one record at a time, which
means a researcher with 200 references met the kit as a data-entry task. That is
a real on-ramp problem and it has nothing to do with the kit's discipline.

WHAT IT REFUSES — the whole design is in this paragraph
It never copies the export's bibliographic fields into `bib/references.bib`. Not
one field. An exported `.bib` is bibliographic data of unknown provenance —
hand-edited, decades old, scraped from a publisher page, or typed from memory by
someone else — and CLAUDE.md Invariant 2 says a reference comes from DOI content
negotiation or is flagged `verified:false`. An import path that trusted the file
would be the fastest way ever built to fill a bibliography with unverified
entries, wearing the kit's own verified stamp.

So the export is treated as exactly two things:
  1. a list of DOIs, each re-fetched from the authoritative record by
     `doi2bib.py` (the sole sanctioned writer of the bib), and
  2. a screening worksheet — title/author/year/venue land in the register, which
     is where unverified metadata is *allowed* to live, because nothing cites it.

An entry with no DOI is registered and reported, never written to the bib: it is
a candidate the author still has to resolve (`doi2bib.py --title-search`), and
saying so is the difference between an import that leaves work visible and one
that leaves it hidden.

This script therefore writes NOTHING itself. Both data files are mutated by
their own sanctioned writers, invoked as subprocesses — `registry_db.py` for the
register, `doi2bib.py --append` for the bib — so the guarantee those two carry
(Invariant 6, hook-enforced) is not weakened by a third writer that happens to
mean well. `test_library_import.py` asserts that by name.

USAGE
Copy the export into the project first (same rule as PDFs, and for the same
reason: the register must be reproducible from the project directory alone).

  python scripts/library_import.py --file sources/zotero.bib --plan   # look first
  python scripts/library_import.py --file sources/zotero.bib          # import
  python scripts/library_import.py --file sources/library.ris --no-fetch
  python scripts/library_import.py --resolve       # fill the bib for what is registered
  python scripts/library_import.py --file sources/zotero.bib --limit 20 --lang tr

Formats: BibTeX (`.bib`) and RIS (`.ris`/`.txt`, the EndNote/Mendeley export).

`--plan` writes nothing and fetches nothing: a 400-record import is tedious to
undo, so looking at what is in the file must not itself be the import. `--resolve`
is how an offline `--no-fetch` import is finished — re-running the import for that
would re-register every record as a duplicate.

Exit codes: 0 ok · 1 error · 2 imported, but some entries could not be resolved
(no DOI, or the fetch failed) — the caller decides whether that blocks.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import clean_doi, die, emit, parse_bibtex, read_jsonl, require_within_cwd

SCRIPTS = Path(__file__).parent

# RIS tags this reads. Deliberately a small set: everything else in a RIS record
# (abstract, keywords, publisher, ISBN, URL, notes) is either unused by the
# register or unverifiable metadata that would only make an import look richer
# than it is.
_RIS_LINE = re.compile(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$")
_RIS_TITLE = ("TI", "T1")
_RIS_VENUE = ("JO", "JF", "T2", "JA")
_RIS_YEAR = ("PY", "Y1", "DA")

_TURKISH_LANG = {"tr", "tur", "turkish", "türkçe", "turkce"}


# BibTeX escapes for the letters this kit's own users are most likely to export:
# a Turkish name reaching the register as "Y\ilmaz" is not a cosmetic problem —
# the register is what the screening sheet, the PRISMA counts and every later
# search are read from, and a name nobody can search for is a record nobody
# finds. Best-effort by design: an accent command not listed here loses its
# diacritic (the fallback rule below), never its letter.
_COMBINING = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308",
              "~": "\u0303", "=": "\u0304", ".": "\u0307", "c": "\u0327",
              "u": "\u0306", "v": "\u030c", "H": "\u030b", "k": "\u0328",
              "r": "\u030a", "d": "\u0323", "b": "\u0331"}
# Symbol accents (\"o, \'e) are unambiguous. Letter accents (\c c, \u{g}) are
# not — `\cite` starts with one — so those require a brace or a space, which is
# how they are actually written and which `\cite` never is.
_SYMBOL_ACCENT = re.compile(r"\\([`'^\"~=.])\s*\{?([a-zA-Z])\}?")
_LETTER_ACCENT = re.compile(r"\\([cuvHkrdb])(?:\s*\{([a-zA-Z])\}|\s+([a-zA-Z])(?![a-zA-Z]))")
_STANDALONE = {r"\\i\b": "ı", r"\\j\b": "ȷ", r"\\ss\b": "ß", r"\\aa\b": "å",
               r"\\AA\b": "Å", r"\\o\b": "ø", r"\\O\b": "Ø", r"\\l\b": "ł", r"\\L\b": "Ł"}


def _compose(base: str, mark: str) -> str:
    return unicodedata.normalize("NFC", base + mark)


def _plain(value: str) -> str:
    """A BibTeX field as text: escapes decoded, grouping braces removed.

    Composed through Unicode rather than a lookup table of the letters this kit
    happens to care about: `\\c{c}` is c + COMBINING CEDILLA, which NFC folds to
    ç, and the same three lines therefore handle Turkish, Czech, Polish and
    French without a table anyone has to remember to extend.
    """
    text = value or ""
    text = _SYMBOL_ACCENT.sub(lambda m: _compose(m.group(2), _COMBINING[m.group(1)]), text)
    text = _LETTER_ACCENT.sub(
        lambda m: _compose(m.group(2) or m.group(3), _COMBINING[m.group(1)]), text)
    for pattern, char in _STANDALONE.items():
        text = re.sub(pattern, char, text)
    # Whatever is left is markup, not content: \textbf{X} keeps X, not the verb.
    text = re.sub(r"\\[a-zA-Z]+\s?", "", text)
    # Grouping braces go; an ESCAPED brace is a character in the title and stays,
    # which is why the escapes are unwrapped after this line rather than before.
    text = re.sub(r"(?<!\\)[{}]", "", text)
    return re.sub(r"\\([&%_$#{}])", r"\1", text).strip()


def _year_of(raw: str) -> int | None:
    m = re.search(r"(1[0-9]|20)\d\d", raw or "")
    return int(m.group(0)) if m else None


def _lang_of(raw: str, default: str) -> str:
    return "tr" if (raw or "").strip().lower() in _TURKISH_LANG else default


def parse_bib_library(text: str, default_lang: str) -> list[dict]:
    out = []
    for entry in parse_bibtex(text):
        f = entry["fields"]
        authors = [a.strip() for a in re.split(r"\s+and\s+", _plain(f.get("author", "")))
                   if a.strip()]
        out.append({
            "title": _plain(f.get("title", "")),
            "authors": authors,
            "year": _year_of(f.get("year", "") or f.get("date", "")),
            "venue": _plain(f.get("journal") or f.get("booktitle") or f.get("publisher") or ""),
            "doi": clean_doi(f.get("doi", "")),
            "lang": _lang_of(f.get("language", ""), default_lang),
            "source_key": entry["key"],
        })
    return out


def parse_ris_library(text: str, default_lang: str) -> list[dict]:
    records, current = [], {}

    def flush():
        if current.get("title") or current.get("doi"):
            records.append({
                "title": current.get("title", ""),
                "authors": current.get("authors", []),
                "year": _year_of(current.get("year", "")),
                "venue": current.get("venue", ""),
                "doi": clean_doi(current.get("doi", "")),
                "lang": _lang_of(current.get("lang", ""), default_lang),
                "source_key": current.get("id", ""),
            })
        current.clear()

    for line in text.splitlines():
        m = _RIS_LINE.match(line.rstrip())
        if not m:
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "ER":
            flush()
        elif tag == "TY":
            # A new record without a closing ER — malformed but common in the
            # wild, and dropping the previous record silently is the one
            # behaviour an import must never have.
            flush()
            current["id"] = value
        elif tag in _RIS_TITLE and not current.get("title"):
            current["title"] = value
        elif tag in ("AU", "A1"):
            current.setdefault("authors", []).append(value)
        elif tag in _RIS_YEAR and not current.get("year"):
            current["year"] = value
        elif tag in _RIS_VENUE and not current.get("venue"):
            current["venue"] = value
        elif tag == "DO" and not current.get("doi"):
            current["doi"] = value
        elif tag == "LA" and not current.get("lang"):
            current["lang"] = value
    flush()
    return records


def parse_library(path: Path, default_lang: str) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".ris" or re.search(r"^TY\s{2}- ", text, re.M):
        return parse_ris_library(text, default_lang)
    return parse_bib_library(text, default_lang)


def fetch_via_doi2bib(doi: str, bib: str, timeout: float = 60.0) -> dict:
    """Append one DOI's authoritative record to the bib, through the only script
    allowed to write it. Returns doi2bib's own JSON payload, or an {"error": ...}
    dict — a failed fetch is reported, never guessed around."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "doi2bib.py"), "--doi", doi,
         "--append", bib, "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if proc.returncode != 0:
        reason = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {"error": reason[-1] if reason else f"doi2bib exited {proc.returncode}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"doi2bib returned unreadable output: {proc.stdout[:120]}"}


def register(payloads: list[dict], registry: str, timeout: float = 120.0) -> dict:
    """Hand the whole batch to registry_db.py on stdin — one call, so its
    in-batch dedup and single atomic write both apply to the import as a unit."""
    if not payloads:
        return {"added": [], "duplicates": [], "total": 0}
    stream = "\n".join(json.dumps(p, ensure_ascii=False) for p in payloads)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "registry_db.py"), "--file", registry,
         "add", "--stdin"],
        input=stream, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if proc.returncode != 0:
        die(f"registry_db.py refused the batch — {(proc.stderr or proc.stdout).strip()}")
    return json.loads(proc.stdout)


def to_payload(entry: dict, source_name: str, bib_key: str | None) -> dict:
    rec = {
        "title": entry["title"],
        "authors": entry["authors"],
        "lang": entry["lang"],
        "status": "candidate",
        "db": "import",
        # Provenance, recorded on the record itself: everything here except the
        # DOI came from a file the kit did not verify, and six months later
        # nothing else would distinguish these rows from screened ones.
        "import_source": source_name,
        "metadata_source": "user-export (unverified)",
    }
    if entry.get("year"):
        rec["year"] = entry["year"]
    if entry.get("venue"):
        rec["venue"] = entry["venue"]
    if entry.get("doi"):
        rec["doi"] = entry["doi"]
    if bib_key:
        rec["bib_key"] = bib_key
    return rec


def run_import(entries: list[dict], *, source_name: str, registry: str, bib: str,
               fetch=None, sleep: float = 0.0, progress=None) -> dict:
    """Resolve first, register second.

    The order is the reason this works in one pass: `doi2bib.py` mints the bib
    key, and the register wants that key on the record. Registering first would
    mean a second update pass keyed by DOI, and a record that briefly exists
    with no link to its own reference.
    """
    # `fetch is False` means --no-fetch (register only). Written as an explicit
    # identity check, not `fetch or default`: False is falsy, so the short form
    # would quietly restore the network path the caller just switched off.
    if fetch is None:
        def fetch(doi):
            return fetch_via_doi2bib(doi, bib)
    payloads, appended, unresolved, failed = [], [], [], []
    for i, entry in enumerate(entries):
        key = None
        if entry.get("doi") and fetch is not False:
            if sleep and i:
                time.sleep(sleep)  # politeness toward doi.org, not a quota
            result = fetch(entry["doi"])
            if result.get("error"):
                failed.append({"doi": entry["doi"], "title": entry["title"][:80],
                               "reason": result["error"]})
            else:
                key = result.get("key")
                if result.get("status") == "appended":
                    appended.append(key)
        elif not entry.get("doi"):
            unresolved.append({"title": entry["title"][:80],
                               "reason": "no DOI in the export — resolve with "
                                         "doi2bib.py --title-search, then re-run"})
        payloads.append(to_payload(entry, source_name, key))
        if progress:
            progress(i + 1, len(entries), entry, key)
    registered = register(payloads, registry)
    return {
        "parsed": len(entries),
        "registered": registered.get("added", []),
        "duplicates": registered.get("duplicates", []),
        "bib_appended": appended,
        "no_doi": unresolved,
        "fetch_failed": failed,
        "note": ("nothing from the export reached the bibliography: DOI-bearing "
                 "entries were re-fetched from the authoritative record, and the "
                 "rest were registered as candidates only"),
    }


def link_bib_key(rec_id: str, key: str, registry: str, timeout: float = 60.0) -> dict:
    """Attach a minted bib key to an already-registered record, through the
    register's own writer (which is also where the uniqueness check lives)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "registry_db.py"), "--file", registry,
         "set-field", rec_id, "bib_key", key],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip().splitlines()[-1]}
    return json.loads(proc.stdout)


def resolve_registered(registry: str, bib: str, *, fetch=None, sleep: float = 0.0,
                       limit: int | None = None, progress=None) -> dict:
    """Fill the bibliography for records already in the register.

    The second half of an offline import, and the reason `--no-fetch` is safe to
    use: re-running the import to "finish the job" would re-register every record
    as a duplicate. This finishes it from the register instead — every record
    that has a DOI and no bib key yet, and nothing else.
    """
    if fetch is None:
        def fetch(doi):
            return fetch_via_doi2bib(doi, bib)
    records = read_jsonl(registry)
    pending = [r for r in records if r.get("doi") and not r.get("bib_key")]
    if limit is not None:
        pending = pending[:limit]
    appended, linked, failed = [], [], []
    for i, rec in enumerate(pending):
        if sleep and i:
            time.sleep(sleep)
        result = fetch(rec["doi"])
        if result.get("error"):
            failed.append({"doi": rec["doi"], "id": rec.get("id"),
                           "reason": result["error"]})
        else:
            key = result.get("key")
            if result.get("status") == "appended":
                appended.append(key)
            if key:
                link = link_bib_key(rec.get("id", ""), key, registry)
                if link.get("error"):
                    failed.append({"doi": rec["doi"], "id": rec.get("id"),
                                   "reason": f"bib key minted but not linked — {link['error']}"})
                else:
                    linked.append({"id": rec.get("id"), "bib_key": key})
        if progress:
            progress(i + 1, len(pending), rec, result.get("key"))
    return {
        "pending": len(pending),
        "bib_appended": appended,
        "linked": linked,
        "fetch_failed": failed,
        "note": ("resolved from the register, not from the export — records "
                 "already carrying a bib key were left alone"),
    }


def plan(entries: list[dict], source_name: str) -> dict:
    """Parse and report. Writes nothing, contacts nothing.

    An import is one of the few operations in this kit that is tedious to undo:
    a 400-record register is not something an author reviews line by line
    afterwards. So the default flow looks first — and looking must not be a
    write, or "let me see what is in there" quietly becomes the import.
    """
    with_doi = [e for e in entries if e.get("doi")]
    langs: dict[str, int] = {}
    for e in entries:
        langs[e["lang"]] = langs.get(e["lang"], 0) + 1
    return {
        "mode": "plan",
        "file": source_name,
        "parsed": len(entries),
        "with_doi": len(with_doi),
        "without_doi": len(entries) - len(with_doi),
        "by_language": langs,
        "sample": [{"title": e["title"][:70], "year": e.get("year"), "doi": e.get("doi")}
                   for e in entries[:5]],
        "note": ("nothing was written and nothing was fetched — re-run without "
                 "--plan to import"),
    }


def _progress(i: int, total: int, entry: dict, key: str | None):
    mark = key or ("no DOI" if not entry.get("doi") else "unresolved")
    print(f"[{i:>4}/{total}] {mark}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help=".bib or .ris export, inside the project")
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--lang", default="en",
                    help="language recorded for entries whose export does not state one")
    ap.add_argument("--limit", type=int, help="import only the first N entries (try a small "
                                              "batch before committing a 400-entry library)")
    ap.add_argument("--plan", action="store_true",
                    help="parse and report only — no writes, no network")
    ap.add_argument("--no-fetch", action="store_true",
                    help="register only — no network, no bib writes. Finish the bib "
                         "later with --resolve, never by re-running the import "
                         "(that would re-register every record as a duplicate).")
    ap.add_argument("--resolve", action="store_true",
                    help="ignore --file: fetch and link the bibliography for records "
                         "already in the register that have a DOI and no bib key")
    ap.add_argument("--sleep", type=float, default=0.5,
                    help="seconds between DOI fetches (default 0.5)")
    ap.add_argument("--quiet", action="store_true", help="no per-entry progress on stderr")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.registry, "--registry")
    require_within_cwd(args.bib, "--bib")
    if args.limit is not None and args.limit < 1:
        die(f"--limit must be at least 1, got {args.limit}")

    if args.resolve:
        if args.file:
            die("--resolve works from the register, not from a file — drop --file")
        if not Path(args.registry).is_file():
            die(f"{args.registry} does not exist — there is nothing registered to resolve")
        Path(args.bib).parent.mkdir(parents=True, exist_ok=True)
        result = resolve_registered(args.registry, args.bib, sleep=args.sleep,
                                    limit=args.limit,
                                    progress=None if args.quiet else _progress)
        emit(result, args.json_out)
        sys.exit(2 if result["fetch_failed"] else 0)

    if not args.file:
        die("nothing to do — pass --file <export.bib|.ris>, or --resolve to finish "
            "the bibliography for records already registered")
    # The export is a read, but it is required to sit inside the project all the
    # same: the register it produces claims to be reproducible from this
    # directory, and a row whose origin was a file in Downloads that no longer
    # exists is not reproducible by anyone, including its author.
    require_within_cwd(args.file, "--file")

    path = Path(args.file)
    if not path.is_file():
        die(f"{args.file} does not exist — copy the export into the project first")
    entries = parse_library(path, args.lang)
    if not entries:
        die(f"{args.file} yielded no records — is it a BibTeX or RIS export? "
            f"(a Zotero 'Quick Copy' text list is neither)")
    if args.limit is not None:
        entries = entries[:args.limit]

    if args.plan:
        emit(plan(entries, path.name), args.json_out)
        return

    if not args.no_fetch:
        Path(args.bib).parent.mkdir(parents=True, exist_ok=True)
    result = run_import(
        entries, source_name=path.name, registry=args.registry, bib=args.bib,
        fetch=False if args.no_fetch else None,
        sleep=0.0 if args.no_fetch else args.sleep,
        progress=None if args.quiet else _progress)
    result["file"] = path.as_posix()
    result["fetched"] = not args.no_fetch
    emit(result, args.json_out)
    if result["no_doi"] or result["fetch_failed"]:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired as e:
        die(f"a sanctioned writer did not return in time — {e}")
    except OSError as e:
        die(f"failed to read the export — {e}")
