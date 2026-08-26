#!/usr/bin/env python3
"""referee_report.py — your referee report, structured and audited. The manuscript never comes here.

WHY THIS EXISTS
Refereeing is the academic duty with the worst tooling and the strictest
confidentiality. A paper sent to you for review arrives under an undertaking that
Elsevier, Springer and NIH state explicitly; handing it to a tool is the
REFEREE's breach, and no amount of report quality undoes it.

So this script inverts the obvious design. It never sees the paper. You read it —
that part was never the hard part. What is hard, and what actually costs the
evening, is writing it up: numbering the comments so the authors can respond to
them, anchoring each one to a place in the text, keeping the recommendation
inside the journal's own option set, and not accidentally signing a report that
is supposed to be anonymous.

All four of those are checkable, and none of them needs the manuscript.

WHAT IT REFUSES
- **To read the manuscript.** Pointed at a .pdf/.docx/.tex, it exits and says why.
  There is no flag for it.
- **To judge whether a comment is fair.** It checks that a Major comment names a
  place in the paper, not whether it is right. Peer review's substance is yours.
- **To know the journal's options.** "Minor revision" exists at most venues and
  not all; `review-form.json` is the journal's own list, which YOU fill. No file
  ⇒ UNCHECKED.
- **To write your review.** `--scaffold` produces headings and nothing under them.

USAGE
  python scripts/referee_report.py --scaffold reviews/referee/report.md
  python scripts/referee_report.py --check reviews/referee/report.md

Exit codes: 0 clean · 1 error (including "that is a manuscript") · 2 findings or
UNCHECKED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd, transliterate, write_text_atomic
from word_budget import count_words

DEFAULT_FORM = "reviews/referee/review-form.json"

# Formats that are the manuscript rather than your notes about it. Refused by
# extension before anything is opened — the check has to happen before the read,
# or it is not a check.
MANUSCRIPT_SUFFIXES = {".pdf", ".docx", ".doc", ".odt", ".tex", ".rtf"}

# An anchor a corresponding author can act on. "The introduction is weak" is an
# opinion; "Section 1, paragraph 3" is a comment.
ANCHOR_RE = re.compile(
    r"(§\s*\d|(?:section|sect\.?|sec\.?|bölüm|bolum)\s*\d"
    r"|(?:line|lines|satır|satir|l\.)\s*\d"
    r"|(?:p\.|pp\.|page|sayfa|s\.)\s*\d"
    r"|(?:table|tablo|figure|fig\.?|şekil|sekil|eq\.?|equation|denklem)\s*\d"
    r"|(?:abstract|özet|ozet|introduction|giriş|giris|methods?|yöntem|yontem"
    r"|results?|bulgular|discussion|tartışma|tartisma|conclusion|sonuç|sonuc"
    r"|references|kaynak)\b)", re.IGNORECASE)

# Ways a referee signs an anonymous report without noticing. The first-person
# possessive is the tell: recommending a paper is fine, recommending YOUR paper
# in the first person is a signature.
SELF_ID_RE = re.compile(
    r"((?:as|in)\s+(?:we|I)\s+(?:showed|demonstrated|argued|published|found)"
    r"|(?:our|my)\s+(?:own\s+)?(?:previous\s+|recent\s+|earlier\s+)?"
    r"(?:work|paper|study|group|lab|article|results)"
    r"|see\s+(?:our|my)\s+"
    r"|(?:kendi|bizim)\s+(?:önceki\s+|onceki\s+|geçmiş\s+|gecmis\s+)?"
    r"(?:çalışma|calisma|makale|grubumuz)"
    r"|çalışmamızda|calismamizda|makalemizde)", re.IGNORECASE)

REQUIRED_HEADINGS = {
    "summary": ("summary", "özet", "ozet", "synopsis"),
    "significance": ("significance", "önem", "onem", "contribution", "katkı", "katki"),
    "major": ("major", "önemli", "onemli", "esaslı", "esasli"),
    "minor": ("minor", "küçük", "kucuk", "ufak"),
    "recommendation": ("recommendation", "öneri", "oneri", "decision", "karar"),
}

# Asked for by most venues and not all, so its absence is reported rather than
# flagged. Its presence matters for the opposite reason: text meant for the
# editor alone must not be sitting in the section the authors receive.
OPTIONAL_HEADINGS = {
    "confidential": ("confidential", "editor", "editöre", "editore", "gizli"),
}

NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$", re.M)

SCAFFOLD = """# Referee report — <manuscript id, never the title>

<!-- Written by you, after you read the paper. The paper does not come into this
     directory, into this kit, or into any tool: it was given to you under a
     confidentiality undertaking. -->

## Summary
<2-4 sentences, in your own words: what the paper claims and how it argues it.
 Authors read this first to find out whether you understood them.>

## Significance
<Is the question worth answering, and does this answer move it? One paragraph.>

## Major comments
1. (Section X.Y) <what is wrong or missing, and what would resolve it>
2. (Table N) <...>

## Minor comments
1. (line NNN) <...>

## Confidential comments to the editor
<Anything the authors should not see. Leave empty rather than filling it.>

## Recommendation
<one of the journal's own options — see reviews/referee/review-form.json>
"""


def load_form(path: Path) -> dict | None:
    """The journal's own recommendation set. 'Minor revision' exists at most
    venues and not all, and a recommendation the portal does not offer is a
    report the editor has to re-request."""
    if not path.is_file():
        return None
    try:
        form = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(form, dict):
        die(f"{path} must hold a JSON object")
    if not form.get("source_url"):
        die(f"{path} has no 'source_url' — the option set comes from the journal's own "
            f"reviewer form, not from memory")
    if not isinstance(form.get("recommendations"), list) or not form["recommendations"]:
        die(f"{path} needs a non-empty 'recommendations' array")
    return form


def _fold(text: str) -> str:
    return transliterate(text).lower()


def _stripped_body(body: str) -> str:
    """The body with scaffold placeholders removed — `<...>` under a heading is
    the scaffold talking, not the referee."""
    return re.sub(r"<[^>\n]*>", "", body).strip()


def parse_report(text: str) -> dict:
    """Headings → bodies, and the numbered items inside major/minor."""
    parts = re.split(r"^#{1,6}[ \t]*(.+?)[ \t]*$", text, flags=re.M)
    found: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        heading, body = _fold(parts[i]), parts[i + 1]
        # Confidential first: "Confidential comments to the editor" contains
        # neither "major" nor "minor", but a heading like "Minor comments
        # (confidential)" would otherwise be claimed by whichever key was tried
        # first, and the editor-only section is the one that must not be
        # mistaken for a section the authors receive.
        for key, words in {**OPTIONAL_HEADINGS, **REQUIRED_HEADINGS}.items():
            if key in found:
                continue
            if any(_fold(w) in heading for w in words):
                found[key] = body
                break
    return found


def comments_in(body: str) -> tuple[list[dict], list[str]]:
    items = [{"n": int(m.group(1)), "text": m.group(2).strip()}
             for m in NUMBERED_RE.finditer(body)]
    # Bullets are how an unnumbered report gets written. Counted separately so
    # the finding is "these are not numbered", not "there are no comments".
    bullets = [m.group(1).strip() for m in
               re.finditer(r"^\s*[-*+]\s+(.+?)\s*$", body, re.M)]
    return items, bullets


def check_report(text: str, form: dict | None) -> dict:
    found = parse_report(text)
    problems = []
    missing = [k for k in REQUIRED_HEADINGS if k not in found]
    if missing:
        problems.append(f"no section for: {', '.join(missing)}")

    major, major_bullets = comments_in(found.get("major", ""))
    minor, minor_bullets = comments_in(found.get("minor", ""))
    if major_bullets:
        problems.append(f"{len(major_bullets)} major comment(s) written as bullets — "
                        f"authors answer point by point and the editor checks coverage "
                        f"by number; an unnumbered comment gets no reply")
    if minor_bullets:
        problems.append(f"{len(minor_bullets)} minor comment(s) written as bullets")

    unanchored = [c for c in major if not ANCHOR_RE.search(c["text"])]
    if unanchored:
        problems.append(f"major comment(s) {[c['n'] for c in unanchored]} name no place "
                        f"in the paper — a section, table, figure or line number is what "
                        f"makes a comment answerable")

    numbering = []
    for label, items in (("major", major), ("minor", minor)):
        seen = [c["n"] for c in items]
        if seen != list(range(1, len(seen) + 1)):
            numbering.append(f"{label} numbering is {seen}, expected 1..{len(seen)}")
    if numbering:
        problems.append("; ".join(numbering))

    self_id = [{"text": m.group(0), "context": text[max(0, m.start() - 60):m.end() + 60]
                .replace("\n", " ").strip()}
               for m in SELF_ID_RE.finditer(text)]
    if self_id:
        problems.append(f"{len(self_id)} phrase(s) identify you as the referee — an "
                        f"anonymous report that points at its author's own work is signed")

    recommendation = None
    rec_body = found.get("recommendation", "")
    rec_lines = [ln.strip() for ln in rec_body.splitlines() if ln.strip()
                 and not ln.strip().startswith("<")]
    if rec_lines:
        recommendation = rec_lines[0]
    options = (form or {}).get("recommendations")
    rec_ok = None
    if recommendation and options:
        rec_ok = any(_fold(recommendation) == _fold(o) for o in options)
        if not rec_ok:
            problems.append(f"recommendation {recommendation!r} is not one of the "
                            f"journal's options {options}")
    elif not recommendation:
        problems.append("no recommendation given")

    words = count_words(text)
    limit = (form or {}).get("max_words")
    if limit and words > limit:
        problems.append(f"report is {words} words, the form allows {limit}")

    report = {
        "sections_found": sorted(found),
        "sections_missing": missing,
        "major": {"count": len(major), "unanchored": [c["n"] for c in unanchored],
                  "as_bullets": len(major_bullets)},
        "minor": {"count": len(minor), "as_bullets": len(minor_bullets)},
        "confidential_to_editor": {
            "present": "confidential" in found,
            "empty": "confidential" in found and not _stripped_body(found["confidential"]),
        },
        "self_identification": self_id,
        "recommendation": recommendation,
        "recommendation_valid": rec_ok,
        "words": words,
        "problems": problems,
        "note": ("this audits the REPORT, never the manuscript. Whether a comment is "
                 "fair, correct or proportionate is not checked and is not checkable"),
    }
    report["result"] = "OK" if not problems else "FINDINGS"
    if form is None:
        report["result"] = "UNCHECKED" if not problems else "FINDINGS"
        report["form_note"] = (
            "no reviews/referee/review-form.json — the recommendation was NOT checked "
            "against the journal's own option set, and no word limit was applied. "
            "Fill it from the reviewer form the journal sent you.")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scaffold", metavar="FILE", help="write the report skeleton")
    ap.add_argument("--check", metavar="FILE", help="audit a finished report")
    ap.add_argument("--form", default=DEFAULT_FORM)
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if bool(args.scaffold) == bool(args.check):
        die("pick exactly one: --scaffold <file> or --check <file>")
    target = args.scaffold or args.check
    require_within_cwd(target, "--scaffold/--check")
    require_within_cwd(args.form, "--form")
    path = Path(target)

    if path.suffix.lower() in MANUSCRIPT_SUFFIXES:
        die(f"{path.name} looks like the manuscript, not your notes about it. This "
            f"script never opens a manuscript under review: the paper was given to "
            f"you under a confidentiality undertaking, and there is no flag that "
            f"overrides it. Write your report as Markdown and point at that.")

    if args.scaffold:
        if path.exists():
            die(f"{target} already exists — refusing to overwrite a report in progress")
        write_text_atomic(path, SCAFFOLD)
        emit({"written": path.as_posix(),
              "next": ("read the paper yourself, fill this in, then: "
                       f"python scripts/referee_report.py --check {path.as_posix()}")},
             args.json_out)
        return

    if not path.is_file():
        die(f"{target} does not exist — python scripts/referee_report.py --scaffold {target}")
    result = check_report(path.read_text(encoding="utf-8", errors="replace"),
                          load_form(Path(args.form)))
    result["file"] = path.as_posix()
    emit(result, args.json_out)
    sys.exit(0 if result["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
