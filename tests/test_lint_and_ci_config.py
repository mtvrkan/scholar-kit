"""The static-analysis layer, bound to something that fails.

CONTRIBUTING.md's promise is that a contributor learns in thirty seconds
whether a change will be accepted. That only holds while the checks it names
are the checks CI actually runs. These tests are the binding — the same
treatment test_governance_docs.py gives every published number, applied to the
tooling claims.

Parsed as TEXT, not YAML: PyYAML is not a runtime dependency of this kit and
adding one so that a meta-test can read a workflow file would be a poor trade.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
PRECOMMIT = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
DEV_REQS = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
RUFF = (ROOT / "ruff.toml").read_text(encoding="utf-8")


# ---------- the tools exist and CI runs them ----------

def test_ruff_config_exists_and_selects_the_defect_finding_rules():
    assert re.search(r"^select\s*=", RUFF, re.M), "ruff.toml selects no rules"
    selected = re.search(r"select\s*=\s*\[([^\]]*)\]", RUFF).group(1)
    for rule in ("E", "W", "F", "B"):
        assert f'"{rule}"' in selected, f"ruff no longer selects {rule}"


def test_every_disabled_ruff_rule_states_why():
    """An ignore list without reasons becomes the place findings go to die.

    Each entry must carry a comment on its own line — that is the difference
    between a decision and an accumulation.
    """
    block = re.search(r"ignore\s*=\s*\[(.*?)\n\]", RUFF, re.S)
    assert block, "ruff.toml has no ignore list to check"
    for line in block.group(1).splitlines():
        code = re.search(r'"([A-Z]+\d+)"', line)
        if code:
            assert "#" in line, f"{code.group(1)} is ignored with no stated reason"


def test_ci_runs_ruff_and_bandit():
    assert "ruff check" in CI, "CI does not run ruff"
    assert re.search(r"bandit\s+-q\s+-ll", CI), (
        "CI does not run bandit at MEDIUM+ severity")


def test_the_bandit_command_ci_runs_actually_passes():
    """Running the gate, not describing it.

    Every other test in this file asserts that CI *names* a tool. None of them
    could tell you whether the tool is currently green, and that gap had already
    cost something: two HIGH B202 findings in dataset_fetch.py sat unsuppressed
    while a docstring in test_remediation_2026_08_15_axes_review.py recorded
    "CI's -ll threshold already passes" — written from the assumption that -ll
    means "MEDIUM only" rather than "MEDIUM and above". The lint job was red on
    a clean tree, and the pre-commit hook was rejecting every commit that
    touched scripts/, for as long as nobody ran it locally.

    So this runs the exact command from ci.yml. A HIGH finding that is genuinely
    a false positive gets a justified `# nosec` at the call site (the argument
    then lives next to the code it defends); one that is not gets fixed. Neither
    outcome is "leave it red and write a note".

    Skipped rather than failed when bandit is absent: the suite must stay
    runnable from a plain `pip install -r requirements.txt`, and a missing dev
    tool is an unanswerable question, not a failing answer.
    """
    import importlib.util
    import subprocess
    import sys
    # find_spec, not `import bandit`: importing it here pulls in pkg_resources
    # and emits a setuptools deprecation warning into every run of this suite,
    # attributed to this test — noise created by the availability check rather
    # than by anything under test.
    if importlib.util.find_spec("bandit") is None:
        pytest.skip("bandit not installed — dev-only dependency")
    m = re.search(r"run:\s*(python -m bandit[^\n]*)", CI)
    assert m, "ci.yml no longer has a runnable bandit line to reproduce"
    proc = subprocess.run([sys.executable, *m.group(1).split()[1:]],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, (
        f"CI's own bandit command exits {proc.returncode} — the lint job is red "
        f"and pre-commit blocks scripts/ commits:\n{proc.stdout}{proc.stderr}")


def test_ci_installs_what_it_runs():
    # A lint step that installs nothing passes by not finding the tool.
    assert "ruff" in DEV_REQS and "bandit" in DEV_REQS
    assert "requirements-dev.txt" in CI


def test_dev_tools_are_pinned_by_major():
    # Same reasoning as requirements.txt's caps: a new default rule in a major
    # bump must not turn CI red without a commit that chose it.
    #
    # pytest and pytest-cov are in this list for a reason found by review, not
    # by a failure: the argument was written for the linters and applied only
    # to them, leaving the runner the whole suite's meaning depends on free to
    # major-bump underneath it. A collection or fixture change there does not
    # only turn CI red — it can turn it quietly green.
    for tool in ("ruff", "bandit", "pytest", "pytest-cov"):
        assert re.search(rf"^{tool}>=[\d.]+,<\d+", DEV_REQS, re.M), (
            f"{tool} is not pinned by major version in requirements-dev.txt")


def test_ci_still_runs_the_suite_on_three_platforms():
    # The lint job is additive. If it ever became the whole of CI, the hooks —
    # whose behaviour genuinely differs across Windows and POSIX — would go
    # unexercised on two of the three.
    for os_name in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert os_name in CI
    assert "python -m pytest -q" in CI


# ---------- coverage is a floor, and stays unpublished ----------

def test_coverage_runs_as_a_floor():
    m = re.search(r"--cov-fail-under=(\d+)", CI)
    assert m, "CI declares no coverage floor"
    assert 40 <= int(m.group(1)) <= 95, (
        "a floor outside this band is either unenforceable or a target in "
        "disguise; see the comment above the coverage job")


def test_coverage_measures_the_subprocesses_the_suite_actually_runs():
    """The floor is only meaningful if the measurement reaches the children.

    Most of this suite runs the scripts as subprocesses. Coverage started in
    the pytest process cannot see into them, and for a long time it did not:
    skill_routing_eval.py read 0% while a dozen tests drove it end to end, and
    the CI comment explained the gap instead of closing it. Three things have
    to hold together, so all three are asserted — an rcfile the children read,
    the env var that makes them read it, and an absolute data file, since the
    children run inside a tmp_path and would otherwise write their data where
    it is deleted at teardown.
    """
    rc = ROOT / ".coveragerc"
    assert rc.exists(), "no .coveragerc — subprocess coverage has nothing to read"
    rc_text = rc.read_text(encoding="utf-8")
    assert re.search(r"^parallel\s*=\s*true", rc_text, re.M), (
        "parallel mode off: the second child to finish truncates the first's data")
    assert "COVERAGE_PROCESS_START" in CI, (
        "CI does not point the child processes at the rcfile, so the coverage "
        "job measures imports only")
    assert re.search(r"COVERAGE_FILE:.*\.coverage", CI), (
        "CI does not pin an absolute COVERAGE_FILE; child data files land in "
        "the tmp_path they run in and vanish")


def test_no_readme_publishes_a_coverage_percentage():
    """The guard against the regression that looks like an improvement.

    Most of this suite drives the scripts as subprocesses, which the collector
    largely cannot see — registry_db.py reads 17% while being one of the most
    exercised modules here. Printing that number next to the test count would
    be publishing a measurement of the instrument. Same rule as
    docs/PERFORMANCE.md's refusal to publish a per-command cost table.
    """
    for name in ("README.md", "README.tr.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"(coverage|kapsam)\D{0,20}\d{1,3}\s*%", text, re.I), (
            f"{name} publishes a coverage percentage — see this test's docstring")


# ---------- pre-commit is the fast subset, not a second source of truth ----------

def test_precommit_runs_ruff_and_bandit_from_the_pinned_dev_environment():
    """`language: system` is the load-bearing detail: a mirrored remote ruff
    would be a second declared version, and the failure mode is silent — CI
    green on one version, the contributor's commit rejected by another."""
    for hook in ("ruff", "bandit"):
        assert re.search(rf"id:\s*{hook}\b", PRECOMMIT), f"{hook} missing from pre-commit"
    assert PRECOMMIT.count("language: system") >= 2


def test_precommit_scans_for_secrets():
    assert "gitleaks" in PRECOMMIT
    assert "detect-private-key" in PRECOMMIT


def test_every_remote_precommit_repo_is_pinned_to_a_tag():
    revs = re.findall(r"^\s*rev:\s*(\S+)", PRECOMMIT, re.M)
    assert revs, "no remote hooks pinned (or none present)"
    for rev in revs:
        assert re.fullmatch(r"v?\d+\.\d+(\.\d+)?", rev), (
            f"pre-commit rev {rev!r} is not an immutable tag — a moving ref here "
            f"is the supply-chain hole SECURITY.md's Actions pinning closes")


def test_precommit_stays_inside_its_time_budget_by_excluding_the_suite():
    # pytest takes minutes. A pre-commit hook that runs it gets bypassed with
    # --no-verify, and a bypassed hook is worse than an absent one because
    # everyone believes it ran. Comment lines are excluded from the scan: the
    # config explains this choice in prose, and the explanation naming the
    # thing it excludes must not read as the thing being wired up.
    directives = [ln for ln in PRECOMMIT.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("pytest" in ln for ln in directives)
