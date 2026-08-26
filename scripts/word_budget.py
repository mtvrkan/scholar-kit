#!/usr/bin/env python3
"""word_budget.py — per-section word counts vs budget; --rq-trace audits RQ↔heading mapping.

Budget source: PROJECT.md "Word budget (total)" plus optional per-section overrides.
Default proportions by paper type (from paper-types skill):
  imrad-like:      intro 15% · methods 25% · results 25% · discussion 30% · conclusion 5%
  review-like:     intro 15% · methods 20% · synthesis 45% · discussion 15% · conclusion 5%
Sections are matched to drafts/<section>.md by filename (intro→introduction.md etc.).

Usage:
  python scripts/word_budget.py [--project PROJECT.md] [--drafts drafts/] [--json]
  python scripts/word_budget.py --rq-trace [--outline outline/outline.md]
Exit codes: 0 within ±10% or info · 2 any section >±10% off budget (only with --strict).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

PROPORTIONS = {
    "imrad": {"introduction": .15, "methods": .25, "results": .25, "discussion": .30, "conclusion": .05},
    "review": {"introduction": .15, "methods": .20, "synthesis": .45, "discussion": .15, "conclusion": .05},
}
ALIASES = {"intro": "introduction", "method": "methods", "methodology": "methods",
           "result": "results", "findings": "results", "related-work": "introduction"}


def read_project(path: Path) -> dict:
    if not path.exists():
        die(f"{path} not found — run /new-project first")
    text = path.read_text(encoding="utf-8")
    total = None
    # Capture the WHOLE value token (\S+, horizontal-space-delimited so it never
    # crosses a newline into the next line), not just its leading [\d,.] run: an
    # earlier `([\d,.]+)` capture stopped at the first non-digit, so "12x34"
    # silently truncated to a valid-looking budget of 12 (and a negative like
    # "-5000" matched nothing at all and fell back to null) — the exact
    # silently-degrading behavior the fail-loud check below exists to prevent.
    m = re.search(r"Word budget \(total\):\*{0,2}[^\S\n]*(\S+)", text)
    if m:
        # The line IS present — malformed input, not an absent budget, so fail
        # loudly rather than silently degrading to "budget_total": null (which
        # masks the break: every section's deviation_pct reads as None and
        # off_budget never fires). Surrounding ** bold markers are tolerated.
        raw = m.group(1).strip("*")
        # A trailing ".d" or ".dd" (e.g. "12,000.50", "12000.5") is an
        # unambiguous DECIMAL suffix, not thousands-grouping — a word count
        # can't have a fractional part, so this is a genuinely invalid value,
        # not just a formatting variant. Reject it explicitly: the blanket
        # strip-both-separators below would otherwise silently collapse
        # "12,000.50" into "1200050" (100x the real value) by treating the
        # decimal point as if it were a third thousands-group separator.
        if re.search(r"\.\d{1,2}$", raw):
            die(f"{path}: \"Word budget (total):\" value '{m.group(1)}' looks like a "
                f"decimal — a word count must be a whole number")
        cleaned = re.sub(r"[,.]", "", raw)
        if not cleaned.isdigit():
            die(f"{path}: \"Word budget (total):\" value '{m.group(1)}' is not a valid number")
        total = int(cleaned)
    tm = re.search(r"\*\*Type:\*\*\s*([\w-]+)", text)
    ptype = tm.group(1).lower() if tm else "TBD"
    rqs = re.findall(r"^\s*[-*]\s*(RQ\d+)\s*:\s*(.+)$", text, re.MULTILINE)
    return {"total": total, "type": ptype, "rqs": rqs}


def count_words(text: str) -> int:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # An odd number of ``` markers means the last fence was never closed (a
    # plausible typo) — the non-greedy pair-matching above leaves everything
    # from that unclosed fence to EOF untouched, silently counting code as
    # prose. Treat it the same as a closed fence: drop to EOF.
    if text.count("```") % 2 == 1:
        text = re.sub(r"```.*\Z", "", text, flags=re.DOTALL)
    # HTML comments: the kit's own evidence-binding syntax (`<!-- EV-0045 -->`),
    # RQ tags, and author notes. A draft that follows /draft carries one per
    # empirical claim, so counting them charges the author for text no reader
    # sees — against a limit the venue enforces on what it publishes. Dropped
    # before headings so a heading commented out is not counted either.
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"^\s{0,3}#{1,6}\s.*$", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)                     # images
    text = re.sub(r"\[@[^\]]+\]", "", text)                              # citations
    # A number carrying an internal separator is ONE word to every counter an
    # author is measured by — Word, a portal's field, a copy editor. `\w` does
    # not contain "." or ",", so a bare `[\w'-]+` pass splits "0,940" into "0"
    # and "940" and "1.572" into "1" and "572": every decimal and every
    # thousands-separated figure is charged twice. In a results-heavy abstract
    # that is tens of words of pure measurement error, all of it against a
    # venue limit. Matched first so the separator is consumed before the
    # general word alternative can break the number apart.
    return len(re.findall(r"\d+(?:[.,]\d+)+|[\w'-]+", text, re.UNICODE))


def section_of(fname: str) -> str:
    stem = Path(fname).stem.lower()
    return ALIASES.get(stem, stem)


def cmd_budget(args):
    proj = read_project(Path(args.project))
    kind = "review" if "review" in proj["type"] else "imrad"
    props = PROPORTIONS[kind]
    rows, total_written = [], 0
    for f in sorted(Path(args.drafts).glob("*.md")):
        if f.name == "STATUS.md":
            continue
        words = count_words(f.read_text(encoding="utf-8", errors="replace"))
        total_written += words
        section = section_of(f.name)
        budget = round(proj["total"] * props[section]) if proj["total"] and section in props else None
        dev = round(100 * (words - budget) / budget, 1) if budget else None
        rows.append({"file": f.name, "section": section, "words": words,
                     "budget": budget, "deviation_pct": dev})
    over = [r for r in rows if r["deviation_pct"] is not None and abs(r["deviation_pct"]) > 10]
    emit({"type": proj["type"], "budget_total": proj["total"], "written_total": total_written,
          "sections": rows, "off_budget": [r["file"] for r in over]}, args.json_out)
    sys.exit(2 if (args.strict and over) else 0)


def cmd_rq_trace(args):
    proj = read_project(Path(args.project))
    if not proj["rqs"]:
        die("no RQs found in PROJECT.md (expect lines like '- RQ1: ...')")
    targets = []
    outline = Path(args.outline)
    if outline.exists():
        targets.append(("outline", outline.read_text(encoding="utf-8", errors="replace")))
    for f in sorted(Path(args.drafts).glob("*.md")):
        if f.name != "STATUS.md":
            targets.append((f.name, f.read_text(encoding="utf-8", errors="replace")))
    if not targets:
        die("nothing to trace — no outline or drafts yet")
    report = []
    for rq_id, rq_text in proj["rqs"]:
        hits = []
        rq_pattern = re.compile(rf"\b{re.escape(rq_id.lower())}\b")
        for name, text in targets:
            for line in text.splitlines():
                # Word-boundary match: plain substring containment made "rq1"
                # match inside "rq10"/"rq11"/... for any project with >= 10
                # RQs, falsely marking RQ1 "traced" from a line that only
                # ever mentions RQ10.
                if rq_pattern.search(line.lower()):
                    hits.append({"where": name, "line": line.strip()[:120]})
        report.append({"rq": rq_id, "text": rq_text[:120], "mentions": len(hits), "hits": hits[:10],
                       "status": "traced" if hits else "UNTRACED"})
    untraced = [r["rq"] for r in report if r["status"] == "UNTRACED"]
    emit({"rqs": report, "untraced": untraced}, args.json_out)
    sys.exit(2 if untraced else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--outline", default="outline/outline.md")
    ap.add_argument("--rq-trace", dest="rq_trace", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 2 when any section is >±10%% off budget")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.project, "--project")
    require_within_cwd(args.drafts, "--drafts")
    require_within_cwd(args.outline, "--outline")
    if args.rq_trace:
        cmd_rq_trace(args)
    else:
        cmd_budget(args)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a project file — {e}")
    except UnicodeDecodeError as e:
        die(f"a project file is not valid UTF-8 — {e}")
