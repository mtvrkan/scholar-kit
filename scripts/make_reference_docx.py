#!/usr/bin/env python3
"""make_reference_docx.py — generate a styled reference.docx for the Pandoc pipeline.

Produces a document whose named styles Pandoc maps onto its output
(--reference-doc): Title, Heading 1-4, First Paragraph, Body Text, Block Text,
Caption, plus a bibliography-friendly hanging-indent style. Pandoc's docx
writer uses "First Paragraph" (no first-line indent) for the paragraph
immediately following a heading and "Body Text" (first-line indent) for every
paragraph after that — both must be defined, or the first paragraph of every
section silently falls back to unstyled "Normal". Defaults follow a common
journal manuscript register (Times New Roman 12, 1.5 spacing, first-line indent);
when an ingested template exists, format-engineer regenerates with its values.

Usage:
  python scripts/make_reference_docx.py [--out templates/paper/reference.docx]
    [--font "Times New Roman"] [--size 12] [--spacing 1.5]
Requires: python-docx (pip install python-docx).
"""
from __future__ import annotations

import argparse
import copy
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd, write_bytes_atomic

# Optional dependency; guarded so a missing python-docx surfaces as a clean
# die() message via main() instead of a raw ModuleNotFoundError before
# argparse even runs.
try:
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
except ImportError:
    Document = None


def style_font(style, font_name: str, size: float, bold=False, italic=False):
    style.font.name = font_name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic


def main():
    if Document is None:
        die("python-docx not installed — pip install python-docx")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="templates/paper/reference.docx")
    ap.add_argument("--font", default="Times New Roman")
    ap.add_argument("--size", type=float, default=12)
    ap.add_argument("--spacing", type=float, default=1.5)
    ap.add_argument("--json", dest="json_out", action="store_true",
                    help="accepted for CLI consistency — output is always JSON")
    args = ap.parse_args()
    require_within_cwd(args.out, "--out")
    # Caption is derived as size-2 and Block Text as size-1; python-docx's Pt()
    # rejects a negative EMU, so a --size of 0/1/2 (or negative) used to crash
    # with a raw ValueError traceback from deep inside python-docx instead of
    # this script's clean ERROR:/exit-1 contract. Validate the derived floor.
    if args.size < 3:
        die(f"--size must be at least 3 (Caption/Block Text are derived as "
            f"size-2 / size-1 and must stay positive), got {args.size}")
    if args.spacing <= 0:
        die(f"--spacing must be positive, got {args.spacing}")
    if not args.font.strip():
        die("--font must not be empty")
    # A directory destination would surface later as write_bytes_atomic's
    # generic "file locked after 60 attempts" retry message — misdiagnosing a
    # never-going-to-succeed os.replace-onto-a-dir as a transient lock. Catch it
    # here with an accurate message instead.
    if Path(args.out).is_dir():
        die(f"--out {args.out} is a directory — pass a file path")

    doc = Document()
    styles = doc.styles

    normal = styles["Normal"]
    style_font(normal, args.font, args.size)
    normal.paragraph_format.line_spacing = args.spacing
    normal.paragraph_format.space_after = Pt(6)

    # Body Text: pandoc's style for the 2nd+ paragraph of a section.
    body = styles["Body Text"] if "Body Text" in [s.name for s in styles] \
        else styles.add_style("Body Text", WD_STYLE_TYPE.PARAGRAPH)
    body.base_style = normal
    body.paragraph_format.first_line_indent = Cm(0.75)
    body.paragraph_format.line_spacing = args.spacing

    # First Paragraph: pandoc's style for the paragraph immediately following
    # a heading — a DIFFERENT style from "Body Text", not a fallback name for
    # the same thing. Without an explicit definition here, python-docx's base
    # template has no "First Paragraph" style at all, so pandoc silently falls
    # back to bare "Normal" (no first-line-indent-removal decision made on
    # purpose, no guaranteed line spacing) for that one paragraph per section
    # — reproduced live: a reference.docx missing this style renders every
    # section's opening paragraph in "Normal" while the 2nd+ paragraphs
    # correctly use "Body Text". No first-line indent (the conventional
    # academic style for the paragraph right after a heading), but the same
    # spacing as Body Text so it doesn't visually clash with the rest of the
    # section.
    first_para = styles["First Paragraph"] if "First Paragraph" in [s.name for s in styles] \
        else styles.add_style("First Paragraph", WD_STYLE_TYPE.PARAGRAPH)
    first_para.base_style = normal
    first_para.paragraph_format.line_spacing = args.spacing
    first_para.paragraph_format.space_after = Pt(6)

    for level, (size, bold, italic) in {
        1: (14, True, False), 2: (13, True, False),
        3: (12, True, False), 4: (12, True, True),
    }.items():
        h = styles[f"Heading {level}"]
        style_font(h, args.font, size, bold=bold, italic=italic)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.line_spacing = args.spacing

    title = styles["Title"]
    style_font(title, args.font, 16, bold=True)

    # Block Text: pandoc uses it for block quotes
    if "Block Text" not in [s.name for s in styles]:
        bq = styles.add_style("Block Text", WD_STYLE_TYPE.PARAGRAPH)
    else:
        bq = styles["Block Text"]
    bq.base_style = normal
    bq.paragraph_format.left_indent = Cm(1.0)
    bq.paragraph_format.right_indent = Cm(1.0)
    style_font(bq, args.font, args.size - 1)

    # Table: pandoc's docx writer references a table style literally named
    # "Table" by ID for every generated table — python-docx's base Document()
    # template defines no such style, so every table silently rendered with
    # no institutional borders/shading at all (verified against real pandoc
    # output: the table XML asks for style ID "Table" regardless of whether
    # reference.docx defines one). Word's built-in "Table Grid" (borders on
    # every cell) is the closest match to standard academic table formatting
    # and the one thing python-docx can materialize without hand-authoring
    # OOXML border properties (its high-level API has no border setter for a
    # table STYLE, only for an actual table instance) — so clone Table Grid's
    # already-correct XML under the "Table" style ID pandoc actually emits.
    if "Table" not in [s.name for s in styles]:
        # add_table(..., style="Table Grid") is the only way python-docx
        # materializes this built-in style's XML into styles.xml; a bare
        # Document() doesn't carry it until something references it.
        _tmp_table = doc.add_table(rows=1, cols=1)
        _tmp_table.style = "Table Grid"
        table_style_el = copy.deepcopy(styles["Table Grid"].element)
        table_style_el.set(qn("w:styleId"), "Table")
        name_el = table_style_el.find(qn("w:name"))
        if name_el is not None:
            name_el.set(qn("w:val"), "Table")
        styles.element.append(table_style_el)
        # Drop the throwaway table — it only existed to force Table Grid's
        # XML into being; the reference doc shouldn't ship a sample table.
        _tmp_table._element.getparent().remove(_tmp_table._element)

    cap = styles["Caption"]
    style_font(cap, args.font, args.size - 2, bold=False, italic=False)
    cap.paragraph_format.space_before = Pt(4)
    cap.paragraph_format.space_after = Pt(10)

    # Bibliography: hanging indent, single-spaced entries
    if "Bibliography" not in [s.name for s in styles]:
        bib = styles.add_style("Bibliography", WD_STYLE_TYPE.PARAGRAPH)
    else:
        bib = styles["Bibliography"]
    bib.base_style = normal
    bib.paragraph_format.first_line_indent = Cm(-1.0)
    bib.paragraph_format.left_indent = Cm(1.0)
    bib.paragraph_format.line_spacing = 1.0
    bib.paragraph_format.space_after = Pt(6)

    # A visible sample so humans opening the file see the register
    doc.add_paragraph("Reference document for scholar-kit Pandoc builds.", style="Title")
    doc.add_paragraph("Heading level 1", style="Heading 1")
    doc.add_paragraph("First-paragraph-of-a-section sample: no first-line indent, "
                      "same spacing as Body Text.", style="First Paragraph")
    doc.add_paragraph("Body text sample paragraph with first-line indent and "
                      "1.5 line spacing. Regenerate with make_reference_docx.py "
                      "when an ingested template dictates other values.", style="Body Text")

    out = Path(args.out)
    buf = io.BytesIO()
    doc.save(buf)
    write_bytes_atomic(out, buf.getvalue())
    emit({"written": out.as_posix()}, args.json_out)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to write the reference docx — {e}")
