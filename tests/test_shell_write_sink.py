"""Regression tests for .claude/hooks/_shell_write_sink.py — shared shell
write-target detection used by both phase_gate.py (Invariant 3) and
protect_data_files.py (Invariant 6) to answer "does this Bash command write
to path P?" across redirects, tee, PowerShell cmdlets, cp/mv/rm, and Python
one-liners. Collected here as the single canonical home for write_targets()
unit tests — these previously accumulated across several dated
"remediation round" files (one per audit pass that found a new evasion), one
function tested in three different files with three different local runners.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(HOOKS))
from _shell_write_sink import write_targets, write_destinations  # noqa: E402


# ---------- write_destinations(): destination-only cp/mv/rename ----------
# (added alongside agent_write_scope.py — an allowlist-style per-agent
# write-scope check needs "did new content land outside my scope", not
# write_targets()'s "every cp/mv argument", or an ordinary
# `cp templates/x build/x` would false-positive on its read-only source.)

def test_write_destinations_cp_omits_readonly_source():
    targets = write_destinations("cp templates/paper/main.tex build/main.tex")
    assert "build/main.tex" in targets
    assert "templates/paper/main.tex" not in targets


def test_write_destinations_mv_omits_source():
    targets = write_destinations("mv scratch/draft.md drafts/intro.md")
    assert "drafts/intro.md" in targets
    assert "scratch/draft.md" not in targets


def test_write_destinations_os_rename_omits_source():
    targets = write_destinations("python -c \"import os; os.rename('scratch/a.md', 'drafts/b.md')\"")
    assert "drafts/b.md" in targets
    assert "scratch/a.md" not in targets


def test_write_destinations_redirect_unaffected():
    # Redirect/tee/PowerShell-cmdlet targets have no source/dest ambiguity —
    # identical to write_targets() for these syntaxes.
    assert write_destinations("echo x > build/out.tex") == write_targets("echo x > build/out.tex")


def test_write_targets_cp_still_reports_both_args():
    # write_targets() itself must be unchanged — protect_data_files.py relies
    # on "every cp/mv argument" to catch a protected file being relocated away.
    targets = write_targets("cp sources/registry.jsonl /tmp/out.bak")
    assert "sources/registry.jsonl" in targets
    assert "/tmp/out.bak" in targets


# ---------- quoted targets containing whitespace ----------

def test_write_targets_handles_quoted_redirect_target_with_space():
    targets = write_targets('echo "x [@fake2024]" > "drafts/my draft.md"')
    assert "drafts/my draft.md" in targets


def test_write_targets_handles_single_quoted_redirect_target_with_space():
    targets = write_targets("echo x > 'drafts/my draft.md'")
    assert "drafts/my draft.md" in targets


def test_write_targets_handles_cp_destination_with_space():
    targets = write_targets("cp scratch/intro.md 'drafts/my draft.md'")
    assert "drafts/my draft.md" in targets


def test_write_targets_handles_rm_target_with_space():
    targets = write_targets('rm -f "reviews/round 1.md"')
    assert "reviews/round 1.md" in targets


def test_write_targets_unquoted_target_still_works():
    targets = write_targets("echo x > drafts/intro.md")
    assert "drafts/intro.md" in targets


# ---------- PowerShell Rename-Item / New-Item -Force ----------

def test_write_targets_detects_rename_item():
    targets = write_targets("Rename-Item sources/registry.jsonl old.bak")
    assert "sources/registry.jsonl" in targets


def test_write_targets_detects_new_item_force():
    targets = write_targets('New-Item -Path sources/registry.jsonl -Value "x" -Force')
    assert "sources/registry.jsonl" in targets


# ---------- tee without a preceding pipe ----------

def test_write_targets_detects_pipeless_tee():
    targets = write_targets('tee sources/registry.jsonl <<< "data"')
    assert "sources/registry.jsonl" in targets


def test_write_targets_bash_tee_still_detected_not_confused_with_tee_object():
    targets = write_targets("echo data | tee sources/registry.jsonl")
    assert "sources/registry.jsonl" in targets


# ---------- Python os.rename/os.replace/os.remove/os.unlink/Path.unlink ----------

def test_write_targets_detects_os_remove():
    targets = write_targets("python -c \"import os; os.remove('sources/registry.jsonl')\"")
    assert "sources/registry.jsonl" in targets


def test_write_targets_detects_os_unlink():
    targets = write_targets("python -c \"import os; os.unlink('sources/registry.jsonl')\"")
    assert "sources/registry.jsonl" in targets


def test_write_targets_detects_os_rename_both_args():
    targets = write_targets(
        "python -c \"import os; os.rename('sources/registry.jsonl', 'x.bak')\"")
    assert "sources/registry.jsonl" in targets
    assert "x.bak" in targets


def test_write_targets_detects_os_replace():
    targets = write_targets(
        "python -c \"import os; os.replace('sources/registry.jsonl', 'x.bak')\"")
    assert "sources/registry.jsonl" in targets


def test_write_targets_detects_pathlib_unlink():
    targets = write_targets(
        "python -c \"from pathlib import Path; Path('sources/registry.jsonl').unlink()\"")
    assert "sources/registry.jsonl" in targets


# ---------- PowerShell cmdlet parameter reordering ----------

def test_write_targets_set_content_value_before_path():
    targets = write_targets('Set-Content -Value "draft text" -Path drafts/intro.md')
    assert "drafts/intro.md" in targets


def test_write_targets_out_file_encoding_before_filepath():
    targets = write_targets("Out-File -Encoding utf8 -FilePath drafts/intro.md")
    assert "drafts/intro.md" in targets


def test_write_targets_new_item_itemtype_before_path():
    targets = write_targets("New-Item -ItemType File -Path drafts/intro.md")
    assert "drafts/intro.md" in targets


def test_write_targets_tee_object_append_before_filepath():
    targets = write_targets("Tee-Object -Append -FilePath drafts/intro.md")
    assert "drafts/intro.md" in targets


def test_write_targets_set_content_path_still_works_when_first():
    # Pre-existing shape (path flag immediately after the cmdlet) must keep working.
    targets = write_targets('Set-Content -Path sources/registry.jsonl -Value "x"')
    assert "sources/registry.jsonl" in targets


# NOTE: variable-indirection (constant-folding) tests for write_targets()
# live in test_remediation_2026_07_04_round4.py, not here — round4 is a
# separate, pre-existing file outside this consolidation's scope.

# ---------- -mv/-rm option-flag false positive (`\b` matches inside "-mv" too) ----------

def test_write_targets_ignores_mv_flag_token():
    assert write_targets("some-tool -mv registry.jsonl") == []


def test_write_targets_ignores_rm_flag_token():
    assert write_targets("some-tool -rm sources/registry.jsonl") == []


def test_write_targets_still_detects_real_mv_command():
    targets = write_targets("mv sources/registry.jsonl /tmp/out.bak")
    assert "sources/registry.jsonl" in targets


def test_write_targets_still_detects_mv_after_chain_operator():
    targets = write_targets("cd /tmp && mv sources/registry.jsonl old.bak")
    assert "sources/registry.jsonl" in targets


def test_write_targets_still_detects_real_rm_command():
    targets = write_targets("rm sources/registry.jsonl")
    assert "sources/registry.jsonl" in targets


def test_write_targets_mv_args_stop_at_single_ampersand():
    # Regression: the stop-set only recognized doubled '&&'/'||', so a single
    # '&' (background-job separator) or bare '|' kept the mv/cp/rm argument
    # scan running past the actual command boundary, scooping the NEXT,
    # unrelated command's arguments in as if they were mv targets — a
    # false-positive DENY on a harmless read-only command downstream.
    targets = write_targets("mv a.txt b.txt & cat registry.jsonl")
    assert "registry.jsonl" not in targets
    assert set(targets) == {"a.txt", "b.txt"}


def test_write_targets_mv_args_stop_at_single_pipe():
    targets = write_targets("mv a.txt b.txt | cat registry.jsonl")
    assert "registry.jsonl" not in targets
    assert set(targets) == {"a.txt", "b.txt"}


def test_write_targets_rm_args_stop_at_single_ampersand():
    targets = write_targets("rm a.txt & cat registry.jsonl")
    assert "registry.jsonl" not in targets
    assert targets == ["a.txt"]


# ---------- `install` verb: coreutils caught, package-manager `install` isn't ----------
# (M1, 2026-07-05 audit) `install` is a real coreutils copy verb, but folding it
# into _COPY_MOVE's whitespace-permissive anchor also fired on the second word
# of `pip install <pkg>` / `npm install` / `apt install`, capturing the package
# name as a bogus write target — a live false-positive DENY of ordinary package
# installs. A dedicated command-position-anchored pattern fixes it.

def test_package_manager_install_is_not_a_write_target():
    for cmd in ("pip install requests", "pip3 install -U rapidfuzz",
                "npm install react", "apt-get install -y pandoc",
                "brew install uv", "cargo install ripgrep"):
        assert write_destinations(cmd) == [], cmd
        assert write_targets(cmd) == [], cmd


def test_coreutils_install_to_protected_file_still_caught():
    targets = write_targets("install -m644 evil sources/registry.jsonl")
    assert "sources/registry.jsonl" in targets


def test_coreutils_install_after_chain_operator_still_caught():
    targets = write_targets("echo hi && install evil sources/registry.jsonl")
    assert "sources/registry.jsonl" in targets


# ---------- quote-awareness: a sink whose anchor is inside quotes is data ----------
# (2026-07-05 audit) `git commit -m "note > drafts/x.md"` used to DENY because
# the `>` inside the quoted commit message was read as a real redirect. A sink
# whose operator/verb anchor falls inside a quoted argument is data, not an
# executed sink. Quoted TARGETS after a genuine operator, and real sinks inside
# nested-shell wrappers (re-scanned by _unwrap), must still be detected.

def test_redirect_inside_quoted_argument_is_not_a_write():
    assert write_targets('git commit -m "note > drafts/intro.md"') == []


def test_verb_inside_quoted_argument_is_not_a_write():
    assert write_targets('git commit -m "cleanup: rm the old drafts here"') == []
    assert write_targets('echo "move the file to build/x"') == []


def test_real_redirect_outside_quotes_still_detected():
    assert "drafts/intro.md" in write_targets("echo x > drafts/intro.md")


def test_quoted_redirect_target_after_real_operator_still_detected():
    # The operator sits OUTSIDE the quotes; the quoted span is only the target.
    assert "drafts/my draft.md" in write_targets('echo x > "drafts/my draft.md"')


def test_sink_inside_shell_wrapper_still_detected_despite_quotes():
    # Anchor is inside the outer -c "..." quotes at top level, but _unwrap
    # re-scans the inner command where it is unquoted.
    assert "sources/registry.jsonl" in write_targets('bash -c "rm sources/registry.jsonl"')
    assert "sources/registry.jsonl" in write_targets("os.system('rm sources/registry.jsonl')")


def test_unbalanced_quote_fails_closed_and_still_detects():
    # An unterminated quote must NOT let the whole tail count as quoted-and-safe:
    # _quoted_spans returns None -> no filtering -> pre-existing detection holds.
    assert "sources/registry.jsonl" in write_targets('echo " > sources/registry.jsonl')


# ---------- in-place editors: the flag must start a token, not sit in a path ----------
# `-[A-Za-z]*i` unanchored matched inside any hyphenated filename containing an
# `i` — `drafts/ek-e-cihaz-eslemesi.md` matched on `-ci`. Every `sed -n`,
# `awk`, and `perl -ne` READ of such a file was reported as a write into a
# gated directory and denied by the phase gate. Four of five appendix files in
# this kit's own manuscript matched.

import pytest  # noqa: E402
from _shell_write_sink import strip_heredocs  # noqa: E402


@pytest.mark.parametrize("cmd", [
    "sed -n '34p' drafts/ek-e-cihaz-eslemesi.md",
    "sed -n '20p;98p' drafts/ek-d-calisma-ozellikleri.md | cut -c1-200",
    "sed -n '1,20p' src/api-client.ts",
    "awk 'NR==3' notes/pre-training.md",
    "perl -ne 'print' data-cleaning.py",
])
def test_reading_a_hyphenated_filename_is_not_an_in_place_edit(cmd):
    assert write_targets(cmd) == []


@pytest.mark.parametrize("cmd,target", [
    ("sed -i 's/a/b/' drafts/a.md", "drafts/a.md"),
    ("sed -i.bak 's/a/b/' drafts/a.md", "drafts/a.md"),
    ("sed -ni 's/a/b/p' drafts/a.md", "drafts/a.md"),
    ("perl -pi -e 's/a/b/' drafts/a.md", "drafts/a.md"),
    # The clustered/suffixed forms AND a hyphenated target in one command: the
    # anchor must not cost the real detection it was protecting.
    ("perl -i.bak -pe 's/a/b/' drafts/ek-e-cihaz.md", "drafts/ek-e-cihaz.md"),
    ("gawk -i inplace '{print}' drafts/a.md", "drafts/a.md"),
])
def test_real_in_place_edits_are_still_detected(cmd, target):
    assert target in write_targets(cmd)


# ---------- a heredoc fed to an interpreter is code, not data ----------
# strip_heredocs() removed every body before detection, so a write performed by
# `python - <<'PY' ... PY` was invisible while the identical `python -c "..."`
# was caught. This module's docstring already promised python one-liners were
# gated; the heredoc spelling of one was not.

_CODE = 'import pathlib\npathlib.Path("drafts/methods.md").write_text("x")'
_PROSE = "This note mentions cat > drafts/methods.md as an example."


@pytest.mark.parametrize("opener", [
    "python - <<'PY'",
    "python3 - <<PY",
    "py -  <<'PY'",
    "python <<'PY'",
    "bash -s <<'PY'",
])
def test_heredoc_piped_into_an_interpreter_is_scanned(opener):
    cmd = opener + "\n" + _CODE + "\nPY"
    assert "drafts/methods.md" in write_targets(cmd)


@pytest.mark.parametrize("opener", [
    "cat <<'PY' > notes/x.md",
    "python analysis/run.py <<'PY'",
    "mail -s hi someone <<'PY'",
])
def test_heredoc_body_that_is_data_is_still_stripped(opener):
    cmd = opener + "\n" + _PROSE + "\nPY"
    assert "drafts/methods.md" not in write_targets(cmd)


def test_the_opening_line_redirect_is_still_gated():
    cmd = "cat <<'PY' > drafts/methods.md\n" + _PROSE + "\nPY"
    assert "drafts/methods.md" in write_targets(cmd)


def test_data_heredoc_body_really_is_removed_not_merely_unmatched():
    # Guards the distinction directly: whatever the sink patterns do or do not
    # match, the body of a data heredoc must not reach them at all.
    cmd = "cat <<'PY' > notes/x.md\n" + _PROSE + "\nPY"
    assert _PROSE not in strip_heredocs(cmd)
    code = "python - <<'PY'\n" + _CODE + "\nPY"
    assert "drafts/methods.md" in strip_heredocs(code)
