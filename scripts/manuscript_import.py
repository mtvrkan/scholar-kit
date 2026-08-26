#!/usr/bin/env python3
"""manuscript_import.py — bring a manuscript that already exists into the kit, without importing its claims.

WHY THIS EXISTS
Every command in this kit assumed the paper started here. The most common request
does not: there is a draft — a Word file from a supervisor, a thesis chapter in
LaTeX, a PDF of last year's submission — and the author wants it reviewed,
verified, restyled, tightened. Until now the only way in was to paste it, which
put the whole manuscript in a context window that dies, with no section files, no
register, and therefore no `/verify-citations`, no `/critique`, no `/submit-check`.

This is the on-ramp. The document is converted, split into section files the rest
of the pipeline understands, and its reference list is read as a **list of
identifiers, not as bibliographic truth** — exactly the treatment `/import-library`
gives a Zotero export, and for the same reason: a reference typed by a human is a
claim about a paper, and this kit's one rule is that claims about papers come from
the authoritative record.

WHAT IT REFUSES
- **To let one field of the reference list into the bibliography.** DOIs are
  extracted and re-fetched through `doi2bib.py`. Entries without a DOI are
  registered as candidates and reported by name; nothing is transcribed.
- **To rewrite the citations in the text.** When a numeric reference list resolves
  to bib keys, the mapping is written to `drafts/citation-map.json` as a
  *proposal*. Silently turning `[12]` into `[@yilmaz2020derin]` would be an
  unreviewed edit to the author's argument, and a mis-mapped one is undetectable
  afterwards.
- **To overwrite existing drafts.** A target file that exists stops the import
  and is named. `--force` exists; the default does not silently replace a section
  someone has been editing for two weeks.
- **To claim the split is the author's structure.** Sections come from the
  headings the document actually has. When it has none — the usual outcome of a
  PDF conversion — that is reported as one file and a warning, not smoothed over.

USAGE
  python scripts/manuscript_import.py --file paper.docx --plan
  python scripts/manuscript_import.py --file paper.docx
  python scripts/manuscript_import.py --file thesis.tex --resolve
  python scripts/manuscript_import.py --file draft.pdf --out-dir drafts

Exit codes: 0 imported · 1 error · 2 refused (targets exist, nothing extractable)
· 3 BLOCKED (pandoc or pymupdf4llm missing for this input type).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd, transliterate  # noqa: E402

SCRIPTS = Path(__file__).parent
DEFAULT_OUT = "drafts"
DEFAULT_REGISTRY = "sources/registry.jsonl"
DEFAULT_BIB = "bib/references.bib"

REFERENCE_HEADINGS = ("references", "reference list", "bibliography", "works cited",
                      "kaynakca", "kaynaklar", "kaynakça", "referanslar", "kaynak listesi")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
PANDOC_CITE_RE = re.compile(r"\[(@[^\]]+)\]")
NUMERIC_CITE_RE = re.compile(r"\[(\d{1,3}(?:\s*[-–,;]\s*\d{1,3})*)\]")
PAREN_CITE_RE = re.compile(r"\(([^()]{0,120}?(?:19|20)\d{2}[a-z]?)\)")
NARRATIVE_CITE_RE = re.compile(
    r"\b([A-ZÇĞİÖŞÜ][\wçğıöşü'’-]+(?:\s+(?:ve|and|&|et al\.?)\s+[A-ZÇĞİÖŞÜ]?[\wçğıöşü'’-]*)?)"
    r"\s*\((?:19|20)\d{2}[a-z]?\)")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*#*$", re.M)


def slug(text: str, limit: int = 40) -> str:
    ascii_text = transliterate(text).lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return (ascii_text or "section")[:limit].strip("-")


def to_markdown(path: Path, work_dir: Path) -> tuple[str, dict]:
    """Whatever the input was, markdown — through the tool that owns that format.

    No format is hand-parsed here: a .docx read with a regex is how a table
    becomes a paragraph and a footnote becomes body text.
    """
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace"), {"via": "read"}
    if suffix == ".pdf":
        try:
            import pdf2md
        except ImportError:  # pragma: no cover - defensive
            print("BLOCKED: pdf2md.py could not be imported", file=sys.stderr)
            sys.exit(3)
        try:
            result = pdf2md.convert(path, work_dir, key="manuscript")
        except SystemExit:
            raise
        except Exception as e:  # pymupdf4llm missing or unreadable PDF
            print(f"BLOCKED: PDF conversion failed — {e}. Install the converter with "
                  f"pip install pymupdf4llm", file=sys.stderr)
            sys.exit(3)
        md_path = Path(result.get("md") or (work_dir / "manuscript" / "manuscript.md"))
        if not md_path.is_file():
            die("the PDF converter produced no markdown file")
        return md_path.read_text(encoding="utf-8", errors="replace"), {
            "via": "pdf2md", "pages": result.get("pages")}
    if suffix in (".docx", ".tex", ".odt", ".rtf", ".html", ".htm"):
        if not shutil.which("pandoc"):
            print("BLOCKED: pandoc is not installed, and a .docx/.tex manuscript is "
                  "converted with it, not parsed by hand. "
                  "see pandoc.org/installing.html — Windows: winget install "
                  "--id JohnMacFarlane.Pandoc", file=sys.stderr)
            sys.exit(3)
        source_format = {".docx": "docx", ".tex": "latex", ".odt": "odt", ".rtf": "rtf",
                         ".html": "html", ".htm": "html"}[suffix]
        out = work_dir / "manuscript.md"
        media = work_dir / "media"
        proc = subprocess.run(
            ["pandoc", "--from", source_format, "--to", "markdown",
             "--wrap=none", f"--extract-media={media}", str(path), "-o", str(out)],
            capture_output=True, text=True, encoding="utf-8", timeout=300)
        if proc.returncode != 0 or not out.is_file():
            die(f"pandoc could not convert {path.name} — "
                f"{(proc.stderr or proc.stdout or '').strip()[:300]}")
        return out.read_text(encoding="utf-8", errors="replace"), {
            "via": "pandoc", "media": media.as_posix() if media.exists() else None}
    die(f"unsupported input {suffix!r} — give .md, .docx, .tex, .pdf, .odt, .rtf or .html")


def split_sections(text: str) -> tuple[list[dict], list[str]]:
    """Split on the headings the document has. No inference of structure."""
    warnings = []
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        warnings.append("the document has no markdown headings — it was imported as a "
                        "single file. This is the usual outcome of a PDF conversion; "
                        "split it by hand, or import the .docx/.tex the PDF was made from")
        return [{"title": "manuscript", "level": 1, "body": text.strip()}], warnings
    sections = []
    preamble = text[:matches[0].start()].strip()
    if preamble:
        sections.append({"title": "front", "level": 1, "body": preamble})
        warnings.append("text before the first heading was kept as 'front' — usually "
                        "the title block and abstract")
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({"title": m.group(2).strip(), "level": len(m.group(1)),
                         "body": text[m.start():end].strip()})
    return sections, warnings


def is_reference_heading(title: str) -> bool:
    folded = transliterate(title).lower().strip(" .:0123456789")
    return any(folded.startswith(h) or folded == h
               for h in (transliterate(x).lower() for x in REFERENCE_HEADINGS))


def parse_reference_entries(body: str) -> list[dict]:
    """The reference list as entries, each carrying whatever identifier it holds.

    Three layouts cover almost everything real: numbered `[1]`, numbered `1.`, and
    blank-line separated. What is NOT attempted is parsing an entry into
    author/title/venue fields — that parse is exactly the transcription this
    script exists to avoid. Only the DOI matters, because only the DOI can be
    checked against the authoritative record.
    """
    lines = [ln.rstrip() for ln in body.splitlines()]
    lines = [ln for ln in lines if not HEADING_RE.match(ln)]
    text = "\n".join(lines).strip()
    if not text:
        return []
    bracket = re.split(r"\n?\s*\[(\d{1,3})\]\s*", "\n" + text)
    if len(bracket) > 2:
        chunks = [bracket[i + 1].strip() for i in range(1, len(bracket) - 1, 2)]
    else:
        numbered = re.split(r"\n\s*(\d{1,3})[.)]\s+", "\n" + text)
        if len(numbered) > 2:
            chunks = [numbered[i + 1].strip() for i in range(1, len(numbered) - 1, 2)]
        else:
            chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
            if len(chunks) < 2:
                chunks = [c.strip() for c in text.splitlines() if len(c.strip()) > 30]
    entries = []
    for i, chunk in enumerate(chunks, start=1):
        flat = re.sub(r"\s+", " ", chunk).strip()
        if len(flat) < 20:
            continue
        doi = DOI_RE.search(flat)
        year = YEAR_RE.search(flat)
        entries.append({
            "index": i,
            "raw": flat[:400],
            "doi": doi.group(0).rstrip(".,;)") if doi else None,
            "year": int(year.group(0)[:4]) if year else None,
        })
    return entries


def find_citations(text: str) -> dict:
    numeric = set()
    for m in NUMERIC_CITE_RE.finditer(text):
        for part in re.split(r"[,;]", m.group(1)):
            part = part.strip()
            range_match = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if range_match:
                start, stop = int(range_match.group(1)), int(range_match.group(2))
                if 0 < stop - start < 200:
                    numeric.update(range(start, stop + 1))
            elif part.isdigit():
                numeric.add(int(part))
    pandoc = {k.strip() for m in PANDOC_CITE_RE.finditer(text)
              for k in m.group(1).split(";")}
    # A bare "(2020)" is the tail of a narrative citation — "Yılmaz (2020)" — and
    # the narrative pattern below already counts it under the author's name.
    # Keeping both would report one citation as two.
    author_year = {re.sub(r"\s+", " ", m.group(1)).strip()
                   for m in PAREN_CITE_RE.finditer(text)
                   if not re.fullmatch(r"(?:19|20)\d{2}[a-z]?", m.group(1).strip())}
    author_year |= {re.sub(r"\s+", " ", m.group(1)).strip()
                    for m in NARRATIVE_CITE_RE.finditer(text)}
    style = ("pandoc" if pandoc else "numeric" if numeric else
             "author-year" if author_year else "none-detected")
    return {"style": style, "numeric": sorted(numeric),
            "pandoc_keys": sorted(pandoc), "author_year": sorted(author_year)[:200],
            "counts": {"numeric": len(numeric), "pandoc": len(pandoc),
                       "author_year": len(author_year)}}


def fetch_via_doi2bib(doi: str, bib: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "doi2bib.py"), "--doi", doi, "--append", bib,
         "--json"], capture_output=True, text=True, encoding="utf-8", timeout=90)
    if proc.returncode != 0:
        reason = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {"error": reason[-1] if reason else f"doi2bib exited {proc.returncode}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"doi2bib returned unreadable output: {proc.stdout[:120]}"}


def register(payloads: list[dict], registry: str) -> dict:
    if not payloads:
        return {"added": [], "duplicates": [], "total": 0}
    stream = "\n".join(json.dumps(p, ensure_ascii=False) for p in payloads)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "registry_db.py"), "--file", registry,
         "add", "--stdin"], input=stream, capture_output=True, text=True,
        encoding="utf-8", timeout=300)
    if proc.returncode != 0:
        die(f"registry_db.py refused the batch — {(proc.stderr or proc.stdout).strip()}")
    return json.loads(proc.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", required=True, help=".md/.docx/.tex/.pdf/.odt/.rtf/.html")
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--bib", default=DEFAULT_BIB)
    ap.add_argument("--lang", default="tr", help="language recorded for imported sources")
    ap.add_argument("--resolve", action="store_true",
                    help="fetch every DOI in the reference list through doi2bib.py and "
                         "register the entries as candidates")
    ap.add_argument("--force", action="store_true",
                    help="overwrite section files that already exist")
    ap.add_argument("--plan", action="store_true",
                    help="convert and report; write nothing, fetch nothing")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.file, "--file")
    require_within_cwd(args.out_dir, "--out-dir")
    src = Path(args.file)
    if not src.is_file():
        die(f"{args.file} does not exist")

    with tempfile.TemporaryDirectory(prefix="scholar-kit-import-") as tmp:
        text, conversion = to_markdown(src, Path(tmp))
    if not text.strip():
        die("the converted document is empty — nothing to import", code=2)

    sections, warnings = split_sections(text)
    body_sections = [s for s in sections if not is_reference_heading(s["title"])]
    reference_sections = [s for s in sections if is_reference_heading(s["title"])]
    entries = []
    for s in reference_sections:
        entries.extend(parse_reference_entries(s["body"]))
    body_text = "\n\n".join(s["body"] for s in body_sections)
    citations = find_citations(body_text)
    words = len(re.findall(r"\w+", body_text))

    out_dir = Path(args.out_dir)
    planned = []
    for i, s in enumerate(body_sections, start=1):
        planned.append({"title": s["title"], "level": s["level"],
                        "words": len(re.findall(r"\w+", s["body"])),
                        "file": (out_dir / f"{i:02d}-{slug(s['title'])}.md").as_posix()})
    existing = [p["file"] for p in planned if Path(p["file"]).exists()]

    with_doi = [e for e in entries if e["doi"]]
    without_doi = [e for e in entries if not e["doi"]]

    if args.plan or (existing and not args.force):
        emit({"file": src.as_posix(), "conversion": conversion,
              "sections": planned, "words": words,
              "references": {"entries": len(entries), "with_doi": len(with_doi),
                             "without_doi": len(without_doi)},
              "citations": citations, "warnings": warnings,
              "existing_targets": existing,
              "result": "REFUSED" if (existing and not args.force) else "PLAN",
              "note": ("nothing was written. " + (
                  f"{len(existing)} target file(s) already exist — pass --force to "
                  f"overwrite, or import into another --out-dir."
                  if existing and not args.force else
                  "Run without --plan to write the sections."))}, args.json_out)
        sys.exit(2 if (existing and not args.force) else 0)

    out_dir.mkdir(parents=True, exist_ok=True)
    for plan_item, section in zip(planned, body_sections, strict=True):
        Path(plan_item["file"]).write_text(section["body"].strip() + "\n", encoding="utf-8")

    resolution = None
    if args.resolve and with_doi:
        require_within_cwd(args.registry, "--registry")
        require_within_cwd(args.bib, "--bib")
        Path(args.bib).parent.mkdir(parents=True, exist_ok=True)
        payloads, failed, mapping = [], [], {}
        for entry in with_doi:
            result = fetch_via_doi2bib(entry["doi"], args.bib)
            key = result.get("key")
            if result.get("error"):
                failed.append({"doi": entry["doi"], "reason": result["error"]})
            elif key:
                mapping[str(entry["index"])] = {"doi": entry["doi"], "bib_key": key}
            payload = {
                "title": entry["raw"][:200],
                "authors": [],
                "lang": args.lang,
                "status": "candidate",
                "db": "manuscript-import",
                "import_source": src.name,
                # The same provenance stamp /import-library uses, for the same
                # reason: six months on, nothing else distinguishes a row that
                # came out of a reference list from one that was screened.
                "metadata_source": "manuscript reference list (unverified)",
                "doi": entry["doi"],
            }
            if entry.get("year"):
                payload["year"] = entry["year"]
            if key:
                payload["bib_key"] = key
            payloads.append(payload)
        registered = register(payloads, args.registry)
        map_path = out_dir / "citation-map.json"
        map_path.write_text(json.dumps(
            {"style": citations["style"], "source": src.name,
             "mapping": mapping,
             "note": ("a PROPOSAL, not an applied edit: nothing in the text was "
                      "rewritten. Turning [12] into [@key] is a change to the "
                      "author's argument and needs their eyes on each one.")},
            ensure_ascii=False, indent=2), encoding="utf-8")
        resolution = {"fetched": len(mapping), "failed": failed,
                      "registered": registered, "map": map_path.as_posix()}

    emit({"file": src.as_posix(), "conversion": conversion,
          "written": [p["file"] for p in planned], "sections": planned, "words": words,
          "references": {"entries": len(entries), "with_doi": len(with_doi),
                         "without_doi": [e["raw"][:120] for e in without_doi][:50]},
          "citations": citations, "warnings": warnings, "resolution": resolution,
          "next": ["python scripts/cite_audit.py",
                   "/verify-citations", "/critique"],
          "note": ("the text is the author's and was not edited. Its reference list was "
                   "read as a list of DOIs — not one field of it entered the "
                   "bibliography, which is what makes /verify-citations meaningful on "
                   "an imported manuscript rather than circular")}, args.json_out)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read or write a file — {e}")
