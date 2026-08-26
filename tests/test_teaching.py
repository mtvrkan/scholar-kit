"""The teaching axis (scripts/syllabus_check.py, scripts/outcome_matrix.py).

Teaching documents fail in exactly the ways a script can catch: weights summing
to 95, an outcome nothing measures, an exam question serving an outcome the
course does not have, a workload table that does not follow from the ECTS, and a
rubric whose four levels differ only by an adverb.

Two refusals are pinned alongside them: "öğrenci konuyu anlar" is reported as
unmeasurable rather than rewritten, and no MÜDEK/ABET outcome list ships — the
programme's own document is the authority or the result is UNCHECKED.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import outcome_matrix as om  # noqa: E402
import syllabus_check as sc  # noqa: E402

SYLLABUS = {
    "course": {"code": "EEM402", "title": "Örüntü Tanıma", "ects": 6, "language": "tr"},
    "outcomes": [
        {"id": "DÇ1", "text": "Sınıflandırma algoritmalarını uygular", "bloom": "apply",
         "programme_outcomes": [{"id": "PÇ1", "level": 3}]},
        {"id": "DÇ2", "text": "Model başarımını değerlendirir", "bloom": "evaluate",
         "programme_outcomes": [{"id": "PÇ2", "level": 2}]},
    ],
    "weeks": [{"week": 1, "topic": "Giriş", "outcomes": ["DÇ1"], "reading": "[@kaya2023deep]"},
              {"week": 2, "topic": "Değerlendirme", "outcomes": ["DÇ2"]}],
    "assessment": [{"name": "Vize", "weight": 40, "outcomes": ["DÇ1"]},
                   {"name": "Final", "weight": 60, "outcomes": ["DÇ1", "DÇ2"]}],
    "workload": [{"activity": "Ders", "count": 14, "hours": 3},
                 {"activity": "Çalışma", "count": 14, "hours": 8},
                 {"activity": "Sınav", "count": 2, "hours": 10}],
}

PROGRAMME = {"programme": "Elektrik-Elektronik Mühendisliği",
             "source_document": "Program çıktıları belgesi, Rev. 4",
             "read_on": "2026-08-15",
             "contribution_scale": [1, 2, 3],
             "outcomes": [{"id": "PÇ1", "text": "Mühendislik problemlerini çözer"},
                          {"id": "PÇ2", "text": "Sonuçları değerlendirir"}]}

EXAM = {"title": "Vize", "total_points": 100,
        "questions": [{"id": "Q1", "points": 60, "outcomes": ["DÇ1"], "bloom": "apply"},
                      {"id": "Q2", "points": 40, "outcomes": ["DÇ2"], "bloom": "evaluate"}]}

RUBRIC = {"title": "Proje", "criteria": [
    {"name": "Yöntem", "weight": 60, "levels": [
        {"label": "3", "descriptor": "Yöntem seçimi verinin yapısıyla gerekçelendirilmiş"},
        {"label": "1", "descriptor": "Yöntem gerekçesiz seçilmiş"}]},
    {"name": "Sunum", "weight": 40, "levels": [
        {"label": "3", "descriptor": "Şekiller eksen etiketli ve okunur"},
        {"label": "1", "descriptor": "Şekillerde eksen etiketi yok"}]}]}


def _run(script, cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, syllabus=SYLLABUS, programme=PROGRAMME, exam=None, rubric=None):
    (tmp_path / "teaching").mkdir(parents=True, exist_ok=True)
    (tmp_path / "teaching" / "syllabus.json").write_text(json.dumps(syllabus),
                                                         encoding="utf-8")
    if programme is not None:
        (tmp_path / "teaching" / "program-outcomes.json").write_text(
            json.dumps(programme), encoding="utf-8")
    if exam is not None:
        (tmp_path / "teaching" / "exam.json").write_text(json.dumps(exam), encoding="utf-8")
    if rubric is not None:
        (tmp_path / "teaching" / "rubric.json").write_text(json.dumps(rubric),
                                                           encoding="utf-8")
    return tmp_path


# ---------- learning outcomes ----------

def test_an_unmeasurable_outcome_is_reported_not_rewritten():
    result = sc.check_outcomes([{"id": "DÇ1", "text": "Öğrenci konuyu anlar"}])
    assert result["outcomes"][0]["unmeasurable_verbs"] == ["anlar"]
    assert any("state of mind" in p for p in result["problems"])


def test_the_english_form_of_the_same_outcome_is_reported():
    result = sc.check_outcomes([{"id": "LO1", "text": "Students will understand the topic"}])
    assert result["outcomes"][0]["unmeasurable_verbs"] == ["understand"]


def test_a_measurable_turkish_verb_is_recognised():
    result = sc.check_outcomes([{"id": "DÇ1", "text": "Sınıflandırma algoritmalarını uygular"}])
    assert result["outcomes"][0]["verb_suggests"] == "apply"
    assert result["problems"] == []


def test_a_declared_level_that_the_verb_contradicts_is_a_finding():
    result = sc.check_outcomes([{"id": "DÇ1", "text": "Algoritmayı tasarlar",
                                 "bloom": "remember"}])
    assert result["outcomes"][0]["mismatch"] is True
    assert any("what the exam will test" in p for p in result["problems"])


def test_a_word_containing_a_vague_verb_is_not_a_false_positive():
    """"kullananlar" contains "anlar". Word boundaries, not substrings."""
    result = sc.check_outcomes([{"id": "DÇ1", "text": "Aracı kullananlar için çözüm üretir"}])
    assert result["outcomes"][0]["unmeasurable_verbs"] == []


# ---------- assessment and coverage ----------

def test_weights_that_do_not_sum_to_100_are_a_finding():
    assessment = [{"name": "Vize", "weight": 40, "outcomes": ["DÇ1"]},
                  {"name": "Final", "weight": 55, "outcomes": ["DÇ2"]}]
    result = sc.check_assessment(assessment, ["DÇ1", "DÇ2"])
    assert any("sum to 95, not 100" in p for p in result["problems"])


def test_an_outcome_nothing_assesses_is_a_finding():
    result = sc.check_assessment([{"name": "Vize", "weight": 100, "outcomes": ["DÇ1"]}],
                                 ["DÇ1", "DÇ2"])
    assert result["unassessed_outcomes"] == ["DÇ2"]


def test_an_assessment_measuring_no_outcome_is_marks_with_no_purpose():
    result = sc.check_assessment([{"name": "Katılım", "weight": 100}], ["DÇ1"])
    assert any("no declared purpose" in p for p in result["problems"])


def test_an_outcome_assessed_but_never_taught_is_a_finding():
    result = sc.check_weeks([{"week": 1, "outcomes": ["DÇ1"]}], ["DÇ1", "DÇ2"])
    assert result["untaught_outcomes"] == ["DÇ2"]


def test_non_contiguous_week_numbering_is_a_finding():
    result = sc.check_weeks([{"week": 1}, {"week": 3}], [])
    assert any("expected 1..2" in p for p in result["problems"])


# ---------- workload / ECTS ----------

def test_a_workload_outside_the_bologna_range_is_a_finding():
    result = sc.check_workload([{"activity": "Ders", "count": 14, "hours": 3}], 6)
    assert result["bologna_range"] == [150, 180]
    assert any("150-180 hours" in p for p in result["problems"])


def test_a_workload_inside_the_bologna_range_passes():
    result = sc.check_workload(SYLLABUS["workload"], 6)
    assert result["total_hours"] == 174
    assert result["problems"] == []


def test_an_institutions_single_figure_replaces_the_range():
    result = sc.check_workload(SYLLABUS["workload"], 6, per_credit=25)
    assert result["expected_hours"] == 150
    assert any("25 h/credit is 150" in p for p in result["problems"])


# ---------- readings ----------

def test_a_reading_key_missing_from_the_bibliography_is_a_finding(tmp_path):
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{other2020,\n}\n",
                                                     encoding="utf-8")
    result = sc.check_readings(SYLLABUS["weeks"], tmp_path / "bib" / "references.bib")
    assert result["unresolved"] == ["kaya2023deep"]


def test_readings_with_no_bibliography_point_at_the_command_that_makes_one(tmp_path):
    result = sc.check_readings(SYLLABUS["weeks"], tmp_path / "nope.bib")
    assert any("/import-library" in p for p in result["problems"])


# ---------- the exam ----------

def test_question_points_that_do_not_sum_to_the_declared_total_are_a_finding():
    exam = json.loads(json.dumps(EXAM))
    exam["questions"][0]["points"] = 50
    result = sc.check_exam(exam, ["DÇ1", "DÇ2"])
    assert any("sum to 90, the paper declares 100" in p for p in result["problems"])


def test_a_question_serving_an_outcome_the_course_does_not_have_is_a_finding():
    exam = json.loads(json.dumps(EXAM))
    exam["questions"][0]["outcomes"] = ["DÇ9"]
    result = sc.check_exam(exam, ["DÇ1", "DÇ2"])
    assert any("an exam wider than the course" in p for p in result["problems"])


def test_an_outcome_no_question_measures_is_a_finding():
    exam = {"total_points": 100,
            "questions": [{"id": "Q1", "points": 100, "outcomes": ["DÇ1"]}]}
    result = sc.check_exam(exam, ["DÇ1", "DÇ2"])
    assert result["unmeasured_outcomes"] == ["DÇ2"]


def test_the_bloom_spread_is_reported():
    result = sc.check_exam(EXAM, ["DÇ1", "DÇ2"])
    assert result["bloom_spread"] == {"apply": 1, "evaluate": 1}


# ---------- the rubric ----------

def test_levels_that_differ_only_by_an_adverb_are_a_finding():
    rubric = {"criteria": [{"name": "Yöntem", "weight": 100, "levels": [
        {"label": "4", "descriptor": "Yöntem çok iyi seçilmiş"},
        {"label": "2", "descriptor": "Yöntem zayıf seçilmiş"}]}]}
    result = sc.check_rubric(rubric)
    assert any("say the same thing once" in p for p in result["problems"])


def test_a_level_that_is_only_an_adverb_describes_nothing():
    rubric = {"criteria": [{"name": "Sunum", "weight": 100, "levels": [
        {"label": "4", "descriptor": "Mükemmel"},
        {"label": "1", "descriptor": "Zayıf"}]}]}
    result = sc.check_rubric(rubric)
    assert any("a grade, not a descriptor" in p for p in result["problems"])


def test_observably_different_levels_pass():
    assert sc.check_rubric(RUBRIC)["problems"] == []


def test_rubric_weights_must_sum_to_100():
    rubric = json.loads(json.dumps(RUBRIC))
    rubric["criteria"][0]["weight"] = 50
    assert any("sum to 90" in p for p in sc.check_rubric(rubric)["problems"])


# ---------- the outcome matrix ----------

def test_a_programme_outcome_no_course_outcome_serves_is_a_finding():
    programme = json.loads(json.dumps(PROGRAMME))
    programme["outcomes"].append({"id": "PÇ3", "text": "Etik sorumluluk"})
    report = om.build(programme, [("EEM402", SYLLABUS)])
    assert report["uncovered_programme_outcomes"] == ["PÇ3"]


def test_a_course_outcome_mapping_to_nothing_is_a_finding():
    syllabus = json.loads(json.dumps(SYLLABUS))
    syllabus["outcomes"][1]["programme_outcomes"] = []
    report = om.build(PROGRAMME, [("EEM402", syllabus)])
    assert any("serving nothing" in p for p in report["problems"])


def test_a_contribution_with_no_assessment_behind_it_is_a_claim_not_a_measurement():
    syllabus = json.loads(json.dumps(SYLLABUS))
    syllabus["assessment"] = [{"name": "Vize", "weight": 100, "outcomes": ["DÇ1"]}]
    report = om.build(PROGRAMME, [("EEM402", syllabus)])
    assert any("a claim, not a measurement" in p for p in report["problems"])


def test_a_contribution_level_outside_the_declared_scale_is_a_finding():
    syllabus = json.loads(json.dumps(SYLLABUS))
    syllabus["outcomes"][0]["programme_outcomes"] = [{"id": "PÇ1", "level": 5}]
    report = om.build(PROGRAMME, [("EEM402", syllabus)])
    assert any("outside the declared scale [1, 2, 3]" in p for p in report["problems"])


def test_no_achievement_percentage_is_computed():
    report = om.build(PROGRAMME, [("EEM402", SYLLABUS)])
    assert "number with no unit" in report["note"]
    assert "achievement" not in json.dumps(report["matrix"])


def test_the_markdown_matrix_carries_the_level_and_the_course_outcome():
    report = om.build(PROGRAMME, [("EEM402", SYLLABUS)])
    table = om.render_matrix(report, "markdown")
    assert "| EEM402 | 3 (DÇ1) | 2 (DÇ2) |" in table


def test_no_programme_file_reports_unchecked_not_ok(tmp_path):
    project = _project(tmp_path, programme=None)
    report = json.loads(_run("outcome_matrix.py", project, "--syllabus",
                             "teaching/syllabus.json", expect=2).stdout)
    assert report["result"] == "UNCHECKED"
    assert "ships no MÜDEK or ABET outcome list" in report["note"]


def test_a_programme_file_with_no_source_is_refused(tmp_path):
    project = _project(tmp_path, programme={"outcomes": [{"id": "PÇ1"}]})
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "outcome_matrix.py"),
         "--syllabus", "teaching/syllabus.json"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "worse than a blank one" in proc.stderr


# ---------- end to end ----------

def test_a_consistent_syllabus_passes(tmp_path):
    project = _project(tmp_path)
    (project / "bib").mkdir()
    (project / "bib" / "references.bib").write_text("@article{kaya2023deep,\n}\n",
                                                    encoding="utf-8")
    report = json.loads(_run("syllabus_check.py", project).stdout)
    assert report["result"] == "OK", report["problems"]


def test_a_consistent_exam_passes(tmp_path):
    project = _project(tmp_path, exam=EXAM)
    report = json.loads(_run("syllabus_check.py", project,
                             "--exam", "teaching/exam.json").stdout)
    assert report["result"] == "OK", report["problems"]


def test_a_consistent_matrix_passes(tmp_path):
    project = _project(tmp_path)
    report = json.loads(_run("outcome_matrix.py", project,
                             "--syllabus", "teaching/syllabus.json").stdout)
    assert report["result"] == "OK", report["problems"]
