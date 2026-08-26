"""The run record (scripts/experiment_db.py) and the environment it ran in.

"The model reached 0.94" is the sentence an empirical paper is built on, and
nothing in this kit could previously answer which run produced it, with which
seed, on which data. These tests pin the four refusals that make the record worth
having: no seed, no unregistered dataset, no winner, and no recomputation of
metrics it never saw.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import env_capture  # noqa: E402
import experiment_db  # noqa: E402

RUN = {"experiment": "baselines", "model": "lightgbm", "dataset": "DS-0001",
       "seed": 42, "metrics": {"roc_auc": 0.809}}


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "experiment_db.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path: Path, datasets=("DS-0001",)) -> Path:
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "analysis" / "datasets.jsonl").write_text(
        "".join(json.dumps({"id": d, "name": d, "source": "uci"}) + "\n" for d in datasets),
        encoding="utf-8")
    return tmp_path


def _add(tmp_path, **overrides):
    return _run(tmp_path, "add", "--payload", json.dumps({**RUN, **overrides}))


def _records(tmp_path):
    text = (tmp_path / "analysis" / "runs.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------- what it refuses ----------

def test_a_run_with_no_seed_is_refused(tmp_path):
    """Not defaulted to 0, not recorded as unset. A run nobody can repeat is not
    evidence, and this is the field most easily left out."""
    _project(tmp_path)
    payload = {k: v for k, v in RUN.items() if k != "seed"}
    proc = _run(tmp_path, "add", "--payload", json.dumps(payload), expect=1)
    assert "seed" in proc.stderr and "repeat" in proc.stderr


def test_a_boolean_seed_is_not_an_integer(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "add", "--payload", json.dumps({**RUN, "seed": True}), expect=1)


def test_a_run_pointing_at_unregistered_data_is_refused(tmp_path):
    _project(tmp_path)
    proc = _run(tmp_path, "add", "--payload", json.dumps({**RUN, "dataset": "DS-9999"}),
                expect=1)
    assert "not in" in proc.stderr


def test_a_run_with_no_dataset_names_the_fix(tmp_path):
    _project(tmp_path)
    payload = {k: v for k, v in RUN.items() if k != "dataset"}
    proc = _run(tmp_path, "add", "--payload", json.dumps(payload), expect=1)
    assert "/find-dataset" in proc.stderr


def test_a_missing_dataset_register_is_refused_rather_than_skipped(tmp_path):
    # The check must not quietly pass just because the file it reads is absent.
    (tmp_path / "analysis").mkdir()
    proc = _run(tmp_path, "add", "--payload", json.dumps(RUN), expect=1)
    assert "does not exist" in proc.stderr


def test_a_non_numeric_metric_is_refused(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "add", "--payload",
         json.dumps({**RUN, "metrics": {"roc_auc": "high"}}), expect=1)


def test_empty_metrics_are_refused(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "add", "--payload", json.dumps({**RUN, "metrics": {}}), expect=1)


def test_no_flag_declares_a_winner(tmp_path):
    """Which mean is larger is not the question a paper answers, and a --best flag
    would let a session skip the paired test that answers the real one."""
    _project(tmp_path)
    _add(tmp_path)
    proc = subprocess.run([sys.executable, str(SCRIPTS / "experiment_db.py"), "summary", "--help"],
                          cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert "--best" not in proc.stdout
    out = json.loads(_run(tmp_path, "summary").stdout)
    assert "no ranking" in out["note"]


# ---------- what it records ----------

def test_the_configuration_is_hashed_canonically(tmp_path):
    # The same configuration typed twice must hash the same, whatever the key order.
    a = experiment_db.config_hash({"lr": 0.1, "depth": 6})
    b = experiment_db.config_hash({"depth": 6, "lr": 0.1})
    assert a == b and len(a) == 64


def test_a_run_is_stored_with_its_hash_and_a_timestamp(tmp_path):
    _project(tmp_path)
    _add(tmp_path, config={"lr": 0.1})
    rec = _records(tmp_path)[0]
    assert rec["id"] == "RUN-0001"
    assert rec["config_hash"] == experiment_db.config_hash({"lr": 0.1})
    assert rec["recorded_at"]


def test_summary_reports_spread_and_the_seeds_behind_it(tmp_path):
    _project(tmp_path)
    for seed, auc in ((42, 0.80), (43, 0.82), (44, 0.84)):
        _add(tmp_path, seed=seed, metrics={"roc_auc": auc})
    group = json.loads(_run(tmp_path, "summary").stdout)["groups"][0]
    assert group["seeds"] == [42, 43, 44] and group["runs"] == 3
    assert round(group["metrics"]["roc_auc"]["mean"], 3) == 0.82
    assert group["metrics"]["roc_auc"]["std"] is not None
    assert group["single_seed"] is False


def test_a_single_run_reports_no_standard_deviation_rather_than_zero(tmp_path):
    # A zero would read as "perfectly stable" when the truth is "measured once".
    _project(tmp_path)
    _add(tmp_path)
    group = json.loads(_run(tmp_path, "summary").stdout)["groups"][0]
    assert group["metrics"]["roc_auc"]["std"] is None
    assert group["single_seed"] is True


# ---------- trace: where did this number come from ----------

def test_trace_finds_the_run_behind_a_reported_number(tmp_path):
    _project(tmp_path)
    _add(tmp_path, metrics={"roc_auc": 0.80912})
    out = json.loads(_run(tmp_path, "trace", "0.809").stdout)
    assert [m["id"] for m in out["matches"]] == ["RUN-0001"]
    assert out["matches"][0]["seed"] == 42


def test_a_number_no_run_produced_exits_two(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    out = json.loads(_run(tmp_path, "trace", "0.94", expect=2).stdout)
    assert out["matches"] == []
    assert "never recorded" in out["note"]


# ---------- verify ----------

def test_verify_catches_a_record_edited_after_it_was_written(tmp_path):
    _project(tmp_path)
    for seed in (42, 43, 44):
        _add(tmp_path, seed=seed, config={"lr": 0.1})
    path = tmp_path / "analysis" / "runs.jsonl"
    records = _records(tmp_path)
    records[0]["config"] = {"lr": 0.5}  # the hash still says 0.1
    path.chmod(0o644)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert any("config_hash" in p["problem"] for p in out["problems"])


def test_verify_reports_a_group_with_too_few_seeds(tmp_path):
    _project(tmp_path)
    _add(tmp_path)
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert any("seed" in p["problem"] for p in out["problems"])


def test_verify_reports_a_run_with_no_environment(tmp_path):
    _project(tmp_path)
    for seed in (42, 43, 44):
        _add(tmp_path, seed=seed)
    out = json.loads(_run(tmp_path, "verify", expect=2).stdout)
    assert any("env_capture" in p["problem"] for p in out["problems"])


def test_a_fully_recorded_experiment_passes(tmp_path):
    _project(tmp_path)
    env, _ = env_capture.capture(["numpy"])
    for seed in (42, 43, 44):
        _add(tmp_path, seed=seed, env=env)
    assert json.loads(_run(tmp_path, "verify").stdout)["result"] == "PASS"


# ---------- the environment ----------

def test_the_environment_carries_no_identity():
    """A hostname or a working directory would travel with every attestation and
    is no part of an experiment's identity."""
    import getpass
    import socket
    env, _ = env_capture.capture(["numpy"])
    blob = json.dumps(env)
    assert socket.gethostname() not in blob
    assert getpass.getuser() not in blob
    assert str(Path.cwd()) not in blob


def test_a_named_package_that_is_absent_is_reported_not_invented():
    env, missing = env_capture.capture(["definitely-not-installed-xyz"])
    assert missing == ["definitely-not-installed-xyz"]
    assert env["packages"] == {}


def test_the_environment_hash_changes_with_the_environment():
    a, _ = env_capture.capture(["numpy"])
    b = dict(a, packages={**a["packages"], "numpy": "0.0.1"})
    import hashlib
    b.pop("hash")
    rehashed = hashlib.sha256(
        json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    assert rehashed != a["hash"]


def test_the_run_record_is_a_protected_data_file():
    from lib_common import is_protected_data_file
    assert is_protected_data_file("analysis/runs.jsonl")


# ---------- --model: the disclosure field the kit could not produce ----------
# compliance_gen.py makes --tool and --uses mandatory for an AI disclosure, and
# a venue wants the version too — while env_capture recorded Python, platform
# and packages, and not the model. The version had to come from session logs
# outside the kit, where a reader of the repo cannot verify it.

def _fake_transcripts(tmp_path, rows):
    """Write a Claude Code-shaped transcript dir for a fake project root."""
    import re as _re
    root = tmp_path / "proj"
    root.mkdir()
    slug = _re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))
    d = tmp_path / "home" / ".claude" / "projects" / slug
    d.mkdir(parents=True)
    with (d / "s1.jsonl").open("w", encoding="utf-8") as f:
        for model in rows:
            f.write(json.dumps({"type": "assistant",
                                "message": {"model": model, "content": []}}) + "\n")
        f.write('{"type": "assistant", "message": {"model"\n')   # truncated line
    return root, d


def test_producing_models_counts_rather_than_names(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    root, _ = _fake_transcripts(tmp_path, ["claude-opus-5"] * 3 + ["claude-sonnet-5"])
    out = env_capture.producing_models(root)
    assert out["status"] == "counted"
    assert out["models"] == {"claude-opus-5": 3, "claude-sonnet-5": 1}
    assert out["turns"] == 4          # the truncated final line is skipped, not guessed


def test_producing_models_ignores_synthetic_turns(tmp_path, monkeypatch):
    # `<synthetic>` marks a harness-generated turn. Counting it would put a
    # model identity in the record for output no model produced.
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    root, _ = _fake_transcripts(tmp_path, ["claude-opus-5", "<synthetic>", "<synthetic>"])
    out = env_capture.producing_models(root)
    assert out["models"] == {"claude-opus-5": 1}


def test_producing_models_reports_unavailable_rather_than_a_plausible_name(tmp_path, monkeypatch):
    # The whole point: an unfound model is not an absent one, and it is
    # certainly not a licence to write "claude-opus-5" because that sounds right.
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    root = tmp_path / "proj"
    root.mkdir()
    out = env_capture.producing_models(root)
    assert out["status"] == "unavailable"
    assert "models" not in out
    assert out["transcript_dir"]      # says where it looked


def test_model_block_is_outside_the_environment_hash(tmp_path, monkeypatch):
    # The hash compares ENVIRONMENTS. A later session appending turns must not
    # change the fingerprint of an environment that did not move.
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    root, d = _fake_transcripts(tmp_path, ["claude-opus-5"])
    first, _ = env_capture.capture(["numpy"], False, root)
    with (d / "s2.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant",
                            "message": {"model": "claude-opus-5"}}) + "\n")
    second, _ = env_capture.capture(["numpy"], False, root)
    assert first["hash"] == second["hash"]
    assert second["produced_by"]["turns"] > first["produced_by"]["turns"]


def test_capture_omits_the_model_block_unless_asked(tmp_path):
    env, _ = env_capture.capture(["numpy"])
    assert "produced_by" not in env
