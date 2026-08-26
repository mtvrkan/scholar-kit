"""Tests for citation_triangulate.py — OpenAlex second-index cross-check.

Calibrated against a real finding: OpenAlex stores only the base title for a
colon-subtitled paper (e.g. "XGBoost", no subtitle field to reconstruct from,
unlike Crossref's CSL-JSON), so a naive full-title comparison would falsely
DISAGREE on well-known, unproblematic papers. _titles_agree tolerates that
truncation signature (near-100 partial_ratio) while still catching a genuinely
wrong paper (confirmed live: an unrelated title scores ~8-46, nowhere near the
95 partial_ratio threshold).
"""
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_triangulate as ct  # noqa: E402


def _entry(key, title, year, author, doi):
    return {"key": key, "fields": {"title": title, "year": year, "author": author, "doi": doi}}


# ---------- _titles_agree: subtitle-truncation tolerance ----------

def test_truncated_openalex_title_agrees_full_local_title():
    agree, sim = ct._titles_agree("XGBoost", "XGBoost: A Scalable Tree Boosting System")
    assert agree is True


def test_identical_titles_agree():
    agree, sim = ct._titles_agree("Random Forests", "Random Forests")
    assert agree is True
    assert sim == 100


def test_genuinely_different_title_disagrees():
    agree, sim = ct._titles_agree("XGBoost", "This Is Definitely The Wrong Title Entirely")
    assert agree is False


def test_openalex_first_author_family_extracts_last_token():
    work = {"authorships": [{"author": {"display_name": "Tianqi Chen"}}]}
    assert ct._openalex_first_author_family(work) == "chen"


def test_openalex_first_author_family_no_authors():
    assert ct._openalex_first_author_family({"authorships": []}) == ""


# ---------- triangulate_entry: mocked OpenAlex responses ----------

def test_no_doi_is_skipped():
    r = ct.triangulate_entry(_entry("x", "T", "2020", "A, B", ""))
    assert r["status"] == "SKIPPED"


@patch.object(ct, "fetch_openalex_work", return_value={})
def test_not_in_openalex_reported_not_error(mock_fetch):
    r = ct.triangulate_entry(_entry("x", "T", "2020", "Smith, A", "10.1/x"))
    assert r["status"] == "NOT_IN_OPENALEX"


@patch.object(ct, "fetch_openalex_work")
def test_agreeing_entry_reports_agree(mock_fetch):
    mock_fetch.return_value = {
        "id": "https://openalex.org/W1", "title": "XGBoost",
        "publication_year": 2016,
        "authorships": [{"author": {"display_name": "Tianqi Chen"}}]}
    r = ct.triangulate_entry(_entry(
        "chen2016xgboost", "XGBoost: A Scalable Tree Boosting System",
        "2016", "Chen, Tianqi and Guestrin, Carlos", "10.1145/2939672.2939785"))
    assert r["status"] == "AGREE"


@patch.object(ct, "fetch_openalex_work")
def test_year_mismatch_flagged(mock_fetch):
    mock_fetch.return_value = {
        "id": "https://openalex.org/W1", "title": "Some Paper",
        "publication_year": 2010,
        "authorships": [{"author": {"display_name": "A Smith"}}]}
    r = ct.triangulate_entry(_entry("x2020", "Some Paper", "2020", "Smith, A", "10.1/x"))
    assert r["status"] == "DISAGREE"
    assert any("year" in d for d in r["disagreements"])


@patch.object(ct, "fetch_openalex_work")
def test_one_year_off_not_flagged(mock_fetch):
    mock_fetch.return_value = {
        "id": "https://openalex.org/W1", "title": "Some Paper",
        "publication_year": 2019,
        "authorships": [{"author": {"display_name": "A Smith"}}]}
    r = ct.triangulate_entry(_entry("x2020", "Some Paper", "2020", "Smith, A", "10.1/x"))
    assert r["status"] == "AGREE"


@patch.object(ct, "fetch_openalex_work")
def test_author_mismatch_flagged(mock_fetch):
    mock_fetch.return_value = {
        "id": "https://openalex.org/W1", "title": "Some Paper",
        "publication_year": 2020,
        "authorships": [{"author": {"display_name": "Someone Else"}}]}
    r = ct.triangulate_entry(_entry("x2020", "Some Paper", "2020", "Smith, A", "10.1/x"))
    assert r["status"] == "DISAGREE"
    assert any("author" in d for d in r["disagreements"])


@patch.object(ct, "fetch_openalex_work")
def test_network_error_reported(mock_fetch):
    mock_fetch.side_effect = ct.requests.RequestException("timeout")
    r = ct.triangulate_entry(_entry("x", "T", "2020", "Smith, A", "10.1/x"))
    assert r["status"] == "NETWORK_ERROR"


# ---------- CLI contract ----------

def test_cli_default_never_blocks_on_disagreement(tmp_path):
    import json
    import subprocess
    bib = tmp_path / "references.bib"
    bib.write_text("@misc{nodoi, title={No DOI here}, verified={true}}\n", encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPTS / "citation_triangulate.py"),
                       "--bib", "references.bib"],
                       cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0
    result = json.loads(p.stdout)
    assert result["skipped"] == 1  # no DOI -> SKIPPED, not a fetch attempt


# --- the same author, indexed two ways ---------------------------------------
# Regression: the first-author check compared OpenAlex's LAST whitespace token
# against the whole comma-prefix of the local BibTeX author field. On a real
# 121-entry bibliography that produced 12 disagreements and not one of them was
# a wrong paper — particled and compound surnames, Unicode hyphens, diacritics,
# and one family-name-first Chinese display name. A verification gate with a 9%
# noise rate is a gate nobody reads.

import pytest  # noqa: E402


def _work(display_name):
    return {"authorships": [{"author": {"display_name": display_name}}]}


@pytest.mark.parametrize("oa,local", [
    ("van der Heijden", "Heijden, Ronald and Kwaijtaal, M"),   # Dutch particle
    ("dos Reis, J", "Reis, J and Silva, M"),                   # Portuguese particle
    ("Abreu-González, R", "González, R and Perez, T"),         # compound surname
    ("Baget‐Bernaldiz, Marc", "Baget-Bernaldiz, M and Pedro, R"),  # U+2010
    ("Özçelik, Ali", "Ozcelik, Ali and Kaya, B"),              # diacritics
    ("Işık, Mehmet", "Isik, Mehmet and Polater, S"),           # dotless i
    ("Lu Li", "Lu, Li and Ren, Peifang"),                      # family name first
])
def test_the_same_author_indexed_differently_agrees(oa, local):
    assert ct._first_author_agrees(_work(oa), local)


@pytest.mark.parametrize("oa,local", [
    ("Smith, John", "Jones, Alice and Brown, Bob"),
    ("Zhang, Wei", "Milan, Andrea and Roth, S"),
])
def test_a_genuinely_different_author_still_disagrees(oa, local):
    """Normalising names must not make every entry agree with every other."""
    assert not ct._first_author_agrees(_work(oa), local)


def test_a_missing_openalex_author_is_not_a_disagreement():
    assert ct._first_author_agrees({"authorships": []}, "Kaya, Ahmet")


def test_single_letter_tokens_are_dropped():
    """A one-letter token is an initial, not a name.

    Kept, it makes "Perez, R" and "Rossi, R" share a token and agree. The
    previous version of this test asserted the outcome instead of the rule and
    passed even with the length filter removed, because the local side never
    contributes given-name initials anyway.
    """
    assert "r" not in ct._name_tokens("Perez, R")
    assert ct._name_tokens("Perez, R") == {"perez"}
    assert ct._name_tokens("van der Heijden") == {"van", "der", "heijden"}


def test_the_normalised_comparison_is_actually_wired_in():
    """End-to-end through triangulate_entry, not just the helper.

    A mutation that reverted the call site to the old last-token comparison
    passed every test above, because they all called _first_author_agrees
    directly. A helper nothing invokes is not a fix.
    """
    # The local field must carry the PARTICLE ("van der Heijden"), which is the
    # shape that made the old comparison fail: it took OpenAlex's last token
    # ("heijden") and looked for it in the local comma-prefix, which is the
    # whole compound. A test whose local side is already bare passes either way.
    entry = {"key": "heijden2017validation",
             "fields": {"doi": "10.1000/x",
                        "title": "Validation of automated screening",
                        "year": "2017",
                        "author": "van der Heijden, Ronald and Kwaijtaal, M"}}
    work = {"title": "Validation of automated screening",
            "publication_year": 2017,
            "authorships": [{"author": {"display_name": "van der Heijden"}}]}
    with patch.object(ct, "fetch_openalex_work", return_value=work):
        res = ct.triangulate_entry(entry)
    assert res["status"] == "AGREE", res.get("disagreements")
