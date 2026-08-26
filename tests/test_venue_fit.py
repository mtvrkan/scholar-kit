"""Tests for venue_fit.py — the target-venue shortlist derived from the registry.

The output is a COUNT presented as guidance, which makes two failure modes
matter more than the usual ones: a wrong merge silently moves sources from one
venue's tally to another's, and a stale/absent index lookup silently turns
"we don't know" into "no flags". Both are pinned here.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "venue_fit.py"
sys.path.insert(0, str(ROOT / "scripts"))

import venue_fit  # noqa: E402


def _write(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8")


def src(i, venue, year=2023, status="included", **extra):
    return {"id": f"SRC-{i:04d}", "title": f"Paper {i}", "year": year,
            "venue": venue, "status": status, **extra}


@pytest.fixture
def project(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "PROJECT.md").write_text("# p\n", encoding="utf-8")
    return tmp_path


def run(project, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=project,
                          capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


def analyze(project, statuses=("included",), top=20):
    return venue_fit.analyze(project / "sources" / "registry.jsonl",
                             project / "sources" / "venues.jsonl", statuses, top)


# ---------- grouping ----------

def test_ranks_venues_by_how_many_of_your_own_sources_they_published(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A"), src(2, "Journal A"), src(3, "Journal A"),
        src(4, "Journal B"), src(5, "Journal B"),
        src(6, "Journal C"),
    ])
    out = analyze(project)
    assert [e["venue"] for e in out["shortlist"]] == ["Journal A", "Journal B", "Journal C"]
    assert out["shortlist"][0]["own_refs"] == 3
    assert out["shortlist"][0]["share"] == 0.5


def test_conference_proceedings_prefix_does_not_split_a_venue(project):
    # "Proceedings of the X" and "X" are one venue. Left unmerged, a conference
    # that dominates your references reads as two mid-sized ones and drops out
    # of the shortlist.
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Proceedings of the International Conference on Machine Learning"),
        src(2, "International Conference on Machine Learning"),
        src(3, "Proc. of International Conference on Machine Learning"),
    ])
    out = analyze(project)
    assert out["distinct_venues"] == 1
    assert out["shortlist"][0]["own_refs"] == 3


def test_case_and_punctuation_variants_group_together(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "IEEE Trans. Med. Imaging"), src(2, "IEEE Trans Med Imaging"),
    ])
    assert analyze(project)["distinct_venues"] == 1


def test_distinct_venues_are_not_merged(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "IEEE Transactions on Medical Imaging"),
        src(2, "IEEE Transactions on Image Processing"),
    ])
    out = analyze(project)
    assert out["distinct_venues"] == 2, out["merged_variants"]


def test_every_fuzzy_merge_is_reported(project):
    # A merge changes the number the user acts on. It must be visible, because
    # only the user can tell whether two similar names are one venue. Note the
    # distinction: case/punctuation folding is normalization (deterministic and
    # lossless, nothing to report); a similarity-threshold merge is a JUDGEMENT
    # and gets reported. This pair — a dropped plural — only survives the fuzzy
    # path.
    pytest.importorskip("rapidfuzz")
    _write(project / "sources" / "registry.jsonl", [
        src(1, "IEEE Transactions on Medical Imaging"),
        src(2, "IEEE Transaction on Medical Imaging"),
    ])
    out = analyze(project)
    assert out["distinct_venues"] == 1
    assert out["merged_variants"], "a fuzzy merge happened but was not reported"


def test_normalization_grouping_is_not_reported_as_a_merge(project):
    # Reporting every case/punctuation fold as a "merge" would bury the handful
    # of judgement calls the user actually needs to check.
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal of Applied Signal Processing"),
        src(2, "Journal of Applied Signal Processing."),
    ])
    out = analyze(project)
    assert out["distinct_venues"] == 1
    assert out["merged_variants"] == []


def test_display_name_is_a_verbatim_registry_string(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Nature Machine Intelligence"), src(2, "Nature Machine Intelligence"),
        src(3, "NATURE MACHINE INTELLIGENCE"),
    ])
    out = analyze(project)
    assert out["shortlist"][0]["venue"] == "Nature Machine Intelligence"


# ---------- status selection ----------

def test_only_included_sources_count_by_default(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", status="included"),
        src(2, "Journal B", status="candidate"),
        src(3, "Journal C", status="excluded"),
        src(4, "Journal D", status="duplicate"),
    ])
    out = analyze(project)
    assert out["sources_counted"] == 1
    assert [e["venue"] for e in out["shortlist"]] == ["Journal A"]


def test_falls_back_to_screened_and_says_so(project):
    # Before full-text decisions there is nothing 'included'. Returning an empty
    # shortlist would be technically true and useless; substituting silently
    # would misrepresent what the numbers are.
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", status="screened"), src(2, "Journal A", status="screened"),
    ])
    out = analyze(project)
    assert out["shortlist"]
    assert "screened" in out["status_note"]
    assert out["statuses_counted"] == ["included", "screened"]


def test_explicit_status_flag_disables_the_fallback(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", status="screened"),
    ])
    out = analyze(project, statuses=("excluded",))
    assert out["shortlist"] == []
    assert "status_note" not in out


def test_sources_without_a_venue_are_counted_not_dropped(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A"), src(2, ""), src(3, None),
    ])
    out = analyze(project)
    assert out["sources_counted"] == 3
    assert out["sources_with_venue"] == 1
    assert out["sources_without_venue"] == 2


def test_empty_registry_reports_empty_rather_than_crashing(project):
    _write(project / "sources" / "registry.jsonl", [])
    out = analyze(project)
    assert out["status"] == "empty"
    assert out["shortlist"] == []


# ---------- index metadata ----------

def test_index_metadata_comes_from_the_registry_record_when_present(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", venue_meta={"quartile": "Q1", "wos_index": "SCIE",
                                        "scopus": True}),
    ])
    entry = analyze(project)["shortlist"][0]
    assert entry["index"]["quartile"] == "Q1"
    assert entry["index_provenance"] == "registry"


def test_index_metadata_falls_back_to_the_venue_check_cache_by_issn(project):
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A", issn="0888-3270")])
    _write(project / "sources" / "venues.jsonl",
           [{"issn": "0888-3270", "display_name": "Journal A", "quartile": "Q2",
             "scopus": True}])
    entry = analyze(project)["shortlist"][0]
    assert entry["index"]["quartile"] == "Q2"
    assert entry["index_provenance"] == "venue-cache"


def test_index_metadata_falls_back_to_the_cache_by_venue_name(project):
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A")])
    _write(project / "sources" / "venues.jsonl",
           [{"display_name": "Journal A", "quartile": "Q3"}])
    assert analyze(project)["shortlist"][0]["index"]["quartile"] == "Q3"


def test_unknown_index_is_reported_as_unknown_with_the_resolving_command(project):
    # The dangerous failure is presenting "we never looked" as "nothing found".
    _write(project / "sources" / "registry.jsonl", [src(1, "Obscure Journal")])
    entry = analyze(project)["shortlist"][0]
    assert entry["index_provenance"] == "unknown"
    assert "venue_check.py" in entry["resolve_with"]
    assert analyze(project)["unresolved_venues"] == 1


def test_unknown_index_never_produces_a_concern(project):
    # An unresolved venue must not be reported as unindexed — that would turn
    # missing data into a finding.
    _write(project / "sources" / "registry.jsonl", [src(1, "Obscure Journal")])
    assert analyze(project)["concerns"] == []


# ---------- concerns: the reference list read backwards ----------

def test_cited_predatory_venue_is_surfaced_as_a_concern(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Fast Publish Journal", venue_meta={"predatory_flag": True}),
        src(2, "Fast Publish Journal", venue_meta={"predatory_flag": True}),
    ])
    out = analyze(project)
    assert out["concerns"][0]["concern"] == "predatory_flag"
    assert out["concerns"][0]["own_refs"] == 2


def test_cited_unindexed_venue_is_surfaced_but_not_as_predatory(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Local Bulletin", venue_meta={"wos_index": "NONE", "scopus": False,
                                             "doaj": False, "tr_dizin": False,
                                             "quartile": None}),
    ])
    concerns = analyze(project)["concerns"]
    assert [c["concern"] for c in concerns] == ["unindexed"]


def test_an_indexed_venue_raises_no_concern(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", venue_meta={"quartile": "Q1", "scopus": True}),
        src(2, "Journal B", venue_meta={"tr_dizin": True}),
        src(3, "Journal C", venue_meta={"wos_index": "ESCI"}),
    ])
    assert analyze(project)["concerns"] == []


def test_venue_flagged_predatory_still_appears_in_the_shortlist(project):
    # Filtering it out would hide that your own references lean on it.
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Fast Publish Journal", venue_meta={"predatory_flag": True}),
    ])
    out = analyze(project)
    assert [e["venue"] for e in out["shortlist"]] == ["Fast Publish Journal"]


# ---------- recency ----------

def test_years_report_newest_and_median(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", year=2011), src(2, "Journal A", year=2015),
        src(3, "Journal A", year=2024),
    ])
    years = analyze(project)["shortlist"][0]["years"]
    assert years == {"newest": 2024, "median": 2015, "with_year": 3}


def test_unparseable_years_are_skipped_not_guessed(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", year="n.d."), src(2, "Journal A", year=None),
        src(3, "Journal A", year=2020),
    ])
    assert analyze(project)["shortlist"][0]["years"] == {
        "newest": 2020, "median": 2020, "with_year": 1}


def test_recency_breaks_ties_between_equally_cited_venues(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Old Journal", year=2004), src(2, "New Journal", year=2025),
    ])
    assert [e["venue"] for e in analyze(project)["shortlist"]] == [
        "New Journal", "Old Journal"]


# ---------- output contract ----------

def test_truncation_is_reported_never_silent(project):
    _write(project / "sources" / "registry.jsonl",
           [src(i, f"Journal {i}") for i in range(1, 8)])
    out = analyze(project, top=3)
    assert len(out["shortlist"]) == 3
    assert out["shortlist_truncated"] == 4


def test_output_states_what_it_measures_and_what_it_does_not(project):
    # The whole risk of this tool is being read as a submission recommendation.
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A")])
    measures = analyze(project)["measures"]
    assert "NOT acceptance probability" in measures


def test_no_composite_score_is_emitted(project):
    # POSITIONING refuses numbers whose weights are hidden. own_refs and share
    # are auditable; a "fit score" would not be.
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A")])
    entry = analyze(project)["shortlist"][0]
    assert not [k for k in entry if "score" in k.lower()], entry.keys()
    assert entry["own_refs"] == 1 and entry["share"] == 1.0


# ---------- CLI ----------

def test_cli_emits_json_and_exits_zero(project):
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A")])
    code, out, err = run(project, "--json")
    assert code == 0, err
    assert json.loads(out)["status"] == "ok"


def test_cli_runs_with_no_registry_file_at_all(project):
    # A fresh project has no registry yet; the tool must say so, not traceback.
    code, out, err = run(project, "--json")
    assert code == 0, err
    assert json.loads(out)["status"] == "empty"


def test_cli_rejects_a_path_outside_the_project(project):
    code, out, err = run(project, "--registry", "../escape.jsonl")
    assert code != 0
    assert "registry" in (out + err).lower()


def test_cli_rejects_a_nonsensical_top(project):
    _write(project / "sources" / "registry.jsonl", [src(1, "Journal A")])
    assert run(project, "--top", "0")[0] != 0


def test_cli_status_flag_is_repeatable(project):
    _write(project / "sources" / "registry.jsonl", [
        src(1, "Journal A", status="included"), src(2, "Journal B", status="screened"),
    ])
    code, out, err = run(project, "--status", "included", "--status", "screened")
    assert code == 0, err
    assert json.loads(out)["distinct_venues"] == 2
