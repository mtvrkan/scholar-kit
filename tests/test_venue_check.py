import datetime
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import venue_check  # noqa: E402


def _fresh() -> str:
    """A `checked_at` guaranteed inside the 30-day cache TTL.

    These fixtures used to hardcode a date. That silently converts a
    cache-behaviour test into a time bomb: the fixture ages past CACHE_TTL_DAYS
    and the assertion starts failing (roundtrip) — or, worse, keeps passing for
    the wrong reason, as in the ISSN-mismatch test below, where a stale record
    is rejected on staleness and would pass even if the ISSN check broke.
    """
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def test_main_guard_declares_oserror_catch():
    # venue_check.py's write path (cache_put) sits behind a real network call,
    # which the rest of this suite deliberately avoids mocking here — a direct
    # static check on the `__main__` guard locks in the fix (an unrecoverable
    # Windows file-lock collision from lib_common's atomic-write retry must
    # surface as a clean die(), not a raw traceback) without a fragile
    # network-mocked subprocess test.
    text = Path(__file__).parent.parent.joinpath("scripts", "venue_check.py").read_text(encoding="utf-8")
    guard = text[text.rindex('if __name__ == "__main__":'):]
    assert "except OSError as e:" in guard
    assert "failed to write" in guard

SCIMAGO = """Rank;Title;Issn;SJR;SJR Best Quartile
1;Mechanical Systems and Signal Processing;08883270, 10961216;2.5;Q1
2;Orta Dizin Dergisi;12345678;0.3;Q3
"""
SCOPUS = """title,issn,eissn
Mechanical Systems and Signal Processing,0888-3270,1096-1216
Scopus Only Journal,11112222,
"""
TRDIZIN = """title,issn
Türk Akademik Dergisi,33334444
"""
WOS = """title,issn,index
Mechanical Systems and Signal Processing,0888-3270,SCIE
Emerging Topics Review,55556666,ESCI
"""


@pytest.fixture
def datasets(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    (d / "scimago.csv").write_text(SCIMAGO, encoding="utf-8")
    (d / "scopus.csv").write_text(SCOPUS, encoding="utf-8")
    (d / "trdizin.csv").write_text(TRDIZIN, encoding="utf-8")
    (d / "wos.csv").write_text(WOS, encoding="utf-8")
    monkeypatch.setattr(venue_check, "DATA_DIR", d)
    return d


def classify(issn=None, title=None):
    meta = {}
    meta.update(venue_check.lookup_local(venue_check.normalize_issn(issn) if issn else "",
                                         title or ""))
    return meta


def test_five_journal_classification(datasets):
    """Acceptance: SCIE Q1 · ESCI · Scopus-only · TR Dizin-only · unindexed all classify correctly."""
    mssp = classify(issn="0888-3270")
    assert mssp["wos_index"] == "SCIE" and mssp["quartile"] == "Q1" and mssp["scopus"] is True

    esci = classify(issn="5555-6666")
    assert esci["wos_index"] == "ESCI"

    scopus_only = classify(issn="1111-2222")
    assert scopus_only.get("scopus") is True and "wos_index" not in scopus_only

    trd = classify(title="Türk Akademik Dergisi")
    assert trd.get("tr_dizin") is True

    nothing = classify(issn="9999-0000")
    assert nothing == {}  # unindexed → caller sets unknown/predatory heuristics


def test_predatory_heuristic():
    known_unindexed = {"openalex_id": "https://openalex.org/S1", "works_count": 500}
    assert venue_check.assess_predatory(known_unindexed) is True
    indexed = {**known_unindexed, "scopus": True}
    assert venue_check.assess_predatory(indexed) is False
    unknown = {"works_count": 500}
    assert venue_check.assess_predatory(unknown) is False


def test_predatory_heuristic_treats_wos_index_none_as_not_indexed():
    # Regression: `--set-wos none` used to store the literal lowercase string
    # "none", but assess_predatory() only excludes uppercase "NONE" (plus None
    # and "unknown") from the "indexed" set — the case mismatch made a venue
    # EXPLICITLY confirmed absent from WoS look "indexed", suppressing the
    # predatory flag in exactly the case it exists to catch.
    confirmed_not_in_wos = {"openalex_id": "https://openalex.org/S1",
                            "works_count": 500, "wos_index": "NONE"}
    assert venue_check.assess_predatory(confirmed_not_in_wos) is True
    # Any recognized index still correctly suppresses the flag.
    also_in_scopus = {**confirmed_not_in_wos, "scopus": True}
    assert venue_check.assess_predatory(also_in_scopus) is False


def test_set_wos_none_stores_uppercase_not_lowercase(run, tmp_path):
    cache = tmp_path / "venues.jsonl"
    code, out, err = run("venue_check.py", "--issn", "9999-1234", "--title", "Some Journal",
                         "--set-wos", "none", "--cache", str(cache), "--json")
    assert code == 0, err
    data = json.loads(out)
    assert data["venue"]["wos_index"] == "NONE", data


def test_cache_roundtrip(tmp_path):
    cache = tmp_path / "venues.jsonl"
    rec = {"issn": "0888-3270", "display_name": "MSSP", "wos_index": "SCIE",
           "checked_at": _fresh()}
    venue_check.cache_put(cache, rec)
    hit = venue_check.cache_get(cache, "08883270", "")
    assert hit and hit["wos_index"] == "SCIE"
    # stale record (31+ days old) is ignored
    venue_check.cache_put(cache, {**rec, "checked_at": "2020-01-01"})
    assert venue_check.cache_get(cache, "08883270", "") is None


def test_cache_get_issn_mismatch_not_overridden_by_title_coincidence(tmp_path):
    """A cached record with a DIFFERENT ISSN but a coincidentally-matching title
    must not be returned as a hit when the caller queries by ISSN — a reused
    journal title string is not proof of identity when ISSNs disagree."""
    cache = tmp_path / "venues.jsonl"
    venue_check.cache_put(cache, {"issn": "1111-1111", "display_name": "Signal Processing",
                                  "wos_index": "SCIE", "checked_at": _fresh()})
    assert venue_check.cache_get(cache, "22222222", "Signal Processing") is None


@pytest.mark.live
def test_live_openalex_smoke():
    meta = venue_check.lookup_openalex("08883270", "")
    assert meta.get("display_name"), meta
