#!/usr/bin/env python3
"""docx_style_check.py — verify a built .docx actually uses the reference doc's styles.

Template-compliance test (quality bar: ingested custom styles must be honored):
compares style definitions (font, size) of the built document against the
reference/ingested .docx, and reports which named styles are USED by paragraphs.

Usage:
  python scripts/docx_style_check.py --built build/paper.docx --reference templates/paper/reference.docx
Exit codes: 0 compliant · 1 error · 2 mismatches found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, require_within_cwd

# Optional dependency; guarded so a missing python-docx surfaces as a clean
# die() message via main() instead of a raw ModuleNotFoundError before
# argparse even runs.
try:
    from docx import Document
except ImportError:
    Document = None

CHECK_STYLES = ["Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4",
                "First Paragraph", "Body Text", "Block Text", "Caption",
                "Bibliography", "Normal", "Table"]


def style_sig(doc, name: str):
    try:
        s = doc.styles[name]
    except KeyError:
        return None
    f = s.font
    return {"font": f.name, "size": f.size.pt if f.size else None,
            "bold": f.bold, "italic": f.italic}


def used_styles(doc) -> dict:
    counts = {}
    for p in doc.paragraphs:
        n = p.style.name if p.style else "?"
        counts[n] = counts.get(n, 0) + 1
    return counts


def main():
    if Document is None:
        die("python-docx not installed — pip install python-docx")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--built", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.built, "--built")
    require_within_cwd(args.reference, "--reference")
    for p in (args.built, args.reference):
        if not Path(p).exists():
            print(f"ERROR: {p} does not exist", file=sys.stderr)
            sys.exit(1)
    try:
        built = Document(args.built)
        ref = Document(args.reference)
    except Exception as e:
        die(f"could not open a .docx (corrupt or not a Word document) — {e}")
    mismatches, compared = [], {}
    for name in CHECK_STYLES:
        b, r = style_sig(built, name), style_sig(ref, name)
        if r is None:
            continue
        compared[name] = {"reference": r, "built": b}
        if b is None:
            mismatches.append({"style": name, "problem": "missing in built document"})
        else:
            for k in ("font", "size"):
                if r[k] is not None and b[k] != r[k]:
                    mismatches.append({"style": name, "problem": f"{k}: built={b[k]} ref={r[k]}"})
    report = {"built": args.built, "reference": args.reference,
              "styles_used_in_built": used_styles(built),
              "mismatches": mismatches, "compliant": not mismatches}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(2 if mismatches else 0)


if __name__ == "__main__":
    main()
