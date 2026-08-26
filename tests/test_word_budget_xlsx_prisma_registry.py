import json

import xlsx_export


PROJECT = """# PROJECT.md
- **Type:** empirical-imrad
- **Research questions:**
  - RQ1: Does CNN beat classical methods?
  - RQ2: Which preprocessing helps most?
- **Word budget (total):** 6500
"""


# ---------- word_budget ----------

def test_word_budget_counts_and_deviation(run, tmp_path):
    (tmp_path / "PROJECT.md").write_text(PROJECT, encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "introduction.md").write_text("# Intro\n" + ("word " * 975), encoding="utf-8")
    code, out, _ = run("word_budget.py")
    assert code == 0
    rep = json.loads(out)
    intro = next(r for r in rep["sections"] if r["section"] == "introduction")
    assert intro["budget"] == 975  # 15% of 6500
    assert abs(intro["deviation_pct"]) <= 1


def test_word_budget_strict_flags_overrun(run, tmp_path):
    (tmp_path / "PROJECT.md").write_text(PROJECT, encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "methods.md").write_text("word " * 3000, encoding="utf-8")  # budget 1625
    code, out, _ = run("word_budget.py", "--strict")
    assert code == 2
    assert json.loads(out)["off_budget"] == ["methods.md"]


def test_word_budget_dies_on_malformed_total(run, tmp_path):
    # The "Word budget (total):" line IS present but unparseable — must fail
    # loudly, not silently degrade to budget_total: null (which would mask
    # every section's deviation_pct silently reading as None).
    (tmp_path / "PROJECT.md").write_text(
        "**Type:** imrad\n**Word budget (total):** ...\n", encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    code, out, err = run("word_budget.py")
    assert code == 1
    assert "Word budget" in err


def test_word_budget_still_works_with_valid_total(run, tmp_path):
    (tmp_path / "PROJECT.md").write_text(PROJECT, encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    code, out, err = run("word_budget.py", "--json")
    assert code == 0, err
    assert json.loads(out)["budget_total"] == 6500


def test_rq_trace(run, tmp_path):
    (tmp_path / "PROJECT.md").write_text(PROJECT, encoding="utf-8")
    outline = tmp_path / "outline"
    outline.mkdir()
    (outline / "outline.md").write_text("## 4.1 CNN vs classical (RQ1)\n", encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    code, out, _ = run("word_budget.py", "--rq-trace")
    rep = json.loads(out)
    assert code == 2  # RQ2 untraced
    assert rep["untraced"] == ["RQ2"]
    traced = next(r for r in rep["rqs"] if r["rq"] == "RQ1")
    assert traced["status"] == "traced"


# ---------- xlsx_export ----------

def test_xlsx_export_all_sheets(run, tmp_path, sample_registry, sample_cards):
    venues = tmp_path / "sources" / "venues.jsonl"
    venues.write_text(json.dumps({"display_name": "MSSP", "issn": "0888-3270",
                                  "wos_index": "SCIE", "quartile": "Q1", "scopus": True,
                                  "checked_at": "2026-07-01"}) + "\n", encoding="utf-8")
    code, out, _ = run("xlsx_export.py")
    assert code == 0, out
    rep = json.loads(out)
    assert set(rep["sheets"]) == {"screening", "extraction", "matrix", "venues", "prisma"}

    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "exports" / "literature-matrix.xlsx")
    ws = wb["screening"]
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref is not None
    assert ws.cell(row=1, column=1).font.bold
    assert ws.max_row == 4  # header + 3 registry rows
    vq = wb["venues"]
    q_cell = next(c for row in vq.iter_rows(min_row=2) for c in row if c.value == "Q1")
    assert q_cell.fill.fgColor.rgb.endswith("C6EFCE")  # Q1 conditional fill


def test_sanitize_sheet_title_replaces_illegal_chars_and_dedupes_collisions():
    from openpyxl import Workbook
    wb = Workbook()
    assert xlsx_export.sanitize_sheet_title("db-IEEE/Xplore", wb) == "db-IEEE-Xplore"
    wb.create_sheet("db-IEEE-Xplore")
    assert xlsx_export.sanitize_sheet_title("db-IEEE/Xplore", wb) == "db-IEEE-Xplore-2"


def test_xlsx_export_slr_sheet_survives_illegal_db_partition_name(run, tmp_path):
    # Regression: a registry's free-text `db` field (e.g. "IEEE/Xplore") built an
    # Excel-illegal sheet name ("\\ / * ? : [ ]") for the per-database partition
    # sheet and crashed the entire export instead of degrading gracefully.
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "id": "SRC-0001", "bib_key": "kaya2023deep", "title": "Deep learning",
        "year": 2023, "venue": "MSSP", "doi": "10.1016/x", "db": "IEEE/Xplore",
        "status": "included",
    }) + "\n", encoding="utf-8")

    code, out, err = run("xlsx_export.py", "--sheet", "slr")
    assert code == 0, err
    rep = json.loads(out)
    assert "slr" in rep["sheets"]
    assert any(s.startswith("db-IEEE-Xplore") for s in rep["sheets"])


# ---------- prisma_flow ----------

def test_prisma_consistent_counts(run, tmp_path):
    counts = {"identified": 341, "duplicates": 58, "screened": 283,
              "excluded_screening": 231, "fulltext": 52, "excluded_fulltext": 32,
              "excluded_reasons": {"predatory venue": 3}, "included": 20}
    code, out, _ = run("prisma_flow.py", "--counts", json.dumps(counts))
    assert code == 0
    rep = json.loads(out)
    assert rep["consistency_errors"] == []
    assert (tmp_path / "outline" / "prisma.mmd").exists()
    assert "n = 341" in (tmp_path / "outline" / "prisma.mmd").read_text(encoding="utf-8")
    assert (tmp_path / "outline" / "prisma.tex").exists()


def test_prisma_flags_inconsistency(run, tmp_path):
    counts = {"identified": 100, "duplicates": 10, "screened": 80,  # 100-10 != 80
              "excluded_screening": 60, "fulltext": 20, "excluded_fulltext": 5,
              "included": 15}
    code, out, _ = run("prisma_flow.py", "--counts", json.dumps(counts))
    assert code == 2
    assert json.loads(out)["consistency_errors"]


def test_prisma_flow_rejects_non_object_counts(run):
    code, out, err = run("prisma_flow.py", "--counts", "[1, 2, 3]")
    assert code == 1
    assert "ERROR" in err
    assert "must be a JSON object" in err


def test_prisma_flow_rejects_wrong_typed_count_value(run):
    counts = json.dumps({"identified": "ten", "duplicates": 2, "screened": 8,
                          "excluded_screening": 2, "fulltext": 6,
                          "excluded_fulltext": 1, "included": 5})
    code, out, err = run("prisma_flow.py", "--counts", counts)
    assert code == 1
    assert "ERROR" in err
    assert "must be integers" in err


def test_prisma_flow_rejects_non_object_excluded_reasons(run):
    counts = json.dumps({"identified": 10, "duplicates": 2, "screened": 8,
                          "excluded_screening": 2, "fulltext": 6,
                          "excluded_fulltext": 1, "included": 5,
                          "excluded_reasons": ["not", "a", "dict"]})
    code, out, err = run("prisma_flow.py", "--counts", counts)
    assert code == 1
    assert "ERROR" in err
    assert "excluded_reasons" in err


def test_prisma_counts_written_before_the_not_retrieved_box_still_validate(run):
    """Backward compatibility: a --counts JSON with no "not_retrieved"/"sought" is a
    flow where nothing was lost between seeking and assessing. It must keep passing,
    with the sought box collapsing onto fulltext rather than erroring."""
    counts = {"identified": 341, "duplicates": 58, "screened": 283,
              "excluded_screening": 231, "fulltext": 52, "excluded_fulltext": 32,
              "excluded_reasons": {}, "included": 20}
    code, out, _ = run("prisma_flow.py", "--counts", json.dumps(counts))
    assert code == 0
    rep = json.loads(out)
    assert rep["consistency_errors"] == []
    assert rep["counts"]["not_retrieved"] == 0
    assert rep["counts"]["sought"] == rep["counts"]["fulltext"] == 52


def test_prisma_derives_the_not_retrieved_box_from_unretrieved_records(run, tmp_path):
    """The defect this box exists to prevent: without it, a record that was sought and
    never obtained is counted as assessed for eligibility. 1 included + 1 excluded at
    full text + 3 unretrieved must report fulltext=2, NOT 5."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "fulltext",
             "reason": "no 2x2 at the referable threshold"}]
    rows += [{"id": f"SRC-000{i}", "status": "unretrieved", "stage": "fulltext",
              "reason": "access-restricted thesis"} for i in (3, 4, 5)]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    c = json.loads(out)["counts"]
    assert c["sought"] == 5
    assert c["not_retrieved"] == 3
    assert c["fulltext"] == 2
    assert json.loads(out)["consistency_errors"] == []
    mmd = (tmp_path / "outline" / "prisma.mmd").read_text(encoding="utf-8")
    assert "Reports not retrieved<br/>(n = 3)" in mmd
    assert "Reports assessed for eligibility<br/>(n = 2)" in mmd
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    assert "Reports not retrieved (n = 3)" in tex


def test_prisma_flags_a_broken_retrieval_arithmetic(run):
    counts = {"identified": 100, "duplicates": 0, "screened": 100,
              "excluded_screening": 40, "sought": 60, "not_retrieved": 10,
              "fulltext": 60,  # 60 - 10 != 60
              "excluded_fulltext": 5, "excluded_reasons": {}, "included": 55}
    code, out, _ = run("prisma_flow.py", "--counts", json.dumps(counts))
    assert code == 2
    assert "sought - not_retrieved != fulltext" in json.loads(out)["consistency_errors"]


def test_prisma_reason_box_counts_only_full_text_exclusions(run, tmp_path):
    """The box says "Excluded (n = <full-text count>)" and then lists reasons. It was
    listing reasons for EVERY exclusion, screening included, so the list could cover
    three times the number the box itself reported — the figure contradicting its own
    caption. PRISMA 2020 asks for reasons at the full-text stage; screening is a count."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "fulltext",
             "reason": "no independent reference standard"},
            {"id": "SRC-0003", "status": "excluded", "stage": "screening",
             "reason": "wrong target condition"},
            {"id": "SRC-0004", "status": "excluded", "stage": "screening",
             "reason": "not a diagnostic accuracy study"}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    c = json.loads(out)["counts"]
    assert c["excluded_fulltext"] == 1
    # The reported payload keeps every reason — a review may want the screening
    # ones too, and that contract predates this fix.
    assert sum(c["excluded_reasons"].values()) == 3
    # What the diagram reads must match what the diagram's box says.
    assert sum(c["excluded_reasons_fulltext"].values()) == c["excluded_fulltext"]
    assert "no independent reference standard" in c["excluded_reasons_fulltext"]
    assert "wrong target condition" not in c["excluded_reasons_fulltext"]
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    exf = next(l for l in tex.splitlines() if "(exf)" in l)
    assert "wrong target condition" not in exf


def test_prisma_flow_shortens_a_paragraph_length_exclusion_reason(run, tmp_path):
    """registry_db takes whatever --reason string the screener typed. One 400-character
    reason made the TikZ side box (text width 4.6cm) tall enough to squeeze the whole
    diagram into an unreadable ribbon — LaTeX warned about the overrun and emitted it
    anyway, so the failure arrived as a silently illegible figure."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    long_reason = "full text: no independent reference standard — " + ("labels inherited " * 40)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "fulltext",
             "reason": long_reason}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, _, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    exf = next(l for l in tex.splitlines() if "(exf)" in l)
    assert len(exf) < 400, "the exclusion box still carries the whole paragraph"
    assert "…" in exf, "truncation must be visible, not silent"
    # The box must still be anchored so it grows downward and cannot overlap the
    # not-retrieved / screening-exclusion boxes above it.
    assert "anchor=north west" in exf


def test_prisma_defers_surplus_reasons_but_keeps_the_arithmetic(run, tmp_path):
    """A review whose screener wrote a distinct sentence per exclusion arrives with as
    many categories as exclusions. Only a few are named; the rest must be reported as a
    count, so a reader adding the box's numbers still reaches the box's own total."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"}]
    rows += [{"id": f"SRC-01{i:02d}", "status": "excluded", "stage": "fulltext",
              "reason": f"distinct reason {i}"} for i in range(9)]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    assert json.loads(out)["counts"]["excluded_fulltext"] == 9
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    exf = next(l for l in tex.splitlines() if "(exf)" in l)
    assert "Excluded (n = 9)" in exf
    named = exf.count("distinct reason")
    assert named == 3, f"expected 3 named reasons, got {named}"
    assert "+6 further reason(s), 6 record(s)" in exf


def test_prisma_flow_converts_real_oserror_to_clean_die(run, tmp_path):
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"status": "included"}) + "\n", encoding="utf-8")
    (tmp_path / "build").write_text("not a directory", encoding="utf-8")  # blocks mkdir(parents=True)
    code, out, err = run("prisma_flow.py", "--registry", "sources/registry.jsonl", "--out-dir", "build")
    assert code == 1
    assert "Traceback" not in err
    assert "failed to write" in err


# ---------- registry_db ----------

def test_registry_add_dedup_and_status(run, tmp_path):
    rec = {"title": "Deep learning for bearing fault diagnosis", "doi": "10.1016/j.ymssp.2023.00001"}
    code, out, _ = run("registry_db.py", "add", "--json", json.dumps(rec))
    assert json.loads(out)["added"] == ["SRC-0001"]

    # same DOI → duplicate
    code, out, _ = run("registry_db.py", "add", "--json", json.dumps({**rec, "title": "Different title"}))
    assert json.loads(out)["duplicates"] == ["SRC-0002"]

    # near-identical title, no DOI → duplicate
    code, out, _ = run("registry_db.py", "add", "--json",
                       json.dumps({"title": "Deep learning for bearing fault diagnosis!"}))
    assert json.loads(out)["duplicates"] == ["SRC-0003"]

    code, out, _ = run("registry_db.py", "set-status", "SRC-0001", "included", "--reason", "core paper")
    assert json.loads(out)["status"] == "included"

    code, out, _ = run("registry_db.py", "stats")
    stats = json.loads(out)
    assert stats["by_status"] == {"included": 1, "duplicate": 2}


def test_registry_add_accepts_payload_flag_as_primary_alias(run, tmp_path):
    # --payload is the primary, unambiguous name for the add sub-command's
    # single-record input; --json (every other test in this file) is kept
    # only as a backward-compatible alias to the same dest.
    rec = {"title": "Deep learning for bearing fault diagnosis"}
    code, out, err = run("registry_db.py", "add", "--payload", json.dumps(rec))
    assert code == 0, err
    assert json.loads(out)["added"] == ["SRC-0001"]


def test_registry_accepts_unretrieved_and_still_refuses_an_invented_status(run):
    """"unretrieved" has to be expressible: without it, a report that was sought and
    never obtained can only be parked in "candidate" (where prisma_flow counts it as
    assessed) or forced into "excluded" (which asserts an eligibility judgement nobody
    made). The enum staying closed otherwise is what keeps the flow arithmetic honest."""
    run("registry_db.py", "add", "--json", json.dumps({"title": "An access-restricted thesis"}))
    code, out, err = run("registry_db.py", "set-status", "SRC-0001", "unretrieved",
                         "--reason", "YOK access restriction", "--stage", "fulltext")
    assert code == 0, err
    assert json.loads(out)["status"] == "unretrieved"

    code, _, err = run("registry_db.py", "set-status", "SRC-0001", "not_retrieved")
    assert code == 1
    assert "unretrieved" in err  # the error lists the real enum


def test_registry_db_rejects_non_object_payload_item_cleanly(run):
    code, out, err = run("registry_db.py", "add", "--stdin",
                         stdin=json.dumps(["not-an-object"]))
    assert code == 1
    assert "expected a JSON object" in err
    assert "Traceback" not in err


def test_registry_db_converts_real_oserror_to_clean_die(run, tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").mkdir()  # a directory, not a file
    code, out, err = run("registry_db.py", "add", "--json", json.dumps({"title": "t", "year": 2024}))
    assert code == 1
    assert "Traceback" not in err
    assert "failed to write" in err


def test_a_background_citation_is_kept_out_of_the_prisma_flow(run, tmp_path):
    """A review cites things the search never returned: the epidemiological
    background, a reporting guideline, a prior review cited for contrast.
    Invariant 1 forces them into the register, and `identified = len(registry)`
    then counted them as records the search identified — inflating every box
    downstream. `scope: "background"` takes them out of the flow and the count
    of what was taken out is reported, so the flow and the register can still be
    reconciled by a reader."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "screening", "reason": "off topic"},
            {"id": "SRC-0003", "status": "included", "scope": "background"},
            {"id": "SRC-0004", "status": "included", "scope": "background"}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    c = json.loads(out)["counts"]
    assert c["identified"] == 2, "background records must not count as identified"
    assert c["background_excluded_from_flow"] == 2
    assert c["included"] == 1
    assert json.loads(out)["consistency_errors"] == []


def test_a_registry_with_no_scope_field_flows_exactly_as_before(run, tmp_path):
    """The default is in-flow: no existing project's numbers may move."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "screening", "reason": "x"}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    c = json.loads(out)["counts"]
    assert c["identified"] == 2 and c["background_excluded_from_flow"] == 0


def test_prisma_groups_reasons_by_category_when_the_record_carries_one(run, tmp_path):
    """PRISMA asks for reasons GROUPED with counts; a register holds one free-text
    reason per record. A conscientious screener writes a distinct sentence for every
    exclusion, so the box ends up listing eleven categories for eleven records — a
    register dump, not a flow diagram. `reason_category` lets the record carry both."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"}]
    rows += [{"id": f"SRC-01{i:02d}", "status": "excluded", "stage": "fulltext",
              "reason": f"full text, record {i}: labels inherited from a public benchmark",
              "reason_category": "No independent reference standard"} for i in range(4)]
    rows += [{"id": "SRC-0200", "status": "excluded", "stage": "fulltext",
              "reason": "full text: classical image processing, not deep learning",
              "reason_category": "Index test not deep learning"}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    c = json.loads(out)["counts"]
    # The reported payload still holds every distinct free-text reason...
    assert len(c["excluded_reasons"]) == 5
    # ...while the diagram groups on the category and still totals correctly.
    assert c["excluded_reasons_fulltext"] == {"No independent reference standard": 4,
                                              "Index test not deep learning": 1}
    assert sum(c["excluded_reasons_fulltext"].values()) == c["excluded_fulltext"]
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    exf = next(l for l in tex.splitlines() if "(exf)" in l)
    assert "No independent reference standard: 4" in exf
    assert "labels inherited" not in exf, "the register's raw text reached the figure"


def test_prisma_falls_back_to_free_text_without_a_category(run, tmp_path):
    """No existing project's diagram changes: a record with no reason_category is
    grouped on its free-text reason exactly as before."""
    registry = tmp_path / "sources" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    rows = [{"id": "SRC-0001", "status": "included"},
            {"id": "SRC-0002", "status": "excluded", "stage": "fulltext",
             "reason": "no independent reference standard"}]
    registry.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    code, out, _ = run("prisma_flow.py", "--registry", "sources/registry.jsonl")
    assert code == 0
    c = json.loads(out)["counts"]
    assert c["excluded_reasons_fulltext"] == {"no independent reference standard": 1}
