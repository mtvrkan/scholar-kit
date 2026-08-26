#!/usr/bin/env python3
"""pdf2md.py — meticulous PDF → Markdown conversion for the SLR pipeline.

Requirement (hocamdan.txt §4): papers saved locally must be converted to .md with
NO data loss — all text, tables, and figures — so agents read/understand them well
and full-paper review from md becomes easy.

Engine: pymupdf4llm (layout-aware text, tables as GitHub markdown, figures extracted
as PNG files referenced from the md). Output layout per source:
  sources/md/<key>/<key>.md          the full paper as markdown
  sources/md/<key>/img/*.png         extracted figures (referenced from the md)
  sources/md/<key>/meta.json         page count, image count, table count, source pdf

Usage:
  python scripts/pdf2md.py --pdf sources/pdf/kaya2023deep.pdf [--key kaya2023deep]
  python scripts/pdf2md.py --all [--pdf-dir sources/pdf] [--out-dir sources/md]
Exit codes: 0 ok · 1 error · 2 some conversions failed (--all mode).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd  # noqa: E402 (utf-8 stdout guard)


def convert(pdf: Path, out_dir: Path, key: str | None = None) -> dict:
    import pymupdf  # noqa: F401 (ensure engine present before heavy work)
    import pymupdf4llm

    key = key or pdf.stem
    if "/" in key or "\\" in key or ".." in key:
        raise ValueError(f"invalid key '{key}' — must not contain path separators or '..'")
    # A drive-letter-prefixed key (e.g. "C:evil") is only dangerous through
    # WindowsPath's `/` operator, which silently drops everything left of a
    # right-hand operand that looks drive-rooted — `out_dir / "C:evil"`
    # resolves to "C:\evil", not "<out_dir>/C:evil", escaping sources/md/
    # entirely. On POSIX, `/` has no such special case (a colon is an
    # ordinary filename character), so the .resolve() containment check below
    # would silently accept it there. But a bib key is project data that can
    # be committed and later opened on a different OS (this kit explicitly
    # supports Windows/macOS/Linux for the same project) — a key that's inert
    # on the host running this check today must not become a live escape the
    # day the project is opened on Windows. Reject the drive-letter pattern
    # outright, regardless of which OS is running this check.
    if re.match(r"^[A-Za-z]:", key):
        raise ValueError(
            f"invalid key '{key}' — starts with a drive letter, which resolves outside "
            f"{out_dir} on Windows even though it's harmless on this host's OS")
    dest = out_dir / key
    # Verify the actual resolved destination stays inside out_dir instead of
    # trying to enumerate every remaining OS-specific escape character.
    resolved_dest, resolved_out = dest.resolve(), out_dir.resolve()
    if resolved_dest != resolved_out and resolved_out not in resolved_dest.parents:
        raise ValueError(f"invalid key '{key}' — resolves outside {out_dir}")
    img_dir = dest / "img"
    dest.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(exist_ok=True)

    md = pymupdf4llm.to_markdown(
        str(pdf),
        write_images=True,
        image_path=str(img_dir),
        image_format="png",
        table_strategy="lines_strict",
        page_chunks=False,
    )
    # image links come back with absolute/OS paths — rewrite relative to the md file
    md = md.replace(str(img_dir).replace("\\", "/"), "img").replace(str(img_dir), "img")

    # A PDF with a broken font-to-unicode map hands back LONE surrogates (an
    # astral char whose low half was dropped). pymupdf4llm keeps them; plain
    # get_text() already degrades the same char to U+FFFD. Encoding one as utf-8
    # raises, killing the whole conversion over a character that is unrecoverable
    # from the file either way. Degrade identically and COUNT it, so the loss is
    # reported in meta.json rather than being silent.
    md, n_lossy = re.subn(r"[\ud800-\udfff]", "�", md)

    md_path = dest / f"{key}.md"
    md_path.write_text(md, encoding="utf-8", newline="\n")

    doc = pymupdf.open(pdf)
    n_pages = doc.page_count
    doc.close()
    images = sorted(p.name for p in img_dir.glob("*.png"))
    # Rough md-table indicator: count each separator ROW once, matching the
    # WHOLE line (pipes/dashes/colons/spaces only, with at least one pipe) so
    # a plain "---" horizontal rule is never mistaken for a table separator.
    # The prior `md.count("\n|---") + md.count("|---|")` double-counted every
    # ordinary separator line like "|---|---|" (it matches both substrings at
    # once), roughly doubling the reported table count.
    n_tables = len(re.findall(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", md, re.MULTILINE))
    meta = {
        "key": key,
        "source_pdf": str(pdf).replace("\\", "/"),
        "pages": n_pages,
        "images_extracted": len(images),
        "table_markers": n_tables,
        "md": str(md_path).replace("\\", "/"),
        "md_chars": len(md),
        "lossy_chars": n_lossy,
    }
    (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", help="single PDF to convert")
    ap.add_argument("--key", help="bib key / folder name (default: pdf stem)")
    ap.add_argument("--all", action="store_true", help="convert every PDF in --pdf-dir")
    ap.add_argument("--pdf-dir", default="sources/pdf")
    ap.add_argument("--out-dir", default="sources/md")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.out_dir, "--out-dir")
    require_within_cwd(args.pdf_dir, "--pdf-dir")
    if args.pdf:
        require_within_cwd(args.pdf, "--pdf")

    out_dir = Path(args.out_dir)
    if args.pdf:
        p = Path(args.pdf)
        if not p.exists():
            die(f"{args.pdf} does not exist")
        try:
            result = convert(p, out_dir, args.key)
        except Exception as e:  # match --all mode's clean-failure reporting
            die(f"conversion failed for {args.pdf}: {e}")
        emit(result, True)
    elif args.all:
        pdfs = sorted(Path(args.pdf_dir).glob("*.pdf"))
        if not pdfs:
            die(f"no PDFs in {args.pdf_dir}")
        results, failed = [], []
        for p in pdfs:
            try:
                results.append(convert(p, out_dir))
            except Exception as e:  # keep batch going; report failures
                failed.append({"pdf": p.name, "error": str(e)[:200]})
        emit({"converted": len(results), "failed": failed, "results": results}, True)
        sys.exit(2 if failed else 0)
    else:
        die("pass --pdf <file> or --all")


if __name__ == "__main__":
    main()
