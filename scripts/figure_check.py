#!/usr/bin/env python3
"""figure_check.py — figure/table existence, numbering, and caption lint for drafts/.

Figure numbering is currently entirely manual (the orchestrator hand-tracks it
across sections) and nothing catches a "Figure 5" prose mention with no such
figure embedded, a figure embedded but never discussed, a number reused twice,
or a gap in the sequence. This script makes those checks deterministic.

Conventions detected (matching how format-engineer/docx-output expect figures
and how data-scientist captions its own outputs — see those skills/agents):
  * An embedded figure is a markdown image whose alt text starts with the
    caption: `![Figure 4. Two-panel forest plot...](../analysis/figures/x.png)`
  * An embedded table is a bold caption line: `**Table 3. Pairwise Spearman...**`
    (tables are usually not images; the caption line IS the "embedded table").
  * A prose mention is any other "Figure N" / "Table N" text (including a
    "Figures 4-9" range), found OUTSIDE the caption lines above.
  * `analysis/captions.md`'s own "## Figure: `path`" / "## Table: `path`"
    headers (the data-scientist's scratch caption drafts) are cross-checked by
    file basename against embedded figures — this catches a figure the
    data-scientist produced but that never made it into any draft at all.

Sub-labels like "Table 1a" are supported (kept as their own label, not folded
into "1"); sequence-gap detection operates on the base integer only.

ORDER, NOT JUST PRESENCE. A complete, gapless, uniquely-numbered set can still
be numbered wrongly: "Table 7b" printed before "Table 6", or a lettered "Table A"
sitting between 8 and 10. Nothing above catches that, because every one of those
checks is order-blind — and a reader who meets Table 12 before Table 7 stops
trusting the numbering, which is the only thing table numbers are for.
`out_of_order` reports a caption whose base number is lower than one already
printed earlier in the SAME file.

Same file, deliberately. Reading order across files is NOT checked and cannot
be: `drafts/` is scanned in filename order, which for any real manuscript
(ozet, abstract, introduction, methods, synthesis, discussion, conclusion,
appendices) is not reading order, and the kit has no manifest that states what
reading order is. Guessing one would produce confident false positives on every
project whose section files are named differently. Within a file the order is
unambiguous, and in practice that is where the numbering drifts, because that is
where captions get inserted.

Report-only by default (never blocks) — a human adjudicates whether a flagged
item is real. `--strict` opts into blocking (exit 2 on any warning).

Usage:
  python scripts/figure_check.py [--drafts drafts/] [--captions analysis/captions.md] [--json]
  python scripts/figure_check.py --strict
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# \n excluded — see cite_audit.py: `[^`]*` spans paragraphs and two stray
# backticks silently hide every figure/table mention between them.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# HTML comments are the kit's evidence-binding and RQ-tagging syntax, so drafts
# are full of them by instruction, and reviewers write notes in them too. A
# "bkz. Şekil 9" inside one is not a mention the manuscript makes: counted as
# one it invents a missing figure and reports the author a warning about prose
# no reader will ever see. Replaced with a space so a comment sitting between
# two words cannot fuse them into a new one.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Turkish is accepted everywhere English is. The kit's default output language is
# Turkish (PROJECT.md), and a check that only knows "Figure N"/"Table N" reported
# a clean bill on a Turkish manuscript because it could not see a single figure
# or table in it — the worst failure mode available to a linter, since silence
# reads as "checked and fine". "Şekil"/"Tablo" also appear ASCII-folded (Sekil,
# Cizelge) in practice, and "Çizelge" is the standard word for a table in a large
# part of the Turkish engineering literature.
_FIG_WORD = r"(?:Figures?|[SŞ]ekil(?:ler)?)"
_TAB_WORD = r"(?:Tables?|Tablo(?:lar)?|[CÇ]izelge(?:ler)?)"
# A Turkish mention carries a case suffix — "Şekil 3'te", "Tablo 1'de", "Şekil 2'deki"
# — so the number cannot be followed by a word boundary alone.
_NUM_END = r"(?![\d])"

IMAGE_FIG_RE = re.compile(
    rf"!\[\s*{_FIG_WORD}\s+(?P<num>\d+[A-Za-z]?)\.\s*[^\]]*\]\((?P<path>[^)]+)\)")
BOLD_TABLE_RE = re.compile(
    rf"^[ \t]*\*\*{_TAB_WORD}\s+(?P<num>\d+[A-Za-z]?)\.\s*[^*]*\*\*", re.MULTILINE)

MENTION_RANGE_RE = {
    "figure": re.compile(rf"\b{_FIG_WORD}\s+(\d+)\s*[-–]\s*(\d+)\b"),
    "table": re.compile(rf"\b{_TAB_WORD}\s+(\d+)\s*[-–]\s*(\d+)\b"),
}
MENTION_SINGLE_RE = {
    "figure": re.compile(rf"\b{_FIG_WORD}\s+(\d+[A-Za-z]?){_NUM_END}"),
    "table": re.compile(rf"\b{_TAB_WORD}\s+(\d+[A-Za-z]?){_NUM_END}"),
}

CAPTIONS_HEADER_RE = re.compile(
    rf"^##\s+({_FIG_WORD}|{_TAB_WORD}):\s*`([^`]+)`", re.MULTILINE)


def _clean(text: str) -> str:
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", COMMENT_RE.sub(" ", text)))


def _base_int(label: str) -> int:
    m = re.match(r"(\d+)", label)
    return int(m.group(1)) if m else -1


def _blank_span(text: str, start: int, end: int) -> str:
    """Replace a matched caption span with spaces of the same length (preserving
    newlines), so its own "Figure N"/"Table N" text is excised from prose-mention
    scanning without shifting any other match's character offsets."""
    span = text[start:end]
    return "".join(c if c == "\n" else " " for c in span)


def _mentions(prose: str, kind: str) -> tuple[set[str], list[dict]]:
    out = set()
    degenerate = []
    for m in MENTION_RANGE_RE[kind].finditer(prose):
        lo, hi = int(m.group(1)), int(m.group(2))
        if hi > lo:
            out.update(str(n) for n in range(lo, hi + 1))
        else:
            # "Table 7-7" or "Table 8-6". The old code dropped these silently,
            # which made a broken range the ONE kind of dangling reference the
            # script could not see: it contributes no mention, so nothing is
            # ever reported missing for it. That blind spot is not theoretical
            # — a global renumbering pass turns "Table 6-7" into "Table 7-7"
            # while every per-number count still reconciles.
            degenerate.append({
                "text": m.group(0), "from": lo, "to": hi,
                "msg": (f"{m.group(0)!r} is not a range"
                        + (" (both ends are the same number)" if hi == lo
                           else " (it counts downwards)"))})
    # Blank out range matches before single-mention scanning so a "Figures 4-9"
    # range doesn't ALSO register a spurious single mention of "4".
    prose_no_ranges = MENTION_RANGE_RE[kind].sub(
        lambda m: " " * len(m.group(0)), prose)
    for m in MENTION_SINGLE_RE[kind].finditer(prose_no_ranges):
        out.add(m.group(1))
    return out, degenerate


def _analyze_kind(files_text: dict[str, str], kind: str, embed_re: "re.Pattern") -> dict:
    embedded: dict[str, list[dict]] = {}
    prose_by_file: dict[str, str] = {}

    in_file_order: dict[str, list[str]] = {}

    for fname, text in files_text.items():
        clean = _clean(text)
        prose = clean
        for m in embed_re.finditer(clean):
            num = m.group("num")
            path = m.groupdict().get("path")
            entry = {"file": fname, "num": num}
            if path:
                entry["path"] = path
            embedded.setdefault(num, []).append(entry)
            # finditer yields matches in position order, so appending here IS
            # document order within this file — no separate sort needed.
            in_file_order.setdefault(fname, []).append(num)
            prose = prose[:m.start()] + _blank_span(prose, m.start(), m.end()) + prose[m.end():]
        prose_by_file[fname] = prose

    mentioned: set[str] = set()
    degenerate_ranges: list[dict] = []
    for fname, prose in prose_by_file.items():
        found, degen = _mentions(prose, kind)
        mentioned |= found
        for d in degen:
            degenerate_ranges.append({"file": fname, **d})

    embedded_nums = set(embedded)
    missing = sorted(mentioned - embedded_nums, key=_base_int)
    orphaned = sorted(embedded_nums - mentioned, key=_base_int)
    duplicates = [{"num": n, "locations": v} for n, v in embedded.items() if len(v) > 1]

    base_ints = sorted({_base_int(n) for n in embedded_nums if _base_int(n) > 0})
    gaps = []
    if base_ints:
        gaps = [n for n in range(base_ints[0], base_ints[-1] + 1) if n not in base_ints]

    out_of_order = []
    for fname, labels in in_file_order.items():
        # A caption is out of order when its base number is BELOW the highest
        # already printed in this file. Comparing against the running maximum
        # rather than the previous label keeps one displaced caption from
        # reporting every caption after it: "7b before 6" is one finding, not
        # a cascade.
        peak_label, peak = None, None
        for label in labels:
            n = _base_int(label)
            if n < 0:
                continue
            if peak is not None and n < peak:
                out_of_order.append(
                    {"file": fname, "label": label, "after": peak_label,
                     "msg": f"{label} is printed after {peak_label} in {fname}"})
            elif peak is None or n > peak:
                peak, peak_label = n, label

    return {
        "embedded_count": len(embedded_nums),
        "mentioned_count": len(mentioned),
        "missing": missing,
        "orphaned": orphaned,
        "duplicate_numbers": duplicates,
        "sequence_gaps": gaps,
        "out_of_order": out_of_order,
        "degenerate_ranges": degenerate_ranges,
        "_embedded": embedded,
    }


def _captions_md_paths(captions_path: Path) -> dict[str, set[str]]:
    """{'Figure': {basenames...}, 'Table': {basenames...}} from analysis/captions.md
    headers like "## Figure: `figures/class_balance.pdf` / `.png`" — the regex
    captures only the first backtick-quoted token (the real path); the trailing
    "/ `.png`" is a second, separately-quoted alternate-extension note that is not
    captured and is not needed (matching by stem is extension-agnostic already)."""
    out = {"Figure": set(), "Table": set()}
    if not captions_path.exists():
        return out
    text = captions_path.read_text(encoding="utf-8", errors="replace")
    for m in CAPTIONS_HEADER_RE.finditer(text):
        kind, path = m.group(1), m.group(2)
        out[kind].add(Path(path.strip()).stem)
    return out


def check(drafts_dir: Path, captions_path: Path) -> dict:
    files = (sorted(p for p in drafts_dir.glob("**/*.md") if p.name != "STATUS.md")
             if drafts_dir.exists() else [])
    files_text = {f.as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in files}

    fig = _analyze_kind(files_text, "figure", IMAGE_FIG_RE)
    tab = _analyze_kind(files_text, "table", BOLD_TABLE_RE)

    # Cross-check embedded figure image paths against analysis/captions.md by
    # basename (extension-agnostic: captions.md often lists "file.pdf / .png").
    cap_names = _captions_md_paths(captions_path)
    embedded_fig_basenames = {
        Path(loc["path"]).stem: num
        for num, locs in fig["_embedded"].items() for loc in locs if "path" in loc
    }
    uncaptioned_figures = sorted(
        f"Figure {num} ({stem})" for stem, num in embedded_fig_basenames.items()
        if cap_names["Figure"] and stem not in cap_names["Figure"]
    ) if captions_path.exists() else []

    fig.pop("_embedded")
    tab.pop("_embedded")

    warnings = (len(fig["missing"]) + len(fig["orphaned"]) + len(fig["duplicate_numbers"])
                + len(fig["sequence_gaps"]) + len(fig["out_of_order"])
                + len(tab["missing"]) + len(tab["orphaned"])
                + len(fig["degenerate_ranges"])
                + len(tab["duplicate_numbers"]) + len(tab["sequence_gaps"])
                + len(tab["out_of_order"]) + len(tab["degenerate_ranges"])
                + len(uncaptioned_figures))

    return {
        "files_scanned": [f.as_posix() for f in files],
        "figures": fig,
        "tables": tab,
        "uncaptioned_figures": uncaptioned_figures,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--captions", default="analysis/captions.md")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.drafts, "--drafts")
    require_within_cwd(args.captions, "--captions")
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    result = check(Path(args.drafts), Path(args.captions))
    emit(result, True)
    sys.exit(2 if (args.strict and result["warnings"]) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"a draft file is not valid UTF-8 — {e}")
