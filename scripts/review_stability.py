#!/usr/bin/env python3
"""review_stability.py — how much the reviewer's judgment moves on one draft.

WHY THIS EXISTS
`/critique --calibrate` already dispatches `reviewer-critic` three times on the
same draft and reports how much the verdict varied. Until now that comparison
was done by the orchestrating model reading its own three reports — which is a
measurement of a model, produced by that model, with nothing deterministic
underneath it. Everything else the kit calls a measurement has a script behind
it; this is that script.

It reads the report format `/critique` already writes (`## MAJOR ISSUES`,
`## MINOR ISSUES`, `## DECISION` — the same headings `/submit-check`'s gate
string-matches) and compares, across N runs:

  decision       — Accept / Minor Revision / Major Revision / Reject
  issue counts   — how many Major and Minor issues each run raised
  flagged parts  — which sections the Major issues point at

WHAT IT CANNOT TELL YOU
Stability is not accuracy — the sentence `/critique` already prints, now bound to
a number. A reviewer that is consistently wrong scores 1.00 here, and a draft
whose real problems are genuinely ambiguous can score low while every run is
defensible. Low agreement is a reason to read all N reports rather than to
trust one; it is not a verdict about the draft, and no gate consumes it.

Accuracy needs papers whose outcome is already known — that is
`calibration_score.py --gold`, and the labels for it are the user's own.

USAGE
  python scripts/review_stability.py reviews/calibration/run-1.md run-2.md run-3.md
  python scripts/review_stability.py --strict --min 0.7 reviews/calibration/*.md

Exit codes: 0 ok · 1 error · 2 --strict and agreement fell below --min.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draft_stability import agreement
from lib_common import die, emit, require_within_cwd

# Ordered longest-first: "Major Revision" contains "Major", and a shorter
# pattern matched first would read every Major Revision as an Accept-adjacent
# verdict of its own.
DECISIONS = [
    ("Major Revision", re.compile(r"\bmajor\s+revisions?\b", re.I)),
    ("Minor Revision", re.compile(r"\bminor\s+revisions?\b", re.I)),
    ("Reject", re.compile(r"\breject\b", re.I)),
    ("Accept", re.compile(r"\baccept\b", re.I)),
]

# The section vocabulary a Major issue can point at, EN and TR. A fixed list,
# not free text: "the part about the sample" and "§3.2" are the same section
# under two descriptions, and matching prose would count them as two.
SECTIONS = {
    "abstract": ("abstract", "özet"),
    "introduction": ("introduction", "giriş"),
    "related work": ("related work", "literature review", "literatür"),
    "methods": ("methods", "method", "methodology", "yöntem", "materials and methods"),
    "results": ("results", "bulgular", "findings"),
    "discussion": ("discussion", "tartışma"),
    "conclusion": ("conclusion", "sonuç"),
    "limitations": ("limitations", "sınırlılıklar", "kısıtlar"),
    "references": ("references", "bibliography", "kaynakça"),
    "figures": ("figure", "table", "şekil", "tablo"),
    "ethics": ("ethics", "etik", "declaration"),
}

_HEADING = re.compile(r"^#{1,6}\s*(.+?)\s*$", re.M)
_ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.*)$", re.M)


def sections_of(text: str) -> dict[str, str]:
    """Report body keyed by heading, uppercased — the headings /critique writes."""
    out, current, buffer = {}, None, []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if current is not None:
                out[current] = "\n".join(buffer)
            current, buffer = m.group(1).strip().upper(), []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        out[current] = "\n".join(buffer)
    return out


def _named(body: dict[str, str], *wanted: str) -> str:
    for heading, text in body.items():
        if any(w in heading for w in wanted):
            return text
    return ""


def issues_in(block: str) -> list[str]:
    """Numbered or bulleted items. A report with neither has no countable
    issues — reported as zero and visible as such, never inferred from prose."""
    return [item.strip() for item in _ITEM.findall(block) if item.strip()]


def decision_in(block: str) -> str | None:
    for name, pattern in DECISIONS:
        if pattern.search(block):
            return name
    return None


def flagged_sections(issues: list[str]) -> tuple[set[str], int]:
    found, unattributed = set(), 0
    for issue in issues:
        lowered = issue.lower()
        hits = {canonical for canonical, aliases in SECTIONS.items()
                if any(alias in lowered for alias in aliases)}
        if hits:
            found |= hits
        else:
            unattributed += 1
    return found, unattributed


def read_report(text: str) -> dict:
    body = sections_of(text)
    major = issues_in(_named(body, "MAJOR"))
    minor = issues_in(_named(body, "MINOR"))
    decision_block = _named(body, "DECISION", "RECOMMENDATION")
    # Fall back to the whole report only when there is no decision heading at
    # all: a verdict stated in a summary line is still the verdict, but reading
    # the whole text FIRST would pick up the word "reject" from an issue
    # description and report it as the decision.
    decision = decision_in(decision_block) or (decision_in(text) if not decision_block else None)
    sections, unattributed = flagged_sections(major)
    return {"decision": decision, "major": len(major), "minor": len(minor),
            "sections": sections, "unattributed_major_issues": unattributed}


def compare(texts: list[str]) -> dict:
    reports = [read_report(t) for t in texts]
    decisions = [r["decision"] for r in reports]
    known = [d for d in decisions if d]
    modal = max(set(known), key=known.count) if known else None
    decision_agreement = (known.count(modal) / len(decisions)) if modal else 0.0

    section_score, section_unstable = agreement([r["sections"] for r in reports])
    majors = [r["major"] for r in reports]
    return {
        "runs": len(reports),
        "decision": {
            "per_run": decisions,
            "modal": modal,
            "agreement": round(decision_agreement, 4),
            "unanimous": bool(modal) and len(set(decisions)) == 1,
        },
        "major_issues": {"per_run": majors, "min": min(majors), "max": max(majors),
                         "note": ("treat any single run's Major count as a lower "
                                  "bound, not a precise figure")},
        "minor_issues": {"per_run": [r["minor"] for r in reports]},
        "flagged_sections": {"agreement": round(section_score, 4),
                             "unstable": section_unstable,
                             "unattributed_per_run":
                                 [r["unattributed_major_issues"] for r in reports]},
        "lowest_agreement": round(min(decision_agreement, section_score), 4),
        "note": ("stability, not accuracy: a reviewer that is consistently wrong "
                 "scores 1.00 here, and low agreement is a reason to read all "
                 "runs rather than a verdict about the draft"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="*", help="2+ independent review reports of ONE draft")
    ap.add_argument("--min", type=float, default=0.67,
                    help="with --strict: the agreement floor (default 0.67 — two "
                         "of three runs agreeing is the weakest result still worth "
                         "acting on without reading every report)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 when the lowest agreement falls below --min")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if len(args.runs) < 2:
        die("give at least 2 review reports — stability is a property of a set of "
            "runs, and one review has none")
    texts = []
    for rel in args.runs:
        require_within_cwd(rel, "runs")
        p = Path(rel)
        if not p.is_file():
            die(f"{rel} does not exist")
        texts.append(p.read_text(encoding="utf-8", errors="replace"))

    result = compare(texts)
    result["files"] = [Path(r).as_posix() for r in args.runs]
    if not any(result["decision"]["per_run"]):
        die("no report states a decision — is this /critique's output? "
            "(expected a '## DECISION' section naming Accept / Minor Revision / "
            "Major Revision / Reject)")
    emit(result, args.json_out)
    if args.strict and result["lowest_agreement"] < args.min:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a review report — {e}")
    except UnicodeDecodeError as e:
        die(f"a review report is not valid UTF-8 — {e}")
