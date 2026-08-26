"""The submission form (scripts/submission_pack.py) and the availability statement.

The second document nobody talks about: title length, abstract words, keyword
count, highlights, the required statements. Every limit is arithmetic and every
one of them is checked by an editorial assistant before a reviewer sees the paper.

What these tests pin is where the limits come from — a file the author fills from
the venue's own guidelines — and what the script refuses to write when a field is
absent.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import submission_pack as sp  # noqa: E402,F401  (import smoke: the module must load)

LIMITS = {"venue": "MSSP", "source_url": "https://example.org/guide",
          "title_max_chars": 80, "abstract_max_words": 250,
          "keywords": {"min": 4, "max": 6},
          "highlights": {"count_min": 3, "count_max": 5, "max_chars": 85},
          "required_statements": ["ethics", "funding"]}


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "submission_pack.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, limits=LIMITS, title="A short title", abstract=None,
             highlights=None, statements=None):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    (tmp_path / "exports" / "submission").mkdir(parents=True, exist_ok=True)
    (tmp_path / "PROJECT.md").write_text(f"**Title (working):** {title}\n", encoding="utf-8")
    (tmp_path / "drafts" / "abstract.md").write_text(
        abstract if abstract is not None else
        "We present a method for X.\n\nKeywords: cnn, bearing, fault, vibration\n",
        encoding="utf-8")
    if limits is not None:
        (tmp_path / "exports" / "submission" / "limits.json").write_text(
            json.dumps(limits), encoding="utf-8")
    if highlights is not None:
        (tmp_path / "exports" / "submission" / "highlights.md").write_text(
            highlights, encoding="utf-8")
    if statements is not None:
        (tmp_path / "exports" / "submission" / "statements.md").write_text(
            statements, encoding="utf-8")
    return tmp_path


# ---------- where the limits come from ----------

def test_no_limits_file_means_measured_but_checked_against_nothing(tmp_path):
    """The refusal that matters: the kit will not recall a journal's limits. A
    remembered limit is the same error class as a remembered DOI."""
    _project(tmp_path, limits=None)
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["result"] == "UNCHECKED", (
        "'no problems found' and 'nothing was checked' must not be the same output")
    assert "checked against nothing" in out["note"]
    assert out["title"]["chars"] > 0 and out["title"]["limit"] is None


def test_a_limits_file_with_no_source_url_is_refused(tmp_path):
    _project(tmp_path, limits={"venue": "X", "title_max_chars": 80})
    proc = _run(tmp_path, "--check", expect=1)
    assert "source_url" in proc.stderr


# ---------- the arithmetic ----------

def test_a_title_over_the_limit_is_caught(tmp_path):
    _project(tmp_path, title="A" * 120)
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert "120 characters" in out["title"]["problem"]


def test_an_abstract_over_the_word_limit_is_caught(tmp_path):
    _project(tmp_path, limits={**LIMITS, "abstract_max_words": 5})
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert "allows 5" in out["abstract"]["problem"]


def test_keyword_count_is_checked_against_the_venue_range(tmp_path):
    _project(tmp_path, abstract="Text.\n\nKeywords: a, b\n")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["keywords"]["count"] == 2 and "at least 4" in out["keywords"]["problem"]


def test_turkish_keyword_line_is_recognised(tmp_path):
    _project(tmp_path, abstract="Metin.\n\nAnahtar kelimeler: cnn, rulman, arıza, titreşim\n")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["keywords"]["count"] == 4


# ---------- highlights ----------

def test_a_highlight_over_the_character_limit_is_named(tmp_path):
    _project(tmp_path, highlights="- " + "x" * 90 + "\n- short\n- also short\n")
    out = json.loads(_run(tmp_path, "--highlights", expect=2).stdout)
    assert out["over_limit"][0]["chars"] == 90


def test_too_few_highlights_is_a_finding(tmp_path):
    _project(tmp_path, highlights="- one\n- two\n")
    out = json.loads(_run(tmp_path, "--highlights", expect=2).stdout)
    assert any("at least 3" in p for p in out["problems"])


def test_a_citation_inside_a_highlight_is_flagged(tmp_path):
    # Highlights are read standalone; [@key] renders as literal text in the form.
    _project(tmp_path, highlights="- A result [@kaya2024]\n- two\n- three\n")
    out = json.loads(_run(tmp_path, "--highlights", expect=2).stdout)
    assert any("citations" in p for p in out["problems"])


def test_highlights_within_the_limits_pass(tmp_path):
    _project(tmp_path, highlights="- one\n- two\n- three\n")
    out = json.loads(_run(tmp_path, "--highlights").stdout)
    assert out["problems"] == [] and out["count"] == 3


def test_a_paragraph_is_not_highlights(tmp_path):
    # Counting its sentences would invent a structure the author did not write.
    _project(tmp_path, highlights="We show that the method works well and is fast.\n")
    out = json.loads(_run(tmp_path, "--highlights", expect=2).stdout)
    assert out["count"] == 0


# ---------- statements ----------

def test_a_required_statement_that_is_missing_names_where_it_comes_from(tmp_path):
    _project(tmp_path)
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert set(out["statements"]["missing"]) == {"ethics", "funding"}
    assert "compliance_gen.py" in out["statements"]["where_each_comes_from"]["funding"]


def test_present_statements_are_not_reported_missing(tmp_path):
    _project(tmp_path, statements="Ethics approval: 2026/117.\nFunding: none.\n")
    out = json.loads(_run(tmp_path, "--check").stdout)
    assert out["statements"]["missing"] == []


# ---------- the manifest ----------

def test_the_manifest_lists_what_is_missing_instead_of_inventing_it(tmp_path):
    """An ORCID, a funder or a data-availability sentence that is not in the
    project is a TODO — each of those has to be true."""
    _project(tmp_path, abstract="Text with no keyword line.\n")
    out = json.loads(_run(tmp_path, "--manifest").stdout)
    assert any("keywords" in t for t in out["todo"])
    assert any("highlights" in t for t in out["todo"])
    assert out["keywords"] == []


def test_the_manifest_carries_what_does_exist(tmp_path):
    _project(tmp_path, title="Real title", highlights="- one\n- two\n- three\n")
    out = json.loads(_run(tmp_path, "--manifest").stdout)
    assert out["title"] == "Real title" and len(out["highlights"]) == 3


# ---------- CLI contract ----------

def test_a_path_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--check", "--drafts", "../elsewhere", expect=1)
    assert "--drafts" in proc.stderr


def test_a_clean_submission_exits_zero(tmp_path):
    _project(tmp_path, highlights="- one\n- two\n- three\n",
             statements="Ethics: n/a. Funding: none.\n")
    out = json.loads(_run(tmp_path).stdout)
    assert out["result"] == "OK"


# ---------- the availability statement ----------

def _availability(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "compliance_gen.py"),
                           "availability", *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _registers(tmp_path, datasets, runs=()):
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "analysis" / "datasets.jsonl").write_text(
        "".join(json.dumps(d) + "\n" for d in datasets), encoding="utf-8")
    if runs:
        (tmp_path / "analysis" / "runs.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    return tmp_path


def test_a_dataset_with_a_doi_and_a_licence_produces_a_real_sentence(tmp_path):
    _registers(tmp_path, [{"id": "DS-0001", "name": "CWRU", "license": "CC-BY-4.0",
                           "license_verified": True, "citation": {"doi": "10.1/x"}}])
    out = json.loads(_availability(tmp_path).stdout)
    assert "10.1/x" in out["statement"] and "CC-BY-4.0" in out["statement"]


def test_a_dataset_with_no_doi_produces_no_sentence(tmp_path):
    """"Available from the corresponding author on reasonable request" is the
    sentence most often found to be untrue after publication. It is not written."""
    _registers(tmp_path, [{"id": "DS-0001", "name": "Private set", "license": "unknown"}])
    out = json.loads(_availability(tmp_path).stdout)
    assert out["statement"] is None
    assert out["incomplete"][0]["missing"]
    assert "reasonable request" not in json.dumps(out["shareable"])


def test_human_subject_data_gets_a_restriction_with_its_recorded_reason(tmp_path):
    _registers(tmp_path, [{"id": "DS-0001", "name": "Cohort", "license": "CC-BY-4.0",
                           "citation": {"doi": "10.1/x"},
                           "ethics": {"human_subjects": True, "irb": "2026/117"}}])
    out = json.loads(_availability(tmp_path).stdout)
    assert "cannot be shared" in out["statement"] and "2026/117" in out["statement"]


def test_recorded_runs_are_mentioned_as_the_replication_package(tmp_path):
    _registers(tmp_path,
               [{"id": "DS-0001", "name": "CWRU", "license": "CC-BY-4.0",
                 "citation": {"doi": "10.1/x"}}],
               [{"id": "RUN-0001", "seed": 42}])
    out = json.loads(_availability(tmp_path).stdout)
    assert "replication package" in out["statement"] and out["runs_recorded"] == 1


def test_no_register_is_refused_rather_than_templated(tmp_path):
    proc = _availability(tmp_path, expect=1)
    assert "not from a template" in proc.stderr


# ---------- what the first real submission check exposed ----------
# All three were found by running --check against a finished manuscript and a
# real journal's limits file for the first time. Each produced a plausible
# number that was wrong.

def test_title_drops_project_md_decision_comments(tmp_path):
    # PROJECT.md carries decision history in trailing HTML comments. One of them
    # turned a 118-character title into 788 — the number compared against the
    # venue's title limit, and the string a person pastes into the portal.
    _project(tmp_path)
    p = tmp_path / "PROJECT.md"
    p.write_text("**Title (working):** Kisa ve dogru baslik <!-- 2026-08-21: uzun bir\n"
                 "karar gerekcesi, birden fazla satir surer ve basliga ait degildir -->\n",
                 encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["title"]["title"] == "Kisa ve dogru baslik"
    assert out["title"]["chars"] == len("Kisa ve dogru baslik")


def test_keyword_line_survives_bold_colon_and_a_wrapped_list(tmp_path):
    # Real markdown writes "**Keywords:** a; b" with the colon INSIDE the bold,
    # and the list wraps. The old pattern captured the closing asterisks into
    # the first keyword ("** diabetic retinopathy") and `.` stopped at the
    # newline, dropping every keyword after the first line.
    _project(tmp_path, abstract=("Text.\n\n**Keywords:** diabetic retinopathy; deep learning;\n"
                                 "diagnostic accuracy; screening; systematic review;\n"
                                 "grey literature\n"))
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["keywords"]["count"] == 6, out["keywords"]
    assert out["keywords"]["keywords"][0] == "diabetic retinopathy"
    assert out["keywords"]["keywords"][-1] == "grey literature"


def test_manuscript_count_excludes_status_log_and_separates_appendices(tmp_path):
    # STATUS.md is the drafting progress log; the kit's own verify-citations
    # skill excludes it. Appendices are manuscript, but a venue's word limit is
    # about the body — folding a long appendix into the body total makes a
    # submittable paper look unsubmittable.
    _project(tmp_path)
    (tmp_path / "drafts" / "STATUS.md").write_text("log " * 500, encoding="utf-8")
    (tmp_path / "drafts" / "ek-a-prisma.md").write_text("appendix " * 300, encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert "STATUS.md" not in out["manuscript"]["files"]
    assert out["manuscript"]["excluded_from_count"] == ["STATUS.md"]
    assert out["manuscript"]["appendix_words"] == 300
    assert out["manuscript"]["appendix_files"] == ["ek-a-prisma.md"]
    assert out["manuscript"]["body_words"] == out["manuscript"]["total_words"]
    assert out["manuscript"]["total_words"] < 300 + 500


def test_bilingual_abstracts_get_their_own_limits(tmp_path):
    # A bilingual manuscript has two abstracts and venues routinely give them
    # different limits. Checking only abstract.md against one number applied the
    # manuscript-language limit to the translation: a Turkish review inside its
    # 250-word limit, whose English abstract the venue allows 15% more, was
    # reported over the limit.
    _project(tmp_path, limits={**LIMITS, "abstract_max_words": 250,
                               "abstract_max_words_by_file": {"ozet.md": 250,
                                                              "abstract.md": 287}})
    (tmp_path / "drafts" / "ozet.md").write_text("kelime " * 250, encoding="utf-8")
    (tmp_path / "drafts" / "abstract.md").write_text("word " * 280, encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    a = out["abstract"]
    assert a["files"]["ozet.md"] == {"words": 250, "limit": 250}
    assert a["files"]["abstract.md"] == {"words": 280, "limit": 287}
    assert "problem" not in a


def test_bilingual_abstract_over_limit_names_the_file(tmp_path):
    _project(tmp_path, limits={**LIMITS,
                               "abstract_max_words_by_file": {"ozet.md": 250,
                                                              "abstract.md": 287}})
    (tmp_path / "drafts" / "ozet.md").write_text("kelime " * 400, encoding="utf-8")
    (tmp_path / "drafts" / "abstract.md").write_text("word " * 100, encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert "ozet.md is 400 words" in out["abstract"]["problem"]
    assert "abstract.md" not in out["abstract"]["problem"]


def test_second_abstract_falls_back_to_the_single_limit(tmp_path):
    # No per-file table: both abstracts are measured against abstract_max_words,
    # which is the pre-existing behaviour and stays the default.
    _project(tmp_path, limits={**LIMITS, "abstract_max_words": 100})
    (tmp_path / "drafts" / "ozet.md").write_text("kelime " * 120, encoding="utf-8")
    (tmp_path / "drafts" / "abstract.md").write_text("word " * 50, encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["abstract"]["files"]["ozet.md"]["limit"] == 100
    assert out["abstract"]["files"]["abstract.md"]["limit"] == 100
    assert "ozet.md is 120 words" in out["abstract"]["problem"]


def test_keyword_lists_that_do_not_correspond_are_reported(tmp_path):
    # Each list is individually within the venue's range, so no single-file
    # check can see this: the Turkish abstract carries four keywords and the
    # English one five. A bilingual manuscript's two lists have to match.
    _project(tmp_path, limits={**LIMITS, "keywords": {"min": 3, "max": 6}},
             abstract="Text.\n\n**Keywords:** a; b; c; d; e\n")
    (tmp_path / "drafts" / "ozet.md").write_text(
        "Metin.\n\n**Anahtar kelimeler:** a; b; c; d\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    kw = out["keywords"]
    assert kw["files"]["ozet.md"]["count"] == 4
    assert kw["files"]["abstract.md"]["count"] == 5
    assert "do not correspond" in kw["problem"]


def test_keywords_fall_back_to_project_md_when_no_abstract_has_them(tmp_path):
    _project(tmp_path, abstract="Text with no keyword line.\n")
    p = tmp_path / "PROJECT.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nKeywords: a, b, c, d\n",
                 encoding="utf-8")
    out = json.loads(_run(tmp_path, "--check", expect=2).stdout)
    assert out["keywords"]["files"]["PROJECT.md"]["count"] == 4
