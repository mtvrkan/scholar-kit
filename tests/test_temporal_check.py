"""Tests for temporal_check.py — implausible dates and anachronistic-citation lint."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import temporal_check as tc  # noqa: E402

TODAY = datetime.date(2026, 7, 5)  # fixed reference; scripts under test call date.today() themselves


def _bib(entries: str, tmp_path) -> Path:
    p = tmp_path / "references.bib"
    p.write_text(entries, encoding="utf-8")
    return p


# ---------- bib temporal sanity ----------

def test_future_year_flagged(tmp_path):
    bib = _bib("@article{x2099, title={T}, year={2099}, verified={true}}\n", tmp_path)
    problems = tc.check_bib_temporal(bib, datetime.date(2026, 7, 5))
    assert any(p["kind"] == "future-year" for p in problems)


def test_current_and_past_year_not_flagged(tmp_path):
    bib = _bib("@article{x2020, title={T}, year={2020}, verified={true}}\n"
               "@article{x2026, title={T2}, year={2026}, verified={true}}\n", tmp_path)
    problems = tc.check_bib_temporal(bib, datetime.date(2026, 7, 5))
    assert problems == []


def test_fetched_before_published_flagged(tmp_path):
    bib = _bib('@article{x2024, title={T}, year={2024}, fetched_at={2020-01-01}, '
               'verified={true}}\n', tmp_path)
    problems = tc.check_bib_temporal(bib, datetime.date(2026, 7, 5))
    assert any(p["kind"] == "fetched-before-published" for p in problems)


def test_fetched_after_published_not_flagged(tmp_path):
    bib = _bib('@article{x2020, title={T}, year={2020}, fetched_at={2026-01-01}, '
               'verified={true}}\n', tmp_path)
    problems = tc.check_bib_temporal(bib, datetime.date(2026, 7, 5))
    assert problems == []


def test_missing_bib_file_returns_empty(tmp_path):
    assert tc.check_bib_temporal(tmp_path / "nope.bib", TODAY) == []


# ---------- card-vs-source year anachronism ----------

def _cards_and_registry(tmp_path, cards, registry):
    cp = tmp_path / "evidence" / "cards.jsonl"
    cp.parent.mkdir(parents=True)
    cp.write_text("\n".join(json.dumps(c) for c in cards) + ("\n" if cards else ""), encoding="utf-8")
    rp = tmp_path / "sources" / "registry.jsonl"
    rp.parent.mkdir(parents=True)
    rp.write_text("\n".join(json.dumps(r) for r in registry) + ("\n" if registry else ""), encoding="utf-8")
    return cp, rp


def test_card_mentioning_later_year_than_source_flagged(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "kaya2019deep",
          "claim": "As of 2024, this approach remained state of the art."}],
        [{"id": "SRC-0001", "bib_key": "kaya2019deep", "year": 2019}])
    problems = tc.check_card_year_anachronism(cp, rp)
    assert len(problems) == 1
    assert problems[0]["mentioned_year"] == 2024 and problems[0]["source_year"] == 2019


def test_a_four_digit_quantity_is_not_read_as_a_22nd_century_year(tmp_path):
    """A card reporting "2111 fundus images" was read as a claim about the year
    2111 and flagged as an anachronism against its 2023 source. No bibliography
    carries a 22nd-century date and no plausible typo produces one, so the 21xx
    branch bought nothing while costing a false positive on every four-digit
    quantity in that range — dataset sizes above all, in a field whose cards are
    made of them."""
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "cavli2023yapay",
          "claim": "The dataset holds 2111 fundus images across five classes."}],
        [{"id": "SRC-0001", "bib_key": "cavli2023yapay", "year": 2023}])
    assert tc.check_card_year_anachronism(cp, rp) == []


def test_a_genuinely_future_year_is_still_flagged_after_the_narrowing(tmp_path):
    """The narrowing must not disarm the check it exists for: 2099 is inside
    20xx and stays a year."""
    bib = _bib("@article{x2099, title={T}, year={2099}, verified={true}}\n", tmp_path)
    assert any(p["kind"] == "future-year"
               for p in tc.check_bib_temporal(bib, TODAY))


def test_card_mentioning_source_own_year_not_flagged(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "kaya2019deep", "claim": "Published in 2019, this study..."}],
        [{"id": "SRC-0001", "bib_key": "kaya2019deep", "year": 2019}])
    assert tc.check_card_year_anachronism(cp, rp) == []


def test_one_year_preprint_lag_allowed(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "kaya2019deep", "claim": "The 2020 journal version confirmed this."}],
        [{"id": "SRC-0001", "bib_key": "kaya2019deep", "year": 2019}])
    assert tc.check_card_year_anachronism(cp, rp) == []


def test_card_with_unknown_source_skipped_gracefully(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "unregistered2099", "claim": "As of 2099..."}],
        [])
    assert tc.check_card_year_anachronism(cp, rp) == []


def test_src_id_source_resolves_via_registry(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "SRC-0001", "claim": "As of 2024, still unresolved."}],
        [{"id": "SRC-0001", "bib_key": "kaya2019deep", "year": 2019}])
    problems = tc.check_card_year_anachronism(cp, rp)
    assert len(problems) == 1


# ---------- CLI contract ----------

def _run(cwd, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / "temporal_check.py"), *args],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    return p.returncode, p.stdout, p.stderr


def test_cli_default_never_blocks(tmp_path):
    _bib("@article{x2099, title={T}, year={2099}, verified={true}}\n", tmp_path)
    code, out, err = _run(tmp_path, "--bib", "references.bib")
    assert code == 0
    assert json.loads(out)["warnings"] >= 1


def test_cli_strict_blocks_on_warnings(tmp_path):
    _bib("@article{x2099, title={T}, year={2099}, verified={true}}\n", tmp_path)
    code, out, err = _run(tmp_path, "--bib", "references.bib", "--strict")
    assert code == 2


def test_cli_clean_project_zero_warnings(tmp_path):
    _bib("@article{x2020, title={T}, year={2020}, verified={true}}\n", tmp_path)
    code, out, err = _run(tmp_path, "--bib", "references.bib", "--strict")
    assert code == 0
    assert json.loads(out)["warnings"] == 0


# --- a four-digit number is a year only when its context says so -------------
# The 21xx exclusion at the top of temporal_check is a range hack for one
# instance of a general class. These two contexts say "not a year", and both
# occur constantly in the literature this kit targets.

import pytest  # noqa: E402


@pytest.mark.parametrize("text", [
    "features are taken from the GAP layer, giving 2048 features per image",
    "these 2048-d feature vectors were then balanced",
    "a held-out set of 2016 images was used",
    "1998 patients were screened at baseline",
    "GAP katmanından 2048 öznitelik alınmıştır",
    "toplam 2019 görüntü değerlendirilmiştir",
])
def test_quantities_and_dimensions_are_not_years(text):
    """2048 is ResNet-50's pooling width, not the year 2048."""
    ms = list(tc.YEAR_RE.finditer(text))
    assert ms, "the regex should still find the digits"
    assert not any(tc._is_a_year_here(text, m) for m in ms)


def test_dimension_pairs_never_match_the_year_regex_at_all():
    """"2048x2048" has no word boundary before the x, so it never reaches the
    guard — worth pinning, because a later loosening of YEAR_RE would expose it."""
    assert list(tc.YEAR_RE.finditer("resized to 2048x2048 pixels")) == []


@pytest.mark.parametrize("text", [
    "this mirrors Polater & Isik 2024, the same APTOS source",
    "consistent with Smith et al. 2023 on the same cohort",
    "as Gulshan 2016 reported for EyePACS-1",
])
def test_author_year_citations_are_not_claims_about_time(text):
    """A card may name ANOTHER study; that is a cross-reference."""
    ms = list(tc.YEAR_RE.finditer(text))
    assert ms
    assert not any(tc._is_a_year_here(text, m) for m in ms)


@pytest.mark.parametrize("text", [
    "the trial ran until 2024 and then stopped",
    "data collected in 2019 were reanalysed",
    "the guideline was published in 2024.",
    "veriler 2019 yılında toplanmıştır",
])
def test_real_year_mentions_are_still_years(text):
    """The guard must not blind the check to genuine temporal claims."""
    ms = list(tc.YEAR_RE.finditer(text))
    assert ms
    assert any(tc._is_a_year_here(text, m) for m in ms)


@pytest.mark.parametrize("text", [
    "The 2022 recalibration protocol is applied to the same cohort",
    "This 2023 revision changed the referral threshold",
    "Bu 2022 protokolü aynı kohorta uygulanmıştır",
])
def test_a_capitalised_function_word_is_not_a_surname(text):
    """A sentence usually starts with a capital letter.

    Without a stopword guard "The 2022 protocol" was exempted as an author-year
    citation — and that over-broad exemption suppressed a genuine anachronism
    that a shipped gold case had been catching. An exemption that swallows true
    positives is the same defect as the false positive it removed, reversed.
    """
    ms = list(tc.YEAR_RE.finditer(text))
    assert ms
    assert any(tc._is_a_year_here(text, m) for m in ms)


def test_the_guard_is_actually_wired_into_the_card_check(tmp_path):
    """End-to-end: the helper must be CALLED, not merely correct.

    A mutation that deleted the guard from check_card_year_anachronism passed
    every test above, because they all called _is_a_year_here directly. A helper
    nothing invokes is not a fix.
    """
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0001", "source": "SRC-0001",
          "claim": "ResNet-50 feature extraction",
          "detail": "the GAP layer gives 2048 features per image"}],
        [{"id": "SRC-0001", "year": 2021}])
    assert tc.check_card_year_anachronism(cp, rp) == []


def test_a_genuine_anachronism_still_reaches_the_report(tmp_path):
    cp, rp = _cards_and_registry(
        tmp_path,
        [{"id": "EV-0002", "source": "SRC-0002",
          "claim": "later guidance",
          "detail": "the recommendation was revised in 2024 following the trial"}],
        [{"id": "SRC-0002", "year": 2019}])
    problems = tc.check_card_year_anachronism(cp, rp)
    assert len(problems) == 1 and problems[0]["mentioned_year"] == 2024
