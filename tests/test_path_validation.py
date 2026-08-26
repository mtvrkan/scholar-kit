"""Regression tests for lib_common.require_within_cwd() and every script-owned
write-destination argument it now guards: evidence_db.py/registry_db.py's
--file, doi2bib.py's --append/--bib, pdf2md.py's --out-dir, bib_doctor.py's
--bib, update_data.py's --dir, xlsx_export.py's --out, prisma_flow.py's
--out-dir, make_reference_docx.py's --out, venue_check.py's --cache, and
patch_hook_interpreter.py's --settings. Several of these are the sole
sanctioned writers for hook-protected files (evidence/cards.jsonl,
sources/registry.jsonl, sources/venues.jsonl, bib/references.bib) — that
guarantee only holds if their path arguments can't be pointed outside the
project; the rest write generated build/data output and are guarded for the
same defense-in-depth reason (an agent whose reasoning has been steered by
adversarial content in a fetched paper choosing a malicious argument value).
"""
import json


def test_evidence_db_rejects_file_escaping_project_dir(run, tmp_path):
    code, out, err = run("evidence_db.py", "--file", "../outside.jsonl", "stats")
    assert code == 1
    assert "--file" in err
    assert not (tmp_path.parent / "outside.jsonl").exists()


def test_evidence_db_rejects_absolute_file_outside_project_dir(run, tmp_path):
    import tempfile
    outside = tempfile.gettempdir() + "/elsewhere_evidence.jsonl"
    code, out, err = run("evidence_db.py", "--file", outside, "stats")
    assert code == 1
    assert "--file" in err


def test_evidence_db_allows_custom_relative_file_within_project_dir(run, tmp_path):
    # A custom (non-default) filename that's still INSIDE the project must
    # keep working — this isn't about forcing the literal default path, only
    # about not escaping the project directory.
    code, out, err = run("evidence_db.py", "--file", "custom/mycards.jsonl", "add", "--json",
                         json.dumps({"source": "a2020x", "type": "finding", "claim": "x"}))
    assert code == 0, err
    assert (tmp_path / "custom" / "mycards.jsonl").exists()


def test_registry_db_rejects_file_escaping_project_dir(run, tmp_path):
    code, out, err = run("registry_db.py", "--file", "../outside.jsonl", "stats")
    assert code == 1
    assert "--file" in err
    assert not (tmp_path.parent / "outside.jsonl").exists()


def test_registry_db_allows_default_file(run, tmp_path):
    code, out, err = run("registry_db.py", "stats")
    assert code == 0, err


def test_doi2bib_rejects_append_escaping_project_dir(run, tmp_path):
    code, out, err = run("doi2bib.py", "--append", "../outside.bib")
    assert code == 1
    assert "--append" in err
    assert not (tmp_path.parent / "outside.bib").exists()


def test_doi2bib_rejects_bib_escaping_project_dir(run, tmp_path):
    code, out, err = run("doi2bib.py", "--verify", "--bib", "../outside.bib")
    assert code == 1
    assert "--bib" in err


def test_doi2bib_allows_custom_relative_bib_within_project_dir(run, tmp_path):
    # A custom (non-default) bib path still INSIDE the project must keep
    # working — this isn't about forcing the literal default path.
    bib_path = tmp_path / "custom" / "refs.bib"
    bib_path.parent.mkdir(parents=True)
    bib_path.write_text("@article{x2020y,\n  title = {T},\n}\n", encoding="utf-8")
    code, out, err = run("doi2bib.py", "--verify", "--bib", "custom/refs.bib", "--json")
    assert "--bib" not in err
    assert code in (0, 2)  # ran verification (may report UNRESOLVED — no DOI field)


def test_pdf2md_rejects_out_dir_escaping_project_dir(run, tmp_path):
    code, out, err = run("pdf2md.py", "--all", "--out-dir", "../outside_md")
    assert code == 1
    assert "--out-dir" in err
    assert not (tmp_path.parent / "outside_md").exists()


def test_pdf2md_allows_custom_relative_out_dir_within_project_dir(run, tmp_path):
    code, out, err = run("pdf2md.py", "--all", "--out-dir", "custom/md", "--pdf-dir", "sources/pdf")
    assert "--out-dir" not in err
    assert code == 1
    assert "no PDFs" in err


def test_pdf2md_rejects_key_that_resolves_outside_out_dir(run, tmp_path):
    # A blacklist of '/', '\\', '..' alone still lets a Windows drive-letter
    # token through: pathlib's `/` operator silently drops the out_dir
    # operand when the right side looks drive-rooted, so
    # `Path("sources/md") / "C:evil"` resolves to "C:\\evil" — escaping
    # sources/md/ entirely without ever containing a blacklisted character.
    pdf_path = tmp_path / "sources" / "pdf" / "in.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/in.pdf", "--key", "C:evil")
    assert code == 1
    assert "invalid key" in err


def test_pdf2md_still_allows_ordinary_key(run, tmp_path):
    pdf_path = tmp_path / "sources" / "pdf" / "in.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/in.pdf", "--key", "kaya2023deep")
    # Must get past the key-containment guard; only fails downstream because
    # this isn't a real PDF for pymupdf4llm to parse.
    assert "invalid key" not in err


def test_qa_inspect_pdf_pages_rejects_path_escaping_project_dir(run, tmp_path):
    code, out, err = run("qa_inspect.py", "pdf-pages", "../outside.pdf")
    assert code == 1
    assert "pdf" in err


def test_qa_inspect_xlsx_sheets_rejects_path_escaping_project_dir(run, tmp_path):
    code, out, err = run("qa_inspect.py", "xlsx-sheets", "../outside.xlsx")
    assert code == 1
    assert "xlsx" in err


def test_qa_inspect_pdf_pages_allows_path_within_project_dir(run, tmp_path):
    code, out, err = run("qa_inspect.py", "pdf-pages", "sources/pdf/missing.pdf")
    # Still fails (file doesn't exist) but must get past the path guard first,
    # i.e. fail with the "does not exist" message, not a path-escape rejection.
    assert code == 1
    assert "does not exist" in err


def test_bib_doctor_rejects_bib_escaping_project_dir(run, tmp_path):
    code, out, err = run("bib_doctor.py", "--bib", "../outside.bib")
    assert code == 1
    assert "--bib" in err


def test_bib_doctor_allows_custom_relative_bib_within_project_dir(run, tmp_path):
    bib_path = tmp_path / "custom" / "refs.bib"
    bib_path.parent.mkdir(parents=True)
    bib_path.write_text(
        "@article{x2020y,\n  title = {T},\n  author = {A, B},\n"
        "  journal = {J},\n  year = {2020},\n}\n", encoding="utf-8")
    code, out, err = run("bib_doctor.py", "--bib", "custom/refs.bib", "--json")
    assert "--bib" not in err
    assert code in (0, 2)  # ran the real audit (may report problems)


def test_update_data_rejects_dir_escaping_project_dir(run, tmp_path):
    code, out, err = run("update_data.py", "--dir", "../outside_data")
    assert code == 1
    assert "--dir" in err
    assert not (tmp_path.parent / "outside_data").exists()


def test_xlsx_export_rejects_out_escaping_project_dir(run, tmp_path):
    code, out, err = run("xlsx_export.py", "--out", "../outside.xlsx")
    assert code == 1
    assert "--out" in err
    assert not (tmp_path.parent / "outside.xlsx").exists()


def test_xlsx_export_allows_custom_relative_out_within_project_dir(run, tmp_path, sample_registry):
    code, out, err = run("xlsx_export.py", "--out", "custom/matrix.xlsx", "--sheet", "screening")
    assert "--out" not in err
    assert code == 0, err
    assert (tmp_path / "custom" / "matrix.xlsx").exists()


def test_prisma_flow_rejects_out_dir_escaping_project_dir(run, tmp_path):
    code, out, err = run("prisma_flow.py", "--out-dir", "../outside_outline", "--counts", "{}")
    assert code == 1
    assert "--out-dir" in err
    assert not (tmp_path.parent / "outside_outline").exists()


def test_prisma_flow_allows_custom_relative_out_dir_within_project_dir(run, tmp_path):
    counts = json.dumps({"identified": 10, "duplicates": 2, "screened": 8,
                          "excluded_screening": 2, "fulltext": 6,
                          "excluded_fulltext": 1, "included": 5})
    code, out, err = run("prisma_flow.py", "--out-dir", "custom/outline", "--counts", counts)
    assert "--out-dir" not in err
    assert (tmp_path / "custom" / "outline").exists()


def test_make_reference_docx_rejects_out_escaping_project_dir(run, tmp_path):
    code, out, err = run("make_reference_docx.py", "--out", "../outside.docx")
    assert code == 1
    assert "--out" in err
    assert not (tmp_path.parent / "outside.docx").exists()


def test_make_reference_docx_allows_custom_relative_out_within_project_dir(run, tmp_path):
    code, out, err = run("make_reference_docx.py", "--out", "custom/reference.docx")
    assert "--out" not in err
    assert code == 0, err
    assert (tmp_path / "custom" / "reference.docx").exists()


def test_venue_check_rejects_cache_escaping_project_dir(run, tmp_path):
    code, out, err = run("venue_check.py", "--cache", "../outside_venues.jsonl", "--issn", "12345678")
    assert code == 1
    assert "--cache" in err
    assert not (tmp_path.parent / "outside_venues.jsonl").exists()


def test_venue_check_allows_custom_relative_cache_within_project_dir(run, tmp_path):
    # --set-wos none writes via cache_put with no network lookup — keeps this a fast,
    # offline-safe check of the path-validation branch specifically.
    code, out, err = run("venue_check.py", "--cache", "custom/venues.jsonl",
                         "--issn", "12345678", "--set-wos", "none")
    assert "--cache" not in err
    assert code == 0, err
    assert (tmp_path / "custom" / "venues.jsonl").exists()


def test_patch_hook_interpreter_rejects_settings_escaping_project_dir(run, tmp_path):
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                         "--settings", "../outside_settings.json")
    assert code == 1
    assert "--settings" in err


def test_patch_hook_interpreter_allows_custom_relative_settings_within_project_dir(run, tmp_path):
    settings_path = tmp_path / "custom" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                         "--settings", "custom/settings.json")
    assert "--settings" not in err


def test_cite_audit_rejects_bib_escaping_project_dir(run, tmp_path):
    code, out, err = run("cite_audit.py", "--bib", "../outside.bib")
    assert code == 1
    assert "--bib" in err


def test_cite_audit_rejects_drafts_escaping_project_dir(run, tmp_path):
    code, out, err = run("cite_audit.py", "--drafts", "../outside_drafts")
    assert code == 1
    assert "--drafts" in err


def test_cite_audit_rejects_file_escaping_project_dir(run, tmp_path):
    code, out, err = run("cite_audit.py", "--file", "../outside.md")
    assert code == 1
    assert "--file" in err


def test_cite_audit_allows_custom_relative_paths_within_project_dir(run, tmp_path):
    drafts = tmp_path / "custom" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "intro.md").write_text("Some text [@kaya2023deep].\n", encoding="utf-8")
    code, out, err = run("cite_audit.py", "--drafts", "custom/drafts",
                         "--bib", "custom/refs.bib", "--json")
    assert "--drafts" not in err
    assert "--bib" not in err
    assert code in (0, 2)
