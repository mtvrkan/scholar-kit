"""Tests for screening_score.py — the kit's screening decisions vs the user's.

Most of these pin refusals rather than arithmetic. The script's value is that it
declines to produce a number when the number would not mean what a reader takes
it to mean: too few records, a degenerate κ, unresolved gold entries, or labels
that were in scope while the decision was made.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import screening_score as ss  # noqa: E402


def _write(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")
    return path


def _gold(rows):
    """The in-memory equivalent of load_gold(), so scoring can be tested without
    a file per case."""
    out = []
    for r in rows:
        key = r.get("id") or r.get("doi") or r.get("bib_key")
        out.append({"key": key, "norm": str(key).lower(), "label": r["label"],
                    "note": r.get("note")})
    return out


def _corpus(n_include=15, n_exclude=15, kit_agrees=True):
    gold, reg = [], []
    for i in range(n_include):
        rid = f"SRC-{i:04d}"
        gold.append({"id": rid, "label": "include"})
        reg.append({"id": rid, "status": "included" if kit_agrees else "excluded",
                    "stage": "screening"})
    for j in range(n_exclude):
        rid = f"SRC-{100 + j:04d}"
        gold.append({"id": rid, "label": "exclude"})
        reg.append({"id": rid, "status": "excluded", "stage": "screening"})
    return gold, reg


# ------------------------------------------------------------------ arithmetic

def test_perfect_agreement_scores_one_across_the_board():
    gold, reg = _corpus()
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["scored"] == 30
    assert r["recall"] == 1.0 and r["precision"] == 1.0 and r["f1"] == 1.0
    assert r["cohen_kappa"] == 1.0
    assert r["missed_includes"] == [] and r["false_includes"] == []


def test_a_missed_include_lands_in_its_own_named_list():
    gold, reg = _corpus()
    reg[0]["status"] = "excluded"  # the kit dropped one the user would keep
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert [m["key"] for m in r["missed_includes"]] == ["SRC-0000"]
    assert r["false_includes"] == []
    assert r["recall"] == 14 / 15
    assert r["precision"] == 1.0
    assert any("nothing downstream can detect" in n for n in r["notes"])


def test_a_false_include_costs_precision_and_not_recall():
    gold, reg = _corpus()
    reg[15]["status"] = "included"  # an excluded record the kit kept
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert [m["key"] for m in r["false_includes"]] == ["SRC-0100"]
    assert r["recall"] == 1.0
    assert r["precision"] == 15 / 16


def test_accuracy_is_never_reported():
    """At a low inclusion rate an exclude-everything screener scores >90%
    accuracy while finding nothing. The number is not in the payload at all, so
    it cannot be quoted."""
    gold, reg = _corpus(n_include=2, n_exclude=28, kit_agrees=False)
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert "accuracy" not in r
    assert r["recall"] == 0.0
    assert r["counts"]["missed_includes"] == 2


# ------------------------------------------------------------------- refusals

def test_below_the_floor_counts_stand_and_rates_do_not():
    gold, reg = _corpus(n_include=3, n_exclude=4)
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["scored"] == 7
    assert r["recall"] is None and r["precision"] is None and r["cohen_kappa"] is None
    assert r["counts"]["both_include"] == 3
    assert any("below the 20-record floor" in n for n in r["notes"])


def test_degenerate_kappa_is_null_not_zero():
    """One side using a single class makes chance agreement 1. Reporting 0 there
    would read as 'no better than chance', which is a measurement; this is the
    absence of one."""
    gold, reg = _corpus(n_include=0, n_exclude=25)
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["cohen_kappa"] is None
    assert any("κ is undefined" in n for n in r["notes"])


def test_unresolved_gold_entries_are_reported_never_dropped():
    gold, reg = _corpus()
    gold.append({"id": "SRC-9999", "label": "include"})
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["unresolved"] == ["SRC-9999"]
    assert r["scored"] == 30
    assert any("matched nothing" in n for n in r["notes"])


def test_undecided_and_duplicate_records_are_skipped_and_counted():
    gold, reg = _corpus()
    reg[0]["status"] = "candidate"
    reg[1]["status"] = "duplicate"
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["skipped"] == {"duplicate": 1, "undecided": 1}
    assert r["scored"] == 28
    assert any("no screening decision yet" in n for n in r["notes"])


# ------------------------------------------------------------------- the stage

def test_a_fulltext_exclusion_counts_as_a_screening_include():
    """It reached full text, so the screening layer kept it. Scoring it as an
    exclusion would charge the screener for a decision a later stage made."""
    gold, reg = _corpus()
    reg[0].update(status="excluded", stage="fulltext")
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["recall"] == 1.0
    assert r["stage"]["fulltext_exclusions_scored_as_include"] == 1
    assert r["missed_includes"] == []


def test_an_unretrieved_record_counts_as_a_screening_include():
    """It was sought for retrieval, so the screener kept it — the failure was
    access, not judgement. Scoring it as undecided would drop it from the
    denominator, and the records you cannot obtain are exactly the ones you
    screened IN, so that silently inflates precision."""
    gold, reg = _corpus()
    reg[0].update(status="unretrieved", stage="fulltext")
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["stage"]["unretrieved_scored_as_include"] == 1
    assert r["skipped"]["undecided"] == 0
    assert r["scored"] == 30
    assert r["missed_includes"] == []


def test_a_stageless_exclusion_is_assumed_screening_and_says_so():
    gold, reg = _corpus()
    reg[0].pop("stage")
    reg[0]["status"] = "excluded"
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["stage"]["assumed_screening"] == 1
    assert any("no `stage` field" in n for n in r["notes"])


def test_records_resolve_by_doi_and_bib_key_too():
    gold = [{"doi": "10.1000/X.1", "label": "include"},
            {"bib_key": "kaya2023deep", "label": "exclude"}]
    reg = [{"id": "SRC-0001", "doi": "10.1000/x.1", "status": "included"},
           {"id": "SRC-0002", "bib_key": "kaya2023deep", "status": "excluded"}]
    r = ss.score(_gold(gold), ss._index_records(reg))
    assert r["scored"] == 2 and r["unresolved"] == []


# ----------------------------------------------------------------------- CLI

def _run(cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / "screening_score.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def test_cli_refuses_without_a_gold_set_and_explains_why(tmp_path):
    _write(tmp_path / "sources" / "registry.jsonl", [{"id": "SRC-0001", "status": "included"}])
    r = _run(tmp_path, "--gold", "eval/screening/gold.jsonl")
    assert r.returncode == 1
    assert "agreement with itself" in r.stderr


def test_cli_refuses_a_decisions_file_that_carries_the_labels(tmp_path):
    """The mechanical half of gold-label isolation — the same check
    calibration_score.py makes about verdicts."""
    _write(tmp_path / "gold.jsonl", [{"id": "SRC-0001", "label": "include"}])
    _write(tmp_path / "reg.jsonl", [{"id": "SRC-0001", "status": "included",
                                     "gold_label": "include"}])
    r = _run(tmp_path, "--gold", "gold.jsonl", "--decisions", "reg.jsonl")
    assert r.returncode == 1
    assert "cannot be scored" in r.stderr


def test_cli_rejects_an_unknown_label(tmp_path):
    _write(tmp_path / "gold.jsonl", [{"id": "SRC-0001", "label": "maybe"}])
    _write(tmp_path / "reg.jsonl", [{"id": "SRC-0001", "status": "included"}])
    r = _run(tmp_path, "--gold", "gold.jsonl", "--decisions", "reg.jsonl")
    assert r.returncode == 1 and "not in ['include', 'exclude']" in r.stderr


def test_cli_output_is_json_and_scores_a_frozen_decisions_file(tmp_path):
    gold, reg = _corpus()
    _write(tmp_path / "gold.jsonl", gold)
    _write(tmp_path / "frozen.jsonl",
           [{"id": r["id"], "decision": "include" if r["status"] == "included"
             else "exclude"} for r in reg])
    r = _run(tmp_path, "--gold", "gold.jsonl", "--decisions", "frozen.jsonl")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["recall"] == 1.0 and payload["stage"]["frozen"] == 30


def test_cli_rejects_a_path_outside_the_project(tmp_path):
    r = _run(tmp_path, "--gold", "../elsewhere/gold.jsonl")
    assert r.returncode == 1 and "--gold" in r.stderr


# ---------- the blinded worksheet ----------
# The README asked the labeller not to look at the kit's decision first. Asking
# was all a document could do; these pin the sheet that decision is not on.

def _registry(tmp_path, n=6):
    return _write(tmp_path / "sources" / "registry.jsonl",
                  [{"id": f"SRC-{i:04d}", "title": f"Çalışma {i}", "year": 2020 + i % 4,
                    "venue": "Dergi", "status": "included" if i % 2 else "excluded",
                    "stage": "screening", "reason": "wrong population"}
                   for i in range(1, n + 1)])


def test_the_worksheet_does_not_carry_the_decision_it_is_meant_to_measure(tmp_path):
    _registry(tmp_path)
    r = _run(tmp_path, "--sample", "4")
    assert r.returncode == 0, r.stderr
    sheet = (tmp_path / "eval" / "screening" / "worksheet.csv").read_text(encoding="utf-8-sig")
    header = sheet.splitlines()[0]
    assert header == "id,title,year,venue,label,reason"
    for leak in ("status", "included", "excluded", "stage", "wrong population"):
        assert leak not in sheet, f"the worksheet leaks the kit's decision: {leak!r}"


def test_the_worksheet_is_reproducible_from_its_seed(tmp_path):
    _registry(tmp_path, n=20)
    first = _run(tmp_path, "--sample", "5", "--out", "a.csv")
    second = _run(tmp_path, "--sample", "5", "--out", "b.csv")
    assert first.returncode == second.returncode == 0
    assert (tmp_path / "a.csv").read_text() == (tmp_path / "b.csv").read_text()
    other = _run(tmp_path, "--sample", "5", "--seed", "2", "--out", "c.csv")
    assert other.returncode == 0
    assert (tmp_path / "c.csv").read_text() != (tmp_path / "a.csv").read_text()


def test_an_existing_worksheet_is_never_overwritten_silently(tmp_path):
    # It may hold labels someone typed by hand for an hour.
    _registry(tmp_path)
    _run(tmp_path, "--sample", "3")
    again = _run(tmp_path, "--sample", "3")
    assert again.returncode == 1 and "--force" in again.stderr


def test_the_worksheet_opens_as_utf8_in_excel(tmp_path):
    # Without the BOM Excel reads the file as the system codepage, and every
    # Turkish title the labeller is judging arrives mangled.
    _registry(tmp_path)
    _run(tmp_path, "--sample", "2")
    raw = (tmp_path / "eval" / "screening" / "worksheet.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert "Çalışma" in raw.decode("utf-8-sig")


def test_a_filled_worksheet_becomes_a_gold_file(tmp_path):
    _registry(tmp_path)
    _run(tmp_path, "--sample", "3")
    sheet = tmp_path / "eval" / "screening" / "worksheet.csv"
    lines = sheet.read_text(encoding="utf-8-sig").splitlines()
    lines[1] = lines[1].rsplit(",", 2)[0] + ",include,"
    lines[2] = lines[2].rsplit(",", 2)[0] + ",exclude,wrong population"
    sheet.write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")
    r = _run(tmp_path, "--from-worksheet", "eval/screening/worksheet.csv")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["labelled"] == 2 and payload["include"] == 1
    gold = [json.loads(line) for line in
            (tmp_path / "eval" / "screening" / "gold.jsonl").read_text(encoding="utf-8").splitlines()]
    assert gold[1]["reason"] == "wrong population"


def test_a_blank_row_is_skipped_not_read_as_an_exclusion(tmp_path):
    # Turning silence into a label would invent exactly the labels this layer
    # refuses to invent.
    _registry(tmp_path)
    _run(tmp_path, "--sample", "3")
    sheet = tmp_path / "eval" / "screening" / "worksheet.csv"
    lines = sheet.read_text(encoding="utf-8-sig").splitlines()
    lines[1] = lines[1].rsplit(",", 2)[0] + ",include,"
    sheet.write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")
    payload = json.loads(_run(tmp_path, "--from-worksheet",
                              "eval/screening/worksheet.csv").stdout)
    assert payload["labelled"] == 1
    assert [row["id"] for row in payload["unlabelled_rows"]]


def test_an_unreadable_label_is_refused_rather_than_guessed(tmp_path):
    _registry(tmp_path)
    _run(tmp_path, "--sample", "2")
    sheet = tmp_path / "eval" / "screening" / "worksheet.csv"
    lines = sheet.read_text(encoding="utf-8-sig").splitlines()
    lines[1] = lines[1].rsplit(",", 2)[0] + ",maybe,"
    sheet.write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")
    r = _run(tmp_path, "--from-worksheet", "eval/screening/worksheet.csv")
    assert r.returncode == 1 and "'maybe'" in r.stderr


def test_the_wrong_csv_is_named_as_the_wrong_csv(tmp_path):
    (tmp_path / "other.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    r = _run(tmp_path, "--from-worksheet", "other.csv")
    assert r.returncode == 1 and "worksheet" in r.stderr


def test_the_three_modes_are_mutually_exclusive(tmp_path):
    _registry(tmp_path)
    r = _run(tmp_path, "--sample", "3", "--gold", "gold.jsonl")
    assert r.returncode == 1 and "pick one" in r.stderr


def test_no_arguments_points_at_the_first_step(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 1 and "--sample" in r.stderr


def test_the_shipped_example_is_not_mistakable_for_a_gold_set():
    """It exists to show the shape. If it were ever named gold.jsonl the script
    would score the kit against five fictional ids and report a number."""
    p = ROOT / "eval" / "screening" / "gold.example.jsonl"
    assert p.exists() and "example" in p.name
    assert not (ROOT / "eval" / "screening" / "gold.jsonl").exists(), (
        "a gold set has been committed — screening labels are the user's own "
        "and must not ship with the kit")
