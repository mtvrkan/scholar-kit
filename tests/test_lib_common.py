"""Direct unit tests for scripts/lib_common.py — previously exercised only
transitively through the scripts that import it (bib_doctor, doi2bib,
evidence_db, registry_db, venue_check, xlsx_export, ...), with no test that
pins its own contract in isolation.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import lib_common  # noqa: E402


# ---------- JSONL round-trip + atomicity ----------

def test_read_jsonl_missing_file_returns_empty_list(tmp_path):
    assert lib_common.read_jsonl(tmp_path / "nope.jsonl") == []


def test_write_then_read_jsonl_round_trip(tmp_path):
    p = tmp_path / "data.jsonl"
    records = [{"id": 1, "name": "Şahin"}, {"id": 2, "name": "Müller"}]
    lib_common.write_jsonl(p, records)
    assert lib_common.read_jsonl(p) == records


def test_write_jsonl_leaves_no_tmp_file_behind(tmp_path):
    p = tmp_path / "data.jsonl"
    lib_common.write_jsonl(p, [{"a": 1}])
    leftovers = list(tmp_path.glob("*.tmp*"))
    assert leftovers == []


def test_append_jsonl_appends_one_line(tmp_path):
    p = tmp_path / "data.jsonl"
    lib_common.append_jsonl(p, {"a": 1})
    lib_common.append_jsonl(p, {"a": 2})
    assert lib_common.read_jsonl(p) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_skips_blank_lines(tmp_path):
    p = tmp_path / "data.jsonl"
    p.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert lib_common.read_jsonl(p) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_dies_on_invalid_json_line(tmp_path, capsys):
    p = tmp_path / "data.jsonl"
    p.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        lib_common.read_jsonl(p)
    assert "invalid JSON line" in capsys.readouterr().err


def test_write_json_atomic_round_trip(tmp_path):
    p = tmp_path / "settings.json"
    lib_common.write_json_atomic(p, {"a": [1, 2, 3]})
    import json
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": [1, 2, 3]}


def test_write_text_atomic_uses_lf_newlines(tmp_path):
    p = tmp_path / "x.txt"
    lib_common.write_text_atomic(p, "line1\nline2\n")
    assert p.read_bytes() == b"line1\nline2\n"


def test_write_bytes_atomic_round_trip(tmp_path):
    p = tmp_path / "x.bin"
    lib_common.write_bytes_atomic(p, b"\x00\x01\x02")
    assert p.read_bytes() == b"\x00\x01\x02"


# ---------- file_lock ----------

def test_file_lock_serializes_within_same_process(tmp_path):
    p = tmp_path / "data.jsonl"
    order = []
    with lib_common.file_lock(p):
        order.append("first-acquired")
    with lib_common.file_lock(p):
        order.append("second-acquired")
    assert order == ["first-acquired", "second-acquired"]


def test_file_lock_creates_sidecar_lock_file(tmp_path):
    p = tmp_path / "data.jsonl"
    with lib_common.file_lock(p):
        pass
    assert (tmp_path / "data.jsonl.lock").exists()


# ---------- require_within_cwd ----------

def test_require_within_cwd_allows_relative_path_inside_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert lib_common.require_within_cwd("sources/registry.jsonl", "--file") == "sources/registry.jsonl"


def test_require_within_cwd_rejects_dotdot_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        lib_common.require_within_cwd("../../etc/passwd", "--file")


def test_require_within_cwd_rejects_absolute_path_outside_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "outside.jsonl"
    with pytest.raises(SystemExit):
        lib_common.require_within_cwd(str(outside), "--file")


def test_require_within_cwd_allows_cwd_itself(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert lib_common.require_within_cwd(str(tmp_path), "--dir") == str(tmp_path)


# ---------- transliterate / normalize helpers ----------

def test_transliterate_turkish_chars():
    assert lib_common.transliterate("Şahin Öztürk Çelik Ğüven Işık") == "Sahin Ozturk Celik Guven Isik"


def test_transliterate_other_latin_diacritics():
    assert lib_common.transliterate("Müller") == "Muller"
    assert lib_common.transliterate("Garcia") == "Garcia"


def test_normalize_title_strips_braces_and_punctuation():
    assert lib_common.normalize_title("{Deep} Learning: A Survey!") == "deep learning a survey"


def test_normalize_issn_strips_hyphens_and_uppercases_x():
    assert lib_common.normalize_issn("0888-333x") == "0888333X"


# ---------- DOI helpers ----------

def test_doi_re_accepts_valid_doi():
    assert lib_common.DOI_RE.match("10.1016/j.ymssp.2023.00001")


def test_doi_re_rejects_malformed_doi():
    assert not lib_common.DOI_RE.match("not-a-doi")
    assert not lib_common.DOI_RE.match("10.1/x")  # needs 4-9 digits after "10."


def test_clean_doi_strips_url_prefix():
    assert lib_common.clean_doi("https://doi.org/10.1016/x") == "10.1016/x"
    assert lib_common.clean_doi("doi:10.1016/x") == "10.1016/x"
    assert lib_common.clean_doi("10.1016/x") == "10.1016/x"


# ---------- minimal BibTeX parser ----------

def test_parse_and_serialize_bibtex_round_trip():
    text = """@article{kaya2023deep,
  title = {Deep learning for bearing fault diagnosis},
  author = {Kaya, Ahmet},
  year = {2023},
}"""
    entries = lib_common.parse_bibtex(text)
    assert len(entries) == 1
    e = entries[0]
    assert e["type"] == "article"
    assert e["key"] == "kaya2023deep"
    assert e["fields"]["author"] == "Kaya, Ahmet"
    out = lib_common.serialize_bibtex(e)
    reparsed = lib_common.parse_bibtex(out)
    assert reparsed[0]["fields"] == e["fields"]


def test_parse_bibtex_ignores_comment_and_string_entries():
    text = "@comment{ignored}\n@string{x = \"y\"}\n@article{a2020x, title={T}}\n"
    entries = lib_common.parse_bibtex(text)
    assert [e["key"] for e in entries] == ["a2020x"]


# ---------- Markdown frontmatter ----------

def test_parse_frontmatter_does_not_swallow_content_after_closing_delimiter():
    # Regression: a "Gate:" reminder inserted BEFORE the closing frontmatter
    # `---` (instead of after it) got silently folded into the `description`
    # field that drives skill routing/matching.
    text = (
        "---\n"
        'name: x\ndescription: "real description."\n'
        "---\n\n"
        "> **Gate:** this belongs to the document body, not the description.\n"
    )
    fm = lib_common.parse_frontmatter(text)
    assert fm["description"] == "real description."
    assert "Gate" not in fm["description"]


@pytest.mark.parametrize("skill", ["docx-output", "latex-thesis"])
def test_repo_skill_descriptions_are_not_contaminated_by_gate_note(skill):
    # Direct regression check on the actual files the frontmatter bug above
    # touched — the bug (Gate blockquote placed before the closing `---`)
    # corrupted exactly these two SKILL.md files' routing-relevant
    # `description` field.
    root = Path(__file__).parent.parent
    p = root / ".claude" / "skills" / skill / "SKILL.md"
    fm = lib_common.parse_frontmatter(p.read_text(encoding="utf-8"))
    assert "Gate" not in fm["description"]
    assert "phase_gate.py" not in fm["description"]
