"""The dataset register (scripts/dataset_db.py).

The link the chain was missing: the data an analysis ran on had no version, no
licence, no citation and no checksum, so "we used the X dataset" rested on
nothing. What these tests pin is mostly what the register refuses to say on the
author's behalf — a licence it did not read, a row count it did not measure, and
an ethics judgement that belongs to an institution.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dataset_db  # noqa: E402,F401  (import smoke: the module must load)

BASE = {"name": "CWRU Bearing", "source": "uci", "url": "https://example.org/cwru",
        "version": "1.0", "task": "classification"}


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "dataset_db.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path: Path, rows: int = 2) -> Path:
    (tmp_path / "analysis" / "data").mkdir(parents=True, exist_ok=True)
    body = "a,b\n" + "".join(f"{i},{i * 2}\n" for i in range(rows))
    (tmp_path / "analysis" / "data" / "train.csv").write_text(body, encoding="utf-8")
    return tmp_path


def _records(tmp_path: Path) -> list[dict]:
    text = (tmp_path / "analysis" / "datasets.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _add(tmp_path, **overrides):
    payload = {**BASE, **overrides}
    return _run(tmp_path, "add", "--payload", json.dumps(payload))


# ---------- what it records ----------

def test_a_dataset_is_registered_with_an_id(tmp_path):
    _project(tmp_path)
    out = json.loads(_add(tmp_path).stdout)
    assert out["added"] == ["DS-0001"]


def test_attach_measures_the_file_rather_than_believing_a_description(tmp_path):
    _project(tmp_path, rows=7)
    _add(tmp_path)
    out = json.loads(_run(tmp_path, "attach", "DS-0001", "analysis/data/train.csv").stdout)
    assert out["n_rows"] == 7, "the header row must not be counted as data"
    rec = _records(tmp_path)[0]
    assert len(rec["files"][0]["sha256"]) == 64 and rec["files"][0]["bytes"] > 0


def test_row_counting_is_declined_for_a_format_it_cannot_read(tmp_path):
    # A row count is a measurement. There is no honest measurement of "rows" in a
    # directory of images, and guessing one would put a number in the methods
    # section that nothing produced.
    _project(tmp_path)
    (tmp_path / "analysis" / "data" / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
    _add(tmp_path)
    _run(tmp_path, "attach", "DS-0001", "analysis/data/scan.png")
    rec = _records(tmp_path)[0]
    assert rec["files"][0]["rows"] is None
    assert "n_rows" not in rec


# ---------- what it refuses ----------

def test_an_unread_licence_is_recorded_as_unknown_not_as_permission(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    rec = _records(tmp_path)[0]
    assert rec["license"] == "unknown" and rec["license_verified"] is False


def test_a_recorded_licence_is_not_a_verified_one(tmp_path):
    # Copying what a dataset page claims and reading the licence itself are two
    # different claims, and the register keeps them apart.
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0")
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    problems = out["datasets"][0]["problems"]
    assert any("not verified" in p for p in problems)


def test_undeclared_human_subjects_are_not_read_as_no(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    assert _records(tmp_path)[0]["ethics"]["human_subjects"] is None


def test_human_subjects_without_an_ethics_reference_is_a_finding(tmp_path):
    _project(tmp_path)
    _add(tmp_path, ethics={"human_subjects": True, "pii": "removed"})
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert any("IRB" in p for p in out["datasets"][0]["problems"])


def test_an_invented_source_is_refused_but_other_is_allowed(tmp_path):
    _project(tmp_path)
    proc = _run(tmp_path, "add", "--payload", json.dumps({**BASE, "source": "definitely-real"}),
                expect=1)
    assert "not in" in proc.stderr
    _run(tmp_path, "add", "--payload", json.dumps({**BASE, "source": "other"}))


def test_a_checksum_cannot_be_typed_in(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    proc = _run(tmp_path, "set-field", "DS-0001", "files", "[]", expect=1)
    assert "measured" in proc.stderr


# ---------- verify: bytes and paperwork are different findings ----------

def test_verify_reports_drift_when_the_data_changed_under_the_record(tmp_path):
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0", license_verified=True,
         citation={"doi": "10.1234/x"})
    _run(tmp_path, "attach", "DS-0001", "analysis/data/train.csv")
    _run(tmp_path, "verify")  # PASS while the bytes are untouched
    (tmp_path / "analysis" / "data" / "train.csv").write_text("a,b\n9,9\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert out["datasets"][0]["status"] == "DRIFT"


def test_verify_separates_a_missing_file_from_a_changed_one(tmp_path):
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0", license_verified=True, citation={"doi": "10.1234/x"})
    _run(tmp_path, "attach", "DS-0001", "analysis/data/train.csv")
    (tmp_path / "analysis" / "data" / "train.csv").unlink()
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert out["datasets"][0]["status"] == "MISSING"
    assert out["datasets"][0]["missing"] == ["analysis/data/train.csv"]


def test_a_record_with_no_files_cannot_pass(tmp_path):
    # Nothing binds it to bytes on disk, which is the whole point of the record.
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0", license_verified=True, citation={"doi": "10.1234/x"})
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert any("no files attached" in p for p in out["datasets"][0]["problems"])


def test_a_complete_record_passes(tmp_path):
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0", license_verified=True,
         citation={"doi": "10.1234/x", "bib_key": "cwru1998"},
         ethics={"human_subjects": False, "pii": "none", "irb": "n/a"})
    _run(tmp_path, "attach", "DS-0001", "analysis/data/train.csv")
    out = json.loads(_run(tmp_path, "verify").stdout)
    assert out["result"] == "PASS"


# ---------- identity ----------

def test_the_same_dataset_at_a_different_version_is_not_a_duplicate(tmp_path):
    # ImageNet-1k and ImageNet-21k are not the same data; a register that
    # collapsed them would make two methods sections describe each other.
    _project(tmp_path)
    _add(tmp_path)
    out = json.loads(_add(tmp_path, version="2.0").stdout)
    assert out["added"] == ["DS-0002"] and out["duplicates"] == []


def test_the_same_dataset_at_the_same_version_is_flagged(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    out = json.loads(_add(tmp_path).stdout)
    assert out["duplicates"] == ["DS-0002"]
    assert _records(tmp_path)[1]["duplicate_of"] == "DS-0001"


# ---------- CLI contract ----------

def test_stats_counts_what_a_reader_would_check(tmp_path):
    _project(tmp_path)
    _add(tmp_path, license="CC-BY-4.0", license_verified=True, citation={"doi": "10.1/x"})
    _add(tmp_path, version="2.0")
    out = json.loads(_run(tmp_path, "stats").stdout)
    assert out["total"] == 2 and out["with_citation"] == 1 and out["license_verified"] == 1


def test_verify_on_an_empty_register_is_an_error_not_a_pass(tmp_path):
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis" / "datasets.jsonl").write_text("", encoding="utf-8")
    proc = _run(tmp_path, "verify", expect=1)
    assert "no datasets" in proc.stderr


def test_a_register_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--file", "../elsewhere.jsonl", "stats", expect=1)
    assert "--file" in proc.stderr


def test_the_register_is_a_protected_data_file():
    """It carries the checksums the drift report is read from. A hash anyone can
    edit as easily as the file it describes reports nothing."""
    from lib_common import is_protected_data_file
    assert is_protected_data_file("analysis/datasets.jsonl")
