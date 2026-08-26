#!/usr/bin/env python3
"""overlap_check.py — where this manuscript repeats your OWN earlier text.

WHY THIS EXISTS
Text recycling is the one integrity question an author can answer without any
external service: does this manuscript reuse sentences from my own previous
papers, thesis chapters, or an earlier draft? Journals ask about it, ethics
committees ask about it, and the answer is usually "a little, in the methods
section, and that is fine" — but only if you know where.

WHAT THIS IS NOT — read before quoting anything it prints
It is **not a similarity score and not a plagiarism check**. POSITIONING.md
refuses those, and this does not sneak one in through the back door:

- It reports **locations, not a percentage.** There is no ratio in the output, by
  design. A percentage invites comparison with an institutional threshold it has
  no relationship to.
- It compares only against **files you point it at** — your own earlier work,
  offline. It searches nothing, and it cannot detect reuse of anyone else's text.
- It **does not replace your institution's tool** (Turnitin, iThenticate). Those
  compare against corpora this has no access to. A clean result here says one
  thing only: these files do not share long passages with these other files.

WHAT COUNTS AS AN OVERLAP
A shared window of N consecutive words (default 12), after normalisation. Short
matches are dropped because method sentences legitimately repeat: "All analyses
were performed in Python 3.11" is not recycling, and a tool that flagged it would
be ignored within a week — the same argument `tr_style_check.py` makes about
false alarms.

USAGE
  python scripts/overlap_check.py --against ../previous-paper/drafts
  python scripts/overlap_check.py --drafts drafts --against thesis-ch3.md --window 15

Exit codes: 0 no overlap above the window · 1 error · 2 overlapping passages found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit

_CITATION = re.compile(r"\[@[^\]]+\]")
_CODE = re.compile(r"```.*?```", re.DOTALL)


def normalise(text: str) -> list[str]:
    text = _CODE.sub(" ", text)
    text = _CITATION.sub(" ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s.*$", " ", text, flags=re.M)
    return re.findall(r"\b[\w'-]+\b", text.lower(), re.UNICODE)


def windows(words: list[str], n: int) -> dict[tuple[str, ...], int]:
    """Every n-word window with the index where it starts. First occurrence
    wins, so a phrase repeated inside one document reports one location."""
    out = {}
    for i in range(max(len(words) - n + 1, 0)):
        out.setdefault(tuple(words[i:i + n]), i)
    return out


def _collect(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*.md") if p.is_file())
    die(f"{target} does not exist")
    return []


def compare(new_files: list[Path], old_files: list[Path], n: int) -> dict:
    findings = []
    old_index: dict[tuple[str, ...], tuple[str, int]] = {}
    for path in old_files:
        for window, start in windows(normalise(
                path.read_text(encoding="utf-8", errors="replace")), n).items():
            old_index.setdefault(window, (path.as_posix(), start))

    for path in new_files:
        words = normalise(path.read_text(encoding="utf-8", errors="replace"))
        hits, i = [], 0
        while i <= len(words) - n:
            window = tuple(words[i:i + n])
            if window in old_index:
                # Extend the match as far as it goes, so one recycled paragraph
                # is one finding rather than forty overlapping windows.
                end = i + n
                source, source_start = old_index[window]
                while (end < len(words)
                       and tuple(words[end - n + 1:end + 1]) in old_index
                       and old_index[tuple(words[end - n + 1:end + 1])][0] == source):
                    end += 1
                hits.append({"words": end - i, "source": source,
                             "passage": " ".join(words[i:min(i + 25, end)]) +
                                        ("…" if end - i > 25 else "")})
                i = end
            else:
                i += 1
        if hits:
            findings.append({"file": path.as_posix(), "passages": hits})
    return {"result": "OVERLAP" if findings else "NONE", "window_words": n,
            "files_compared": len(new_files), "against": len(old_files),
            "findings": findings,
            "note": ("locations, not a score: there is no percentage here by design, "
                     "and this compares ONLY against the files you named. It is not a "
                     "plagiarism check and does not replace your institution's tool"),
            "reminder": ("reused methods text is often acceptable and sometimes "
                         "unavoidable; what matters is that you know where it is, cite "
                         "your earlier work, and follow the venue's text-recycling policy")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts", help="this manuscript")
    ap.add_argument("--against", required=True, action="append", metavar="PATH",
                    help="your OWN earlier file or directory (repeatable)")
    ap.add_argument("--window", type=int, default=12,
                    help="consecutive words that count as an overlap (default 12)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if args.window < 6:
        die(f"--window {args.window} is too small: at six words or fewer this reports "
            f"ordinary phrasing, and a check nobody believes is a check nobody runs")
    new_files = _collect(Path(args.drafts))
    if not new_files:
        die(f"{args.drafts} holds no markdown to compare")
    old_files = [p for target in args.against for p in _collect(Path(target))]
    if not old_files:
        die("--against matched no files")
    # Deliberately NOT require_within_cwd: your earlier papers live outside this
    # project, which is the whole point. Nothing is written, and nothing leaves
    # the machine — this is the one read the sandbox rule would only obstruct.
    new_resolved = {p.resolve() for p in new_files}
    old_files = [p for p in old_files if p.resolve() not in new_resolved]
    if not old_files:
        die("every --against file is also in --drafts — that compares the manuscript "
            "with itself")

    result = compare(new_files, old_files, args.window)
    emit(result, args.json_out)
    sys.exit(2 if result["result"] == "OVERLAP" else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
