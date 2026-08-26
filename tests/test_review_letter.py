"""A real decision letter (scripts/review_letter.py).

The document the kit could not take: an editor's letter with three reviewers and
forty numbered comments. Editors check one thing mechanically before reading the
science — is there a response to every comment — and an unanswered comment reads
as an evaded one.

These tests pin the parse (numbering restarts per reviewer, and a letter with no
numbering is not split into invented comments) and the coverage check (matched on
numbers, never on wording, and never a judgement about adequacy).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import review_letter as rl  # noqa: E402

LETTER = """Dear Dr X, we invite a major revision.

## Reviewer 1

1. The sample size is not justified in Section 3.
2. Figure 2 is unreadable at print size.

## Reviewer 2

1. The comparison with baseline B is unfair.
2. Please report confidence intervals.
"""


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "review_letter.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _files(tmp_path, letter=LETTER, response=None):
    (tmp_path / "reviews").mkdir(exist_ok=True)
    (tmp_path / "reviews" / "letter.md").write_text(letter, encoding="utf-8")
    if response is not None:
        (tmp_path / "reviews" / "response.md").write_text(response, encoding="utf-8")
    return tmp_path


# ---------- parsing ----------

def test_numbering_restarts_per_reviewer_and_ids_stay_distinct():
    """Every real letter numbers from 1 again for each reviewer. A flat pass
    produces four different comments all called '1'."""
    parsed = rl.parse_letter(LETTER)
    ids = [c["id"] for c in parsed["comments"]]
    assert "Reviewer 1.1" in ids and "Reviewer 2.1" in ids
    assert len(set(ids)) == len(ids)


def test_the_editor_block_is_kept_as_its_own_comment():
    parsed = rl.parse_letter(LETTER)
    assert any(c["reviewer"] == "Editor" for c in parsed["comments"])


def test_a_letter_with_no_numbering_is_one_comment_not_invented_ones():
    # Splitting on paragraphs would produce phantom comments and a coverage
    # percentage over them that means nothing.
    text = ("## Reviewer 1\n\nThe paper is interesting but the evaluation is weak.\n\n"
            "The writing also needs work throughout.\n")
    parsed = rl.parse_letter(text)
    assert parsed["count"] == 1
    assert "rather than split on paragraphs" in parsed["comments"][0]["note"]


def test_turkish_and_alternative_headings_are_recognised():
    for heading in ("## Hakem 1", "## Referee 1", "R1:"):
        parsed = rl.parse_letter(f"{heading}\n\n1. Bir yorum.\n")
        assert parsed["comments"][0]["reviewer"] == "Reviewer 1", heading


def test_a_reviewer_mentioned_mid_sentence_is_not_a_new_section():
    text = "## Reviewer 1\n\n1. As reviewer 2 noted elsewhere, the sample is small.\n"
    parsed = rl.parse_letter(text)
    assert parsed["reviewers"] == ["Reviewer 1"]


def test_various_numbering_shapes_are_parsed():
    text = "## Reviewer 1\n\n(1) First.\n2) Second.\nComment 3: Third.\n1.4 Fourth.\n"
    parsed = rl.parse_letter(text)
    assert [c["number"] for c in parsed["comments"]] == ["1", "2", "3", "1.4"]


# ---------- coverage ----------

def test_an_unanswered_comment_is_named(tmp_path):
    response = ("## Reviewer 1\n\n1. Added.\n2. Redrawn.\n\n"
                "## Reviewer 2\n\n1. Rerun.\n\n## Editor\n\nThank you.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md", expect=2).stdout)
    assert out["coverage"]["missing"] == ["Reviewer 2.2"]


def test_every_comment_answered_exits_zero(tmp_path):
    response = ("## Editor\n\nThank you.\n\n## Reviewer 1\n\n1. Added.\n2. Redrawn.\n\n"
                "## Reviewer 2\n\n1. Rerun.\n2. CIs added.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md").stdout)
    assert out["coverage"]["missing"] == []
    assert out["coverage"]["answered_count"] == out["coverage"]["total"]


def test_thanking_the_editor_is_not_answering_the_editor(tmp_path):
    """A courtesy line is not a response. Counting it as one is the false
    positive that makes a coverage number worse than none."""
    response = ("We thank the editor and both reviewers.\n\n## Reviewer 1\n\n"
                "1. Added.\n2. Redrawn.\n\n## Reviewer 2\n\n1. Rerun.\n2. CIs added.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md", expect=2).stdout)
    assert out["coverage"]["missing"] == ["Editor.unnumbered"]


def test_the_r_dot_n_shorthand_counts_as_an_answer(tmp_path):
    response = ("## Editor\n\nOk.\n\nR1.1 Added. R1.2 Redrawn. R2.1 Rerun. "
                "R2.2 Confidence intervals are now reported.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md").stdout)
    assert out["coverage"]["missing"] == []


def test_a_response_to_a_comment_that_was_never_made_is_reported(tmp_path):
    # Usually a mis-numbered response; the editor sees an answer to a question
    # nobody asked, which reads worse than a gap.
    response = ("## Editor\n\nOk.\n\nR1.1 Added. R1.2 Redrawn. R2.1 Rerun. R2.2 Added. "
                "R3.1 We disagree.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md", expect=2).stdout)
    assert out["coverage"]["unmatched_in_response"] == ["Reviewer 3.1"]


def test_matching_is_on_numbers_not_on_wording(tmp_path):
    """A response that echoes a reviewer's phrasing without answering by number
    is not counted — repeating the question is not answering it."""
    response = ("## Editor\n\nOk.\n\n## Reviewer 1\n\nThe sample size is not justified "
                "in Section 3, and Figure 2 is unreadable at print size.\n\n"
                "## Reviewer 2\n\n1. Rerun.\n2. Added.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md", expect=2).stdout)
    assert set(out["coverage"]["missing"]) == {"Reviewer 1.1", "Reviewer 1.2"}


def test_adequacy_is_explicitly_not_judged(tmp_path):
    response = ("## Editor\n\nOk.\n\n## Reviewer 1\n\n1. No.\n2. No.\n\n"
                "## Reviewer 2\n\n1. No.\n2. No.\n")
    _files(tmp_path, response=response)
    out = json.loads(_run(tmp_path, "--parse", "reviews/letter.md",
                          "--coverage", "reviews/response.md").stdout)
    assert out["coverage"]["missing"] == []
    assert "adequate" in out["coverage"]["note"]


# ---------- CLI contract ----------

def test_a_missing_letter_says_where_to_put_it(tmp_path):
    proc = _run(tmp_path, "--parse", "reviews/letter.md", expect=1)
    assert "pdf2md" in proc.stderr


def test_a_file_that_is_not_a_letter_is_refused(tmp_path):
    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "letter.md").write_text("\n\n", encoding="utf-8")
    proc = _run(tmp_path, "--parse", "reviews/letter.md", expect=1)
    assert "no comments" in proc.stderr


def test_a_path_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--parse", "../elsewhere.md", expect=1)
    assert "--parse" in proc.stderr


def test_output_is_exactly_one_json_object(tmp_path):
    _files(tmp_path)
    json.loads(_run(tmp_path, "--parse", "reviews/letter.md").stdout)
