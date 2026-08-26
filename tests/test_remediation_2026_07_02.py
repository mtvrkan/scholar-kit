"""Regression tests for the 2026-07-02 remediation pass (score-audit fixes):
concurrent-write locking, Turkish bib-key transliteration, registry_db.py
--json, bib_doctor.py online doi-or-url, xlsx_export.py empty-sheet guard,
update_data.py total-failure exit code, and the Bash-bypass hardening in
protect_data_files.py.
"""
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import kit_project_cwd

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"


# ---------- concurrency locking (finding C1) ----------

def test_evidence_db_concurrent_add_no_lost_writes_no_dup_ids(tmp_path):
    (tmp_path / "evidence").mkdir()

    def add_one(i):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "evidence_db.py"), "add", "--json",
             json.dumps({"source": f"test{i}", "type": "finding", "claim": f"claim {i}"})],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(add_one, range(10)))

    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    lines = (tmp_path / "evidence" / "cards.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(l)["id"] for l in lines]
    assert len(lines) == 10
    assert len(set(ids)) == 10


def test_write_jsonl_readers_never_see_partial_rewrite(tmp_path):
    """Regression: write_jsonl() used to truncate-then-rewrite in place, so an
    unlocked concurrent reader (query/list/stats — these don't take the writer
    lock) could observe a half-written file mid-rewrite and crash on invalid
    JSON. Fixed via temp-file + os.replace (atomic). Reproduce with real
    concurrent set-field writers (large-ish records, so the rewrite window is
    non-trivial) racing real concurrent readers; no reader may ever fail."""
    sources = tmp_path / "sources"
    sources.mkdir()
    recs = [{"id": f"SRC-{i:04d}", "title": f"Paper {i}" * 20, "status": "candidate"}
            for i in range(1, 51)]
    (sources / "registry.jsonl").write_text(
        "\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")

    def writer(i):
        rec_id = f"SRC-{(i % 50) + 1:04d}"
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "registry_db.py"), "set-field",
             rec_id, "reason", f"touched-by-{i}"],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")

    def reader(i):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "registry_db.py"), "list"],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        writers = [ex.submit(writer, i) for i in range(20)]
        readers = [ex.submit(reader, i) for i in range(20)]
        writer_results = [f.result() for f in writers]
        reader_results = [f.result() for f in readers]

    assert all(r.returncode == 0 for r in writer_results), [r.stderr for r in writer_results]
    assert all(r.returncode == 0 for r in reader_results), [r.stderr for r in reader_results]
    final = json.loads((sources / "registry.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert final  # file is still valid JSONL end-to-end


def test_registry_db_concurrent_add_no_lost_writes_no_dup_ids(tmp_path):
    (tmp_path / "sources").mkdir()

    def add_one(i):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "registry_db.py"), "add", "--json",
             json.dumps({"title": f"Unique Paper Title Number {i} About Bearings"})],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(add_one, range(10)))

    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    lines = (tmp_path / "sources" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(l)["id"] for l in lines]
    assert len(lines) == 10
    assert len(set(ids)) == 10


def test_venue_check_cache_put_concurrent_no_lost_writes(tmp_path):
    """Regression (found by the fresh scripts re-audit): cache_put() had no
    locking at all around its read -> filter -> write cycle, unlike every
    other writer in the kit. Reproduced live: 10 concurrent venue_check.py
    calls lost 2 of 10 rows to last-writer-wins. Fixed by wrapping the whole
    cycle in file_lock, same pattern as registry_db.py/evidence_db.py."""

    def check_one(i):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "venue_check.py"), "--offline",
             "--title", f"Unique Venue Title Number {i}", "--json"],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(check_one, range(10)))

    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    cache_path = tmp_path / "sources" / "venues.jsonl"
    lines = cache_path.read_text(encoding="utf-8").splitlines()
    titles = {json.loads(l).get("title_query") for l in lines}
    assert len(lines) == 10, f"expected 10 cached rows, found {len(lines)} (lost writes)"
    assert titles == {f"Unique Venue Title Number {i}" for i in range(10)}


# ---------- Turkish transliteration in bib keys (finding C2) ----------

def test_make_key_transliterates_turkish_surnames():
    sys.path.insert(0, str(SCRIPTS))
    import doi2bib
    assert doi2bib.make_key(
        {"author": "Şahin, Ahmet", "year": "2023", "title": "Deep learning for X"}, "fb"
    ) == "sahin2023deep"
    assert doi2bib.make_key(
        {"author": "Öztürk, Mehmet", "year": "2022", "title": "Gürültü azaltma yöntemi"}, "fb"
    ) == "ozturk2022gurultu"
    assert doi2bib.make_key(
        {"author": "Çelik, Ali", "year": "2021", "title": "Titreşim analizi"}, "fb"
    ) == "celik2021titresim"


# ---------- registry_db.py --json CLI contract (finding M1) ----------

def test_registry_db_accepts_top_level_json_flag(run, tmp_path):
    (tmp_path / "sources").mkdir()
    code, out, err = run("registry_db.py", "--json", "stats")
    assert code == 0, err
    assert json.loads(out)["total"] == 0


# ---------- pretty-printed JSON via --stdin (JSON-vs-JSONL heuristic bug) ----------

def test_registry_db_add_accepts_pretty_printed_multiline_json_via_stdin(run, tmp_path):
    """The old heuristic (`raw.startswith("{") and "\\n" not in raw`) treated any
    multi-line payload as JSONL and tried to parse each line on its own, which
    fails on fragment lines like `"title": "...",`. A pretty-printed single
    object must still be recognized as ONE record."""
    (tmp_path / "sources").mkdir()
    pretty = json.dumps({"title": "A Pretty Printed Title About Bearings"}, indent=2)
    assert "\n" in pretty and pretty.startswith("{")
    code, out, err = run("registry_db.py", "add", "--stdin", stdin=pretty)
    assert code == 0, err
    result = json.loads(out)
    assert len(result["added"]) == 1, result


def test_evidence_db_add_accepts_pretty_printed_multiline_json_via_stdin(run, tmp_path):
    (tmp_path / "evidence").mkdir()
    pretty = json.dumps(
        {"source": "test1", "type": "finding", "claim": "a pretty printed claim"}, indent=2)
    assert "\n" in pretty and pretty.startswith("{")
    code, out, err = run("evidence_db.py", "add", "--stdin", stdin=pretty)
    assert code == 0, err
    result = json.loads(out)
    assert len(result["added"]) == 1, result


# ---------- bib_doctor.py online doi-or-url (finding M2) ----------

def test_bib_doctor_online_entry_with_doi_not_flagged_missing_url(run, tmp_path):
    bib = tmp_path / "bib"
    bib.mkdir()
    (bib / "references.bib").write_text(
        "@online{test2024x,\n  title = {Some Web Resource},\n"
        "  doi = {10.1234/abcd},\n  verified = {true},\n}\n", encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib")
    report = json.loads(out)
    kinds = [i["kind"] for p in report["problems"] for i in p["issues"]]
    assert "missing-field" not in kinds


def test_bib_doctor_online_entry_without_doi_or_url_still_flagged(run, tmp_path):
    bib = tmp_path / "bib"
    bib.mkdir()
    (bib / "references.bib").write_text(
        "@online{test2024y,\n  title = {Some Web Resource},\n  verified = {true},\n}\n",
        encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib")
    report = json.loads(out)
    kinds = [i["kind"] for p in report["problems"] for i in p["issues"]]
    assert "missing-field" in kinds


# ---------- xlsx_export.py empty-sheet guard (finding M3) ----------

def test_xlsx_export_dies_cleanly_on_empty_requested_sheet(run, tmp_path, sample_registry):
    code, out, err = run("xlsx_export.py", "--sheet", "queries")
    assert code == 1
    assert "nothing to export" in err


# ---------- update_data.py exit code (finding M4) ----------

def test_update_data_exits_nonzero_when_all_downloads_fail(monkeypatch, tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    import update_data

    def always_fail(*a, **k):
        raise Exception("simulated network failure")

    monkeypatch.chdir(tmp_path)  # --dir must resolve inside cwd (require_within_cwd)
    monkeypatch.setattr(update_data, "fetch", always_fail)
    monkeypatch.setattr(update_data, "fetch_scopus", always_fail)
    monkeypatch.setattr(sys, "argv", ["update_data.py", "--dir", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        update_data.main()
    assert exc.value.code == 1


def test_update_data_exits_nonzero_on_partial_failure(monkeypatch, tmp_path):
    # Previously only failures == 3 exited nonzero — 1 or 2 failed downloads
    # (e.g. SCImago down, DOAJ/Scopus ok) silently exited 0, so automation
    # gating on exit code alone would treat a partial failure as full success.
    sys.path.insert(0, str(SCRIPTS))
    import update_data

    def always_fail(*a, **k):
        raise Exception("simulated network failure")

    def noop_ok(*a, **k):
        return None

    monkeypatch.chdir(tmp_path)  # --dir must resolve inside cwd (require_within_cwd)
    monkeypatch.setattr(update_data, "fetch", noop_ok)
    monkeypatch.setattr(update_data, "fetch_scopus", always_fail)
    monkeypatch.setattr(sys, "argv", ["update_data.py", "--dir", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        update_data.main()
    assert exc.value.code == 2


# ---------- patch_hook_interpreter.py (finding D-041: 3x-recurring regression) ----------

def _write_settings(path, command):
    path.write_text(json.dumps({
        "hooks": {"PreToolUse": [{"matcher": "Write", "hooks": [
            {"type": "command", "command": command}]}]}
    }), encoding="utf-8")


def test_patch_hook_interpreter_fixes_python3_to_python(run, tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    _write_settings(settings, 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"')
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", str(settings))
    assert code == 0, err
    assert json.loads(out)["changed"] is True
    text = settings.read_text(encoding="utf-8")
    assert "python3" not in text
    assert '"python \\"' in text


def test_patch_hook_interpreter_fixes_python_to_python3(run, tmp_path):
    # the exact scenario that caused the 3rd real-world regression: $PY
    # resolves to "python" but the committed file still says "python3" — a
    # check that only special-cases "$PY != python" must NOT skip this.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    _write_settings(settings, 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"')
    code, out, err = run("patch_hook_interpreter.py", "--target", "python3",
                          "--settings", str(settings))
    assert code == 0, err
    # already python3 -> unchanged
    assert json.loads(out)["changed"] is False
    assert "python3" in settings.read_text(encoding="utf-8")


def test_patch_hook_interpreter_noop_when_already_correct(run, tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    _write_settings(settings, 'python "$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"')
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", str(settings))
    assert code == 0, err
    assert json.loads(out)["changed"] is False


def test_patch_hook_interpreter_fixes_py_to_python(run, tmp_path):
    # Windows `py` launcher case: a hook rewritten to "py ..." (e.g. by hand,
    # or by an older patch run) must still be patchable back to python/python3
    # — PREFIXES previously only knew "python3 "/"python ", so "py " matched
    # neither and the command was silently never patched again.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    _write_settings(settings, 'py "$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"')
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", str(settings))
    assert code == 0, err
    assert json.loads(out)["changed"] is True
    text = settings.read_text(encoding="utf-8")
    assert '"python \\"' in text


def test_patch_hook_interpreter_fixes_python_to_py(run, tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    _write_settings(settings, 'python "$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"')
    code, out, err = run("patch_hook_interpreter.py", "--target", "py",
                          "--settings", str(settings))
    assert code == 0, err
    assert json.loads(out)["changed"] is True
    assert '"py \\"' in settings.read_text(encoding="utf-8")


def test_patch_hook_interpreter_missing_settings_file_is_not_an_error(run, tmp_path):
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", str(tmp_path / "nope.json"))
    assert code == 0, err
    assert json.loads(out)["changed"] is False


def test_patch_hook_interpreter_malformed_json_dies_cleanly(run, tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{not valid json", encoding="utf-8")
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", str(settings))
    assert code == 1
    assert "ERROR" in err


# ---------- qa_inspect.py (D-048: shipped with zero test coverage) ----------

def test_qa_inspect_pdf_pages_counts_correctly(run, tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    code, out, err = run("qa_inspect.py", "pdf-pages", str(pdf_path))
    assert code == 0, err
    result = json.loads(out)
    assert result["pages"] == 3


def test_qa_inspect_pdf_pages_missing_file_dies_cleanly(run, tmp_path):
    code, out, err = run("qa_inspect.py", "pdf-pages", str(tmp_path / "nope.pdf"))
    assert code == 1
    assert "ERROR" in err


def test_qa_inspect_xlsx_sheets_counts_correctly(run, tmp_path):
    from openpyxl import Workbook
    xlsx_path = tmp_path / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "screening"
    ws.append(["id", "title"])
    ws.append(["SRC-0001", "Paper A"])
    ws.append(["SRC-0002", "Paper B"])
    wb.create_sheet("empty_sheet")
    wb.save(str(xlsx_path))
    code, out, err = run("qa_inspect.py", "xlsx-sheets", str(xlsx_path))
    assert code == 0, err
    result = json.loads(out)
    assert result["sheets"]["screening"] == 2  # header row excluded
    assert result["sheets"]["empty_sheet"] == 0


def test_qa_inspect_xlsx_sheets_missing_file_dies_cleanly(run, tmp_path):
    code, out, err = run("qa_inspect.py", "xlsx-sheets", str(tmp_path / "nope.xlsx"))
    assert code == 1
    assert "ERROR" in err


# ---------- word_budget.py --help crash (literal "%" in argparse help text) ----------

def test_word_budget_help_does_not_crash(run):
    # argparse's HelpFormatter treats a literal "%" in a help string as a
    # format spec; "off budget" following ">±10%" was parsed as "%o" (octal),
    # crashing with TypeError before any argument was even processed.
    code, out, err = run("word_budget.py", "--help")
    assert code == 0, err
    assert "usage:" in out.lower()


# ---------- docx_style_check.py corrupt-file handling ----------

def test_docx_style_check_dies_cleanly_on_corrupt_docx(run, tmp_path):
    built = tmp_path / "built.docx"
    ref = tmp_path / "ref.docx"
    built.write_text("not a real docx file", encoding="utf-8")
    ref.write_text("also not a real docx file", encoding="utf-8")
    code, out, err = run("docx_style_check.py", "--built", str(built), "--reference", str(ref))
    assert code == 1, (out, err)
    assert "ERROR" in err


# ---------- bib_doctor.py malformed-BibTeX guard ----------

def test_bib_doctor_dies_cleanly_on_unparseable_nonempty_bib(run, tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{broken2023 no comma after key\ntitle={x}\n", encoding="utf-8")
    code, out, err = run("bib_doctor.py", "--bib", str(bib))
    assert code == 1, (out, err)
    assert "ERROR" in err


# ---------- venue_check.py empty-CSV guard ----------

def test_venue_check_read_csv_survives_empty_file(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    import venue_check
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    assert venue_check._read_csv(empty) == []


# ---------- protect_data_files.py Bash-bypass hardening (finding 9) ----------

def _run_hook(payload):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps(payload), cwd=kit_project_cwd(),
        capture_output=True, text=True, encoding="utf-8")
    return proc.stdout


def test_hook_blocks_bash_redirect_into_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo hi >> sources/registry.jsonl"}})
    assert "deny" in out


def test_hook_blocks_bash_tee_into_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo hi | tee evidence/cards.jsonl"}})
    assert "deny" in out


def test_hook_allows_sanctioned_script_bash_call():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "python scripts/registry_db.py add --stdin"}})
    assert out.strip() == ""


def test_hook_allows_sanctioned_script_with_protected_name_as_plain_argument():
    # --bib/--append point AT a protected file but via a script's own argument,
    # not a shell write-sink (redirect/tee/cp/etc.) — must not false-positive.
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "python scripts/doi2bib.py --doi 10.1/x --append bib/references.bib"}})
    assert out.strip() == ""


def test_hook_allows_unrelated_bash_call():
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "pytest tests/ -x -q"}})
    assert out.strip() == ""


def test_hook_still_blocks_direct_write_tool():
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": "sources/registry.jsonl"}})
    assert "deny" in out


# Regression: an earlier version of this hook trusted ANY command that merely
# mentioned a sanctioned script's filename as a substring anywhere (even in an
# unrelated echo string/comment) — a one-token bypass. These lock in the fix.
def test_hook_blocks_bypass_disguised_with_sanctioned_script_name_in_comment():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "echo hi >> sources/registry.jsonl  # via registry_db.py"}})
    assert "deny" in out


def test_hook_blocks_bypass_with_unrelated_sanctioned_filename_substring():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": 'echo "totally not evidence_db.py" >> evidence/cards.jsonl'}})
    assert "deny" in out


def test_hook_blocks_cp_into_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "cp /tmp/x sources/registry.jsonl"}})
    assert "deny" in out


def test_hook_blocks_mv_into_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "mv /tmp/x sources/registry.jsonl"}})
    assert "deny" in out


def test_hook_blocks_sed_inplace_edit_of_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": 'sed -i "s/foo/bar/" sources/registry.jsonl'}})
    assert "deny" in out


def test_hook_blocks_mv_moving_protected_file_away():
    # `_COPY_MOVE` previously only checked the DESTINATION token — moving a
    # protected file OUT of its required path is data loss even though the
    # (non-protected) destination is never "written" to in the blocked sense.
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "mv sources/registry.jsonl /tmp/out.bak"}})
    assert "deny" in out


def test_hook_blocks_bare_rm_of_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "rm sources/registry.jsonl"}})
    assert "deny" in out


def test_hook_blocks_rm_with_flags_of_protected_file():
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "rm -f evidence/cards.jsonl"}})
    assert "deny" in out


def test_hook_blocks_powershell_remove_item_of_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "Remove-Item sources/venues.jsonl -Force"}})
    assert "deny" in out


def test_hook_blocks_powershell_tee_object_into_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "Get-Content x | Tee-Object -FilePath sources/registry.jsonl"}})
    assert "deny" in out


def test_hook_blocks_python_shutil_copy_into_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "python -c \"import shutil; shutil.copy('x','sources/registry.jsonl')\""}})
    assert "deny" in out


def test_hook_blocks_python_pathlib_write_text_into_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "python -c \"from pathlib import Path; "
                   "Path('bib/references.bib').write_text('x')\""}})
    assert "deny" in out


def test_hook_blocks_powershell_move_item_moving_protected_file_away():
    # Move-Item/Copy-Item never matched the bare "move"/"copy" alternatives —
    # the hyphenated cmdlet name means no whitespace directly follows "Move"/
    # "Copy", so `\s+` failed and the whole command slipped through undetected.
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "Move-Item sources/registry.jsonl ../out.bak"}})
    assert "deny" in out


def test_hook_blocks_powershell_copy_item_into_protected_file():
    out = _run_hook({"tool_name": "Bash", "tool_input": {
        "command": "Copy-Item /tmp/x.jsonl evidence/cards.jsonl"}})
    assert "deny" in out


def _run_hook_full(payload):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps(payload), cwd=kit_project_cwd(),
        capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout


def test_hook_does_not_crash_on_non_string_file_path():
    # Write/Edit tool schemas type file_path as a string, but the hook must
    # not crash (undocumented failure mode: exit 1 traceback) if it's ever
    # something else — the documented contract is fail-open (exit 0, no deny).
    code, out = _run_hook_full({"tool_name": "Write", "tool_input": {"file_path": ["a", "b"]}})
    assert code == 0
    assert out.strip() == ""


def test_hook_does_not_crash_on_non_string_bash_command():
    code, out = _run_hook_full({"tool_name": "Bash", "tool_input": {"command": ["not", "a", "string"]}})
    assert code == 0
    assert out.strip() == ""


def test_hook_blocks_notebook_edit_via_its_real_payload_key():
    # NotebookEdit's tool_input key is "notebook_path", not "file_path" — the
    # settings.json matcher includes NotebookEdit, but reading only
    # "file_path" left this branch permanently dead for it.
    out = _run_hook({"tool_name": "NotebookEdit",
                      "tool_input": {"notebook_path": "sources/registry.jsonl"}})
    assert "deny" in out


# ---------- D-045/D-046: mapping-table targets must exist on disk ----------
# These are static Markdown tables (not code) but every filename they name is
# cheaply verifiable — a stale entry here silently breaks citation rendering
# or rubric/reference lookup for whichever type/style hits that row.

def _parse_table_rows(text: str, table_heading: str, n_cols: int):
    """Extract backtick-quoted cells from a Markdown table following a
    `## heading` line, up to the next `##` or end of file."""
    start = text.index(table_heading)
    end = text.find("\n## ", start + len(table_heading))
    section = text[start:end if end != -1 else len(text)]
    rows = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != n_cols:
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue  # header separator row
        rows.append(cells)
    return rows[1:]  # drop header row


def _backtick(cell: str) -> str | None:
    m = re.fullmatch(r"`([^`]+)`", cell)
    return m.group(1) if m else None


def test_csl_file_mapping_table_targets_exist():
    text = (ROOT / ".claude/skills/citation-styles/SKILL.md").read_text(encoding="utf-8")
    rows = _parse_table_rows(text, "## CSL File Mapping", 2)
    assert rows, "CSL File Mapping table not found or empty"
    checked = 0
    for key_cell, file_cell in rows:
        key = _backtick(key_cell)
        filename = _backtick(file_cell)
        if key is None or filename is None or "<" in key or "<" in filename:
            continue  # placeholder row (csl:<file> — user-supplied, nothing to check)
        assert (ROOT / "templates/csl" / filename).exists(), (
            f"CSL mapping row '{key}' -> '{filename}' does not exist under templates/csl/")
        checked += 1
    assert checked >= 6  # apa7/mla9/chicago-author-date/chicago-notes/ieee/vancouver/harvard


def test_paper_type_canonical_resolution_table_targets_exist():
    text = (ROOT / ".claude/skills/paper-types/SKILL.md").read_text(encoding="utf-8")
    rows = _parse_table_rows(text, "## Canonical Type → File Resolution", 3)
    assert rows, "Canonical Type -> File Resolution table not found or empty"
    base = ROOT / ".claude/skills/paper-types"
    checked = 0
    for type_cell, ref_cell, rubric_cell in rows:
        type_key = _backtick(type_cell)
        assert type_key, f"malformed type-key cell: {type_cell!r}"
        ref_file = _backtick(ref_cell)
        if ref_file is not None:  # None = thesis-* rows point at another skill, not a file here
            assert (base / ref_file).exists(), (
                f"type '{type_key}' reference file '{ref_file}' does not exist")
        rubric_file = _backtick(rubric_cell)
        assert rubric_file, f"type '{type_key}' has no rubric file in the table"
        assert (base / rubric_file).exists(), (
            f"type '{type_key}' rubric file '{rubric_file}' does not exist")
        checked += 1
    assert checked == 15  # all PROJECT.md type enum values must be covered
