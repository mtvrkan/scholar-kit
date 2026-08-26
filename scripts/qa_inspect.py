#!/usr/bin/env python3
"""qa_inspect.py — read-only inspection primitives for qa-auditor's back-step checks.

qa-auditor (conversion/excel stages) needs to independently re-derive a PDF's
page count and an Excel workbook's sheet/row layout — ad-hoc Bash one-liners
for this fall outside the `python scripts/*` allowlist pattern in
.claude/settings.json and would trigger a permission prompt on every
invocation. This script gives qa-auditor a sanctioned, allowlisted way to do
both, consistent with the kit's "scripts execute, agents don't freehand"
convention.

Usage:
  python scripts/qa_inspect.py pdf-pages sources/pdf/kaya2023deep.pdf
  python scripts/qa_inspect.py xlsx-sheets exports/literature-matrix.xlsx
Exit codes: 0 ok · 1 error (file not found / unreadable).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd


def cmd_pdf_pages(args):
    require_within_cwd(args.pdf, "pdf")
    p = Path(args.pdf)
    if not p.exists():
        die(f"{p} does not exist")
    try:
        import pymupdf
    except ImportError:
        die("pymupdf not installed — pip install pymupdf")
    try:
        doc = pymupdf.open(p)
        try:
            pages = doc.page_count
            images = sum(len(doc.get_page_images(i)) for i in range(pages))
        finally:
            doc.close()
    except Exception as e:
        die(f"could not open {p}: {e}")
    emit({"file": p.as_posix(), "pages": pages, "images": images}, True)


def cmd_xlsx_sheets(args):
    require_within_cwd(args.xlsx, "xlsx")
    p = Path(args.xlsx)
    if not p.exists():
        die(f"{p} does not exist")
    try:
        from openpyxl import load_workbook
    except ImportError:
        die("openpyxl not installed — pip install openpyxl")
    try:
        wb = load_workbook(p, read_only=True, data_only=True)
        try:
            sheets = {ws.title: max(ws.max_row - 1, 0) for ws in wb.worksheets}
        finally:
            wb.close()
    except Exception as e:
        die(f"could not open {p}: {e}")
    emit({"file": p.as_posix(), "sheets": sheets}, True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", dest="json_out", action="store_true",
                     help="accepted for CLI consistency — output is always JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pdf = sub.add_parser("pdf-pages")
    p_pdf.add_argument("pdf")
    p_xlsx = sub.add_parser("xlsx-sheets")
    p_xlsx.add_argument("xlsx")
    args = ap.parse_args()
    {"pdf-pages": cmd_pdf_pages, "xlsx-sheets": cmd_xlsx_sheets}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read the input file — {e}")
