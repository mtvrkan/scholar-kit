"""Tests for run_evals.py — the gold-set measurement harness, plus the gate that
runs the shipped gold sets.

A measurement harness that silently reports a perfect score is worse than no
harness: it converts an untested checker into a documented one. Most of these
tests are therefore about the harness REFUSING to produce a flattering number —
on an empty case list, a duplicate id, an unknown entrypoint, or a threshold
naming a metric that was never computed.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_evals as ev  # noqa: E402


def _gold(tmp_path, manifest: dict, name: str = "demo") -> Path:
    d = tmp_path / "gold" / name
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False),
                                     encoding="utf-8")
    return tmp_path / "gold"


def _claim_manifest(cases, thresholds=None):
    return {"task": "demo", "entrypoint": "claim_check",
            "thresholds": thresholds or {}, "cases": cases}


# ---------- subset matching ----------

def test_expect_matches_on_named_fields_only():
    assert ev.matches({"mode": "M1"}, {"mode": "M1", "signal": "x", "where": "y"})


def test_expect_fails_when_a_named_field_differs():
    assert not ev.matches({"mode": "M1", "signal": "x"}, {"mode": "M1", "signal": "z"})


def test_empty_expect_matches_anything():
    # Deliberate: an entry naming no fields asserts nothing. Manifests express
    # "expect nothing" with an empty LIST, not an empty dict.
    assert ev.matches({}, {"mode": "M7"})


# ---------- scoring arithmetic ----------

def test_true_positive_counted(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "a", "drafts": {"d.md": "X causes Y [@k2020]."},
         "cards": [{"id": "EV-1", "source": "k2020", "claim": "X is associated with Y"}],
         "expect": [{"check": "overclaim"}]}]))
    t = ev.run_all(gold)["tasks"][0]
    assert (t["tp"], t["fp"], t["fn"]) == (1, 0, 0)


def test_false_negative_counted(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "a", "drafts": {"d.md": "Nothing notable here."},
         "cards": [], "expect": [{"check": "overclaim"}]}]))
    t = ev.run_all(gold)["tasks"][0]
    assert (t["tp"], t["fn"]) == (0, 1)
    assert t["failing_cases"][0]["missed"] == [{"check": "overclaim"}]


def test_false_positive_counted(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "a", "drafts": {"intro.md": "Prevalence reached 47.3% last year."},
         "cards": [], "expect": []}]))
    t = ev.run_all(gold)["tasks"][0]
    assert t["fp"] == 1 and t["failing_cases"][0]["spurious"]


def test_one_expectation_consumes_one_finding(tmp_path):
    # Two identical findings against one expectation must leave the second as a
    # false positive, not be double-credited by the same expect entry.
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "a",
         "drafts": {"intro.md": "Prevalence reached 47.3%.\n\nIncidence reached 12.8%."},
         "cards": [], "expect": [{"check": "uncited"}]}]))
    t = ev.run_all(gold)["tasks"][0]
    assert (t["tp"], t["fp"]) == (1, 1)


def test_positive_and_negative_case_counts_reported(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "a", "drafts": {"d.md": "Nothing."}, "cards": [], "expect": []},
        {"id": "b", "drafts": {"intro.md": "Prevalence reached 47.3%."}, "cards": [],
         "expect": [{"check": "uncited"}]}]))
    t = ev.run_all(gold)["tasks"][0]
    # Precision is only honest when negatives exist; the report states the
    # balance so a suite that drops its negatives is visible.
    assert t["positive_cases"] == 1 and t["negative_cases"] == 1


# ---------- refusals: the harness must not flatter ----------

def test_empty_case_list_is_an_error_not_a_perfect_score(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([]))
    with pytest.raises(SystemExit):
        ev.run_all(gold)


def test_duplicate_case_id_rejected(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"id": "same", "drafts": {"d.md": "x"}, "cards": [], "expect": []},
        {"id": "same", "drafts": {"d.md": "y"}, "cards": [], "expect": []}]))
    with pytest.raises(SystemExit):
        ev.run_all(gold)


def test_case_without_id_rejected(tmp_path):
    gold = _gold(tmp_path, _claim_manifest([
        {"drafts": {"d.md": "x"}, "cards": [], "expect": []}]))
    with pytest.raises(SystemExit):
        ev.run_all(gold)


def test_unknown_entrypoint_rejected(tmp_path):
    gold = _gold(tmp_path, {"task": "demo", "entrypoint": "nope", "cases": [
        {"id": "a", "drafts": {}, "expect": []}]})
    with pytest.raises(SystemExit):
        ev.run_all(gold)


def test_unknown_threshold_metric_counts_as_missed(tmp_path):
    # A typo'd threshold key must fail loudly rather than gate on nothing.
    gold = _gold(tmp_path, _claim_manifest(
        [{"id": "a", "drafts": {"d.md": "Nothing."}, "cards": [], "expect": []}],
        thresholds={"precison": 0.9}))
    assert ev.run_all(gold)["tasks"][0]["thresholds_missed"] == ["precison"]


def test_unmeasurable_metric_counts_as_missed(tmp_path):
    # All-negative suite: recall is undefined (no positives), so a recall
    # threshold cannot be satisfied and must not silently pass.
    gold = _gold(tmp_path, _claim_manifest(
        [{"id": "a", "drafts": {"d.md": "Nothing."}, "cards": [], "expect": []}],
        thresholds={"recall": 0.9}))
    assert ev.run_all(gold)["tasks"][0]["thresholds_missed"] == ["recall"]


def test_missed_threshold_surfaces_in_run_summary(tmp_path):
    gold = _gold(tmp_path, _claim_manifest(
        [{"id": "a", "drafts": {"d.md": "Nothing."}, "cards": [],
          "expect": [{"check": "overclaim"}]}],
        thresholds={"recall": 0.9}))
    assert ev.run_all(gold)["any_threshold_missed"] is True


def test_named_task_that_does_not_exist_is_an_error(tmp_path):
    gold = _gold(tmp_path, _claim_manifest(
        [{"id": "a", "drafts": {"d.md": "x"}, "cards": [], "expect": []}]))
    with pytest.raises(SystemExit):
        ev.run_all(gold, only="missing-task")


# ---------- the shipped gold sets (this is the CI gate) ----------

def test_shipped_gold_sets_exist():
    tasks = {p.parent.name for p in ev.discover(ROOT / "eval" / "gold")}
    assert {"claim_strength", "failure_modes"} <= tasks


def test_shipped_gold_sets_meet_their_thresholds():
    result = ev.run_all(ROOT / "eval" / "gold")
    failures = [(t["task"], t["thresholds_missed"],
                 [c["id"] for c in t["failing_cases"]])
                for t in result["tasks"] if t["thresholds_missed"]]
    assert not failures, f"gold-set thresholds missed: {failures}"


def test_shipped_gold_sets_carry_negatives():
    # Without negative cases a suite cannot measure precision, and its 1.00
    # would mean "never declined to fire", which is not the same as correct.
    for t in ev.run_all(ROOT / "eval" / "gold")["tasks"]:
        assert t["negative_cases"] > 0, f"{t['task']} has no negative cases"


def test_shipped_gold_sets_declare_thresholds():
    for t in ev.run_all(ROOT / "eval" / "gold")["tasks"]:
        assert t["thresholds"], f"{t['task']} declares no thresholds — it gates nothing"


def test_shipped_gold_sets_are_held_to_the_stricter_line():
    """0.95 on precision AND recall, every set, no exceptions.

    A threshold is not a quality bar here — it is the line a MUTATION has to
    fall below to be caught, so a low one silently retires mutations as a set
    grows (MEASUREMENT.md, "Why every set is held to 0.95"). `claim_strength`
    reached 0.95 by that route; `tr_style` was one added positive case from
    losing `percent-detector-disabled` at 0.90 and nothing would have said so.
    A new gold set copied from an old manifest inherits whatever it copied,
    which is why this is asserted rather than left to review.
    """
    for t in ev.run_all(ROOT / "eval" / "gold")["tasks"]:
        for metric in ("precision", "recall"):
            got = t["thresholds"].get(metric)
            assert got is not None, f"{t['task']} declares no {metric} threshold"
            assert got >= 0.95, (
                f"{t['task']} gates {metric} at {got} — the floor is 0.95")


def test_measurement_doc_results_table_matches_the_harness():
    """MEASUREMENT.md says "do not hand-edit this table". Nothing enforced it.

    A document arguing that every claim should be bound to something that fails
    cannot carry an unbound table of its own results — and this is the table a
    reader quotes. Case counts and the positive/negative split are derived here
    row by row; precision and recall are deliberately not, because the table
    prints them to two places and the harness computes full floats.
    """
    import re
    doc = (ROOT / "eval" / "MEASUREMENT.md").read_text(encoding="utf-8")
    rows = dict()
    for m in re.finditer(r"^\|\s*`(\w+)`\s*\|\s*(\d+)\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|", doc, re.M):
        rows[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    assert rows, "MEASUREMENT.md no longer carries a per-gold-set results table"
    actual = {t["task"]: (t["cases"], t["positive_cases"], t["negative_cases"])
              for t in ev.run_all(GOLD)["tasks"]}
    assert set(rows) == set(actual), (
        f"table lists {sorted(rows)}; the harness runs {sorted(actual)}")
    for task, stated in rows.items():
        assert stated == actual[task], (
            f"MEASUREMENT.md states {task} = {stated} (cases, pos, neg); the "
            f"harness reports {actual[task]}")
    total = re.search(r"^\|\s*\*\*total\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*"
                      r"\*\*(\d+)\s*/\s*(\d+)\*\*", doc, re.M)
    assert total, "the results table no longer carries a total row"
    sums = tuple(sum(v[i] for v in actual.values()) for i in range(3))
    assert tuple(int(g) for g in total.groups()) == sums, (
        f"total row says {total.groups()}; the sets sum to {sums}")


# ---------- mutation check (the second CI gate) ----------
# Thresholds prove the checker does what its author meant on the cases the
# author chose. They cannot prove the cases would notice if the checker stopped
# doing it — a negative case that stays silent however the code is broken scores
# like a case that measures something. That gap is what these tests close, and
# it was not hypothetical: the first mutation run found three survivors, two of
# them in gold sets that had been shipping at a perfect score.

GOLD = ROOT / "eval" / "gold"


def _manifests():
    return sorted(GOLD.glob("*/manifest.json"))


def test_every_shipped_gold_set_declares_mutations():
    for manifest in _manifests():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        mutations = data.get("mutations") or []
        assert mutations, (
            f"{manifest.parent.name} declares no mutations — nothing establishes "
            f"that its cases would notice the checker breaking")
        ids = [m.get("id") for m in mutations]
        assert all(ids), f"{manifest.parent.name}: a mutation has no id"
        assert len(set(ids)) == len(ids), f"{manifest.parent.name}: duplicate mutation id"
        for mutation in mutations:
            assert mutation.get("breaks"), (
                f"{manifest.parent.name}:{mutation['id']} does not say what it "
                f"breaks — a mutation nobody can read is a mutation nobody can "
                f"judge the value of")


def test_no_declared_mutation_survives_its_gold_set():
    result = ev.run_all(GOLD, mutate=True)
    survivors = result["mutation_check"]["survivors"]
    assert not survivors, (
        f"these mutations did NOT drop their gold set below threshold: "
        f"{survivors}. Each names a real hole in the cases — the checker can "
        f"lose that behaviour and the suite still reports a pass.")
    assert result["mutation_check"]["total"] >= len(_manifests()), (
        "fewer mutations than gold sets — some set is unguarded")


def test_a_mutation_whose_anchor_moved_fails_loudly(tmp_path):
    # The failure mode that would quietly hollow this out: the checker is
    # refactored, the anchor string no longer appears, and a mutation that
    # substitutes nothing "passes" forever.
    with pytest.raises(SystemExit):
        ev._mutated_module("claim_check",
                           [["this string is not in claim_check.py", "x"]],
                           "moved-anchor")


def test_a_mutation_that_changes_nothing_is_rejected():
    with pytest.raises(SystemExit):
        ev._mutated_module("claim_check", [["import re", "import re"]], "no-op")


def test_the_mutant_is_isolated_from_the_real_module():
    # run_mutations swaps the mutant into sys.modules under the real name. If it
    # failed to restore, every later gold set — and every later test — would run
    # against a broken checker and the damage would look like a code defect.
    import claim_check

    before = claim_check.ARTEFACT_RE.pattern
    ev.run_mutations(GOLD / "claim_strength" / "manifest.json")
    assert sys.modules["claim_check"] is claim_check
    assert claim_check.ARTEFACT_RE.pattern == before


def test_cli_mutate_strict_exits_zero_while_every_mutation_is_caught(run):
    code, out, err = run("run_evals.py", "--mutate", "--strict")
    assert code == 0, err
    assert json.loads(out)["any_mutation_survived"] is False


# ---------- CLI contract ----------

def test_cli_reports_all_tasks(run):
    code, out, _ = run("run_evals.py")
    assert code == 0
    assert json.loads(out)["gold_sets"] >= 2


def test_cli_strict_exits_zero_when_thresholds_met(run):
    code, _, _ = run("run_evals.py", "--strict")
    assert code == 0


def test_cli_runs_from_any_directory(run):
    # The `run` fixture executes from a temp cwd. Gold sets are kit-owned and
    # read relative to the kit root, so the traversal guard must be kit-relative
    # too — guarding against cwd killed the harness anywhere but the kit root.
    code, out, err = run("run_evals.py", "--task", "claim_strength")
    assert code == 0, err
    assert json.loads(out)["tasks"][0]["task"] == "claim_strength"


def test_gold_path_outside_the_kit_rejected(run):
    code, _, err = run("run_evals.py", "--gold", "../../elsewhere")
    assert code == 1 and "--gold" in err


def test_measurement_doc_prose_set_count_and_range_match_the_harness():
    """The two hand-typed numbers left beside the bound ones.

    `test_measurement_doc_results_table_matches_the_harness` binds the table and
    `test_measurement_doc_prose_totals_match_the_harness` binds "N cases" and the
    negative/positive split. What stayed prose is the sentence's *shape*:

        202 cases across nine checkers — 10 to 71 per set

    "nine" and "10 to 71" describe the same artifact the rest of the sentence is
    derived from, and neither moves when a tenth gold set lands: the case total
    updates, the word does not, and the range silently misreports the smallest
    set — which is the number that carries the weight, since this paragraph
    exists to say the sets are small. The same drift class as ROUTING-EVAL.md's
    accuracy claim (see tests/test_routing_eval_currency.py): a figure derived
    and honest, and the sentence built on it left behind.
    """
    import re

    WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
             12: "twelve"}
    # Collapsed: the sentence wraps mid-phrase in the source, and a check that
    # depended on where the line broke would fail on a reflow that changed
    # nothing it cares about.
    doc = re.sub(r"\s+", " ",
                 (ROOT / "eval" / "MEASUREMENT.md").read_text(encoding="utf-8"))
    tasks = ev.run_all(GOLD)["tasks"]
    n = len(tasks)
    word = WORDS.get(n, str(n))
    lo = min(t["cases"] for t in tasks)
    hi = max(t["cases"] for t in tasks)

    assert re.search(rf"cases across {word} checkers", doc), (
        f"MEASUREMENT.md says 'across <N> checkers' for a different N; the "
        f"harness runs {n} gold sets, so the prose should read "
        f"'across {word} checkers'."
    )
    assert re.search(rf"\b{lo} to {hi} per set\b", doc), (
        f"MEASUREMENT.md states a per-set range that is no longer the harness's: "
        f"the smallest gold set holds {lo} cases and the largest {hi}, so the "
        f"prose should read '{lo} to {hi} per set'. The lower bound is the "
        "load-bearing half — the paragraph's whole point is that the sets are "
        "small enough that a perfect score is a weak claim."
    )
