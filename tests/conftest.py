"""Shared fixtures for scholar-kit script tests. Live-network tests are marked
@pytest.mark.live and skipped unless RUN_LIVE=1 (plan: mocked + 1 live smoke each)."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


# ---------------------------------------------------------------------------
# Subject areas — the single source of truth for "which tests cover X?"
#
# Most test files are named after the module they exercise, so the filename
# already answers that question. The regression suites are not: they are named
# after the REVIEW ROUND that produced them (test_remediation_<date>_<round>),
# because each round's findings genuinely span several subsystems at once and
# renaming one of those files after a single subsystem would be a lie about
# what it holds. Splitting them per subject was considered and rejected: the
# helpers (`_run_hook`, `_hit`, `_find_git_bash`, …) are per-file and ~290
# tests would move, for no gain a lookup table does not already give.
#
# So the map is declared here instead, once, and `pytest_collection_modifyitems`
# turns it into real pytest markers:
#
#     python -m pytest -m hooks        # every enforcement-hook test, all files
#     python -m pytest -m "citation and not live"
#
# tests/README.md is the human-readable rendering of this same dict, and
# tests/test_tests_index.py fails the build if the two drift apart, if a test
# file is missing from the map, or if the map names a file that no longer
# exists. See tests/README.md for what each area means.
AREAS = {
    "hooks": [
        "test_agent_write_scope_hook.py",
        "test_cite_warn_hook.py",
        "test_codex_adapter.py",
        "test_degrade_visibility.py",
        "test_enforcement_notice_hook.py",
        "test_hook_change_records.py",
        "test_phase_gate_hook.py",
        "test_pipeline_end_to_end.py",
        "test_project_scope_hook.py",
        "test_provenance.py",
        "test_protect_data_files_hook.py",
        "test_protected_file_permissions.py",
        "test_session_status_hook.py",
        "test_shell_write_sink.py",
        "test_template_supremacy_gate_hook.py",
        "test_remediation_2026_07_02.py",
        "test_remediation_2026_07_04_fixes.py",
        "test_remediation_2026_07_04_round2.py",
        "test_remediation_2026_07_04_round3.py",
        "test_remediation_2026_07_04_round8.py",
        "test_remediation_2026_07_04_round9.py",
        "test_remediation_2026_07_04_round10.py",
        "test_remediation_2026_07_04_round11.py",
        "test_remediation_2026_07_05_hook_review.py",
        "test_remediation_2026_07_05_round12.py",
    ],
    "citation": [
        "test_bib_and_cite.py",
        "test_citation_triangulate.py",
        "test_doi2bib.py",
        "test_evidence_db.py",
        "test_dataset_db.py",
        "test_experiment_db.py",
        "test_manuscript_import.py",
        "test_review_letter.py",
        "test_referee_report.py",
        "test_coauthor_diff.py",
        "test_deposit_pack.py",
        "test_dossier_score.py",
        "test_submission_pack.py",
        "test_gold_citations.py",
        "test_library_import.py",
        "test_write_verify_status.py",
        "test_word_budget_xlsx_prisma_registry.py",
        "test_prisma_flow.py",
        "test_remediation_2026_07_02.py",
        "test_remediation_2026_07_04_fixes.py",
        "test_remediation_2026_07_04_round2.py",
        "test_remediation_2026_07_04_round3.py",
        "test_remediation_2026_07_04_round4.py",
        "test_remediation_2026_07_04_round10.py",
        "test_remediation_2026_07_04_round11.py",
        "test_remediation_2026_07_05_kit_improvements.py",
        "test_remediation_2026_07_05_round12.py",
    ],
    "build": [
        "test_build_scripts_path_guard.py",
        "test_pipeline_end_to_end.py",
        "test_template_compliance.py",
        "test_remediation_2026_07_03_review.py",
        "test_remediation_2026_07_04_review.py",
        "test_remediation_2026_07_04_round3.py",
        "test_remediation_2026_07_04_round4.py",
        "test_remediation_2026_07_04_round9.py",
    ],
    "export": [
        "test_replication_pack.py",
        "test_deposit_pack.py",
        "test_dmp_gen.py",
        "test_proposal_check.py",
        "test_word_budget_xlsx_prisma_registry.py",
        "test_remediation_2026_07_02.py",
        "test_remediation_2026_07_03_review.py",
        "test_remediation_2026_07_04_fixes.py",
        "test_remediation_2026_07_04_round2.py",
        "test_remediation_2026_07_04_round4.py",
        "test_remediation_2026_07_04_round9.py",
        "test_remediation_2026_07_04_round10.py",
        "test_remediation_2026_07_04_round11.py",
    ],
    "lint": [
        "test_audit_regressions.py",
        "test_calibration_score.py",
        "test_claim_check.py",
        "test_draft_stability.py",
        "test_compliance_gen.py",
        "test_consistency_check.py",
        "test_draft_integrity.py",
        "test_evidence_funnel.py",
        "test_failure_scan.py",
        "test_figure_check.py",
        "test_lib_stats.py",
        "test_collection_check.py",
        "test_coauthor_diff.py",
        "test_ethics_pack.py",
        "test_proposal_check.py",
        "test_referee_report.py",
        "test_teaching.py",
        "test_frontmatter_check.py",
        "test_leakage_check.py",
        "test_overlap_check.py",
        "test_meta_analysis.py",
        "test_review_stability.py",
        "test_screening_score.py",
        "test_temporal_check.py",
        "test_tr_style_check.py",
        "test_translation_check.py",
        "test_venue_check.py",
        "test_venue_fit.py",
        "test_run_evals.py",
        "test_remediation_2026_07_05_hook_review.py",
        "test_remediation_2026_07_05_kit_improvements.py",
        "test_remediation_2026_08_15_axes_review.py",
    ],
    "kitmeta": [
        "test_changelog_scope.py",
        "test_codex_sync.py",
        "test_enforcement_notice_hook.py",
        "test_first_run.py",
        "test_governance_docs.py",
        "test_hook_change_records.py",
        # `test_site.py` is added below, and only when it is here: the website
        # lives on its own branch, so this file exists on one and not the other.
        # A static entry would satisfy "every file is mapped" on the branch that
        # has it and fail "every mapped file exists" on the branch that does
        # not — the two index tests pull in opposite directions for a file whose
        # absence is correct rather than a rename someone forgot to follow.
        "test_kit_meta_scripts.py",
        "test_lint_and_ci_config.py",
        "test_patch_hook_interpreter.py",
        "test_plugin_manifest.py",
        "test_routing_eval_currency.py",
        "test_run_evals.py",
        "test_skill_cli_contracts.py",
        "test_tests_index.py",
        "test_token_report.py",
        "test_update_data.py",
        "test_remediation_2026_07_02.py",
        "test_remediation_2026_07_03_review.py",
        "test_remediation_2026_07_04_fixes.py",
        "test_remediation_2026_07_04_review.py",
        "test_remediation_2026_07_04_round8.py",
        "test_remediation_2026_07_04_round9.py",
        "test_remediation_2026_07_04_round10.py",
        "test_remediation_2026_07_05_hook_review.py",
        "test_remediation_2026_07_05_round12.py",
        "test_remediation_2026_08_13_review3.py",
        "test_remediation_2026_08_15_axes_review.py",
    ],
    "corelib": [
        "test_lib_common.py",
        "test_provenance.py",
        "test_remediation_2026_08_13_review3.py",
        "test_protected_file_permissions.py",
        "test_path_validation.py",
        "test_build_scripts_path_guard.py",
        "test_remediation_2026_07_04_fixes.py",
        "test_remediation_2026_07_04_round11.py",
        "test_remediation_2026_07_05_hook_review.py",
    ],
    "empirical": [
        "test_collection_check.py",
        "test_collect_run.py",
        "test_dataset_db.py",
        "test_dataset_fetch.py",
        "test_dmp_gen.py",
        "test_ethics_pack.py",
        "test_experiment_db.py",
        "test_leakage_check.py",
        "test_results_table.py",
        "test_train_runner.py",
    ],
    "pipeline": [
        "test_pipeline_end_to_end.py",
        "test_slr_pipeline.py",
    ],
}


# Only where the site's suite is checked out — see the note in "kitmeta" above.
if (Path(__file__).parent / "test_site.py").exists():
    AREAS["kitmeta"].append("test_site.py")

def pytest_configure(config):
    config.addinivalue_line("markers", "live: hits real network; needs RUN_LIVE=1")
    for area in AREAS:
        config.addinivalue_line(
            "markers", f"{area}: subject area (see tests/README.md); declared in conftest.AREAS")


def kit_project_cwd() -> str:
    """A throwaway directory that the enforcement hooks recognise as a project.

    The hooks no-op outside a Scholar-Kit project (`.claude/hooks/_project_scope.py`),
    because as a plugin they run in every session and gate on names — `drafts/`,
    `build/`, `references.bib` — that are ordinary everywhere else.

    Hook tests that pass no `cwd` used to inherit pytest's, which is the KIT
    root: not a paper project, and rightly not treated as one. They need a
    directory that is. Created once per pytest process and reused; it holds only
    the marker file, so tests that also write state still pass their own
    `tmp_path` and touch the marker there.
    """
    global _KIT_PROJECT_CWD
    if _KIT_PROJECT_CWD is None:
        d = Path(tempfile.mkdtemp(prefix="scholar-kit-hooktest-"))
        (d / "PROJECT.md").touch()
        _KIT_PROJECT_CWD = str(d)
    return _KIT_PROJECT_CWD


_KIT_PROJECT_CWD = None


_AREAS_BY_FILE = {}
for _area, _files in AREAS.items():
    for _f in _files:
        _AREAS_BY_FILE.setdefault(_f, []).append(_area)


def pytest_collection_modifyitems(config, items):
    # Area markers are applied FIRST and unconditionally — before the live-skip
    # early return below, which would otherwise leave `-m hooks` silently empty
    # whenever RUN_LIVE=1.
    for item in items:
        for area in _AREAS_BY_FILE.get(Path(str(item.fspath)).name, ()):
            item.add_marker(getattr(pytest.mark, area))

    if os.environ.get("RUN_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="live network test — set RUN_LIVE=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def run(tmp_path):
    """Run a scholar-kit script as a subprocess inside tmp_path; return (code, stdout, stderr)."""
    import subprocess

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    def _run(script, *args, stdin=None):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            input=stdin, capture_output=True, text=True, cwd=tmp_path,
            encoding="utf-8", errors="replace", env=env)
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    return _run


@pytest.fixture
def sample_cards(tmp_path):
    cards = [
        {"id": "EV-0001", "source": "kaya2023deep", "type": "finding",
         "claim": "CNN beats SVM on bearing faults", "strength": 4,
         "tags": ["rq1", "cnn"], "metrics": {"F1": 0.93, "dataset": "CWRU"}, "lang": "en"},
        {"id": "EV-0002", "source": "demir2022vibration", "type": "method",
         "claim": "Wavelet preprocessing pipeline", "strength": 3,
         "tags": ["rq2"], "conflicts_with": ["EV-0001"], "lang": "tr"},
    ]
    p = tmp_path / "evidence" / "cards.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join(json.dumps(c) for c in cards) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def sample_bib(tmp_path):
    bib = """@article{kaya2023deep,
  title = {Deep learning for bearing fault diagnosis},
  author = {Kaya, Ahmet and Yilmaz, Berk},
  journal = {Mechanical Systems and Signal Processing},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
  verified = {true},
}

@article{demir2022vibration,
  title = {Vibration analysis with wavelets},
  author = {Demir, Cem},
  journal = {Journal of Sound and Vibration},
  year = {2022},
  doi = {https://doi.org/10.1016/j.jsv.2022.00002},
  verified = {true},
}
"""
    p = tmp_path / "bib" / "references.bib"
    p.parent.mkdir(parents=True)
    p.write_text(bib, encoding="utf-8")
    return p


@pytest.fixture
def sample_registry(tmp_path):
    recs = [
        {"id": "SRC-0001", "title": "Deep learning for bearing fault diagnosis",
         "authors": ["Kaya, A."], "year": 2023, "venue": "MSSP", "doi": "10.1016/j.ymssp.2023.00001",
         "lang": "en", "relevance_score": 0.95, "status": "included", "bib_key": "kaya2023deep",
         "venue_meta": {"wos_index": "SCIE", "quartile": "Q1", "scopus": True}},
        {"id": "SRC-0002", "title": "Vibration analysis with wavelets", "year": 2022,
         "lang": "en", "relevance_score": 0.7, "status": "excluded", "reason": "no metrics reported"},
        {"id": "SRC-0003", "title": "Rulman ariza teshisi", "year": 2021, "lang": "tr",
         "relevance_score": 0.6, "status": "candidate"},
    ]
    p = tmp_path / "sources" / "registry.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    return p
