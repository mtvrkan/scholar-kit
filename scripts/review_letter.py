#!/usr/bin/env python3
"""review_letter.py — a real decision letter, parsed; and a response, checked for coverage.

WHY THIS EXISTS
The kit could simulate a review (`/critique`) and work through its own findings
(`/revise`). What it could not take was the document an author actually receives:
an editor's decision letter with three reviewers and forty numbered comments,
where the work is not "what should I fix" but "have I answered every single one,
and can the editor see that I have".

Editors check exactly one thing mechanically before reading the science: is there
a response to every comment. An unanswered comment reads as an evaded comment,
and it is the most common reason a revision goes back for a second round on
process rather than on substance.

  --parse    the letter → a structured list of comments (reviewer, number, text)
  --coverage the response letter vs that list → answered, missing, or invented

WHAT IT REFUSES
- **To judge whether a response is adequate.** It checks that each comment is
  addressed somewhere, by its number, and that no response answers a comment the
  letter never made. Whether the answer satisfies the reviewer is a scientific
  judgement and belongs to the author and, ultimately, the reviewer.
- **To infer structure that is not there.** A letter with no reviewer headings and
  no numbering is reported as ONE block per reviewer rather than split on
  paragraphs — a false split produces phantom comments and a coverage number that
  means nothing.
- **To rewrite the letter.** It never edits the input. Reviewer text is quoted in
  the response by the author (or by `/respond-review`), never paraphrased by this
  script.

USAGE
  python scripts/review_letter.py --parse reviews/decision-letter.md
  python scripts/review_letter.py --parse reviews/decision-letter.md \\
      --coverage reviews/response-r1.md

Exit codes: 0 every comment answered · 1 error · 2 comments unanswered (or the
response answers something the letter never asked).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

# "Reviewer 2", "REVIEWER #2", "Hakem 2", "Referee 2", "R2:" — the shapes a real
# letter uses. Deliberately anchored to a line start: "as reviewer 2 noted" in
# the middle of a paragraph is a reference to a reviewer, not a new section.
_REVIEWER_RE = re.compile(
    r"^\s{0,3}(?:#{1,4}\s*)?(?:\*{0,2})"
    r"(?:reviewer|referee|hakem|reviewer's report)\s*#?\s*(\d+)|^\s{0,3}R(\d+)\s*[:.]",
    re.I | re.M)
# "1.", "1)", "(1)", "Comment 1:", "1.4"
#
# A flat number MUST carry a separator; a hierarchical one (1.4) need not. That
# asymmetry is deliberate: "2020 studies were screened" starts a real sentence in
# a real letter and would otherwise become comment 2020, while "1.4 The sample…"
# is numbering in every letter that uses it and almost never prose.
_COMMENT_RE = re.compile(
    r"^\s{0,3}\*{0,2}(?:comment|yorum|madde)?\s*"
    r"(?:\((\d+(?:\.\d+)*)\)|(\d+(?:\.\d+)*)\s*[.):\-]|(\d+\.\d+))"
    r"\s+(.+)$", re.I | re.M)


_EDITOR_RE = re.compile(r"^\s{0,3}(?:#{1,4}\s*)?(?:\*{0,2})(?:editor|editör|associate editor)",
                        re.I | re.M)


def _number_of(match: re.Match) -> str:
    return match.group(1) or match.group(2) or match.group(3)


def parse_letter(text: str) -> dict:
    """Split into reviewer blocks, then into numbered comments.

    Two-stage on purpose: comment numbering restarts per reviewer in nearly every
    real letter, so a flat numbering pass produces four different comments all
    called "1" and a coverage check that cannot distinguish them.
    """
    marks = []
    for m in _REVIEWER_RE.finditer(text):
        number = m.group(1) or m.group(2)
        marks.append((m.start(), f"Reviewer {number}"))
    for m in _EDITOR_RE.finditer(text):
        marks.append((m.start(), "Editor"))
    marks.sort()

    blocks = []
    if not marks:
        # No reviewer headings at all: one block. Splitting on paragraphs here
        # would invent comments, and a coverage percentage over invented
        # comments is worse than no percentage.
        blocks.append(("Reviewer 1", text))
    else:
        if marks[0][0] > 0 and text[:marks[0][0]].strip():
            blocks.append(("Editor", text[:marks[0][0]]))
        for i, (pos, who) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            blocks.append((who, text[pos:end]))

    comments, seen = [], set()
    for who, body in blocks:
        found = list(_COMMENT_RE.finditer(body))
        for m in found:
            number = _number_of(m)
            label = f"{who}.{number}"
            if label in seen:      # a repeated number inside one block: keep the first
                continue
            seen.add(label)
            comments.append({"reviewer": who, "number": number, "id": label,
                             "text": m.group(4).strip()[:400]})
        if not found and body.strip():
            label = f"{who}.unnumbered"
            if label not in seen:
                seen.add(label)
                comments.append({"reviewer": who, "number": "unnumbered", "id": label,
                                 "text": " ".join(body.split())[:400],
                                 "note": "no numbering found in this block — treated as "
                                         "one comment rather than split on paragraphs"})
    return {"reviewers": sorted({c["reviewer"] for c in comments}),
            "comments": comments, "count": len(comments)}


def coverage(comments: list[dict], response: str) -> dict:
    """Which comment ids the response actually addresses.

    Matching is on the id as the author writes it — "R2.3", "Reviewer 2, Comment 3",
    "2.3" under a "Reviewer 2" heading — not on wording similarity: a response that
    happens to repeat a reviewer's phrasing is not evidence that it answers it.
    """
    answered, missing = [], []
    blocks = {}
    for m in _REVIEWER_RE.finditer(response):
        number = m.group(1) or m.group(2)
        blocks[m.start()] = f"Reviewer {number}"
    positions = sorted(blocks)

    def block_at(index: int) -> str | None:
        current = None
        for pos in positions:
            if pos <= index:
                current = blocks[pos]
            else:
                break
        return current

    for comment in comments:
        who, number = comment["reviewer"], comment["number"]
        if number == "unnumbered":
            # A HEADING for that reviewer, not a mention of them. "We thank the
            # editor and both reviewers" is a courtesy line, and counting it as
            # an answer to the editor's own requests is the kind of false
            # positive that makes a coverage number worse than none.
            hit = bool(re.search(rf"^\s{{0,3}}(?:#{{1,4}}\s*)?\*{{0,2}}{re.escape(who)}\b",
                                 response, re.I | re.M))
        else:
            escaped = re.escape(number)
            short = re.escape(who.replace("Reviewer ", "R"))
            hit = bool(re.search(rf"\b{short}\s*[.\-–]\s*{escaped}\b", response, re.I))
            if not hit:
                # A bare "3." inside the response's own "Reviewer 2" section.
                for m in re.finditer(rf"^\s{{0,3}}\(?{escaped}\)?\s*[.):-]", response, re.M):
                    if block_at(m.start()) == who:
                        hit = True
                        break
        (answered if hit else missing).append(comment["id"])

    # The inverse error: a response section for a comment the letter never made.
    # Usually a mis-numbered response, occasionally a comment pasted from the
    # wrong review — either way the editor sees an answer to a question nobody
    # asked, which reads worse than a gap.
    known = {c["id"] for c in comments}
    invented = []
    for m in re.finditer(r"\bR(\d+)\s*[.\-–]\s*((?:\d+\.)?\d+)\b", response, re.I):
        label = f"Reviewer {m.group(1)}.{m.group(2)}"
        if label not in known and label not in invented:
            invented.append(label)

    return {"answered": answered, "missing": missing, "unmatched_in_response": invented,
            "answered_count": len(answered), "total": len(comments),
            "note": ("matched on comment NUMBERS, not on wording: a response that "
                     "repeats a reviewer's phrasing is not evidence that it answers "
                     "it. Whether an answer is adequate is not checked here at all")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parse", required=True, metavar="LETTER",
                    help="the decision letter, as text/markdown")
    ap.add_argument("--coverage", metavar="RESPONSE",
                    help="the response letter to check against it")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.parse, "--parse")
    letter = Path(args.parse)
    if not letter.is_file():
        die(f"{args.parse} does not exist — save the editor's letter there first "
            f"(paste it into a .md file; a PDF must be converted with pdf2md.py)")
    parsed = parse_letter(letter.read_text(encoding="utf-8", errors="replace"))
    if not parsed["comments"]:
        die(f"{args.parse} yielded no comments — is this the decision letter?")

    result = {"letter": letter.as_posix(), **parsed}
    if args.coverage:
        require_within_cwd(args.coverage, "--coverage")
        response = Path(args.coverage)
        if not response.is_file():
            die(f"{args.coverage} does not exist")
        result["coverage"] = coverage(
            parsed["comments"], response.read_text(encoding="utf-8", errors="replace"))
        result["response"] = response.as_posix()

    emit(result, args.json_out)
    if args.coverage:
        cov = result["coverage"]
        sys.exit(2 if cov["missing"] or cov["unmatched_in_response"] else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"the letter is not valid UTF-8 — {e}")
