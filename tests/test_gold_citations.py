"""Gold-DOI regression harness — live network, skipped unless RUN_LIVE=1.

`tests/gold_citations.jsonl` holds a small set of well-known, stable DOIs with
independently-known title/year/first-author metadata. Two of the five (the
XGBoost and LIME papers) are the exact ACM/Crossref colon-title-split case that
once produced a false FABRICATED verdict in doi2bib.py's cmd_verify — this
harness pins that fix down against the REAL live metadata, not just a synthetic
CSL fixture (see test_remediation_2026_07_05_kit_improvements.py for the
synthetic/fast version of the same check). The other three are single-field-
title control cases that should always PASS, with or without the subtitle fix,
guarding against a future change breaking the common case while "fixing" the
edge case.

Run explicitly: RUN_LIVE=1 python -m pytest tests/test_gold_citations.py -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doi2bib  # noqa: E402
from lib_common import normalize_title  # noqa: E402

GOLD = [json.loads(line) for line in
        (ROOT / "tests" / "gold_citations.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()]

pytestmark = pytest.mark.live


@pytest.mark.parametrize("entry", GOLD, ids=[e["doi"] for e in GOLD])
def test_csl_metadata_matches_known_ground_truth(entry):
    csl = doi2bib.fetch_csl(entry["doi"])
    assert csl, f"doi.org returned nothing for {entry['doi']}"

    full_title = doi2bib._csl_full_title(csl)
    from rapidfuzz import fuzz
    sim = fuzz.token_sort_ratio(normalize_title(full_title), normalize_title(entry["expected_title"]))
    assert sim >= 90, (
        f"{entry['doi']}: reconstructed title {full_title!r} only {sim:.0f}% similar "
        f"to expected {entry['expected_title']!r}")

    year = doi2bib._csl_year(csl)
    assert year == entry["expected_year"], f"{entry['doi']}: year {year} != expected {entry['expected_year']}"

    fam = doi2bib._first_author_family(csl)
    assert fam == entry["expected_first_author_family"], (
        f"{entry['doi']}: first author family {fam!r} != expected {entry['expected_first_author_family']!r}")


def test_fetch_then_verify_round_trip_passes_for_every_gold_doi(tmp_path):
    """The true end-to-end regression: fetch each gold DOI's real BibTeX via
    cmd_fetch, write it to a bib file, then run cmd_verify against it — this is
    exactly the fetch->verify path that produced the original false-FABRICATED
    bug on the XGBoost/LIME entries, reproduced here against live data."""
    import subprocess

    # doi2bib writes references.bib itself, relative to cwd=tmp_path — there is
    # deliberately no path built here for it to write to.
    for entry in GOLD:
        code = subprocess.run(
            [sys.executable, str(SCRIPTS / "doi2bib.py"), "--doi", entry["doi"],
             "--append", "references.bib", "--json"],
            cwd=tmp_path, capture_output=True, text=True, timeout=30)
        assert code.returncode == 0, f"fetch failed for {entry['doi']}: {code.stderr}"

    verify = subprocess.run(
        [sys.executable, str(SCRIPTS / "doi2bib.py"), "--verify", "--bib", "references.bib", "--json"],
        cwd=tmp_path, capture_output=True, text=True, timeout=60)
    result = json.loads(verify.stdout)
    fabricated = [r for r in result["entries"] if r["status"] == "FABRICATED"]
    assert not fabricated, f"gold DOIs falsely flagged FABRICATED: {fabricated}"
    assert result["result"] in ("PASS", "FIX"), f"unexpected verify result: {result}"
