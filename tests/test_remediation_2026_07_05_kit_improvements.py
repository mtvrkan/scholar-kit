"""Regression tests for the kit-improvement pass driven by the first real
end-to-end paper run (stroke-prediction / XAI benchmark).

Four confirmed script bugs surfaced during that production and are fixed here:

  * doi2bib.py: cmd_verify now compares the local title against the FULL
    reconstructed "Title: Subtitle" (via _csl_full_title), so an ACM/Crossref
    entry whose colon-title Crossref splits into separate CSL "title" +
    "subtitle" fields no longer false-FABRICATEs (observed on chen2016xgboost
    and ribeiro2016why, similarity 30/49 against the title-only string).
  * bib_doctor.py: a preprint (arXiv/bioRxiv/etc.) that doi.org content-
    negotiation types as @article but that legitimately has no journal is no
    longer flagged "missing field 'journal'"; a locator (doi|url) is required
    instead (observed on fisher2018all, an arXiv preprint).
  * venue_check.py: an OpenAlex title `search` result is now re-ranked by
    actual title similarity and rejected if it is not a close match, instead of
    blindly taking results[0] — which attached "Biotechnology and
    Bioengineering" (Wiley) metadata to a "Bioengineering" (MDPI) query.
  * evidence_db.py: `add --stdin` decodes the raw byte buffer as UTF-8 instead
    of trusting the console/locale codepage, so Greek/math symbols in a card
    (ξ, π, σ, Ω, Σ) survive on Windows (cp1254) instead of arriving as mojibake.
"""
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doi2bib      # noqa: E402
import bib_doctor   # noqa: E402
import venue_check  # noqa: E402


# ---------- doi2bib.py: colon-title subtitle reconstruction ----------

def test_csl_full_title_concatenates_subtitle():
    csl = {"title": "XGBoost", "subtitle": ["A Scalable Tree Boosting System"]}
    assert doi2bib._csl_full_title(csl) == "XGBoost: A Scalable Tree Boosting System"


def test_csl_full_title_no_subtitle_is_title_only():
    assert doi2bib._csl_full_title({"title": "Random Forests"}) == "Random Forests"


def test_csl_full_title_multiple_subtitles():
    csl = {"title": "Why Should I Trust You",
           "subtitle": ["Explaining the Predictions of Any Classifier"]}
    assert doi2bib._csl_full_title(csl) == \
        "Why Should I Trust You: Explaining the Predictions of Any Classifier"


def test_reconstructed_title_matches_combined_local_title():
    # The scenario that produced the false FABRICATED: local bib title is the
    # combined form, CSL splits it. Reconstructed CSL title must score high.
    from rapidfuzz import fuzz
    from lib_common import normalize_title
    csl = {"title": "XGBoost", "subtitle": ["A Scalable Tree Boosting System"]}
    local = "XGBoost: A Scalable Tree Boosting System"
    title_only = fuzz.token_sort_ratio(normalize_title(csl["title"]), normalize_title(local))
    full = fuzz.token_sort_ratio(normalize_title(doi2bib._csl_full_title(csl)),
                                 normalize_title(local))
    assert title_only < 70   # the old comparison would FABRICATE
    assert full >= 97        # the fixed comparison PASSes


# ---------- bib_doctor.py: preprints don't require a journal ----------

def _article(key, fields):
    return {"type": "article", "key": key, "fields": fields}


def test_arxiv_preprint_article_not_flagged_missing_journal():
    e = _article("fisher2018all", {
        "author": "Fisher, Aaron", "title": "All Models are Wrong",
        "year": "2018", "doi": "10.48550/arXiv.1801.01489", "verified": "true"})
    problems, _ = bib_doctor.audit([e])
    kinds = {i["kind"] for p in problems for i in p["issues"]}
    msgs = " ".join(i["msg"] for p in problems for i in p["issues"])
    assert "missing-field" not in kinds or "journal" not in msgs


def test_biorxiv_doi_detected_as_preprint():
    assert bib_doctor._is_preprint({"doi": "10.1101/2020.01.01.123456"})


def test_archiveprefix_field_detected_as_preprint():
    assert bib_doctor._is_preprint({"archiveprefix": "arXiv", "eprint": "1801.01489"})


def test_journal_named_arxiv_detected_as_preprint():
    assert bib_doctor._is_preprint({"journal": "arXiv preprint arXiv:1801.01489"})


def test_real_article_without_journal_still_flagged():
    # A genuine journal article missing its journal is still a real problem.
    e = _article("kaya2023deep", {
        "author": "Kaya, Ahmet", "title": "Deep learning for bearing faults",
        "year": "2023", "doi": "10.1016/j.ymssp.2023.00001", "verified": "true"})
    problems, _ = bib_doctor.audit([e])
    msgs = " ".join(i["msg"] for p in problems for i in p["issues"])
    assert "journal" in msgs


def test_preprint_without_locator_still_flagged():
    # A preprint with neither doi nor url is unlocatable — must still flag.
    e = _article("ghost2020", {
        "archiveprefix": "arXiv", "author": "Ghost, A", "title": "No locator",
        "year": "2020", "verified": "true"})
    problems, _ = bib_doctor.audit([e])
    msgs = " ".join(i["msg"] for p in problems for i in p["issues"])
    assert "url|doi" in msgs


# ---------- venue_check.py: OpenAlex title match must be re-ranked ----------

def test_best_title_match_rejects_wrong_journal():
    results = [
        {"display_name": "Biotechnology and Bioengineering", "id": "W-wrong"},
        {"display_name": "Bioengineering", "id": "W-right"},
    ]
    # Even though OpenAlex ranks the wrong one first, similarity re-ranking wins.
    assert venue_check._best_title_match(results, "Bioengineering")["id"] == "W-right"


def test_best_title_match_returns_none_when_no_close_match():
    results = [{"display_name": "Biotechnology and Bioengineering", "id": "W-wrong"}]
    assert venue_check._best_title_match(results, "Bioengineering") is None


def test_best_title_match_accepts_exact():
    results = [{"display_name": "IEEE Access", "id": "W-1"}]
    assert venue_check._best_title_match(results, "IEEE Access")["id"] == "W-1"


def test_best_title_match_empty_results():
    assert venue_check._best_title_match([], "Anything") is None


# ---------- evidence_db.py: stdin is UTF-8, not the console codepage ----------

def test_evidence_db_stdin_preserves_utf8_under_non_utf8_locale(tmp_path):
    # Simulate the Windows console codepage by forcing a non-UTF-8 text encoding
    # on the child's stdio. Because add --stdin now reads sys.stdin.buffer and
    # decodes UTF-8 itself, the Greek/math symbols must survive regardless.
    import os
    cards = tmp_path / "cards.jsonl"
    cards.write_text("", encoding="utf-8")
    payload = {"source": "kaya2023x", "type": "finding",
               "claim": "surrogate error ξ grows with π and σ (Ω, Σ)"}
    env = {**os.environ, "PYTHONIOENCODING": "cp1254", "PYTHONUTF8": "0"}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "evidence_db.py"), "--file", str(cards),
         "add", "--stdin"],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True, cwd=tmp_path, env=env, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    stored = json.loads(cards.read_text(encoding="utf-8").strip())
    assert stored["claim"] == payload["claim"]
    assert "ξ" in stored["claim"] and "Σ" in stored["claim"]
