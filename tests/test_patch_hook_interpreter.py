"""Regression tests for scripts/patch_hook_interpreter.py's behavior on a
malformed .claude/settings.json (path-guard tests for --settings live in
test_path_validation.py alongside every other script's --file/--out-style
argument guard; this file covers the script's own structural handling)."""
import json


def test_rejects_hook_group_as_string(run, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"hooks": {"PreToolUse": ["not-an-object"]}}),
                             encoding="utf-8")
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                         "--settings", "settings.json")
    assert code == 1
    assert "ERROR" in err


def test_rejects_hooks_key_as_dict(run, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"hooks": {"PreToolUse": {"hooks": []}}}),
                             encoding="utf-8")
    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                         "--settings", "settings.json")
    assert code == 1
    assert "ERROR" in err
    assert "must be an array" in err
