#!/usr/bin/env python3
"""cite_audit.py — cross-diff in-text pandoc citations [@key] against bib/references.bib.

Reports:
  * missing: cited in drafts but absent from the .bib (blocks finalization)
  * orphans: present in the .bib but never cited (information only)
  * placeholders: literal [CITATION NEEDED] tags still in the text
  * material_gaps: literal [MATERIAL GAP] tags still in the text
  * llm_supplemented: literal [LLM-SUPPLEMENTED] tags (reported, never blocks)
  * unverified_cited: cited entries lacking verified={true}

The three tags mark different states and must not be collapsed into one:
  [CITATION NEEDED]  — the claim is fine, a source for it has not been attached.
  [MATERIAL GAP]     — no session material covers this at all, and the writer
                       REFUSED to fill it from model memory. Both of these are
                       holes in a finished manuscript, so both block.
  [LLM-SUPPLEMENTED] — the author explicitly authorized filling a gap from model
                       knowledge. That is a legitimate choice, so it never
                       blocks — but it is exactly what a reviewer needs to see,
                       so it is always reported rather than passed over in
                       silence. An authorized fill that leaves no trace is
                       indistinguishable from an unauthorized one.

Usage:
  python scripts/cite_audit.py [--drafts drafts/] [--bib bib/references.bib] [--json]
  python scripts/cite_audit.py --quick --file drafts/methods.md    # hook mode: one file, terse
Exit codes: 0 clean · 1 error · 2 missing keys or placeholders found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, parse_bibtex, require_within_cwd

# pandoc citation keys: @key inside brackets or bare @key (letters/digits/some punctuation)
CITE_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_:.#$%&+?<>~/-]*[A-Za-z0-9])")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# `[^`]*` — without the \n exclusion — spans paragraphs: two stray backticks
# anywhere in a document (a unit written as 5`, a quoted keystroke) pair up and
# swallow everything between them, INCLUDING every [@key] in that span. In this
# module that is a false NEGATIVE in the blocking check: keys silently vanish
# from `cited`, so a citation with no bibliography entry is never reported as
# missing and the gate passes a manuscript it should have stopped. A code span
# is a single-line construct; `tr_style_check.py` already had it right.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# An HTML comment is not prose. The four siblings of this check — claim_check,
# figure_check, tr_style_check, word_budget — all read one as text until it was
# fixed, and this one was never tested either way. It matters more here than it
# sounds: the kit's own evidence binding IS an HTML comment (`<!-- EV-0045 -->`),
# so every draft written the way /draft asks is full of them, and a paragraph
# commented out during revision stays in the file on purpose.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\[CITATION NEEDED\]", re.IGNORECASE)
MATERIAL_GAP_RE = re.compile(r"\[MATERIAL GAP\]|\[KANIT YOK\]", re.IGNORECASE)
LLM_SUPPLEMENTED_RE = re.compile(r"\[LLM-?SUPPLEMENTED\]|\[MODEL BİLGİSİ\]", re.IGNORECASE)


def extract_citations(text: str) -> set[str]:
    text = FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    text = COMMENT_RE.sub("", text)
    # drop emails (word@domain) — require @ not preceded by a word char
    return {m.group(1) for m in CITE_RE.finditer(text)
            if m.start() == 0 or not text[m.start() - 1].isalnum()}


def check(drafts_dir: Path, bib_path: Path, single_file: Path | None = None) -> dict:
    """The audit itself, independent of argv and of exit codes.

    Extracted from main() so the gold-set harness (`scripts/run_evals.py`) can
    measure this checker the way it measures the others. main() keeps every
    argument-validation and exit-code decision — those are CLI concerns and the
    tests that pin them still exercise the CLI, not this function.
    """
    bib_entries = (parse_bibtex(bib_path.read_text(encoding="utf-8"))
                   if bib_path.exists() else [])
    bib_keys = {e["key"] for e in bib_entries}
    unverified = {e["key"] for e in bib_entries
                  if e["fields"].get("verified", "").lower() != "true"}

    files = [single_file] if single_file else sorted(drafts_dir.glob("**/*.md"))
    files = [f for f in files if f.exists() and f.name != "STATUS.md"]
    cited, placeholders, material_gaps, llm_supplemented = set(), [], [], []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        cited |= extract_citations(text)
        for i, line in enumerate(text.splitlines(), 1):
            where = f"{f.as_posix()}:{i}"
            if PLACEHOLDER_RE.search(line):
                placeholders.append(where)
            if MATERIAL_GAP_RE.search(line):
                material_gaps.append(where)
            if LLM_SUPPLEMENTED_RE.search(line):
                llm_supplemented.append(where)

    return {"files_scanned": [f.as_posix() for f in files],
            "cited": len(cited), "bib_entries": len(bib_keys),
            "missing": sorted(cited - bib_keys),
            "orphans": sorted(bib_keys - cited),
            "placeholders": placeholders,
            "material_gaps": material_gaps,
            "llm_supplemented": llm_supplemented,
            "unverified_cited": sorted(cited & unverified)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--file", help="audit a single file (hook mode)")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--quick", action="store_true", help="terse one-line output for hooks; never blocks")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.bib, "--bib")
    require_within_cwd(args.drafts, "--drafts")
    if args.file:
        require_within_cwd(args.file, "--file")
    # A wrong --file / --drafts path used to yield files_scanned=[], 0 missing,
    # 0 placeholders, exit 0 — indistinguishable from a genuinely clean
    # bibliography, so a path typo silently PASSED the citation gate that
    # write_verify_status.py depends on. Named-but-absent inputs are an error,
    # not "clean". (A missing DEFAULT drafts/ dir stays fine: a fresh project
    # with no drafts yet legitimately scans nothing.)
    if args.file and not Path(args.file).exists():
        die(f"--file {args.file} does not exist")
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")

    res = check(Path(args.drafts), Path(args.bib),
                Path(args.file) if args.file else None)
    missing = res["missing"]
    placeholders = res["placeholders"]
    material_gaps = res["material_gaps"]

    if args.quick:
        if missing or placeholders or material_gaps:
            print(f"cite_audit: {len(missing)} undefined key(s) {missing[:5]}"
                  f"{' …' if len(missing) > 5 else ''}; {len(placeholders)} [CITATION NEEDED] "
                  f"tag(s); {len(material_gaps)} [MATERIAL GAP] tag(s)")
        else:
            print("cite_audit: clean")
        sys.exit(0)  # hook mode is visibility-only, never blocks

    emit(res, True)
    # llm_supplemented is deliberately NOT in this condition: an authorized fill
    # is a legitimate authoring decision, not a defect. It is reported so a
    # reviewer sees it, and that is the whole job.
    sys.exit(2 if (missing or placeholders or material_gaps) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"bib file is not valid UTF-8 — {e}")
