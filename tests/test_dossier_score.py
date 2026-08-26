"""The promotion dossier (scripts/dossier_score.py), with no memory at all.

Two things are pinned here. The first is the finding that justifies the script:
an ESCI paper entered under the SCI-E criterion — usually honestly, because the
journal was SCIE when the work started — is caught against the venue cache rather
than trusted from the export.

The second is the boundary. `POSITIONING.md` refuses cross-paper memory, and this
is the feature that looked like it would have to move that line. It does not: the
script keeps nothing, and `test_nothing_is_written_outside_the_project_directory`
is what makes that a guarantee rather than a promise.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dossier_score as ds  # noqa: E402

CRITERIA = {
    "authority": "Example University promotion table 2026",
    "source_url": "https://example.edu/kriterler.pdf",
    "read_on": "2026-08-15",
    "minimum_total": 100,
    "criteria": [
        {"id": "A1", "label": "SCI-E/SSCI article", "points": 20,
         "match": {"type": "article", "index": ["SCIE", "SSCI"]}, "min_count": 2},
        {"id": "A5", "label": "ESCI article", "points": 10,
         "match": {"type": "article", "index": ["ESCI"]}},
        {"id": "B1", "label": "Conference paper", "points": 5,
         "match": {"type": "conference"}, "max_count": 2},
    ],
}

VENUES = [
    {"issn": "08883270", "display_name": "Mechanical Systems and Signal Processing",
     "wos_index": "SCIE", "scopus": True, "quartile": "Q1", "checked_at": "2026-08-01"},
    {"issn": "12345678", "display_name": "Journal of Emerging Things",
     "wos_index": "ESCI", "scopus": False, "checked_at": "2026-08-01"},
]

PUBS = [
    {"title": "A CNN for bearing faults", "year": 2024, "type": "article",
     "venue": "Mechanical Systems and Signal Processing", "issn": "0888-3270",
     "index": "SCIE"},
    {"title": "Transfer learning under load", "year": 2025, "type": "article",
     "venue": "Journal of Emerging Things", "issn": "1234-5678", "index": "SCIE"},
    {"title": "A short conference note", "year": 2023, "type": "conference",
     "venue": "Some Symposium"},
]


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "dossier_score.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, pubs=PUBS, criteria=CRITERIA, venues=VENUES, name="pubs.json"):
    (tmp_path / "dossier").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sources").mkdir(parents=True, exist_ok=True)
    (tmp_path / "dossier" / name).write_text(json.dumps(pubs), encoding="utf-8")
    if criteria is not None:
        (tmp_path / "dossier" / "criteria.json").write_text(json.dumps(criteria),
                                                            encoding="utf-8")
    (tmp_path / "sources" / "venues.jsonl").write_text(
        "".join(json.dumps(v) + "\n" for v in venues), encoding="utf-8")
    return tmp_path


# ---------- the finding that justifies the script ----------

def test_a_claimed_scie_that_the_cache_says_is_esci_is_reported():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    mismatch = report["index_mismatches"][0]
    assert mismatch["claimed"] == "SCIE"
    assert mismatch["verified"] == ["ESCI"]
    assert mismatch["checked_at"] == "2026-08-01"


def test_the_mismatched_paper_scores_against_the_verified_index_not_the_claim():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    row = next(r for r in report["rows"] if r["title"].startswith("Transfer"))
    assert row["criterion"] == "A5"
    assert row["points"] == 10


def test_verified_publications_carry_the_date_the_index_was_checked():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    row = next(r for r in report["rows"] if r["title"].startswith("A CNN"))
    assert row["verified_on"] == "2026-08-01"
    assert row["state"] == "verified"


# ---------- unverified is its own bucket ----------

def test_an_unverified_venue_is_neither_counted_nor_dropped():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    assert report["per_criterion"]["B1"]["pending"] == 1
    assert report["per_criterion"]["B1"]["counted"] == 0
    assert report["points_pending_verification"] == 5
    assert report["points_counted"] == 30  # 20 (SCIE) + 10 (ESCI), not the conference


def test_the_unverified_venue_comes_with_the_command_that_resolves_it():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    assert "venue_check.py" in report["unverified_venues"][0]["resolve_with"]


# ---------- the arithmetic ----------

def test_a_criterion_cap_stops_counting_past_it():
    pubs = [{"title": f"Conf {i}", "year": 2023, "type": "conference",
             "venue": "Some Symposium", "issn": "99999999"} for i in range(4)]
    venues = VENUES + [{"issn": "99999999", "display_name": "Some Symposium",
                        "wos_index": "NONE", "checked_at": "2026-08-01"}]
    report = ds.score(pubs, CRITERIA, venues)
    assert report["per_criterion"]["B1"]["counted"] == 2
    assert report["per_criterion"]["B1"]["over_cap"] == 2
    assert report["points_counted"] == 10


def test_a_criterion_below_its_stated_minimum_is_a_finding():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    assert any("minimum of 2" in p for p in report["problems"])


def test_a_publication_matching_no_criterion_is_named():
    pubs = [{"title": "A book", "year": 2022, "type": "book", "venue": "A Press"}]
    report = ds.score(pubs, CRITERIA, [])
    assert report["unmatched_publications"] == ["A book"]


def test_sufficiency_is_never_decided():
    report = ds.score(json.loads(json.dumps(PUBS)), CRITERIA, VENUES)
    assert report["minimum_total"] == 100
    assert "committee's decision" in report["note"]
    assert "sufficient" not in json.dumps(report["per_criterion"])


# ---------- the boundary ----------

def test_nothing_is_written_outside_the_project_directory(tmp_path):
    """The whole reason this feature did not have to move POSITIONING's
    cross-paper-memory line."""
    project = _project(tmp_path / "proj")
    sibling = tmp_path / "elsewhere"
    sibling.mkdir()
    before = sorted(p.name for p in tmp_path.iterdir())
    _run(project, "--publications", "dossier/pubs.json", expect=2)
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert list(sibling.iterdir()) == []


def test_a_write_target_outside_the_project_is_refused(tmp_path):
    project = _project(tmp_path / "proj")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dossier_score.py"),
         "--publications", "dossier/pubs.json", "--cv", "--write", "../escaped.md"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "inside the current project directory" in proc.stderr


def test_no_criteria_file_reports_unchecked_not_ok(tmp_path):
    report = json.loads(_run(_project(tmp_path, criteria=None),
                             "--publications", "dossier/pubs.json", expect=2).stdout)
    assert report["result"] == "UNCHECKED"
    assert "will not recall a point value" in report["note"]
    assert report["publications"] == 3  # listed, just not scored


def test_a_criteria_file_with_no_source_is_refused(tmp_path):
    project = _project(tmp_path, criteria={"criteria": [{"id": "A1", "points": 20}]})
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dossier_score.py"),
         "--publications", "dossier/pubs.json"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "source_url" in proc.stderr


# ---------- inputs ----------

def test_a_bibtex_export_is_read_as_publications(tmp_path):
    bib = ("@article{a2024,\n  title = {A CNN for bearing faults},\n"
           "  journal = {Mechanical Systems and Signal Processing},\n"
           "  issn = {0888-3270},\n  year = {2024},\n}\n")
    project = _project(tmp_path, name="pubs.bib")
    (project / "dossier" / "pubs.bib").write_text(bib, encoding="utf-8")
    report = json.loads(_run(project, "--publications", "dossier/pubs.bib",
                             expect=2).stdout)
    row = report["rows"][0]
    assert row["type"] == "article"
    assert row["verified_indexes"] == ["SCIE", "SCOPUS"]


def test_a_csv_export_is_read_as_publications(tmp_path):
    project = _project(tmp_path, name="pubs.csv")
    (project / "dossier" / "pubs.csv").write_text(
        "Title,Year,Type,Venue,ISSN\nA CNN,2024,article,MSSP,0888-3270\n",
        encoding="utf-8")
    report = json.loads(_run(project, "--publications", "dossier/pubs.csv",
                             expect=2).stdout)
    assert report["rows"][0]["year"] == 2024


def test_an_unsupported_export_format_names_what_to_use(tmp_path):
    project = _project(tmp_path)
    (project / "dossier" / "pubs.xml").write_text("<x/>", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dossier_score.py"),
         "--publications", "dossier/pubs.xml"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "both export BibTeX" in proc.stderr


# ---------- the CV ----------

def test_the_cv_groups_by_the_criteria_tables_own_categories(tmp_path):
    out = _run(_project(tmp_path), "--publications", "dossier/pubs.json", "--cv").stdout
    assert "## SCI-E/SSCI article" in out
    assert "## ESCI article" in out
    assert "index unverified" in out  # the conference paper, honestly labelled


def test_the_cv_says_nothing_was_recalled(tmp_path):
    out = _run(_project(tmp_path), "--publications", "dossier/pubs.json", "--cv").stdout
    assert "Nothing here was recalled" in out
