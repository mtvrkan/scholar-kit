#!/usr/bin/env python3
"""validate_kit.py — structural integrity check for the scholar-kit installation.

Checks:
  * every .claude/skills/*/SKILL.md has YAML frontmatter with name + description,
    body < 520 lines (500 nominal cap + ~4% buffer), and workflow commands
    carry disable-model-invocation: true
  * every .claude/agents/*.md has name/description/tools/model frontmatter and the
    4 contract blocks (ROLE / INPUT CONTRACT / PROCEDURE / OUTPUT CONTRACT)
  * scripts/ has all expected tools; hooks referenced in settings.json exist
  * templates: CSL styles present, reference.docx present
  * broken relative links inside SKILL.md files (reference/... targets exist)

Usage: python scripts/validate_kit.py [--json]     (run from kit root)
Exit codes: 0 clean · 2 problems found.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die
from lib_common import parse_frontmatter as frontmatter  # noqa: F401  (also applies utf-8 guard)

ROOT = Path(__file__).parent.parent
WORKFLOW_COMMANDS = {
    "new-project", "lit-review", "journal-check", "outline", "draft", "analyze-data",
    "verify-citations", "critique", "revise", "export-excel", "ingest-template",
    "submit-check", "status", "defense-prep", "slr",
    "ethics-application", "dmp", "merge-coauthor", "review-paper", "deposit",
    "proposal", "project-report", "dossier",
    "syllabus", "exam", "rubric", "accreditation", "supervision",
}
KNOWLEDGE_SKILLS = {
    "paper-types", "thesis-structure", "citation-styles", "literature-review",
    "evidence-cards", "academic-writing", "reporting-guidelines", "ml-research",
    "comparative-analysis", "latex-thesis", "docx-output",
}
AGENTS = {
    "literature-scout", "source-analyst", "citation-verifier", "methodology-advisor",
    "data-scientist", "reviewer-critic", "style-auditor", "format-engineer",
    "qa-auditor",
}
SCRIPTS = ["evidence_db.py", "registry_db.py", "doi2bib.py", "venue_check.py",
           "bib_doctor.py", "cite_audit.py", "word_budget.py", "xlsx_export.py",
           "prisma_flow.py", "latex_build.sh", "docx_build.sh", "update_data.py", "pdf2md.py",
           "make_reference_docx.py", "docx_style_check.py", "template_compliance.py",
           "qa_inspect.py",
           "patch_hook_interpreter.py", "skill_routing_eval.py", "extract_skill_descriptions.py",
           "codex_sync.py",
           "write_verify_status.py", "claim_check.py", "failure_scan.py", "run_evals.py", "calibration_score.py", "screening_score.py", "venue_fit.py", "meta_analysis.py", "tr_style_check.py", "token_report.py",
           "provenance.py", "draft_stability.py",
           "dataset_fetch.py", "collect_run.py", "train_runner.py", "results_table.py",
           "results_figure.py", "manuscript_import.py", "translation_check.py",
           "ethics_pack.py", "dmp_gen.py", "coauthor_diff.py", "referee_report.py",
           "deposit_pack.py", "proposal_check.py", "dossier_score.py",
           "syllabus_check.py", "outcome_matrix.py"]
CSL = ["apa.csl", "ieee.csl", "modern-language-association.csl",
       "chicago-author-date.csl", "vancouver.csl", "harvard-cite-them-right.csl"]
# Enforcement/UX hooks that MUST stay wired to a specific event. Checking only
# that a *referenced* hook file exists (below) misses the failure that both
# review passes flagged: enforcement "fully depends on hooks being wired in
# settings.json", so silently dropping a hook entry — or moving it to the wrong
# event — disables data-file protection / phase gating with no other signal.
# The interpreter-drift check catches a hook that can't launch; this catches a
# hook that was never wired in the first place.
REQUIRED_HOOKS = {
    "protect_data_files.py": "PreToolUse",
    "phase_gate.py": "PreToolUse",
    "agent_write_scope.py": "PreToolUse",
    "template_supremacy_gate.py": "PreToolUse",
    "cite_warn.py": "PostToolUse",
    "session_status.py": "SessionStart",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out", action="store_true")
    ap.parse_args()  # output is always JSON; the flag is accepted for consistency
    problems = []

    # skills
    skills_dir = ROOT / ".claude" / "skills"
    found_skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    for missing in (WORKFLOW_COMMANDS | KNOWLEDGE_SKILLS) - found_skills:
        problems.append(f"skill missing: {missing}")
    for p in sorted(skills_dir.glob("*/SKILL.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        rel = p.relative_to(ROOT).as_posix()
        if not fm.get("name") or not fm.get("description"):
            problems.append(f"{rel}: frontmatter missing name/description")
        body_lines = len(text.splitlines())
        if body_lines > 520:
            problems.append(f"{rel}: body {body_lines} lines (>520 cap)")
        if p.parent.name in WORKFLOW_COMMANDS and fm.get("disable-model-invocation") != "true":
            problems.append(f"{rel}: workflow command lacks disable-model-invocation: true")
        for link in re.findall(r"\]\((reference/[^)#]+)\)", text):
            if not (p.parent / link).exists():
                problems.append(f"{rel}: broken link {link}")

    # agents
    agents_dir = ROOT / ".claude" / "agents"
    found_agents = {p.stem for p in agents_dir.glob("*.md")}
    for missing in AGENTS - found_agents:
        problems.append(f"agent missing: {missing}")
    for p in sorted(agents_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        rel = p.relative_to(ROOT).as_posix()
        for field in ("name", "description", "tools", "model"):
            if not fm.get(field):
                problems.append(f"{rel}: frontmatter missing {field}")
        for block in ("# ROLE", "# INPUT CONTRACT", "# PROCEDURE", "# OUTPUT CONTRACT"):
            if block not in text:
                problems.append(f"{rel}: missing contract block '{block}'")

    # scripts, hooks, templates
    for s in SCRIPTS:
        if not (ROOT / "scripts" / s).exists():
            problems.append(f"script missing: scripts/{s}")
    settings = ROOT / ".claude" / "settings.json"
    if settings.exists():
        try:
            cfg = json.loads(settings.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            problems.append(f".claude/settings.json is not valid JSON — {e.msg}")
            cfg = None
        if cfg is not None and not isinstance(cfg, dict):
            problems.append(f".claude/settings.json must be a JSON object, got {type(cfg).__name__}")
            cfg = None
        wired = set()  # (event, hook_filename) actually present in settings.json
        for event, groups in ((cfg.get("hooks") or {}) if cfg is not None else {}).items():
            if not isinstance(groups, list):
                problems.append(f"settings.json hooks.{event} must be an array")
                continue
            for g in groups:
                if not isinstance(g, dict):
                    problems.append(f"settings.json hooks.{event}[] entry must be an object")
                    continue
                hook_list = g.get("hooks", [])
                if not isinstance(hook_list, list):
                    problems.append(f"settings.json hooks.{event}[].hooks must be an array")
                    continue
                for h in hook_list:
                    if not isinstance(h, dict):
                        problems.append(f"settings.json hooks.{event}[].hooks[] entry must be an object")
                        continue
                    command = h.get("command", "")
                    if not isinstance(command, str):
                        continue
                    m = re.search(r"\.claude/hooks/(\w+\.py)", command)
                    if m:
                        wired.add((event, m.group(1)))
                        if not (ROOT / ".claude" / "hooks" / m.group(1)).exists():
                            problems.append(f"settings.json {event} hook missing file: {m.group(1)}")
                    # PreToolUse/PostToolUse hooks fail OPEN (Claude Code proceeds
                    # with the tool call if the hook process can't even start) —
                    # an interpreter that was never patched to what's actually on
                    # PATH (see DECISIONS.md D-017/D-027/D-041) silently disables
                    # data-file protection and phase gating with no warning
                    # anywhere else. Catch it here instead.
                    # Match the WHOLE leading interpreter token, not a truncated
                    # prefix: a `^(python3?|py)\b` capture pulls "python3" out of
                    # a "python3.11 …" command and then checks shutil.which for
                    # the wrong name. Capture the first whitespace-delimited token
                    # and check it only when it's a python-family interpreter
                    # (covers python3.11, /usr/bin/python3, py.exe).
                    interp = re.match(r"^(\S+)", command)
                    interp_tok = interp.group(1) if interp else ""
                    interp_base = interp_tok.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    if re.match(r"^(python3?(\.\d+)*|py)(\.exe)?$", interp_base, re.IGNORECASE) \
                            and not shutil.which(interp_tok):
                        problems.append(
                            f"settings.json {event} hook interpreter '{interp_tok}' not "
                            f"found on PATH — hook silently no-ops (fail-open); run "
                            f"INSTALL.sh/INSTALL.ps1 or patch_hook_interpreter.py --target <interpreter>")
        # A referenced hook that exists is not enough: the enforcement layer
        # only holds if every required hook is actually wired to its event. A
        # settings.json that is valid JSON but silently drops (or misroutes)
        # protect_data_files / phase_gate / agent_write_scope leaves data-file
        # protection and phase gating off with no other signal. Only assert this
        # when the hooks structure parsed cleanly — a malformed file already
        # reported its own shape errors above, and re-flagging every required
        # hook as "not wired" on top of that would just be noise.
        if cfg is not None and isinstance(cfg.get("hooks", {}), dict):
            for hook_file, event in sorted(REQUIRED_HOOKS.items()):
                if (event, hook_file) not in wired:
                    problems.append(
                        f"required hook not wired: {hook_file} must be a {event} hook in "
                        f"settings.json — enforcement/UX layer is disabled without it")
    else:
        problems.append(".claude/settings.json missing")
    for c in CSL:
        if not (ROOT / "templates" / "csl" / c).exists():
            problems.append(f"CSL missing: templates/csl/{c}")
    if not (ROOT / "templates" / "paper" / "reference.docx").exists():
        problems.append("templates/paper/reference.docx missing")

    counts = {"skills": len(found_skills), "agents": len(found_agents),
              "problems": len(problems)}
    print(json.dumps({"counts": counts, "problems": problems}, ensure_ascii=False, indent=2))
    sys.exit(2 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a kit file — {e}")
    except UnicodeDecodeError as e:
        die(f"a kit file is not valid UTF-8 — {e}")
