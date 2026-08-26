#!/usr/bin/env python3
"""coauthor_diff.py — what the co-author's returned file changed, in the four dimensions that matter.

WHY THIS EXISTS
`/import-manuscript` brings a manuscript in. It has no answer for the far more
frequent event: the supervisor sends the file back. Word's own track-changes view
answers "which words moved", which is the one question whose answer is obvious
and the one that hides the three that are not —

  * a citation key disappeared while the sentence it supported stayed
  * a number changed, or a new one appeared that no run produced
  * a claim moved up the strength ladder ("our results suggest" → "we prove")

Those three survive a read-through because they look like the paper. So they are
extracted mechanically, and the prose diff is reported as counts underneath them.

WHAT IT REFUSES
- **To merge.** Nothing is written into `drafts/`. The report is what you read
  first; applying an edit stays a decision with a person behind it.
- **To compare prose.** Two honest edits of one paragraph share no sentence, and
  a similarity score over them measures nothing. Word counts per section, and the
  four extractions — that is the whole comparison.
- **To rule that a change is wrong.** A removed citation may be the right call. A
  strengthened claim may have earned it in the same revision. Every finding here
  is "this changed, look at it", never "this is an error".

USAGE
  python scripts/coauthor_diff.py --returned inbox/paper-supervisor.docx
  python scripts/coauthor_diff.py --returned rev.docx --drafts drafts --runs analysis/runs.jsonl

Exit codes: 0 nothing flagged · 1 error · 2 flagged findings · 3 BLOCKED (converter
missing — pandoc for .docx/.tex, pymupdf4llm for .pdf).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import manuscript_import as mi
import translation_check as tc
from claim_check import RUNG_NAME, rung_of, split_sentences
from cite_audit import extract_citations
from lib_common import die, emit, read_jsonl, require_within_cwd, transliterate

DEFAULT_DRAFTS = "drafts"
DEFAULT_RUNS = "analysis/runs.jsonl"

# A claim at or above "predictive" is one a reviewer will test against the
# results. Below it, a wording change is style; at or above it, it is a promise.
FLAG_RUNG = 2

WORD_RE = re.compile(r"\w+", re.UNICODE)


def _fold_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", transliterate(title).lower()).strip()


def sections_of(text: str) -> dict[str, str]:
    """Heading → body, folded on the heading so 'Yöntem' and 'YÖNTEM' are one
    section. A duplicate heading keeps the first — a document with two sections
    of the same name is reported, not silently merged."""
    out: dict[str, str] = {}
    for section in mi.split_sections(text)[0]:
        key = _fold_title(section["title"])
        out.setdefault(key, section["body"])
    return out


def local_text(drafts: Path) -> str:
    if not drafts.is_dir():
        die(f"{drafts} does not exist — there is nothing to compare against")
    files = sorted(drafts.glob("*.md"))
    if not files:
        die(f"{drafts} holds no .md files — there is nothing to compare against")
    return "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)


def word_delta(before: str, after: str) -> dict:
    a, b = WORD_RE.findall(before), WORD_RE.findall(after)
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    added = removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    return {"words_before": len(a), "words_after": len(b),
            "words_added": added, "words_removed": removed}


def citation_delta(before: str, after: str) -> dict:
    a, b = extract_citations(before), extract_citations(after)
    return {"added": sorted(b - a), "removed": sorted(a - b)}


def number_delta(before: str, after: str) -> dict:
    """New, gone, and rounded-differently — kept apart, because a digit that
    moved and a digit that lost a decimal place are different events and only
    one of them is worth a reviewer's attention."""
    a, b = tc.numbers(before), tc.numbers(after)
    new = sorted(set(b) - set(a))
    gone = sorted(set(a) - set(b))
    rounded = []
    for value in list(new):
        partner = tc._rounding_partner(value, set(gone))
        if partner:
            rounded.append({"before": partner, "after": value})
            new.remove(value)
            gone.remove(partner)
    return {"new": new, "gone": gone, "rounding_only": rounded,
            "raw_after": {v: b[v] for v in new}}


def claim_delta(before: str, after: str) -> list[dict]:
    """Claims that got STRONGER, not sentences that got rewritten.

    The first version flagged any new sentence standing at or above the
    predictive rung, which fired on every reworded sentence that already carried
    a ladder verb — "Transfer learning improves X" edited to "Transfer learning
    improves X under load" reported a strengthened claim that had not moved an
    inch. Noise of that shape is how a check stops being read.

    So each new sentence is matched against its nearest predecessor first. With a
    match, the finding is a rung that went UP. With no match, the sentence is
    genuinely new and the finding is a strong claim arriving from nowhere.
    """
    old = [s.strip() for s in split_sentences(before) if s.strip()]
    old_set = set(old)
    hits = []
    for sentence in split_sentences(after):
        text = sentence.strip()
        if not text or text in old_set:
            continue
        rung, phrase = rung_of(text)
        if rung is None or rung < FLAG_RUNG:
            continue
        near = difflib.get_close_matches(text, old, n=1, cutoff=0.6)
        if near:
            previous, _ = rung_of(near[0])
            if previous is not None and previous >= rung:
                continue  # reworded, not strengthened
            hits.append({"rung": rung, "rung_name": RUNG_NAME.get(rung, str(rung)),
                         "previous_rung": (RUNG_NAME.get(previous, str(previous))
                                           if previous is not None else None),
                         "phrase": phrase, "sentence": text[:200],
                         "was": near[0][:200]})
        else:
            hits.append({"rung": rung, "rung_name": RUNG_NAME.get(rung, str(rung)),
                         "previous_rung": None, "phrase": phrase,
                         "sentence": text[:200], "was": None})
    return hits


def run_register_numbers(runs_path: str) -> set[str]:
    """Every metric value the run register holds, canonicalised. A number in the
    returned manuscript that is not in here was not produced by a recorded run —
    which is either an unrecorded run or a typed number."""
    values: set[str] = set()
    for rec in read_jsonl(runs_path):
        metrics = rec.get("metrics")
        if not isinstance(metrics, dict):
            continue
        for value in metrics.values():
            if isinstance(value, (int, float)):
                canonical = tc.normalise_number(str(value))
            elif isinstance(value, str):
                canonical = tc.normalise_number(value)
            else:
                continue
            if canonical:
                values.add(canonical)
    return values


def docx_comments(path: Path) -> list[dict]:
    """Word comments, read out of the file itself.

    Pandoc drops them, and they are frequently the only place the supervisor
    said WHY. Parsed from `word/comments.xml` with the tag stripper below rather
    than a dependency: this is one flat element list, not a document model.
    """
    if path.suffix.lower() != ".docx":
        return []
    try:
        with zipfile.ZipFile(path) as z:
            if "word/comments.xml" not in z.namelist():
                return []
            xml = z.read("word/comments.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, OSError, KeyError):
        return []
    out = []
    for m in re.finditer(r"<w:comment\b([^>]*)>(.*?)</w:comment>", xml, re.DOTALL):
        attrs, body = m.group(1), m.group(2)
        author = re.search(r'w:author="([^"]*)"', attrs)
        date = re.search(r'w:date="([^"]*)"', attrs)
        text = " ".join(t.group(1) for t in re.finditer(r"<w:t[^>]*>(.*?)</w:t>",
                                                        body, re.DOTALL))
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            out.append({"author": author.group(1) if author else None,
                        "date": date.group(1) if date else None, "text": text})
    return out


def compare(before_text: str, after_text: str, register: set[str]) -> dict:
    before_sections = sections_of(before_text)
    after_sections = sections_of(after_text)
    shared = [k for k in after_sections if k in before_sections]

    per_section = []
    for key in shared:
        b, a = before_sections[key], after_sections[key]
        entry = {"section": key, **word_delta(b, a),
                 "citations": citation_delta(b, a),
                 "numbers": number_delta(b, a),
                 "claims_strengthened": claim_delta(b, a)}
        entry["unchanged"] = (entry["words_added"] == 0 and entry["words_removed"] == 0)
        per_section.append(entry)

    whole_numbers = number_delta(before_text, after_text)
    unbacked = [v for v in whole_numbers["new"] if v not in register] if register else []

    flags = []
    for entry in per_section:
        for key in entry["citations"]["removed"]:
            flags.append({"kind": "citation_removed", "section": entry["section"],
                          "key": key,
                          "why": "the sentence may have kept the claim the citation "
                                 "supported — check before accepting"})
        for hit in entry["claims_strengthened"]:
            flags.append({"kind": "claim_strengthened", "section": entry["section"],
                          "rung": hit["rung_name"], "phrase": hit["phrase"],
                          "sentence": hit["sentence"],
                          "why": "a new claim at or above the predictive rung"})
    for value in unbacked:
        flags.append({"kind": "number_not_in_run_register", "value": value,
                      "as_written": whole_numbers["raw_after"].get(value, []),
                      "why": "no recorded run produced this value — either the run "
                             "was never registered, or the number was typed"})

    return {
        "sections_before": sorted(before_sections),
        "sections_after": sorted(after_sections),
        "sections_added": sorted(set(after_sections) - set(before_sections)),
        "sections_removed": sorted(set(before_sections) - set(after_sections)),
        "per_section": per_section,
        "numbers_overall": whole_numbers,
        "run_register_values": len(register),
        "flags": flags,
        "note": ("prose is never compared sentence by sentence — two honest edits of "
                 "one paragraph share no wording. What is compared is citation keys, "
                 "quantities, claim strength and word counts."),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--returned", required=True, metavar="FILE",
                    help="the file the co-author sent back (.docx/.tex/.md/.pdf)")
    ap.add_argument("--drafts", default=DEFAULT_DRAFTS)
    ap.add_argument("--runs", default=DEFAULT_RUNS)
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--returned", args.returned), ("--drafts", args.drafts),
                        ("--runs", args.runs)):
        require_within_cwd(value, flag)
    returned = Path(args.returned)
    if not returned.is_file():
        die(f"{args.returned} does not exist")

    before = local_text(Path(args.drafts))
    with tempfile.TemporaryDirectory() as tmp:
        after, meta = mi.to_markdown(returned, Path(tmp))

    register = run_register_numbers(args.runs)
    report = compare(before, after, register)
    report["returned"] = returned.as_posix()
    report["converted_via"] = meta.get("via")
    report["comments"] = docx_comments(returned)
    report["result"] = "FLAGGED" if report["flags"] else "NO_FLAGS"
    report["next"] = ("nothing was written to drafts/. Apply what you accept yourself; "
                      "then /verify-citations, and /experiment trace for any number "
                      "flagged above")
    emit(report, args.json_out)
    sys.exit(2 if report["flags"] else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
