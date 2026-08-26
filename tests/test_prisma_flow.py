"""Tests for prisma_flow.py — the PRISMA 2020 flow renderer.

Two defect classes are pinned here, both found by a fresh-context review of a
real manuscript:

  * the full-text exclusion box borrowed SCREENING reasons when no full-text
    dict was supplied, printing three counts summing to 1328 under a box
    labelled "Excluded (n = 53)";
  * a review carrying studies forward from an earlier phase had to count those
    records twice — once as "not retrieved", again as "included" — because the
    flow had no outlet for them.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import prisma_flow as pf  # noqa: E402



# --- the full-text exclusion box lists FULL-TEXT reasons, or none -------------
def test_screening_reasons_never_land_in_the_fulltext_box():
    """Regression: the box announcing "Excluded (n = 53)" printed three counts
    summing to 1328 underneath, because it fell back to the all-stage reason
    dict when no full-text dict was supplied. A reader cannot tell a mislabelled
    box from a correct one, so a bare box is the safer output."""
    counts = {"identified": 1572, "duplicates": 0, "screened": 1572,
              "excluded_screening": 1328, "sought": 244, "not_retrieved": 94,
              "fulltext": 150, "excluded_fulltext": 53, "included": 97,
              "excluded_reasons": {"title screening": 591, "prescreen rule": 499,
                                   "abstract screening": 238}}
    tex = pf.tikz(dict(counts))
    assert "591" not in tex and "499" not in tex and "238" not in tex
    mmd = pf.mermaid(dict(counts))
    assert "591" not in mmd and "499" not in mmd and "238" not in mmd


def test_fulltext_reasons_are_printed_when_supplied():
    counts = {"identified": 1572, "duplicates": 0, "screened": 1572,
              "excluded_screening": 1328, "sought": 244, "not_retrieved": 94,
              "fulltext": 150, "excluded_fulltext": 53, "included": 97,
              "excluded_reasons": {"title screening": 591},
              "excluded_reasons_fulltext": {"index test not deep learning": 32,
                                            "no independent reference": 7,
                                            "no sens/spec at threshold": 12}}
    tex = pf.tikz(dict(counts))
    assert "32" in tex and "591" not in tex


# --- carried-forward box ------------------------------------------------------
def test_carried_forward_box_keeps_the_flow_consistent():
    """A review carrying studies forward otherwise counts them twice — once
    under "not retrieved" and again under "included"."""
    counts = {"identified": 1572, "duplicates": 0, "screened": 1572,
              "excluded_screening": 1328, "sought": 244, "not_retrieved": 91,
              "carried_forward_unretrieved": 3,
              "fulltext": 150, "excluded_fulltext": 53, "included": 97,
              "excluded_reasons": {}}
    assert pf.check(dict(counts)) == []


def test_without_the_box_the_same_numbers_are_inconsistent():
    counts = {"identified": 1572, "duplicates": 0, "screened": 1572,
              "excluded_screening": 1328, "sought": 244, "not_retrieved": 91,
              "fulltext": 150, "excluded_fulltext": 53, "included": 97,
              "excluded_reasons": {}}
    errs = pf.check(dict(counts))
    assert any("not_retrieved" in e for e in errs)


def test_absent_carried_forward_reduces_to_the_prisma_identity():
    """No project without the key may see its numbers or its message change."""
    counts = {"identified": 100, "duplicates": 0, "screened": 100,
              "excluded_screening": 40, "sought": 60, "not_retrieved": 10,
              "fulltext": 50, "excluded_fulltext": 20, "included": 30,
              "excluded_reasons": {}}
    assert pf.check(dict(counts)) == []
    bad = dict(counts, not_retrieved=11)
    assert pf.check(bad) == ["sought - not_retrieved != fulltext"]


def test_carried_forward_box_is_absent_when_zero():
    counts = {"identified": 100, "duplicates": 0, "screened": 100,
              "excluded_screening": 40, "sought": 60, "not_retrieved": 10,
              "fulltext": 50, "excluded_fulltext": 20, "included": 30,
              "excluded_reasons": {}}
    assert "Carried forward" not in pf.tikz(dict(counts))
    assert "Carried forward" not in pf.mermaid(dict(counts))


# --- the artefact on disk, not just the counters ------------------------------
def _counts():
    return {"identified": 1572, "duplicates": 0, "screened": 1572,
            "excluded_screening": 1328, "sought": 244, "not_retrieved": 91,
            "fulltext": 150, "excluded_fulltext": 53, "included": 97,
            "carried_forward_unretrieved": 3, "excluded_reasons": {},
            "excluded_reasons_fulltext": {"no reference standard": 7}}


def test_verify_passes_on_the_file_it_just_rendered(tmp_path):
    c = _counts()
    (tmp_path / "prisma.tex").write_text(pf.tikz(c), encoding="utf-8")
    (tmp_path / "prisma.mmd").write_text(pf.mermaid(c), encoding="utf-8")
    assert pf.verify_artifacts(c, tmp_path) == []


def test_verify_catches_a_diagram_copied_from_somewhere_else(tmp_path):
    """The defect this exists for: check() validated the counters while a build
    step copied a diagram carrying a DIFFERENT, abandoned flow over the
    generated one. Every counter identity held; the figure the typesetter read
    contradicted every number in the text."""
    c = _counts()
    stale = dict(c, identified=170, screened=166, duplicates=4,
                 excluded_screening=19, sought=147, not_retrieved=36,
                 fulltext=111, excluded_fulltext=11, included=100,
                 carried_forward_unretrieved=0)
    (tmp_path / "prisma.tex").write_text(pf.tikz(stale), encoding="utf-8")
    (tmp_path / "prisma.mmd").write_text(pf.mermaid(stale), encoding="utf-8")
    errs = pf.verify_artifacts(c, tmp_path)
    assert len(errs) == 2
    assert "prisma.tex" in errs[0] and "170" in errs[0] and "1572" in errs[0]


def test_verify_reports_a_missing_artefact_rather_than_passing(tmp_path):
    """A figure the build never produced must not read as verified: absence is
    the one state where "no mismatch found" is most misleading."""
    errs = pf.verify_artifacts(_counts(), tmp_path)
    assert len(errs) == 2
    assert all("not on disk" in e for e in errs)


def test_verify_notices_a_single_moved_box(tmp_path):
    """Staleness is rarely wholesale. One counter edited in the source and not
    re-rendered is the common case, and it must fail exactly like the wholesale
    one."""
    c = _counts()
    (tmp_path / "prisma.tex").write_text(pf.tikz(dict(c, included=96)),
                                         encoding="utf-8")
    (tmp_path / "prisma.mmd").write_text(pf.mermaid(c), encoding="utf-8")
    errs = pf.verify_artifacts(c, tmp_path)
    assert len(errs) == 1 and "prisma.tex" in errs[0]


# --- --counts-file: argv is not a safe channel for a non-ASCII reason ---------
def test_counts_file_preserves_a_non_ascii_reason(run, tmp_path):
    """Why the flag exists: the same object passed through argv came back as
    "taþymayan" on a Turkish console codepage, and the mangled reason was
    typeset into the figure with no error anywhere."""
    import json
    reason = "ön elemede yöntem/konu terimi taşımayan"
    payload = {"_why": "counters live beside the prose that explains them",
               "counts": {**_counts(),
                          "excluded_reasons_fulltext": {reason: 53}}}
    (tmp_path / "counts.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "out").mkdir()
    code, out, err = run("prisma_flow.py", "--counts-file", "counts.json",
                         "--out-dir", "out", "--json")
    assert code == 0, err
    assert reason in (tmp_path / "out" / "prisma.tex").read_text(encoding="utf-8")


def test_counts_file_and_counts_together_are_refused(run, tmp_path):
    (tmp_path / "counts.json").write_text("{}", encoding="utf-8")
    code, out, err = run("prisma_flow.py", "--counts", "{}",
                         "--counts-file", "counts.json")
    assert code == 1
    assert "not both" in (out + err)


def test_verify_exits_2_and_writes_nothing_when_the_artefact_is_stale(run, tmp_path):
    import json
    (tmp_path / "counts.json").write_text(
        json.dumps({"counts": _counts()}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "out").mkdir()
    stale = dict(_counts(), included=100, carried_forward_unretrieved=0)
    (tmp_path / "out" / "prisma.tex").write_text(pf.tikz(stale), encoding="utf-8")
    (tmp_path / "out" / "prisma.mmd").write_text(pf.mermaid(stale), encoding="utf-8")
    before = (tmp_path / "out" / "prisma.tex").read_text(encoding="utf-8")
    code, out, err = run("prisma_flow.py", "--counts-file", "counts.json",
                         "--out-dir", "out", "--verify", "--json")
    assert code == 2, err
    payload = json.loads(out)
    assert payload["artifact_errors"] and payload["written"] == []
    assert (tmp_path / "out" / "prisma.tex").read_text(encoding="utf-8") == before


# --- box labels follow the manuscript's language ------------------------------
def test_default_labels_are_english(tmp_path):
    c = _counts()
    assert "Records identified" in pf.tikz(c)
    assert "Studies included" in pf.mermaid(c)


def test_labels_file_replaces_box_labels_in_both_renderers(tmp_path):
    """Why this exists: the kit's own example review printed 'Records
    identified' above 'indeks test derin öğrenme değil'. The figure is part of
    the manuscript, so it follows the manuscript's language."""
    import json
    (tmp_path / "tr.json").write_text(json.dumps(
        {"identified": "Tanımlanan kayıt", "included": "Dahil edilen çalışma"},
        ensure_ascii=False), encoding="utf-8")
    labels = pf.resolve_labels(str(tmp_path / "tr.json"))
    c = _counts()
    for render in (pf.tikz, pf.mermaid):
        out = render(c, labels)
        assert "Tanımlanan kayıt" in out
        assert "Dahil edilen çalışma" in out
        assert "Records identified" not in out
        # An unnamed key keeps its English default — a partial file is valid.
        assert "Reports sought for retrieval" in out


def test_labels_file_with_an_unknown_key_is_refused(run, tmp_path):
    """A typo'd key would silently leave the English default in the figure, so
    it fails loudly instead: the whole point of the flag is that the reader
    should not find one stray English label."""
    import json
    (tmp_path / "counts.json").write_text(
        json.dumps({"counts": _counts()}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "bad.json").write_text(
        json.dumps({"identifed": "typo"}), encoding="utf-8")
    (tmp_path / "out").mkdir()
    code, out, err = run("prisma_flow.py", "--counts-file", "counts.json",
                         "--labels", "bad.json", "--out-dir", "out")
    assert code == 1
    assert "identifed" in (out + err)


def test_carried_forward_box_is_localised_too(tmp_path):
    """The carried-forward box is the kit's own deviation from PRISMA, so it is
    the label most likely to be forgotten when localising."""
    labels = dict(pf.DEFAULT_LABELS, carried_forward="Önceki fazdan taşınan")
    out = pf.tikz(_counts(), labels)
    assert "Önceki fazdan taşınan" in out
    assert "Carried forward" not in out


def test_verify_compares_against_the_same_labels(tmp_path):
    """--verify re-renders to compare; if it rendered with different labels than
    the file was written with, every localised project would read as stale."""
    labels = dict(pf.DEFAULT_LABELS, identified="Tanımlanan kayıt")
    c = _counts()
    (tmp_path / "prisma.tex").write_text(pf.tikz(c, labels), encoding="utf-8")
    (tmp_path / "prisma.mmd").write_text(pf.mermaid(c, labels), encoding="utf-8")
    assert pf.verify_artifacts(c, tmp_path, labels) == []
