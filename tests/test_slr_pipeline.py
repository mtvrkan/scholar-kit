"""Tests for the hocamdan SLR pipeline additions: query log, SLR Excel sheets, pdf2md."""
import json


def test_log_query_appends_jsonl(run, tmp_path):
    code, out, err = run("registry_db.py", "log-query", "--db", "scopus",
                         "--query", "TITLE-ABS-KEY(x AND y)", "--hits", "78")
    assert code == 0, err
    code, out, _ = run("registry_db.py", "log-query", "--db", "wos",
                       "--query", "TS=(x)", "--hits", "58", "--note", "refined")
    log = (tmp_path / "sources" / "search-log.jsonl").read_text(encoding="utf-8")
    lines = [json.loads(l) for l in log.strip().splitlines()]
    assert len(lines) == 2
    assert lines[0]["db"] == "scopus" and lines[0]["hits"] == 78
    assert lines[1]["note"] == "refined" and lines[1]["date"]


def test_registry_list_filters_by_db(run, tmp_path):
    run("registry_db.py", "add", "--json", json.dumps({"title": "A", "db": "scopus"}))
    run("registry_db.py", "add", "--json", json.dumps({"title": "B", "db": "wos"}))
    code, out, _ = run("registry_db.py", "list", "--db", "scopus")
    recs = json.loads(out)
    assert len(recs) == 1 and recs[0]["title"] == "A"


def test_xlsx_slr_queries_and_per_db_sheets(run, tmp_path, sample_registry, sample_cards):
    # add db fields + a search log + an extract
    run("registry_db.py", "set-field", "SRC-0001", "db", "scopus")
    run("registry_db.py", "set-field", "SRC-0002", "db", "wos")
    run("registry_db.py", "log-query", "--db", "scopus", "--query", "Q1", "--hits", "10")
    ex_dir = tmp_path / "evidence" / "extracts"
    ex_dir.mkdir(parents=True)
    (ex_dir / "kaya2023deep.json").write_text(json.dumps({
        "key": "kaya2023deep", "registry_id": "SRC-0001",
        "sections": {"abstract": "CNN beats SVM."},
        "fields": {"Alan": "PHM", "Model Türü": "CNN"},
        "key_references": [{"text": "LeCun 2015", "bib_key": "lecun2015deep"}],
    }, ensure_ascii=False), encoding="utf-8")

    code, out, _ = run("xlsx_export.py")
    assert code == 0, out
    rep = json.loads(out)
    for expected in ("queries", "slr", "db-scopus", "db-wos"):
        assert expected in rep["sheets"], rep["sheets"]

    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "exports" / "literature-matrix.xlsx")
    slr = wb["slr"]
    headers = [c.value for c in slr[1]]
    assert "Alan" in headers and "Model Türü" in headers  # dynamic fields
    assert "include" in headers
    # strict=True, not False: header row and data row come from the same sheet,
    # so a length mismatch is a real xlsx_export defect (a column written
    # without a header, or vice versa) — zip would otherwise drop it silently
    # and the assertions below would still pass on the truncated dict.
    row = {h: c.value for h, c in zip(headers, slr[2], strict=True)}
    assert row["bib_key"] == "kaya2023deep"
    assert row["include"] == "Dahil"
    assert "lecun2015deep" in (row["key_references"] or "")
    assert wb["db-scopus"].max_row == 2  # header + 1 record


def test_pdf2md_lossless_conversion(run, tmp_path):
    import pymupdf
    pdf_dir = tmp_path / "sources" / "pdf"
    pdf_dir.mkdir(parents=True)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 80), "Sample Title", fontsize=18)
    page.insert_text((72, 120), "Body text with finding F1=0.93.", fontsize=11)
    page.draw_rect(pymupdf.Rect(72, 200, 200, 300), fill=(0.8, 0.2, 0.2))
    doc.save(pdf_dir / "sample2026.pdf")
    doc.close()

    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/sample2026.pdf",
                         "--key", "sample2026")
    assert code == 0, err
    meta = json.loads(out)
    assert meta["pages"] == 1
    md = (tmp_path / "sources" / "md" / "sample2026" / "sample2026.md").read_text(encoding="utf-8")
    assert "Sample Title" in md
    assert "F1=0.93" in md.replace("`", "")  # exact value survives
    assert (tmp_path / "sources" / "md" / "sample2026" / "meta.json").exists()


def test_pdf2md_single_file_mode_dies_cleanly_on_corrupt_pdf(run, tmp_path):
    # --pdf mode previously called convert() unwrapped, unlike --all mode
    # (which already caught exceptions and reported them as clean JSON) — a
    # non-PDF file crashed with a raw pymupdf traceback instead of die().
    pdf_dir = tmp_path / "sources" / "pdf"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "fake.pdf").write_text("not a real pdf", encoding="utf-8")
    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/fake.pdf", "--key", "fake")
    assert code == 1, (out, err)
    assert "ERROR" in err
    assert "Traceback" not in err


def test_pdf2md_rejects_path_traversal_in_key(run, tmp_path):
    import pymupdf
    pdf_dir = tmp_path / "sources" / "pdf"
    pdf_dir.mkdir(parents=True)
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf_dir / "x.pdf")
    doc.close()
    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/x.pdf", "--key", "../../evil")
    assert code == 1, (out, err)
    assert not (tmp_path.parent.parent / "evil").exists()
