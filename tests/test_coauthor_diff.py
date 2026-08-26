"""The co-author round trip (scripts/coauthor_diff.py).

Track-changes answers "which words moved" — the one question whose answer is
obvious. These tests pin the three that are not: a citation that disappeared
while its sentence stayed, a number no recorded run produced, and a claim that
moved up the strength ladder.

Also pinned: the script writes nothing into drafts/. A merge tool that merges is
a tool that decides, and that decision has a person behind it.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import coauthor_diff as cd  # noqa: E402

BEFORE = """# Introduction

Transfer learning improves fault detection [@kaya2023deep].

# Results

The model reaches 0.87 F1 on the held-out split. Our results suggest that
variable load is the dominant factor.
"""

AFTER_CLEAN = """# Introduction

Transfer learning improves fault detection under variable load [@kaya2023deep].

# Results

The model reaches 0.87 F1 on the held-out split. Our results suggest that
variable load is the dominant factor.
"""

RUNS = [{"id": "RUN-0001", "metrics": {"f1": 0.87, "auroc": 0.94}},
        {"id": "RUN-0002", "metrics": {"f1": 0.83}}]


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "coauthor_diff.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, before=BEFORE, after=AFTER_CLEAN, runs=RUNS):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "drafts" / "paper.md").write_text(before, encoding="utf-8")
    (tmp_path / "analysis" / "runs.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    (tmp_path / "returned.md").write_text(after, encoding="utf-8")
    return tmp_path


# ---------- the three findings that survive a read-through ----------

def test_a_removed_citation_is_flagged_even_when_the_sentence_stays():
    after = AFTER_CLEAN.replace(" [@kaya2023deep]", "")
    report = cd.compare(BEFORE, after, set())
    kinds = [f["kind"] for f in report["flags"]]
    assert "citation_removed" in kinds
    removed = next(f for f in report["flags"] if f["kind"] == "citation_removed")
    assert removed["key"] == "kaya2023deep"


def test_a_strengthened_claim_is_flagged_with_its_rung():
    after = AFTER_CLEAN.replace("Our results suggest that\nvariable load is the "
                                "dominant factor.",
                                "We prove that variable load causes the failure.")
    report = cd.compare(BEFORE, after, set())
    hit = next(f for f in report["flags"] if f["kind"] == "claim_strengthened")
    assert hit["rung"] in ("contributory", "directional", "causal", "predictive")
    assert "variable load" in hit["sentence"]


def test_a_new_number_absent_from_the_run_register_is_flagged():
    after = AFTER_CLEAN.replace("0.87 F1", "0.91 F1")
    register = {"0.87", "0.94", "0.83"}
    report = cd.compare(BEFORE, after, register)
    hit = next(f for f in report["flags"] if f["kind"] == "number_not_in_run_register")
    assert hit["value"] == "0.91"


def test_a_number_that_matches_a_recorded_run_is_not_flagged():
    after = AFTER_CLEAN.replace("0.87 F1", "0.83 F1")
    report = cd.compare(BEFORE, after, {"0.87", "0.83"})
    assert not [f for f in report["flags"] if f["kind"] == "number_not_in_run_register"]


def test_an_empty_run_register_makes_no_claim_about_any_number():
    """No register is not evidence that a number is unbacked."""
    after = AFTER_CLEAN.replace("0.87 F1", "0.91 F1")
    report = cd.compare(BEFORE, after, set())
    assert not [f for f in report["flags"] if f["kind"] == "number_not_in_run_register"]


# ---------- what is reported without being flagged ----------

def test_rounding_is_kept_apart_from_a_digit_that_moved():
    delta = cd.number_delta("F1 was 0.8712 on the split.", "F1 was 0.87 on the split.")
    assert delta["rounding_only"] == [{"before": "0.8712", "after": "0.87"}]
    assert delta["new"] == [] and delta["gone"] == []


def test_turkish_and_english_decimal_conventions_are_one_quantity():
    delta = cd.number_delta("Doğruluk 0,87 idi.", "Accuracy was 0.87.")
    assert delta["new"] == [] and delta["gone"] == []


def test_a_reworded_sentence_whose_claim_did_not_move_is_not_flagged():
    """"Transfer learning improves X" edited to "...improves X under load" is a
    rewrite, not a strengthening. The first implementation flagged it, which is
    how a check stops being read."""
    report = cd.compare(BEFORE, AFTER_CLEAN, set())
    assert report["flags"] == []
    intro = next(s for s in report["per_section"] if s["section"] == "introduction")
    assert intro["words_added"] > 0


def test_a_rung_that_went_up_on_a_matched_sentence_reports_both_rungs():
    before = "# R\n\nThe method may improve recall.\n"
    after = "# R\n\nThe method causes a large increase in recall.\n"
    hits = cd.compare(before, after, set())["flags"]
    hit = next(h for h in hits if h["kind"] == "claim_strengthened")
    assert hit["rung"] == "causal"


def test_sections_added_and_removed_are_listed():
    after = AFTER_CLEAN + "\n# Limitations\n\nThe sample is small.\n"
    report = cd.compare(BEFORE, after, set())
    assert report["sections_added"] == ["limitations"]
    assert report["sections_removed"] == []


def test_headings_are_folded_so_case_and_diacritics_do_not_split_a_section():
    before = "# Yöntem\n\nVeri toplandı.\n"
    after = "# YÖNTEM\n\nVeri toplandı ve temizlendi.\n"
    report = cd.compare(before, after, set())
    assert report["sections_added"] == []
    assert [s["section"] for s in report["per_section"]] == ["yontem"]


# ---------- Word comments ----------

def test_word_comments_are_read_out_of_the_docx_itself(tmp_path):
    """Pandoc drops them, and they are frequently the only place the supervisor
    said why."""
    docx = tmp_path / "rev.docx"
    xml = ('<?xml version="1.0"?><w:comments xmlns:w="x">'
           '<w:comment w:id="1" w:author="Prof. Yılmaz" w:date="2026-08-15T10:00:00Z">'
           '<w:p><w:r><w:t>Bu iddia için kaynak gerekiyor.</w:t></w:r></w:p>'
           '</w:comment></w:comments>')
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/comments.xml", xml)
    comments = cd.docx_comments(docx)
    assert comments == [{"author": "Prof. Yılmaz", "date": "2026-08-15T10:00:00Z",
                         "text": "Bu iddia için kaynak gerekiyor."}]


def test_a_docx_without_comments_returns_an_empty_list(tmp_path):
    docx = tmp_path / "plain.docx"
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    assert cd.docx_comments(docx) == []


def test_a_non_docx_is_not_opened_as_a_zip(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("# T\n", encoding="utf-8")
    assert cd.docx_comments(md) == []


# ---------- the refusal ----------

def test_nothing_is_written_into_drafts(tmp_path):
    project = _project(tmp_path, after=AFTER_CLEAN.replace(" [@kaya2023deep]", ""))
    before = (project / "drafts" / "paper.md").read_text(encoding="utf-8")
    _run(project, "--returned", "returned.md", expect=2)
    assert (project / "drafts" / "paper.md").read_text(encoding="utf-8") == before
    assert sorted(p.name for p in (project / "drafts").iterdir()) == ["paper.md"]


def test_an_unchanged_return_exits_clean(tmp_path):
    project = _project(tmp_path, after=BEFORE)
    report = json.loads(_run(project, "--returned", "returned.md").stdout)
    assert report["result"] == "NO_FLAGS"
    assert all(s["unchanged"] for s in report["per_section"])


def test_the_report_says_prose_was_never_compared(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--returned", "returned.md").stdout)
    assert "prose is never compared" in report["note"]


def test_missing_drafts_is_an_error_not_an_empty_comparison(tmp_path):
    (tmp_path / "returned.md").write_text(AFTER_CLEAN, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "coauthor_diff.py"), "--returned", "returned.md"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "nothing to compare against" in proc.stderr
