"""draft_integrity.py — the draft files as files, not as prose.

The defect that motivated this script appeared three separate times in this
kit's own development, twice AFTER it had been fixed once, because each fix
wired up the one block someone had noticed. These tests exist so the fourth
time is caught by a machine.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import draft_integrity as di  # noqa: E402


def _project(tmp_path, drafts: dict, sources: dict | None = None):
    d = tmp_path / "drafts"
    d.mkdir()
    for name, text in drafts.items():
        (d / name).write_text(text, encoding="utf-8")
    for name, text in (sources or {}).items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return d, tmp_path


# --------------------------------------------------------- generated blocks

def test_generated_block_with_a_writer_is_clean(tmp_path):
    d, root = _project(
        tmp_path,
        {"results.md": (
            "<!-- TABLE5:BASLANGIC — uretilmis, elle duzenlemeyin -->\n"
            "| a | b |\n"
            "<!-- TABLE5:BITIS -->\n")},
        {"analysis/tables_build.py": 'embed_block(target, "TABLE5", body)\n'})
    r = di.check(d, root)
    assert r["warnings"] == 0
    assert r["generated_blocks"] == ["TABLE5"]
    assert "TABLE5" in r["generated_block_writers"]


def test_generated_block_nobody_writes_is_flagged(tmp_path):
    # The exact defect: the block says a script owns it; no script does.
    d, root = _project(
        tmp_path,
        {"results.md": (
            "<!-- TABLE6:BASLANGIC — uretilmis, elle duzenlemeyin -->\n"
            "| a | b |\n"
            "<!-- TABLE6:BITIS -->\n")},
        {"analysis/tables_build.py": 'embed_block(target, "TABLE5", body)\n'})
    r = di.check(d, root)
    assert len(r["unwritten_generated_blocks"]) == 1
    assert r["unwritten_generated_blocks"][0]["tag"] == "TABLE6"
    assert r["warnings"] == 1


def test_english_generated_marker_also_recognised(tmp_path):
    d, root = _project(
        tmp_path,
        {"results.md": ("<!-- T1:BASLANGIC generated — do not edit -->\n"
                        "x\n<!-- T1:BITIS -->\n")},
        {})
    r = di.check(d, root)
    assert [x["tag"] for x in r["unwritten_generated_blocks"]] == ["T1"]


def test_begin_end_spelling_also_recognised(tmp_path):
    d, root = _project(
        tmp_path,
        {"results.md": ("<!-- T1:BEGIN generated -->\nx\n<!-- T1:END -->\n")},
        {})
    r = di.check(d, root)
    assert r["blocks_found"] == 1
    assert [x["tag"] for x in r["unwritten_generated_blocks"]] == ["T1"]


def test_script_owned_block_that_does_not_say_so_is_flagged(tmp_path):
    # The mirror case. A hand edit here is not wrong — it is erased, and
    # nothing warned against it.
    d, root = _project(
        tmp_path,
        {"results.md": "<!-- TABLEA:BASLANGIC -->\n| a |\n<!-- TABLEA:BITIS -->\n"},
        {"analysis/pooled_table.py": 'START = "<!-- TABLEA:BASLANGIC -->"\n'})
    r = di.check(d, root)
    assert len(r["undeclared_generated_blocks"]) == 1
    u = r["undeclared_generated_blocks"][0]
    assert u["tag"] == "TABLEA"
    assert u["written_by"] == ["analysis/pooled_table.py"]
    assert r["unwritten_generated_blocks"] == []


def test_hand_block_with_no_writer_and_no_claim_is_not_a_finding(tmp_path):
    # A plain marker pair nobody generates and that claims nothing is just a
    # marker. Flagging it would make the check fire on every anchor comment.
    d, root = _project(
        tmp_path,
        {"results.md": "<!-- NOTES:BASLANGIC -->\nhand written\n<!-- NOTES:BITIS -->\n"},
        {})
    r = di.check(d, root)
    assert r["warnings"] == 0


def test_a_copy_of_the_block_in_build_does_not_count_as_a_writer(tmp_path):
    # build/ carries assembled copies of the drafts. Finding the tag there
    # proves the block was COPIED, not that anything generates it.
    d, root = _project(
        tmp_path,
        {"results.md": ("<!-- T9:BASLANGIC — uretilmis -->\nx\n<!-- T9:BITIS -->\n")},
        {"build/makale.md": "<!-- T9:BASLANGIC — uretilmis -->\nx\n<!-- T9:BITIS -->\n"})
    r = di.check(d, root)
    assert [x["tag"] for x in r["unwritten_generated_blocks"]] == ["T9"]


# ------------------------------------------------------------ marker shape

def test_unclosed_marker_flagged(tmp_path):
    d, root = _project(tmp_path, {"results.md": "<!-- T1:BASLANGIC -->\nbody\n"}, {})
    r = di.check(d, root)
    kinds = [p["kind"] for p in r["marker_problems"]]
    assert kinds == ["unclosed-marker"]


def test_close_without_open_flagged(tmp_path):
    d, root = _project(tmp_path, {"results.md": "body\n<!-- T1:BITIS -->\n"}, {})
    r = di.check(d, root)
    assert [p["kind"] for p in r["marker_problems"]] == ["close-without-open"]


def test_reopened_tag_flagged(tmp_path):
    d, root = _project(
        tmp_path,
        {"results.md": ("<!-- T1:BASLANGIC -->\na\n"
                        "<!-- T1:BASLANGIC -->\nb\n<!-- T1:BITIS -->\n")}, {})
    r = di.check(d, root)
    assert [p["kind"] for p in r["marker_problems"]] == ["marker-reopened"]


def test_two_tags_interleaved_are_both_closed(tmp_path):
    # Nesting/interleaving is legal as long as each tag opens and closes.
    d, root = _project(
        tmp_path,
        {"results.md": ("<!-- A:BASLANGIC -->\n<!-- B:BASLANGIC -->\n"
                        "<!-- A:BITIS -->\n<!-- B:BITIS -->\n")}, {})
    r = di.check(d, root)
    assert r["marker_problems"] == []
    assert r["blocks_found"] == 2


# ------------------------------------------------------- control characters

def test_control_character_flagged(tmp_path):
    # A backslash escape that went through one interpreter too many:
    # "\\begingroup\\footnotesize" arrives as BS + "egingroup" + FF + "ootnotesize".
    line = chr(8) + "egingroup" + chr(12) + "ootnotesize"
    d, root = _project(tmp_path, {"results.md": "```{=latex}\n" + line + "\n```\n"}, {})
    r = di.check(d, root)
    assert len(r["control_characters"]) == 1
    hit = r["control_characters"][0]
    assert hit["line"] == 2
    assert hit["control"] == ["U+0008", "U+000C"]


def test_replacement_character_flagged(tmp_path):
    d, root = _project(tmp_path, {"results.md": "ta�ymayan bir sonu�\n"}, {})
    r = di.check(d, root)
    assert r["control_characters"][0]["replacement_chars"] == 2


def test_tabs_and_newlines_are_not_control_findings(tmp_path):
    d, root = _project(tmp_path, {"results.md": "a\tb\nc\td\n"}, {})
    r = di.check(d, root)
    assert r["control_characters"] == []
    assert r["warnings"] == 0


# --------------------------------------------------------------------- cli

def test_status_md_is_skipped(tmp_path):
    d, root = _project(
        tmp_path,
        {"STATUS.md": "<!-- T1:BASLANGIC — uretilmis -->\nx\n<!-- T1:BITIS -->\n",
         "results.md": "clean\n"}, {})
    r = di.check(d, root)
    assert r["blocks_found"] == 0
    assert r["warnings"] == 0


def test_cli_strict_exits_2_on_warning(tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "results.md").write_text(
        "<!-- T1:BASLANGIC — uretilmis -->\nx\n<!-- T1:BITIS -->\n", encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "draft_integrity.py"), "--strict"],
        cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode == 2
    assert json.loads(p.stdout)["warnings"] == 1


def test_cli_default_is_warn_only(tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "results.md").write_text(
        "<!-- T1:BASLANGIC — uretilmis -->\nx\n<!-- T1:BITIS -->\n", encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "draft_integrity.py")],
        cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode == 0
    assert json.loads(p.stdout)["warnings"] == 1


def test_missing_drafts_dir_is_not_an_error(tmp_path):
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "draft_integrity.py")],
        cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode == 0
    assert json.loads(p.stdout)["files_scanned"] == []
