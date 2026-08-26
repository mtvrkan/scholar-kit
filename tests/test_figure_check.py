"""Tests for figure_check.py — figure/table existence, numbering, caption lint.

Calibrated against a real defect found by running this script against the first
end-to-end paper's actual drafts: a bootstrap-CI forest plot was embedded as
"Figure 4" but never referenced by that number anywhere in the prose discussing
it — an orphaned figure nothing previously caught.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import figure_check as fc  # noqa: E402


def _project(tmp_path, drafts: dict, captions: str | None = None):
    d = tmp_path / "drafts"
    d.mkdir()
    for name, text in drafts.items():
        (d / name).write_text(text, encoding="utf-8")
    cap_path = tmp_path / "analysis" / "captions.md"
    if captions is not None:
        cap_path.parent.mkdir(parents=True)
        cap_path.write_text(captions, encoding="utf-8")
    return d, cap_path


def test_clean_manuscript_no_warnings(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "Figure 1 shows the class balance.\n"
            "![Figure 1. Class balance.](../analysis/figures/class_balance.png)\n\n"
            "Table 1 reports performance.\n\n"
            "**Table 1. Test-set performance.**\n"
        )})
    r = fc.check(d, cap)
    assert r["warnings"] == 0
    assert r["figures"]["missing"] == r["figures"]["orphaned"] == []
    assert r["tables"]["missing"] == r["tables"]["orphaned"] == []


def test_orphaned_figure_embedded_but_never_mentioned(tmp_path):
    # Reproduces the real defect: Figure 4 embedded, never referenced elsewhere.
    d, cap = _project(tmp_path, {
        "results.md": (
            "Figure 1 shows class balance.\n"
            "![Figure 1. Class balance.](../analysis/figures/class_balance.png)\n\n"
            "![Figure 4. Bootstrap CI forest plot.](../analysis/figures/ci_forest.png)\n")
    })
    r = fc.check(d, cap)
    assert r["figures"]["orphaned"] == ["4"]
    assert r["warnings"] >= 1


def test_missing_figure_mentioned_but_not_embedded(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": "As Figure 2 shows, the model performed well.\n"
    })
    r = fc.check(d, cap)
    assert r["figures"]["missing"] == ["2"]


def test_figure_range_mention_expands(tmp_path):
    d, cap = _project(tmp_path, {
        "discussion.md": "Figures 4-6 present the XAI comparison.\n",
        "results.md": (
            "![Figure 4. A.](../analysis/figures/a.png)\n"
            "![Figure 5. B.](../analysis/figures/b.png)\n"
            "![Figure 6. C.](../analysis/figures/c.png)\n"),
    })
    r = fc.check(d, cap)
    assert r["figures"]["missing"] == []
    assert r["figures"]["orphaned"] == []


def test_duplicate_figure_number_flagged(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "![Figure 1. First.](../analysis/figures/a.png)\n"
            "![Figure 1. Second, wrongly numbered the same.](../analysis/figures/b.png)\n"
            "See Figure 1.\n")
    })
    r = fc.check(d, cap)
    assert len(r["figures"]["duplicate_numbers"]) == 1
    assert r["figures"]["duplicate_numbers"][0]["num"] == "1"


def test_sequence_gap_detected(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "![Figure 1. A.](../analysis/figures/a.png)\n"
            "![Figure 3. C.](../analysis/figures/c.png)\n"
            "Figure 1 and Figure 3 discussed here.\n")
    })
    r = fc.check(d, cap)
    assert r["figures"]["sequence_gaps"] == [2]


def test_table_1a_sublabel_supported_no_false_gap(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "**Table 1. Main results.**\n\n"
            "**Table 1a. Bootstrap CIs.**\n\n"
            "Table 1 and Table 1a are discussed.\n")
    })
    r = fc.check(d, cap)
    assert r["tables"]["missing"] == []
    assert r["tables"]["orphaned"] == []
    assert r["tables"]["duplicate_numbers"] == []


def test_own_caption_text_does_not_count_as_prose_mention(tmp_path):
    # A figure's OWN alt-text caption contains "Figure N" — that must not, by
    # itself, satisfy the "mentioned in prose" check (else orphan detection
    # would never fire for any embedded figure).
    d, cap = _project(tmp_path, {
        "results.md": "![Figure 7. Standalone, discussed nowhere else.](../analysis/figures/g.png)\n"
    })
    r = fc.check(d, cap)
    assert r["figures"]["orphaned"] == ["7"]


def test_captions_md_cross_check_flags_uncaptioned_figure(tmp_path):
    captions = "## Figure: `figures/a.pdf` / `.png`\n**Figure 1.** caption text\n"
    d, cap = _project(tmp_path, {
        "results.md": (
            "![Figure 1. A.](../analysis/figures/a.png)\n"
            "![Figure 2. B, no captions.md entry.](../analysis/figures/b.png)\n"
            "Figure 1 and Figure 2 discussed.\n")
    }, captions=captions)
    r = fc.check(d, cap)
    assert any("Figure 2" in x for x in r["uncaptioned_figures"])
    assert not any("Figure 1" in x for x in r["uncaptioned_figures"])


def test_no_captions_md_skips_that_check_gracefully(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": "![Figure 1. A.](../analysis/figures/a.png)\nFigure 1 shown.\n"
    })  # captions=None -> file doesn't exist
    r = fc.check(d, cap)
    assert r["uncaptioned_figures"] == []


def test_cli_default_never_blocks(tmp_path):
    _project(tmp_path, {"results.md": "Figure 9 shows something never embedded.\n"})
    p = subprocess.run([sys.executable, str(SCRIPTS / "figure_check.py")],
                       cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0
    assert json.loads(p.stdout)["figures"]["missing"] == ["9"]


def test_cli_strict_blocks_on_warnings(tmp_path):
    _project(tmp_path, {"results.md": "Figure 9 shows something never embedded.\n"})
    p = subprocess.run([sys.executable, str(SCRIPTS / "figure_check.py"), "--strict"],
                       cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 2


def test_html_comment_mention_is_not_a_mention(tmp_path):
    # Drafts are full of HTML comments BY INSTRUCTION (evidence binding, RQ
    # tags, reviewer notes). A "bkz. Şekil 9" inside one is not a reference the
    # manuscript makes; counting it invents a missing figure out of prose no
    # reader will ever see.
    d, cap = _project(tmp_path, {
        "tartisma.md": "Bir şey.\n<!-- bkz. Şekil 9 ve Tablo 8 -->\nSonuç.\n"})
    r = fc.check(d, cap)
    assert r["figures"]["mentioned_count"] == 0
    assert r["tables"]["mentioned_count"] == 0
    assert r["figures"]["missing"] == r["tables"]["missing"] == []
    assert r["warnings"] == 0


def test_commented_out_embed_is_not_embedded(tmp_path):
    # The other direction: a figure commented OUT is not present, and must not
    # satisfy the mention that points at it.
    d, cap = _project(tmp_path, {
        "results.md": (
            "Figure 1 shows the class balance.\n"
            "<!-- ![Figure 1. Class balance.](../analysis/figures/class_balance.png) -->\n")
    })
    r = fc.check(d, cap)
    assert r["figures"]["embedded_count"] == 0
    assert r["figures"]["missing"] == ["1"]


# --- out_of_order (round-10 Minor 3: a complete, gapless, uniquely-numbered
# set can still be numbered wrongly, and every pre-existing check is
# order-blind).

def test_out_of_order_table_flagged(tmp_path):
    # The exact shape the manuscript carried: a sub-lettered caption printed
    # before the number it belongs after, so 6 lands after 7b.
    d, cap = _project(tmp_path, {
        "results.md": (
            "**Table 5. Characteristics.**\n\n"
            "Table 5, Table 6, Table 7 and Table 7b are discussed.\n\n"
            "**Table 7b. Convergence status.**\n\n"
            "**Table 6. Risk of bias.**\n\n"
            "**Table 7. Applicability.**\n")
    })
    r = fc.check(d, cap)
    t = r["tables"]
    # The point of the test: the OLD checks all pass on this input.
    assert t["sequence_gaps"] == []
    assert t["duplicate_numbers"] == []
    assert t["missing"] == t["orphaned"] == []
    # And the new one does not.
    assert len(t["out_of_order"]) == 1
    assert t["out_of_order"][0]["label"] == "6"
    assert t["out_of_order"][0]["after"] == "7b"
    assert r["warnings"] == 1


def test_out_of_order_reports_one_finding_not_a_cascade(tmp_path):
    # One displaced caption must not report every caption that follows it.
    d, cap = _project(tmp_path, {
        "results.md": (
            "Table 1, Table 2, Table 3 and Table 9 are discussed.\n\n"
            "**Table 9. Late.**\n\n"
            "**Table 1. First.**\n\n"
            "**Table 2. Second.**\n\n"
            "**Table 3. Third.**\n")
    })
    r = fc.check(d, cap)
    labels = [x["label"] for x in r["tables"]["out_of_order"]]
    assert labels == ["1", "2", "3"], labels
    # Each is measured against the running peak (9), not against its
    # predecessor — otherwise 2-after-1 and 3-after-2 would read as ordered
    # and the displacement of 9 would vanish after the first row.
    assert {x["after"] for x in r["tables"]["out_of_order"]} == {"9"}


def test_ascending_order_across_two_files_is_not_flagged(tmp_path):
    # Reading order across files is NOT knowable from filenames; the check is
    # deliberately per-file. "results.md" sorts before "zz_appendix.md" here by
    # accident, and the check must not depend on that accident either way.
    d, cap = _project(tmp_path, {
        "results.md": "Table 9 is discussed.\n\n**Table 9. Late number, early file.**\n",
        "zz_appendix.md": "Table 1 is discussed.\n\n**Table 1. Early number, late file.**\n",
    })
    r = fc.check(d, cap)
    assert r["tables"]["out_of_order"] == []


def test_out_of_order_figures_too(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "Figure 1 and Figure 2 are discussed.\n\n"
            "![Figure 2. Second.](../analysis/figures/b.png)\n\n"
            "![Figure 1. First.](../analysis/figures/a.png)\n")
    })
    r = fc.check(d, cap)
    assert [x["label"] for x in r["figures"]["out_of_order"]] == ["1"]


def test_sub_labels_in_ascending_order_are_clean(tmp_path):
    # "3" then "3a" then "4" is correct numbering, not a violation: the base
    # integer never decreases.
    d, cap = _project(tmp_path, {
        "results.md": (
            "Table 3, Table 3a and Table 4 are discussed.\n\n"
            "**Table 3. Base.**\n\n"
            "**Table 3a. Sub.**\n\n"
            "**Table 4. Next.**\n")
    })
    r = fc.check(d, cap)
    assert r["tables"]["out_of_order"] == []
    assert r["warnings"] == 0


# --- degenerate_ranges (round-11 Minor 1: a global renumbering pass turned
# "Table 6-7" into "Table 7-7", and every per-number count still reconciled).

def test_degenerate_range_same_endpoints_flagged(tmp_path):
    d, cap = _project(tmp_path, {
        "methods.md": (
            "**Table 6. A.**\n\n**Table 7. B.**\n\n"
            "Table 6, Table 7 and Table 7-7 are derived from these.\n")
    })
    r = fc.check(d, cap)
    assert len(r["tables"]["degenerate_ranges"]) == 1
    assert r["tables"]["degenerate_ranges"][0]["text"].endswith("7-7")
    # The point: with the range silently dropped, nothing else fires at all.
    assert r["tables"]["missing"] == []
    assert r["tables"]["orphaned"] == []


def test_descending_range_flagged(tmp_path):
    d, cap = _project(tmp_path, {
        "methods.md": "**Table 1. A.**\n\n**Table 2. B.**\n\nSee Tables 2-1.\n"
    })
    r = fc.check(d, cap)
    degen = r["tables"]["degenerate_ranges"]
    assert len(degen) == 1
    assert "counts downwards" in degen[0]["msg"]


def test_normal_range_is_not_degenerate(tmp_path):
    d, cap = _project(tmp_path, {
        "results.md": (
            "Figures 1-3 are discussed.\n\n"
            "![Figure 1. A.](a.png)\n\n![Figure 2. B.](b.png)\n\n"
            "![Figure 3. C.](c.png)\n")
    })
    r = fc.check(d, cap)
    assert r["figures"]["degenerate_ranges"] == []
    assert r["warnings"] == 0
