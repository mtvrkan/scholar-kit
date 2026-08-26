"""Running the collection the protocol describes (scripts/collect_run.py).

The kit runs the collection now, which makes the conditions it will not relax the
only thing worth testing hard: the protocol is complete before a request goes out,
a field that is not in the protocol is never collected, and the robots verdict has
no override. The extraction functions are tested directly because they are where a
site's shape meets the plan's declaration.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import collect_run as cr  # noqa: E402

PROTOCOL = """# Veri Toplama Protokolü

## Amaç
RQ1.
## Hukuki dayanak
KVKK: kişisel veri yok.
## İzin / kaynak
robots.txt okundu; hız sınırı 1/sn.
## Örnekleme
1-2 sayfa.
## Alanlar
title, published_at
## Veri minimizasyonu
Başka alan toplanmaz.
## Saklama
12 ay.
## Onam
Uygulanamaz.
## Etik kurul
Gerekmiyor.
## İletişim
sorumlu@example.org
"""


def _project(tmp_path, fields=None, protocol=PROTOCOL):
    (tmp_path / "analysis").mkdir(parents=True, exist_ok=True)
    (tmp_path / "analysis" / "collection-protocol.md").write_text(protocol, encoding="utf-8")
    plan = {"name": "t", "mode": "api", "protocol": "analysis/collection-protocol.md",
            "contact": "sorumlu@example.org",
            "urls": ["http://127.0.0.1:1/api/items"],
            "record_path": "data.items",
            "fields": fields or {"title": "title", "published_at": "published_at"}}
    (tmp_path / "analysis" / "collection-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return "analysis/collection-plan.json"


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "collect_run.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- the refusals, before any request ----------

def test_a_field_the_protocol_never_mentions_is_refused(tmp_path):
    """The check that keeps "we only collected the post text" true six weeks later,
    when someone added author_email to the plan because it was in the response."""
    plan = _project(tmp_path, fields={"title": "title", "author_email": "email"})
    out = json.loads(_run(tmp_path, "--plan", plan, "--dry-run", expect=2).stdout)
    kinds = {r["kind"]: r for r in out["refusals"]}
    assert kinds["undeclared_fields"]["fields"] == ["author_email"]


def test_an_incomplete_protocol_stops_the_run(tmp_path):
    plan = _project(tmp_path, protocol="# Protokol\n## Amaç\nRQ1.\n")
    out = json.loads(_run(tmp_path, "--plan", plan, "--dry-run", expect=2).stdout)
    kinds = {r["kind"] for r in out["refusals"]}
    assert "protocol" in kinds
    assert set(out["protocol"]["missing"]) >= {"consent", "retention"}


def test_there_is_no_flag_that_overrides_a_robots_disallow():
    """Pinned as a source fact: a --force here would make the robots check
    decoration, and the author would be the one explaining it."""
    flags = [line for line in (SCRIPTS / "collect_run.py").read_text(
        encoding="utf-8").splitlines() if "ap.add_argument(" in line]
    joined = " ".join(flags)
    for escape in ("--force", "--ignore-robots", "--no-robots", "--yes"):
        assert escape not in joined, f"{escape} would make the robots check decoration"


def test_a_plan_missing_its_contact_is_rejected(tmp_path):
    (tmp_path / "analysis").mkdir(parents=True, exist_ok=True)
    (tmp_path / "analysis" / "p.md").write_text(PROTOCOL, encoding="utf-8")
    (tmp_path / "analysis" / "plan.json").write_text(json.dumps(
        {"name": "t", "mode": "api", "protocol": "analysis/p.md",
         "fields": {"title": "title"}}), encoding="utf-8")
    proc = _run(tmp_path, "--plan", "analysis/plan.json", "--dry-run", expect=1)
    assert "contact" in (proc.stderr + proc.stdout)


# ---------- extraction ----------

def test_api_rows_are_built_only_from_declared_fields():
    body = json.dumps({"data": {"items": [
        {"title": "a", "published_at": "2026-01-01", "author_email": "x@y.z"}]}})
    plan = {"record_path": "data.items", "fields": {"title": "title"}}
    assert cr.rows_from_api(body, plan) == [{"title": "a"}]


def test_a_missing_field_in_one_record_does_not_lose_the_others():
    body = json.dumps({"items": [{"t": "a"}, {}, {"t": "c"}]})
    rows = cr.rows_from_api(body, {"record_path": "items", "fields": {"t": "t"}})
    assert [r["t"] for r in rows] == ["a", "", "c"]


def test_html_extraction_returns_zero_rows_rather_than_guessing():
    # The kit ships no HTML parser and does not pretend to: a pattern that no
    # longer matches is reported as zero rows, not as a partial scrape.
    plan = {"row_pattern": r"<article>.*?</article>", "fields": {"title": r"<h2>(.*?)</h2>"}}
    assert cr.rows_from_html("<div>nothing here</div>", plan) == []
    got = cr.rows_from_html("<article><h2>Başlık</h2></article>", plan)
    assert got == [{"title": "Başlık"}]


def test_dotted_paths_walk_lists_and_missing_keys():
    payload = {"a": {"b": [{"c": 1}, {"c": 2}]}}
    assert cr.dotted(payload, "a.b.1.c") == 2
    assert cr.dotted(payload, "a.z.c") is None


def test_the_url_template_expands_inclusively():
    urls = cr.plan_urls({"url_template": "https://x.org/p/{n}", "range": [2, 4]})
    assert urls == ["https://x.org/p/2", "https://x.org/p/3", "https://x.org/p/4"]
