"""Regression tests for bugs found in the post-build audit (2026-07-02)."""
import json
import sys

sys.path.insert(0, "scripts")
import venue_check  # noqa: E402


# Audit finding 1: cache_put kept duplicates when ISSN matched but title differed
def test_cache_put_replaces_same_issn_different_title(tmp_path):
    cache = tmp_path / "venues.jsonl"
    venue_check.cache_put(cache, {"issn": "0888-3270", "display_name": "MSSP",
                                  "wos_index": "unknown", "checked_at": "2026-07-01"})
    venue_check.cache_put(cache, {"issn": "0888-3270",
                                  "display_name": "Mechanical Systems and Signal Processing",
                                  "wos_index": "SCIE", "checked_at": "2026-07-02"})
    from lib_common import read_jsonl
    records = read_jsonl(cache)
    assert len(records) == 1
    assert records[0]["wos_index"] == "SCIE"


def test_cache_put_keeps_distinct_venues(tmp_path):
    cache = tmp_path / "venues.jsonl"
    venue_check.cache_put(cache, {"issn": "0888-3270", "display_name": "MSSP"})
    venue_check.cache_put(cache, {"issn": "1096-1216", "display_name": "Other Journal"})
    from lib_common import read_jsonl
    assert len(read_jsonl(cache)) == 2


# Audit finding 2: key collision handling appended "b" only once
def test_doi2bib_key_collision_loops(run, tmp_path, monkeypatch):
    bib = tmp_path / "bib"
    bib.mkdir()
    (bib / "references.bib").write_text(
        "@article{kaya2023deep,\n  title = {A},\n  doi = {10.1/a},\n}\n\n"
        "@article{kaya2023deepb,\n  title = {B},\n  doi = {10.1/b},\n}\n", encoding="utf-8")
    from lib_common import parse_bibtex
    entry = {"type": "article", "key": "kaya2023deep",
             "fields": {"title": "C", "doi": "10.1/c", "author": "Kaya, X", "year": "2023"}}
    existing = parse_bibtex((bib / "references.bib").read_text(encoding="utf-8"))
    while any(e["key"] == entry["key"] for e in existing):
        entry["key"] += "b"
    assert entry["key"] == "kaya2023deepbb"  # skips BOTH taken keys


# Audit finding 4: PRISMA fulltext derivation used a nonexistent status value
def test_prisma_derive_counts_by_stage(run, tmp_path):
    recs = [
        {"id": "SRC-0001", "title": "a", "status": "included"},
        {"id": "SRC-0002", "title": "b", "status": "excluded", "stage": "fulltext",
         "reason": "no metrics"},
        {"id": "SRC-0003", "title": "c", "status": "excluded", "stage": "screening",
         "reason": "off topic"},
        {"id": "SRC-0004", "title": "d", "status": "excluded", "reason": "off topic"},
        {"id": "SRC-0005", "title": "e", "status": "duplicate"},
    ]
    src = tmp_path / "sources"
    src.mkdir()
    (src / "registry.jsonl").write_text(
        "\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    rep = json.loads(out)
    c = rep["counts"]
    assert code == 0, rep
    # sought/not_retrieved joined the schema with the PRISMA 2020 "reports not
    # retrieved" box; no record here is unretrieved, so sought collapses onto fulltext
    # and the stage partition this test guards is unchanged.
    # excluded_reasons_fulltext joined later still: "excluded_reasons" keeps every
    # exclusion's reason (unchanged, and this test's original claim), while the
    # diagram's box — which announces the FULL-TEXT count — reads the narrower dict,
    # so it can no longer list reasons for more records than it says it excluded.
    assert c == {"identified": 5, "duplicates": 1, "screened": 4,
                 "excluded_screening": 2, "sought": 2, "not_retrieved": 0,
                 "background_excluded_from_flow": 0,
                 "fulltext": 2, "excluded_fulltext": 1,
                 "excluded_reasons": {"no metrics": 1, "off topic": 2},
                 "excluded_reasons_fulltext": {"no metrics": 1}, "included": 1}
    assert rep["consistency_errors"] == []


# Audit finding 3: xlsx_export crashed on cards missing claim/id
def test_xlsx_export_survives_sparse_cards(run, tmp_path, sample_registry):
    ev = tmp_path / "evidence"
    ev.mkdir()
    (ev / "cards.jsonl").write_text(
        json.dumps({"source": "kaya2023deep", "type": "method", "tags": ["rq1"]}) + "\n",
        encoding="utf-8")
    code, out, _ = run("xlsx_export.py")
    assert code == 0, out


def test_consistency_check_binds_prisma_numbers_to_the_register(run, tmp_path):
    """External review, 2026-08-16: the Methods section said "34 could not be
    retrieved ... 19 assessed ... 12 excluded" while the diagram, the abstract and
    the results all said 35/18/11 — the prose had been left behind by a register
    correction. Four rounds of peer review missed it; a reader found it in one pass.
    The manuscript elsewhere claims its numbers "cannot go stale silently", so this
    is the check that has to make that true."""
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in (
            [{"id": "SRC-0001", "status": "included"},
             {"id": "SRC-0002", "status": "excluded", "stage": "fulltext", "reason": "x"}]
            + [{"id": f"SRC-01{i}", "status": "unretrieved"} for i in range(3)])),
        encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    # 1 included + 1 full-text exclusion + 3 unretrieved -> fulltext=2, not 5.
    (drafts / "methods.md").write_text(
        "Beş rapor arandı. <!-- PRISMA: fulltext=5 -->\n", encoding="utf-8")
    code, out, _ = run("consistency_check.py")
    rep = json.loads(out)["prisma"]
    assert rep["checked"] is True
    assert [m["stage"] for m in rep["mismatches"]] == ["fulltext"]
    assert rep["mismatches"][0]["stated"] == 5
    assert rep["mismatches"][0]["expected"] == 2


def test_consistency_check_reports_unbound_prisma_stages(run, tmp_path):
    """A binding nobody wrote cannot be checked, so silence must not read as
    agreement — the same posture template_compliance.py takes with `unbound`."""
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").write_text(
        json.dumps({"id": "SRC-0001", "status": "included"}) + "\n", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "methods.md").write_text("Hiçbir sayı bağlanmadı.\n", encoding="utf-8")
    code, out, _ = run("consistency_check.py")
    rep = json.loads(out)["prisma"]
    assert rep["mismatches"] == []
    assert "included" in rep["unbound"] and rep["bound"] == []


def test_consistency_check_accepts_a_correct_prisma_binding(run, tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in
                [{"id": "SRC-0001", "status": "included"},
                 {"id": "SRC-0002", "status": "included"}]), encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "methods.md").write_text(
        "İki çalışma dahil edildi. <!-- PRISMA: included=2 -->\n", encoding="utf-8")
    code, out, _ = run("consistency_check.py")
    rep = json.loads(out)["prisma"]
    assert rep["mismatches"] == []
    assert rep["bound"] == ["included"]
