"""The on-ramp for a library that already exists (scripts/library_import.py).

The feature is a convenience; the tests are about the thing it must not become.
An import path is the fastest way ever built to fill a bibliography with
unverified entries, so what is pinned here is the refusal: not one field of the
export reaches `bib/references.bib`, DOI-bearing entries are re-fetched by
`doi2bib.py`, DOI-less ones are registered and REPORTED, and the importer writes
neither data file itself — both go through their sanctioned writers.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import library_import  # noqa: E402

BIB = """@article{kaya2023deep,
  title = {{Deep learning for stroke}},
  author = {Kaya, Ahmet and Y{\\i}lmaz, Berk},
  journal = {Journal of Testing},
  year = {2023},
  doi = {https://doi.org/10.1234/abc123},
  language = {Turkish}
}

@inproceedings{demir2020nodoi,
  title = {A paper with no identifier},
  author = {Demir, Can},
  booktitle = {Proc. of Nothing},
  year = {2020}
}
"""

RIS = """TY  - JOUR
AU  - Şahin, Elif
TI  - Türkçe metin sınıflandırma
JO  - Bilişim Dergisi
PY  - 2022
DO  - 10.5555/xyz
LA  - tur
ER  -

TY  - CONF
AU  - Smith, John
T1  - Something without an identifier
T2  - Proc of X
Y1  - 2019
"""


def _project(tmp_path: Path, name: str, text: str) -> Path:
    (tmp_path / "sources").mkdir(exist_ok=True)
    (tmp_path / "sources" / name).write_text(text, encoding="utf-8")
    return tmp_path


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "library_import.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _records(tmp_path: Path) -> list[dict]:
    text = (tmp_path / "sources" / "registry.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------- parsing the two export formats ----------

def test_bibtex_export_yields_one_record_per_entry():
    entries = library_import.parse_bib_library(BIB, "en")
    assert [e["title"] for e in entries] == ["Deep learning for stroke",
                                             "A paper with no identifier"]
    assert entries[0]["year"] == 2023 and entries[0]["venue"] == "Journal of Testing"


def test_a_doi_url_in_the_export_is_normalised_to_a_bare_doi():
    # Zotero exports the doi.org URL form; every DOI comparison in this codebase
    # (dedup, verification) is against the bare one.
    assert library_import.parse_bib_library(BIB, "en")[0]["doi"] == "10.1234/abc123"


def test_a_latex_escaped_turkish_name_reaches_the_register_as_a_searchable_name():
    # "Y\ilmaz" is not a cosmetic defect: the register is what screening and every
    # later search read, and a name nobody can search for is a record nobody finds.
    assert library_import.parse_bib_library(BIB, "en")[0]["authors"] == [
        "Kaya, Ahmet", "Yılmaz, Berk"]


def test_accents_outside_turkish_compose_too():
    # The decoder is Unicode composition, not a table of the letters this kit
    # happens to care about — so French, Czech and Polish arrive intact without
    # anyone remembering to extend a list.
    entries = library_import.parse_bib_library(
        "@article{k,\n title={Sur la m{\\'e}thode de {\\v c}ap},\n author={A, B}\n}\n", "en")
    assert entries[0]["title"] == "Sur la méthode de čap"


def test_markup_loses_the_command_and_keeps_the_text():
    entries = library_import.parse_bib_library(
        "@article{k,\n title={A \\textbf{bold} claim},\n author={A, B}\n}\n", "en")
    assert entries[0]["title"] == "A bold claim"


def test_the_export_language_field_decides_the_record_language():
    assert library_import.parse_bib_library(BIB, "en")[0]["lang"] == "tr"
    assert library_import.parse_bib_library(BIB, "en")[1]["lang"] == "en"


def test_ris_records_are_parsed_including_the_last_one_without_a_closing_tag():
    # A RIS file whose final record has no ER is malformed and common; dropping
    # that record silently is the one behaviour an import must never have.
    entries = library_import.parse_ris_library(RIS, "en")
    assert len(entries) == 2
    assert entries[0]["doi"] == "10.5555/xyz" and entries[0]["lang"] == "tr"
    assert entries[1]["title"] == "Something without an identifier"


def test_the_format_is_detected_from_content_not_only_the_suffix(tmp_path):
    # An EndNote export saved as .txt is still RIS.
    p = tmp_path / "lib.txt"
    p.write_text(RIS, encoding="utf-8")
    assert len(library_import.parse_library(p, "en")) == 2


# ---------- the refusal ----------

def test_no_field_of_the_export_reaches_the_bibliography(tmp_path, monkeypatch):
    """The load-bearing test. The export carries a complete, plausible BibTeX
    entry; the fetch fails; the bib must still not exist."""
    _project(tmp_path, "lib.bib", BIB)
    monkeypatch.chdir(tmp_path)
    result = library_import.run_import(
        library_import.parse_bib_library(BIB, "en"),
        source_name="lib.bib", registry="sources/registry.jsonl", bib="bib/references.bib",
        fetch=lambda doi: {"error": "network error"})
    assert result["bib_appended"] == []
    assert [f["doi"] for f in result["fetch_failed"]] == ["10.1234/abc123"]
    assert not (tmp_path / "bib" / "references.bib").exists()


def test_an_entry_without_a_doi_is_registered_and_reported(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    # exit 2: imported, but something is left for the author to resolve.
    out = json.loads(_run(tmp_path, "--file", "sources/lib.bib", "--no-fetch",
                          "--quiet", expect=2).stdout)
    assert len(out["registered"]) == 2
    assert [u["title"] for u in out["no_doi"]] == ["A paper with no identifier"]
    assert "--title-search" in out["no_doi"][0]["reason"]


def test_no_fetch_really_makes_no_fetch(tmp_path, monkeypatch):
    # Pins the falsy-default bug this flag invites: `fetch or default` would
    # quietly restore the network path for every DOI-bearing entry.
    _project(tmp_path, "lib.bib", BIB)
    monkeypatch.chdir(tmp_path)

    def explode(*a, **kw):  # pragma: no cover - must never run
        raise AssertionError("the network path ran under --no-fetch")

    monkeypatch.setattr(library_import, "fetch_via_doi2bib", explode)
    result = library_import.run_import(
        library_import.parse_bib_library(BIB, "en"),
        source_name="lib.bib", registry="sources/registry.jsonl",
        bib="bib/references.bib", fetch=False)
    assert result["registered"] and result["bib_appended"] == []


def test_the_importer_writes_neither_data_file_itself():
    # It orchestrates the two sanctioned writers; it is not a third one. If this
    # ever fails, Invariant 6's hook-enforced guarantee has quietly acquired an
    # exception that no hook knows about.
    source = (SCRIPTS / "library_import.py").read_text(encoding="utf-8")
    for forbidden in ("write_jsonl", "append_jsonl", "write_text_atomic", "serialize_bibtex"):
        assert forbidden not in source, (
            f"library_import.py uses {forbidden} — it must delegate every write to "
            f"registry_db.py / doi2bib.py")


def test_the_batch_goes_to_registry_db_and_the_fetch_to_doi2bib(monkeypatch):
    seen = []

    class _Proc:
        returncode = 0
        stdout = '{"added": ["SRC-0001"], "duplicates": [], "total": 1}'
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: seen.append(cmd) or _Proc())
    library_import.register([{"title": "x"}], "sources/registry.jsonl")
    assert seen and seen[0][1].endswith("registry_db.py") and seen[0][-2:] == ["add", "--stdin"]

    seen.clear()
    _Proc.stdout = '{"status": "appended", "key": "kaya2023deep"}'
    library_import.fetch_via_doi2bib("10.1/x", "bib/references.bib")
    assert seen[0][1].endswith("doi2bib.py") and "--append" in seen[0]


# ---------- what the register records ----------

def test_imported_records_carry_their_unverified_provenance(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", "--quiet", expect=2)
    for rec in _records(tmp_path):
        assert rec["db"] == "import" and rec["import_source"] == "lib.bib"
        assert rec["metadata_source"] == "user-export (unverified)"
        assert rec["status"] == "candidate"


def test_the_bib_key_minted_by_doi2bib_lands_on_the_register_record(tmp_path, monkeypatch):
    # Resolve-then-register exists for this: the record links to its own
    # reference in the same write, never in a second pass.
    _project(tmp_path, "lib.bib", BIB)
    monkeypatch.chdir(tmp_path)
    library_import.run_import(
        library_import.parse_bib_library(BIB, "en"),
        source_name="lib.bib", registry="sources/registry.jsonl", bib="bib/references.bib",
        fetch=lambda doi: {"status": "appended", "key": "kaya2023deep"})
    records = _records(tmp_path)
    assert records[0]["bib_key"] == "kaya2023deep"
    assert "bib_key" not in records[1]  # the entry with no DOI has no reference yet


def test_a_second_import_of_the_same_library_is_deduplicated(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", "--quiet", expect=2)
    out = json.loads(_run(tmp_path, "--file", "sources/lib.bib", "--no-fetch",
                          "--quiet", expect=2).stdout)
    assert out["registered"] == [] and len(out["duplicates"]) == 2


# ---------- looking is not importing ----------

def test_plan_writes_nothing_and_says_so(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    out = json.loads(_run(tmp_path, "--file", "sources/lib.bib", "--plan").stdout)
    assert out["parsed"] == 2 and out["with_doi"] == 1 and out["without_doi"] == 1
    assert out["by_language"] == {"tr": 1, "en": 1}
    assert not (tmp_path / "sources" / "registry.jsonl").exists()
    assert "nothing was written" in out["note"]


def test_plan_shows_a_sample_so_the_author_can_recognise_the_library(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    out = json.loads(_run(tmp_path, "--file", "sources/lib.bib", "--plan").stdout)
    assert out["sample"][0]["title"].startswith("Deep learning")


# ---------- finishing an offline import ----------

def test_resolve_fills_the_bib_for_registered_records_without_re_registering(tmp_path, monkeypatch):
    # The reason --no-fetch is safe: re-running the import to finish the job
    # would re-register every record as a duplicate.
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", "--quiet", expect=2)
    monkeypatch.chdir(tmp_path)
    result = library_import.resolve_registered(
        "sources/registry.jsonl", "bib/references.bib",
        fetch=lambda doi: {"status": "appended", "key": "kaya2023deep"})
    assert result["pending"] == 1
    assert result["linked"] == [{"id": "SRC-0001", "bib_key": "kaya2023deep"}]
    records = _records(tmp_path)
    assert len(records) == 2, "resolve must not add records"
    assert records[0]["bib_key"] == "kaya2023deep"


def test_resolve_skips_records_that_already_carry_a_bib_key(tmp_path, monkeypatch):
    _project(tmp_path, "lib.bib", BIB)
    monkeypatch.chdir(tmp_path)
    library_import.run_import(
        library_import.parse_bib_library(BIB, "en"),
        source_name="lib.bib", registry="sources/registry.jsonl", bib="bib/references.bib",
        fetch=lambda doi: {"status": "appended", "key": "kaya2023deep"})

    def explode(doi):  # pragma: no cover - must never run
        raise AssertionError("re-fetched a record that already has its reference")

    assert library_import.resolve_registered(
        "sources/registry.jsonl", "bib/references.bib", fetch=explode)["pending"] == 0


def test_a_key_that_is_minted_but_not_linked_is_reported_as_a_failure(tmp_path, monkeypatch):
    # Half-done is the state an import must never report as done: the bib gained
    # an entry the register cannot point at.
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", "--quiet", expect=2)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(library_import, "link_bib_key",
                        lambda *a, **kw: {"error": "bib_key already used by SRC-0009"})
    result = library_import.resolve_registered(
        "sources/registry.jsonl", "bib/references.bib",
        fetch=lambda doi: {"status": "appended", "key": "kaya2023deep"})
    assert result["linked"] == []
    assert "not linked" in result["fetch_failed"][0]["reason"]


def test_resolve_refuses_to_be_given_a_file(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    proc = _run(tmp_path, "--resolve", "--file", "sources/lib.bib", expect=1)
    assert "drop --file" in proc.stderr


def test_resolve_without_a_register_says_what_is_missing(tmp_path):
    (tmp_path / "sources").mkdir()
    proc = _run(tmp_path, "--resolve", expect=1)
    assert "nothing registered to resolve" in proc.stderr


# ---------- CLI contract ----------

def test_limit_imports_only_the_first_n(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    out = json.loads(_run(tmp_path, "--file", "sources/lib.bib", "--no-fetch",
                          "--limit", "1", "--quiet").stdout)
    assert out["parsed"] == 1 and len(out["registered"]) == 1


def test_a_zero_limit_is_refused(tmp_path):
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", "--limit", "0", expect=1)


def test_an_export_outside_the_project_is_refused(tmp_path):
    outside = tmp_path / "outside.bib"
    outside.write_text(BIB, encoding="utf-8")
    project = tmp_path / "project"
    (project / "sources").mkdir(parents=True)
    proc = _run(project, "--file", str(outside), "--no-fetch", expect=1)
    assert "inside the current project directory" in proc.stderr


def test_a_file_that_is_not_a_library_is_refused(tmp_path):
    _project(tmp_path, "lib.bib", "Kaya, A. (2023). Deep learning for stroke.\n")
    proc = _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", expect=1)
    assert "no records" in proc.stderr


def test_a_missing_export_names_the_fix(tmp_path):
    (tmp_path / "sources").mkdir()
    proc = _run(tmp_path, "--file", "sources/absent.bib", "--no-fetch", expect=1)
    assert "copy the export into the project" in proc.stderr


def test_no_input_at_all_names_both_ways_in(tmp_path):
    proc = _run(tmp_path, expect=1)
    assert "--file" in proc.stderr and "--resolve" in proc.stderr


def test_output_is_exactly_one_json_object(tmp_path):
    _project(tmp_path, "lib.ris", RIS)
    out = json.loads(_run(tmp_path, "--file", "sources/lib.ris", "--no-fetch",
                          "--quiet", expect=2).stdout)
    assert out["fetched"] is False


@pytest.mark.parametrize("flag", ["--no-fetch", "--quiet"])
def test_the_documented_flags_exist(tmp_path, flag):
    _project(tmp_path, "lib.bib", BIB)
    _run(tmp_path, "--file", "sources/lib.bib", "--no-fetch", flag, "--limit", "1")
