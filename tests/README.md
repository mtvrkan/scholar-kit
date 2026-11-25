# tests/ — what covers what

`python -m pytest` runs everything. This file answers the other question: **which
tests protect behaviour X?**

Most files are named after the module they exercise, so for those the filename is
the answer (`test_phase_gate_hook.py` → `phase_gate.py`). The regression suites
are the exception, and the reason is worth stating rather than apologising for.

## Why some files are named after a review round

`test_remediation_<date>_<round>.py` holds the regressions locked in by one
independent review pass. Each round's findings genuinely span several subsystems
at once — round 9 alone fixed `_shell_write_sink.py`, `phase_gate.py`,
`agent_write_scope.py`, `latex_build.sh` and `xlsx_export.py` — so renaming that
file after any single subsystem would misdescribe it, and splitting it per
subject would move ~290 tests plus their per-file helpers (`_run_hook`, `_hit`,
`_find_git_bash`, …) for no gain a lookup table does not already give.

The round name is also load-bearing provenance: `DECISIONS.md` cites these files
by name from the entry that explains *why* each test exists. Renaming them
breaks that trail.

So the mapping is declared instead — once, in `tests/conftest.py::AREAS` — and
turned into real pytest markers.

## Selecting by subject

```bash
python -m pytest -m hooks                 # every enforcement-hook test, all files
python -m pytest -m "citation and not live"
python -m pytest -m "hooks or corelib"
```

## Areas

| Area | What it covers |
|---|---|
| `hooks` | The enforcement layer: `protect_data_files`, `phase_gate`, `agent_write_scope`, `template_supremacy_gate`, `cite_warn`, `session_status`, and the shared `_shell_write_sink` / `_project_scope` / `_degrade` helpers; `codex`: the same gates reached from OpenAI Codex through `.codex/hooks/codex_adapter.py` (`test_codex_adapter.py`) — plus the OS-permission half of Invariant 6 (`lib_common.protect/unprotect`), which is the layer that needs no pattern to recognise a write. Invariants 3 and 6 live or die here. |
| `citation` | The zero-fabrication chain: `doi2bib`, `bib_doctor`, `cite_audit`, `citation_triangulate`, `evidence_db`, `registry_db`, `write_verify_status`. |
| `build` | Output production: `latex_build.sh`, `docx_build.sh`, `docx_style_check`, `template_compliance`, `make_reference_docx`, `pdf2md`. |
| `export` | Deliverables short of the final manuscript: `xlsx_export`, `prisma_flow`, `word_budget`. |
| `lint` | The advisory (WARN-only) checkers and their statistics: `claim_check`, `failure_scan`, `consistency_check`, `figure_check`, `temporal_check`, `tr_style_check`, `evidence_funnel`, `meta_analysis`, `calibration_score`, `screening_score`, `venue_check`, `venue_fit`, `compliance_gen`, `lib_stats`. |
| `kitmeta` | The kit about itself: `validate_kit`, plugin/marketplace manifests (Claude Code and Codex), `codex_sync` and the generated Codex files it must keep current, installer first-run, `patch_hook_interpreter`, `run_evals`, `skill_routing_eval`, `token_report`, `update_data`, and the governance-doc assertions that bind every published number to a test. |
| `corelib` | Shared primitives every script depends on: `lib_common`, path validation, build-script path guards. |
| `empirical` | The path from data to a number: `dataset_db`, `dataset_fetch`, `collection_check`, `collect_run`, `train_runner`, `experiment_db`, `leakage_check`, `results_table`, `results_figure`. What these pin is mostly refusals — an unread licence, an undeclared field, an unregistered dataset, a seedless run — because that is where an empirical paper goes wrong silently. |
| `pipeline` | End-to-end contracts: the `/slr` pipeline, and the whole draft -> gate -> submission-check path run against ONE realistic project (`test_pipeline_end_to_end.py`). The second exists because twelve defects once passed the entire unit suite and failed on first real use — the units were right about the inputs they were given and wrong about the inputs a real manuscript has. |

A file may sit in several areas; that is the normal case for a regression suite
and is not a defect.

## Adding tests

- **New behaviour in an existing module** → extend that module's own test file.
- **A finding from a review pass that spans subsystems** → a new
  `test_remediation_<YYYY_MM_DD>_<tag>.py`, and add it to every area it touches
  in `conftest.AREAS`.
- **Anything else** → name the file after the module under test, not after the
  date you wrote it.

`tests/test_tests_index.py` enforces the parts of this that can be enforced:
every test file appears in `AREAS`, every file named in `AREAS` exists, every
area is documented in the table above, and a date-named file outside the
`test_remediation_*` convention fails the build.
