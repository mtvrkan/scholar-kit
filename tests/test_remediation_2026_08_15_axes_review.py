"""Self-review of the D-098 axes, and the seven defects it found.

Every gate was green when this review started — validate_kit, ruff, the full
suite, both eval harnesses. Green gates are not correctness, and six of the seven
findings below are the same failure wearing different clothes: **a check that
reports OK for having checked nothing.**

  1. `dmp_gen --check` on an empty dataset register → OK, exit 0
  2. `proposal_check` with a call file carrying `source_url` but no `fields` →
     zero sections checked, reported OK (and never UNCHECKED, because the
     authority file existed)
  3. `syllabus_check` on a syllabus with no learning outcomes → OK, because every
     other check on it is relative to that list
  4. `syllabus_check` workload with no ECTS beside it → a quiet `checked: false`
  5. `dossier_score` on an empty publication export → OK
  6. `dossier_score` dropping publications past a criterion cap without naming them
  7. `ethics_pack` matching collected field names as substrings, so a column
     called `id` or `e` read as disclosed by any sentence containing those letters
     — a false NEGATIVE on the one check that script exists for
  8. `proposal_check --report` with no work-package plan → OK, exit 0
  9. `syllabus_check`'s Bloom verbs prefix-matched in English too, so "useful"
     read as *apply*, "namely" as *remember* and "statement" as *remember* — an
     unmeasurable outcome passing as measurable

Plus two the tests could not see: the three new project directories were missing
from `.claude/settings.json`'s write allowlist, and `/dmp`'s SKILL.md documented
`dataset_db.py verify DS-0002` when the flag is `--id`.

Recorded here as a not-a-defect, and the note was itself wrong — the tenth
finding, from the next review pass: bandit reports two HIGH B202
`tarfile.extractall` findings in `dataset_fetch.py`. The first half stands. The
extraction is guarded (path-escape check, symlink/hardlink refusal, member and
size ceilings, `filter="data"` on 3.12+) and B202 is a pattern match that cannot
see any of that. The second half — "CI's `-ll` threshold already passes" — was
written without running the command. `-ll` reports MEDIUM **and above**, HIGH is
above MEDIUM, so bandit exited 1: the `lint` job was red on a clean tree and the
pre-commit hook blocked every commit touching `scripts/`. Which is the same
failure as the six above, one layer out — a gate recorded as passing by someone
who did not run it. Both call sites now carry a justified `# nosec B202`, and
`tests/test_lint_and_ci_config.py` runs the CI command instead of describing it.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dmp_gen as dg  # noqa: E402
import dossier_score as ds  # noqa: E402
import ethics_pack as ep  # noqa: E402
import proposal_check as pc  # noqa: E402
import syllabus_check as sc  # noqa: E402


def _run(script, cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- 1. an empty register is not a clean one ----------

def test_a_dmp_over_an_empty_dataset_register_is_unchecked(tmp_path):
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis" / "datasets.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "analysis" / "runs.jsonl").write_text("", encoding="utf-8")
    report = json.loads(_run("dmp_gen.py", tmp_path, "--check", expect=2).stdout)
    assert report["result"] == "UNCHECKED"
    assert "nothing was derived and nothing was checked" in report["note"]


def test_a_populated_register_still_reports_ok():
    """The fix must not turn every clean run into UNCHECKED."""
    complete = {"id": "DS-1", "name": "d", "license": "CC-BY-4.0",
                "license_verified": True, "citation": {"doi": "10.1/x"},
                "url": "https://x", "files": [{"path": "a.csv", "sha256": "ab" * 32}]}
    assert dg.build([complete], [], dg.CORE_SECTIONS, False)["result"] == "OK"


# ---------- 2. an authority file with no list checks nothing ----------

def test_a_call_file_with_no_fields_array_is_refused(tmp_path):
    (tmp_path / "proposal").mkdir()
    (tmp_path / "proposal" / "call-fields.json").write_text(
        json.dumps({"source_url": "https://x", "duration_months": 12}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPTS / "proposal_check.py"), "--check"],
                          cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "checks nothing and would report OK" in proc.stderr


def test_a_call_field_entry_with_no_name_is_named_rather_than_matching_everything():
    """An empty label is a substring of every heading, so the first section in the
    document became that field's answer."""
    result = pc.check_narrative("# P\n\n## Summary\nreal text\n",
                                {"fields": [{"max_words": 10}], "source_url": "x"})
    assert any("has no 'name'" in p for p in result["problems"])
    assert result["fields"][0]["malformed"] is True


# ---------- 3 & 4. a syllabus that promises nothing ----------

def test_a_syllabus_with_no_outcomes_does_not_pass_by_vacancy():
    result = sc.check_outcomes([])
    assert any("pass by vacancy" in p for p in result["problems"])


def test_the_whole_syllabus_run_fails_when_there_are_no_outcomes(tmp_path):
    (tmp_path / "teaching").mkdir()
    (tmp_path / "teaching" / "syllabus.json").write_text(
        json.dumps({"course": {"code": "X", "ects": 6}}), encoding="utf-8")
    report = json.loads(_run("syllabus_check.py", tmp_path, expect=2).stdout)
    assert report["result"] == "FINDINGS"


def test_a_workload_with_no_ects_says_it_was_not_checked():
    result = sc.check_workload([{"activity": "Ders", "count": 14, "hours": 3}], None)
    assert result["checked"] is False
    assert any("measured against nothing" in p for p in result["problems"])


def test_no_workload_table_at_all_also_says_so():
    result = sc.check_workload([], 6)
    assert any("no workload table" in p for p in result["problems"])


# ---------- 5 & 6. the dossier ----------

def test_an_empty_publication_export_is_a_finding():
    report = ds.score([], {"source_url": "x", "criteria": [{"id": "A1", "points": 1}]},
                      [])
    assert any("holds no entries" in p for p in report["problems"])
    assert report["result"] == "FINDINGS"


def test_publications_dropped_past_a_cap_are_named_not_just_counted():
    criteria = {"source_url": "x", "criteria": [
        {"id": "B1", "points": 5, "match": {"type": "conference"}, "max_count": 1}]}
    venues = [{"issn": "99999999", "display_name": "S", "wos_index": "NONE",
               "checked_at": "2026-08-01"}]
    pubs = [{"title": f"Conf {i}", "year": 2023, "type": "conference",
             "venue": "S", "issn": "99999999"} for i in range(3)]
    report = ds.score(pubs, criteria, venues)
    bucket = report["per_criterion"]["B1"]
    assert bucket["not_counted"] == ["Conf 1", "Conf 2"]
    assert any("in export order rather than by merit" in p for p in report["problems"])


def test_scoring_does_not_write_back_into_the_export():
    """An earlier version stamped the looked-up quartile onto the caller's dicts,
    so a second run saw data the first one invented."""
    pubs = [{"title": "P", "year": 2024, "type": "article", "venue": "J",
             "issn": "1111-1111"}]
    venues = [{"issn": "11111111", "display_name": "J", "wos_index": "ESCI",
               "quartile": "Q3", "checked_at": "2026-08-01"}]
    ds.score(pubs, {"source_url": "x", "criteria": [{"id": "A1", "points": 1}]}, venues)
    assert "_quartile" not in pubs[0]


# ---------- 7. the substring that read as disclosure ----------

def test_a_short_field_name_is_not_disclosed_by_coincidence():
    """`id` and `e` appear inside almost any Turkish sentence. Matched as
    substrings, both read as disclosed — a false negative on the one check
    ethics_pack exists for."""
    result = ep.check_consent("Katilimcidan sadece metin toplanir.", ["id", "e"])
    assert sorted(result["fields_undisclosed"]) == ["e", "id"]


def test_a_genuinely_named_short_field_still_counts_as_disclosed():
    result = ep.check_consent("Toplanan veriler: id, e-posta ve metin.", ["id"])
    assert result["fields_undisclosed"] == []


def test_the_underscore_and_space_spellings_are_both_accepted():
    assert ep.check_consent("post metni toplanir", ["post_metni"])["fields_undisclosed"] == []
    assert ep.check_consent("post_text toplanir", ["post_text"])["fields_undisclosed"] == []


def test_a_field_name_inside_a_longer_word_is_not_a_disclosure():
    result = ep.check_consent("Veriler kimliksizlestirilir.", ["kimlik"])
    assert result["fields_undisclosed"] == ["kimlik"]


# ---------- 8. a progress report with no plan behind it ----------

def test_a_progress_report_with_no_work_package_plan_is_a_finding(tmp_path):
    (tmp_path / "proposal").mkdir()
    report = json.loads(_run("proposal_check.py", tmp_path, "--report", expect=2).stdout)
    assert report["result"] == "FINDINGS"
    assert any("no plan to report against" in p for p in report["problems"])


# ---------- 9. Bloom verbs, matched per language ----------

def test_an_english_word_that_merely_starts_with_a_bloom_verb_is_not_one():
    """"useful" is not "use"; "namely" is not "name"; "statement" is not "state"."""
    for text in ("Students find useful patterns in data",
                 "Namely, the three cases below",
                 "This statement is given in the notes",
                 "The user interface"):
        assert sc.bloom_of(text) is None, text


def test_english_inflections_including_the_y_to_ies_form_are_recognised():
    assert sc.bloom_of("Applies the method") == "apply"
    assert sc.bloom_of("Apply the method") == "apply"
    assert sc.bloom_of("Uses the algorithm") == "apply"
    assert sc.bloom_of("Justifies the choice") == "evaluate"
    assert sc.bloom_of("Designing a controller") == "create"


def test_turkish_keeps_its_open_suffix_because_the_language_is_agglutinative():
    for text in ("Öğrenci algoritmayı uygular", "Algoritmayı uygulayabilir",
                 "Uygulamayı gerçekleştirir", "Model başarımını değerlendirir"):
        assert sc.bloom_of(text) is not None, text


def test_the_unmeasurable_verbs_still_read_as_unmeasurable():
    assert sc.bloom_of("Öğrenci konuyu anlar") is None
    assert sc.bloom_of("Students will understand the topic") is None


def test_the_highest_level_wins_not_the_first_one_in_the_table():
    """"Sınıflandırma algoritmalarını uygular" is an *apply* outcome; the noun
    "sınıflandırma" shares a stem with *classify*, and first-match returned
    `understand` for it purely because that level is earlier in the table."""
    assert sc.bloom_of("Sınıflandırma algoritmalarını uygular") == "apply"
    assert sc.bloom_of("Explains and then designs the controller") == "create"
    assert sc.bloom_of("Lists and evaluates the alternatives") == "evaluate"


# ---------- the two the tests could not see ----------

def test_the_new_project_directories_are_writable(tmp_path):
    """Every command in the funding, career and teaching axes writes into one of
    these three. Without the allowlist entries the first write is a permission
    prompt in a command that is supposed to run unattended."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))
    allow = set(settings["permissions"]["allow"])
    for directory in ("proposal", "teaching", "dossier"):
        assert f"Write(./{directory}/**)" in allow, directory
        assert f"Edit(./{directory}/**)" in allow, directory


def test_the_dmp_skill_documents_the_flag_verify_actually_takes():
    """`dataset_db.py verify` takes --id; the contract test only checks flags that
    ARE written, so a positional written where a flag belongs slipped through."""
    text = (ROOT / ".claude" / "skills" / "dmp" / "SKILL.md").read_text(encoding="utf-8")
    assert "verify --id DS-0002" in text
    assert "verify DS-0002" not in text.replace("verify --id DS-0002", "")


def test_the_project_template_carries_the_three_new_directories():
    for directory in ("proposal", "teaching", "dossier"):
        assert (ROOT / "project-template" / directory).is_dir(), directory
