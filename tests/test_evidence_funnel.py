"""Tests for evidence_funnel.py — the cards -> sources -> cited -> bib funnel.

Motivated by the recurring "100+ cards but only 19 references — is it broken?"
confusion. The funnel makes the legitimate narrowing explicit and flags only the
actionable case: an INCLUDED external source whose card was never cited.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evidence_funnel as ef  # noqa: E402


def _mk(tmp_path, cards, registry, drafts, bib):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "cards.jsonl").write_text(
        "\n".join(json.dumps(c) for c in cards) + ("\n" if cards else ""), encoding="utf-8")
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").write_text(
        "\n".join(json.dumps(r) for r in registry) + ("\n" if registry else ""), encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    for name, text in drafts.items():
        (tmp_path / "drafts" / name).write_text(text, encoding="utf-8")
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text(bib, encoding="utf-8")
    return (tmp_path / "evidence" / "cards.jsonl", tmp_path / "sources" / "registry.jsonl",
            tmp_path / "drafts", tmp_path / "bib" / "references.bib")


def test_funnel_counts_and_string(tmp_path):
    paths = _mk(
        tmp_path,
        cards=[
            {"id": "EV-0001", "source": "kaya2023deep", "type": "finding"},
            {"id": "EV-0002", "source": "kaya2023deep", "type": "method"},
            {"id": "EV-0003", "source": "demir2022x", "type": "finding"},
        ],
        registry=[
            {"id": "SRC-0001", "bib_key": "kaya2023deep", "status": "included"},
            {"id": "SRC-0002", "bib_key": "demir2022x", "status": "included"},
        ],
        drafts={"results.md": "As shown [@kaya2023deep], accuracy improved."},
        bib="@article{kaya2023deep, title={X}, verified={true}}\n")
    r = ef.build_funnel(*paths)
    assert r["cards"]["total"] == 3
    assert r["cards"]["distinct_sources"] == 2
    assert r["registry"]["included"] == 2
    assert r["cited_in_text"] == 1
    assert r["bib_entries"] == 1
    assert "3 cards -> 2 distinct sources" in r["funnel"]


def test_actionable_orphan_is_included_but_uncited(tmp_path):
    paths = _mk(
        tmp_path,
        cards=[{"id": "EV-0003", "source": "demir2022x", "type": "finding"}],
        registry=[{"id": "SRC-0002", "bib_key": "demir2022x", "status": "included"}],
        drafts={"results.md": "No citation here."},
        bib="")
    r = ef.build_funnel(*paths)
    assert [o["id"] for o in r["orphan_cards"]] == ["EV-0003"]
    assert r["expected_uncited"] == []


def test_own_result_card_is_expected_not_orphan(tmp_path):
    paths = _mk(
        tmp_path,
        cards=[{"id": "EV-0009", "source": "own-analysis", "type": "own-result"}],
        registry=[],
        drafts={"results.md": "Our model reached AUC 0.81 (Table 1)."},
        bib="")
    r = ef.build_funnel(*paths)
    assert r["orphan_cards"] == []
    assert [o["id"] for o in r["expected_uncited"]] == ["EV-0009"]


def test_own_source_prefix_card_is_expected(tmp_path):
    # A non-own-result card sourced to the own-analysis anchor (e.g. a method
    # card describing the study's own pipeline) is still own work, not an orphan.
    paths = _mk(
        tmp_path,
        cards=[{"id": "EV-0010", "source": "own-analysis", "type": "method"}],
        registry=[],
        drafts={"methods.md": "We used stratified splits."},
        bib="")
    r = ef.build_funnel(*paths)
    assert r["orphan_cards"] == []
    assert len(r["expected_uncited"]) == 1


def test_excluded_source_card_is_expected(tmp_path):
    paths = _mk(
        tmp_path,
        cards=[{"id": "EV-0021", "source": "retracted2024", "type": "finding"}],
        registry=[{"id": "SRC-0021", "bib_key": "retracted2024", "status": "excluded"}],
        drafts={"discussion.md": "A retracted study once claimed near-perfect metrics."},
        bib="")
    r = ef.build_funnel(*paths)
    assert r["orphan_cards"] == []
    assert [o["id"] for o in r["expected_uncited"]] == ["EV-0021"]


def test_src_id_source_resolves_to_bib_key(tmp_path):
    # A card that references its source by SRC id (before a bib_key was assigned)
    # must resolve to the bib_key to be recognized as cited.
    paths = _mk(
        tmp_path,
        cards=[{"id": "EV-0001", "source": "SRC-0001", "type": "finding"}],
        registry=[{"id": "SRC-0001", "bib_key": "kaya2023deep", "status": "included"}],
        drafts={"results.md": "See [@kaya2023deep]."},
        bib="@article{kaya2023deep, title={X}, verified={true}}\n")
    r = ef.build_funnel(*paths)
    assert r["orphan_cards"] == []  # resolved via SRC id -> bib_key -> cited


def test_cli_report_only_exit_zero(tmp_path):
    _mk(tmp_path,
        cards=[{"id": "EV-0003", "source": "demir2022x", "type": "finding"}],
        registry=[{"id": "SRC-0002", "bib_key": "demir2022x", "status": "included"}],
        drafts={"results.md": "no cite"}, bib="")
    p = subprocess.run([sys.executable, str(SCRIPTS / "evidence_funnel.py")],
                       cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0
    assert json.loads(p.stdout)["orphan_cards"]
