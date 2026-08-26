"""The deposit-ready package (scripts/replication_pack.py).

The usual replication package is a zip of whatever was on the desktop. This one
is assembled from records that already exist — so the tests are mostly about what
it refuses to put in: data it was told not to redistribute, and a claim of
reproducibility it cannot see behind.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import replication_pack as rp  # noqa: E402

OPEN_DATASET = {"id": "DS-0001", "name": "CWRU", "license": "CC-BY-4.0",
                "license_verified": True, "citation": {"doi": "10.1/x"},
                "files": [{"path": "analysis/data/train.csv", "sha256": "a" * 64, "bytes": 10}]}
RUN = {"id": "RUN-0001", "experiment": "baselines", "model": "lgbm", "dataset": "DS-0001",
       "seed": 42, "metrics": {"roc_auc": 0.81}, "env": {"python": "3.13.5", "hash": "abc123"}}


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "replication_pack.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, datasets=(OPEN_DATASET,), runs=(RUN,), code=True, bib=True):
    (tmp_path / "analysis" / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "analysis" / "figures").mkdir(parents=True, exist_ok=True)
    (tmp_path / "analysis" / "data" / "train.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "analysis" / "figures" / "f1.png").write_bytes(b"png")
    if code:
        (tmp_path / "analysis" / "01_eda.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "analysis" / "datasets.jsonl").write_text(
        "".join(json.dumps(d) + "\n" for d in datasets), encoding="utf-8")
    (tmp_path / "analysis" / "runs.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    if bib:
        (tmp_path / "bib").mkdir(exist_ok=True)
        (tmp_path / "bib" / "references.bib").write_text("@article{a, title={T}}\n",
                                                         encoding="utf-8")
    (tmp_path / "PROJECT.md").write_text("- **Title (working):** A real study\n",
                                          encoding="utf-8")
    return tmp_path


# ---------- what it refuses to redistribute ----------

def test_human_subject_data_is_never_copied(tmp_path):
    """The alternative is a data-protection incident with a DOI on it."""
    d = {**OPEN_DATASET, "ethics": {"human_subjects": True, "pii": "pseudonymised"}}
    _project(tmp_path, datasets=(d,))
    # Exit 0: data that cannot be shared is a correct package, not an incomplete
    # one. The gaps list is about what the package fails to ESTABLISH.
    out = json.loads(_run(tmp_path, "--build").stdout)
    assert out["datasets_included"] == []
    assert "human-subjects" in out["datasets_referenced_only"][0]["excluded_because"]


def test_an_unknown_licence_is_not_permission_to_redistribute(tmp_path):
    _project(tmp_path, datasets=({**OPEN_DATASET, "license": "unknown"},))
    out = json.loads(_run(tmp_path, "--build").stdout)
    assert out["datasets_included"] == []


def test_a_no_derivatives_licence_is_respected(tmp_path):
    _project(tmp_path, datasets=({**OPEN_DATASET, "license": "CC-BY-ND-4.0"},))
    out = json.loads(_run(tmp_path, "--build").stdout)
    assert "restricts redistribution" in out["datasets_referenced_only"][0]["excluded_because"]


def test_data_files_are_never_copied_but_their_checksums_travel(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "--build")
    package = tmp_path / "exports" / "replication"
    assert not (package / "data").exists() and not (package / "train.csv").exists()
    manifest = json.loads((package / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "analysis/data/train.csv" in manifest["data_files_not_included"]


# ---------- what it refuses to claim ----------

def test_runs_without_an_environment_are_reported_as_a_gap(tmp_path):
    _project(tmp_path, runs=({k: v for k, v in RUN.items() if k != "env"},))
    out = json.loads(_run(tmp_path, "--build", expect=2).stdout)
    assert any("environment" in g for g in out["gaps"])


def test_the_readme_says_when_no_environment_was_recorded(tmp_path):
    _project(tmp_path, runs=({k: v for k, v in RUN.items() if k != "env"},))
    _run(tmp_path, "--build", expect=2)
    readme = (tmp_path / "exports" / "replication" / "README.md").read_text(encoding="utf-8")
    assert "No environment was recorded" in readme


def test_no_runs_at_all_is_a_named_gap(tmp_path):
    _project(tmp_path, runs=())
    out = json.loads(_run(tmp_path, "--build", expect=2).stdout)
    assert any("/experiment" in g for g in out["gaps"])


def test_a_package_with_no_code_says_it_is_a_data_deposit(tmp_path):
    _project(tmp_path, code=False)
    out = json.loads(_run(tmp_path, "--build", expect=2).stdout)
    assert any("data deposit" in g for g in out["gaps"])


def test_the_gaps_are_written_into_the_readme(tmp_path):
    # A reader of the package sees the same limits the author saw.
    _project(tmp_path, runs=())
    _run(tmp_path, "--build", expect=2)
    readme = (tmp_path / "exports" / "replication" / "README.md").read_text(encoding="utf-8")
    assert "does NOT establish" in readme


# ---------- what it does assemble ----------

def test_a_complete_project_builds_and_exits_zero(tmp_path):
    _project(tmp_path)
    out = json.loads(_run(tmp_path, "--build").stdout)
    assert out["result"] == "COMPLETE"
    package = tmp_path / "exports" / "replication"
    for name in ("README.md", "MANIFEST.json", "ENVIRONMENT.json", "runs.jsonl",
                 "datasets.jsonl", "01_eda.py", "references.bib"):
        assert (package / name).exists(), name


def test_the_manifest_hashes_every_copied_file(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "--build")
    package = tmp_path / "exports" / "replication"
    manifest = json.loads((package / "MANIFEST.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        assert rp.sha256_of(package / name) == digest, name


def test_the_readme_states_the_seeds_and_the_licence(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "--build")
    readme = (tmp_path / "exports" / "replication" / "README.md").read_text(encoding="utf-8")
    assert "42" in readme and "CC-BY-4.0" in readme and "A real study" in readme


def test_plan_is_the_default_and_writes_nothing(tmp_path):
    _project(tmp_path)
    _run(tmp_path)
    assert not (tmp_path / "exports").exists()


# ---------- CLI contract ----------

def test_a_project_with_no_analysis_at_all_is_refused(tmp_path):
    proc = _run(tmp_path, expect=1)
    assert "no analysis here" in proc.stderr


def test_a_path_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--out", "../elsewhere", expect=1)
    assert "--out" in proc.stderr
