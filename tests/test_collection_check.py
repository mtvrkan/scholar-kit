"""Collecting data yourself (scripts/collection_check.py).

The failure mode here is not a wrong number, it is a wrong act — data taken from
a site that forbids it, personal data carried into a repository, human subjects
with no ethics approval. Three of those questions have deterministic answers and
this script answers exactly those three. What the tests pin hardest is the
boundary: it reports the rule, it does not rule on legality, and it never prints
the personal data it finds.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import collection_check as cc  # noqa: E402


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "collection_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- the PII scan ----------

def test_personal_data_is_counted(tmp_path):
    (tmp_path / "d.csv").write_text(
        "id,email,score\n1,ali@example.com,5\n2,veli@example.com,7\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--scan", "d.csv", expect=2).stdout)
    assert out["files"][0]["matches"]["email"] == 2


def test_the_matched_values_are_never_printed(tmp_path):
    """The load-bearing test. A scanner that echoes what it found has copied the
    personal data into a terminal, a log and a transcript — the harm it was run
    to prevent."""
    (tmp_path / "d.csv").write_text(
        "id,email,tc\n1,ali@example.com,10000000146\n", encoding="utf-8")
    proc = _run(tmp_path, "--scan", "d.csv", expect=2)
    for secret in ("ali@example.com", "10000000146"):
        assert secret not in proc.stdout, f"the scan printed {secret!r}"


def test_a_column_that_declares_its_intent_is_flagged_while_empty(tmp_path):
    # An empty "email" column today is a column someone fills tomorrow.
    (tmp_path / "d.csv").write_text("id,email\n1,\n2,\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--scan", "d.csv", expect=2).stdout)
    assert out["files"][0]["columns"]["email"]["declared"] is True


def test_turkish_column_names_are_recognised(tmp_path):
    (tmp_path / "d.csv").write_text("ad,telefon,puan\nX,,5\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--scan", "d.csv", expect=2).stdout)
    assert set(out["files"][0]["columns"]) == {"ad", "telefon"}


def test_a_clean_file_exits_zero(tmp_path):
    (tmp_path / "d.csv").write_text("sensor,rms\nA,0.31\nB,0.44\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--scan", "d.csv").stdout)
    assert out["files"][0]["matches"] == {} and out["files"][0]["columns"] == {}


def test_the_scan_says_where_the_finding_should_be_declared(tmp_path):
    (tmp_path / "d.csv").write_text("id,email\n1,a@b.co\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--scan", "d.csv", expect=2).stdout)
    assert "dataset_db.py" in out["next"]


# ---------- the protocol completeness check ----------

def test_a_protocol_missing_sections_names_them():
    result = cc.check_protocol("# Protocol\n\n## Purpose\nMeasure X.\n")
    assert "purpose" in result["present"]
    for section in ("retention", "consent", "contact", "legal_basis"):
        assert section in result["missing"]


def test_not_applicable_written_once_does_not_satisfy_two_sections():
    # A scrape of public statistics legitimately has no consent step. Writing
    # "not applicable" under Consent must not also tick Ethics approval.
    result = cc.check_protocol("## Consent\nNot applicable — no human subjects.\n")
    assert "consent" in result["present"]
    assert "ethics_approval" in result["missing"]


def test_a_turkish_protocol_is_read_as_a_protocol():
    text = ("## Amaç\nX\n## Hukuki dayanak\nKVKK m.5\n## İzin\nrobots.txt\n"
            "## Örnekleme\nY\n## Alanlar\nZ\n## Veri minimizasyonu\nW\n"
            "## Saklama\n6 ay\n## Onam\nyok\n## Etik kurul\n2026/12\n## İletişim\nA\n")
    assert cc.check_protocol(text)["missing"] == []


def test_completeness_is_not_approval():
    result = cc.check_protocol("purpose legal basis permission sampling fields "
                               "minimisation retention consent ethics contact")
    assert result["missing"] == []
    assert "not" in result["note"] and "acceptable" in result["note"]


def test_a_missing_protocol_file_points_at_the_scaffold(tmp_path):
    proc = _run(tmp_path, "--protocol", "absent.md", expect=1)
    assert "/collect-data" in proc.stderr


# ---------- robots.txt: report the rule, refuse the verdict ----------

def _robots(monkeypatch, body, status=200):
    class _Resp:
        status_code = status
        encoding = "utf-8"
        text = body

    monkeypatch.setattr(cc, "http_get_with_retry", lambda url, **kw: _Resp())


def test_a_disallowed_path_is_reported_with_the_rule_that_says_so(monkeypatch):
    _robots(monkeypatch, "User-agent: *\nDisallow: /private/\nCrawl-delay: 5\n")
    result = cc.robots_verdict("https://example.org/private/page", "scholar-kit")
    assert result["allowed"] is False
    assert any("Disallow: /private/" in rule for rule in result["rules"])


def test_an_allowed_path_is_allowed(monkeypatch):
    _robots(monkeypatch, "User-agent: *\nDisallow: /private/\n")
    assert cc.robots_verdict("https://example.org/public/page", "scholar-kit")["allowed"] is True


def test_a_missing_robots_file_is_an_absence_of_a_rule_not_a_permission(monkeypatch):
    _robots(monkeypatch, "", status=404)
    result = cc.robots_verdict("https://example.org/x", "scholar-kit")
    assert result["allowed"] is None and result["publishes_rules"] is False
    assert "not a permission" in result["reason"]


def test_the_verdict_carries_the_decision_it_cannot_make(monkeypatch):
    """robots.txt is a request, not the law. A tool that returned a bare
    allowed:true would be handing out legal advice by implication."""
    _robots(monkeypatch, "User-agent: *\nAllow: /\n")
    result = cc.robots_verdict("https://example.org/x", "scholar-kit")
    assert "Terms of Service" in result["human_decision"]


def test_crawl_delay_is_surfaced(monkeypatch):
    _robots(monkeypatch, "User-agent: *\nCrawl-delay: 10\nDisallow:\n")
    assert cc.robots_verdict("https://example.org/x", "scholar-kit")["crawl_delay"] == 10


# ---------- CLI contract ----------

def test_exactly_one_mode_at_a_time(tmp_path):
    (tmp_path / "d.csv").write_text("a\n1\n", encoding="utf-8")
    proc = _run(tmp_path, "--scan", "d.csv", "--protocol", "d.csv", expect=1)
    assert "exactly one" in proc.stderr


def test_no_mode_at_all_is_refused(tmp_path):
    _run(tmp_path, expect=1)


def test_a_file_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--scan", "../elsewhere.csv", expect=1)
    assert "--scan" in proc.stderr
