"""Label-free measurement of the drafting stage (scripts/draft_stability.py).

`eval/MEASUREMENT.md` records drafting as unmeasured, because accuracy needs a
gold set and the kit refuses to invent one. Stability needs none: two renderings
of one section from one evidence set either agree about which sources they cite,
which quantities they report and how strongly they claim each source, or one of
them put something in the text that did not come from the evidence.

These tests pin the three dimensions, the things deliberately NOT compared
(prose, wording, length), and — by name — the fact that a consistently wrong
stage scores a perfect 1.00.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import draft_stability  # noqa: E402


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "draft_stability.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _runs(tmp_path, *texts) -> list[str]:
    names = []
    for i, text in enumerate(texts, start=1):
        p = tmp_path / f"run-{i}.md"
        p.write_text(text, encoding="utf-8")
        names.append(p.name)
    return names


# ---------- the three dimensions ----------

def test_identical_renderings_agree_completely(tmp_path):
    text = "The model reached 0.81 AUC [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, text, text)).stdout)
    assert result["lowest_agreement"] == 1.0


def test_a_source_cited_in_only_one_rendering_is_reported(tmp_path):
    a = "Boosting is associated with better recall [@kaya2024stroke].\n"
    b = ("Boosting is associated with better recall [@kaya2024stroke], as also "
         "reported elsewhere [@demir2023xai].\n")
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["citations"]["unstable"] == ["demir2023xai"]
    assert result["citations"]["agreement"] == 0.5


def test_a_quantity_in_only_one_rendering_is_reported(tmp_path):
    a = "The model reached 0.81 AUC [@kaya2024stroke].\n"
    b = "The model reached 0.84 AUC [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert set(result["numbers"]["unstable"]) == {"0.81", "0.84"}


def test_the_same_quantity_written_in_both_decimal_conventions_agrees(tmp_path):
    # A Turkish rendering writes 0,81 where an English one writes 0.81. That is
    # typography (tr_style_check.py's subject), not a disagreement about what
    # was measured.
    a = "Model 0,81 AUC değerine ulaştı [@kaya2024stroke].\n"
    b = "The model reached 0.81 AUC [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["numbers"]["agreement"] == 1.0


def test_a_bare_year_is_not_treated_as_a_reported_quantity(tmp_path):
    # Years track how the literature happens to be phrased in each rendering,
    # not what the section reports.
    a = "Earlier work from 2019 framed this differently [@kaya2024stroke].\n"
    b = "Earlier work framed this differently [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["numbers"]["agreement"] == 1.0


def test_a_percentage_is_a_reported_quantity_even_when_it_looks_like_a_year(tmp_path):
    a = "Coverage reached 2019% of the baseline [@kaya2024stroke].\n"
    b = "Coverage reached 91% of the baseline [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["numbers"]["agreement"] < 1.0


def test_a_source_claimed_more_strongly_in_one_rendering_is_reported(tmp_path):
    a = "Hypertension is associated with stroke risk [@kaya2024stroke].\n"
    b = "Hypertension causes stroke [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    conflicts = result["claim_strength"]["conflicts"]
    assert [c["key"] for c in conflicts] == ["kaya2024stroke"]
    assert result["claim_strength"]["agreement"] == 0.0


def test_claim_strength_only_compares_keys_every_rendering_cited(tmp_path):
    # A key one rendering never mentioned is already a citation disagreement;
    # counting it again here would report one defect as two.
    a = "X is associated with Y [@kaya2024stroke].\n"
    b = "X is associated with Y [@kaya2024stroke]. Z causes W [@demir2023xai].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["claim_strength"]["compared_keys"] == 1
    assert result["claim_strength"]["conflicts"] == []


# ---------- what is deliberately not compared ----------

def test_different_prose_expressing_the_same_content_agrees(tmp_path):
    a = "We report an AUC of 0.81 for the boosted model [@kaya2024stroke].\n"
    b = ("The boosted model's area under the curve, 0.81, is reported here "
         "[@kaya2024stroke]. This section is deliberately much longer than the "
         "other rendering, and says so at length.\n")
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, b)).stdout)
    assert result["lowest_agreement"] == 1.0


def test_a_section_reporting_no_quantities_is_not_penalised(tmp_path):
    # An empty observation set is perfect consistency about reporting nothing;
    # scoring it 0.0 would flag every qualitative draft in the kit.
    text = "This section reviews the framing of the problem [@kaya2024stroke].\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, text, text)).stdout)
    assert result["numbers"]["agreement"] == 1.0


# ---------- the limit, asserted by name ----------

def test_a_consistently_wrong_stage_scores_perfectly():
    """Stability is not accuracy. Both renderings cite a source that does not
    exist and report a number nothing supports; the score is 1.00, and any report
    of this number has to carry that sentence."""
    wrong = "The model reached 0.99 AUC [@nonexistent2030fake].\n"
    result = draft_stability.compare([wrong, wrong])
    assert result["lowest_agreement"] == 1.0
    assert "not accuracy" in result["note"]


# ---------- CLI contract ----------

def test_one_rendering_is_refused(tmp_path):
    _run(tmp_path, *_runs(tmp_path, "x [@a2024b]\n"), expect=1)


def test_three_renderings_require_agreement_from_all_of_them(tmp_path):
    # Intersection over union across all runs at once: a key two of three cite is
    # still a key one of them invented or dropped.
    a = "X [@one2024a]\n"
    result = json.loads(_run(tmp_path, *_runs(tmp_path, a, a, "X [@two2024b]\n")).stdout)
    assert result["runs"] == 3
    assert result["citations"]["agreement"] == 0.0


def test_strict_exits_two_below_the_floor(tmp_path):
    a = "X is associated with Y [@one2024a].\n"
    b = "X is associated with Y [@two2024b].\n"
    _run(tmp_path, "--strict", *_runs(tmp_path, a, b), expect=2)


def test_strict_exits_zero_at_the_floor(tmp_path):
    text = "X is associated with Y [@one2024a].\n"
    _run(tmp_path, "--strict", *_runs(tmp_path, text, text), expect=0)


def test_output_is_exactly_one_json_object(tmp_path):
    text = "X [@one2024a]\n"
    json.loads(_run(tmp_path, *_runs(tmp_path, text, text)).stdout)
