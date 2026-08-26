#!/usr/bin/env python3
"""collect_run.py — run the collection the protocol describes, and only that one.

WHY THIS EXISTS
`/collect-data` produced a protocol and three checks, and then the collector
itself was written by hand, differently every time. That is the wrong place for
improvisation: the rate limit, the field list, the robots verdict and the request
log are exactly the parts a reviewer or an ethics board asks about, and they were
the parts living in a script nobody kept. A collector written fresh each session
also has no memory — an interrupted run restarts from the first page and hits the
site twice for everything it already had.

So the plan becomes a file, and this runs it. The protocol is the authority: a
field that is not written down in the protocol is not collected, because the
allowlist and the paperwork must be the same list or the paperwork is fiction.

WHAT IT REFUSES
- **To collect without a complete protocol.** `collection_check.py --protocol`
  runs first, here, not as a suggestion. A missing section stops the run.
- **To collect an undeclared field.** Every field in the plan must appear in the
  protocol's own text. This is the check that keeps "we only collected public
  post text" true six weeks later, when someone added `author_email` to the plan
  because it was right there in the response.
- **To fetch a path robots.txt disallows.** No override flag. A tool with a
  `--force` here is a tool whose robots check is decoration, and the author would
  be the one explaining it.
- **To pretend to be a browser.** The User-Agent names the kit and carries the
  contact address from the plan. No cookie jars, no login, no JS rendering, no
  CAPTCHA handling — a wall is an answer, and the answer is to ask the site owner
  or find another source.
- **To run without a ceiling.** `--max-requests` (200 by default) and
  `--max-minutes` both stop the run. An unbounded loop against someone else's
  server is the failure mode that ends in a block list, and it always starts as
  "just let it finish".

USAGE
  python scripts/collect_run.py --plan analysis/collection-plan.json --dry-run
  python scripts/collect_run.py --plan analysis/collection-plan.json --limit 5
  python scripts/collect_run.py --plan analysis/collection-plan.json
  python scripts/collect_run.py --plan analysis/collection-plan.json --resume

Exit codes: 0 collected · 1 error · 2 refused (protocol, undeclared field, robots
disallow, or the run stopped on a server signal) · 3 BLOCKED (requests missing).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - surfaced as a clean die() in main()
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from collection_check import check_protocol, robots_verdict, scan_file, _fold  # noqa: E402
from lib_common import die, emit, require_within_cwd  # noqa: E402

DEFAULT_MIN_DELAY = 1.0
DEFAULT_MAX_REQUESTS = 200
DEFAULT_MAX_MINUTES = 30.0
TIMEOUT = 30
# Server signals that mean stop, not retry harder. 429 is the site telling you the
# rate is too high; a collector that backs off and continues is still the thing it
# asked to stop.
STOP_STATUSES = (429, 503)


def load_plan(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        die(f"{path} does not exist — /collect-data scaffolds the plan next to the "
            f"protocol")
    try:
        plan = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg} (line {e.lineno})")
    for field in ("name", "mode", "protocol", "contact", "fields"):
        if not plan.get(field):
            die(f"plan is missing {field!r}. Required: name, mode (api|html), "
                f"protocol (path), contact (who the site owner would write to), "
                f"fields (the allowlist)")
    if plan["mode"] not in ("api", "html"):
        die(f"mode {plan['mode']!r} must be 'api' (JSON responses) or 'html'")
    if not isinstance(plan["fields"], dict) or not plan["fields"]:
        die("'fields' must be a non-empty object mapping column name → extractor")
    return plan


def plan_urls(plan: dict) -> list[str]:
    urls = list(plan.get("urls") or [])
    template = plan.get("url_template")
    if template:
        rng = plan.get("range")
        if not (isinstance(rng, list) and len(rng) == 2):
            die("'url_template' needs 'range': [first, last] — inclusive page numbers")
        first, last = int(rng[0]), int(rng[1])
        if last < first:
            die(f"range [{first}, {last}] runs backwards")
        for n in range(first, last + 1):
            try:
                urls.append(template.format(n=n, page=n, offset=n))
            except (KeyError, IndexError):
                die("'url_template' may only use {n} (also available as {page}, {offset})")
    if not urls:
        die("plan lists no URLs — give 'urls' or 'url_template' + 'range'")
    bad = [u for u in urls if urllib.parse.urlsplit(u).scheme not in ("http", "https")]
    if bad:
        die(f"{len(bad)} URL(s) are not absolute http(s), e.g. {bad[0]!r}")
    return urls


def undeclared_fields(plan: dict, protocol_text: str) -> list[str]:
    """Fields the plan collects that the protocol never mentions.

    Matched on the folded text so a Turkish heading and a Turkish column name meet
    (`_fold` strips diacritics and lowercases; `"İ".lower()` does not).
    """
    folded = _fold(protocol_text)
    return sorted(name for name in plan["fields"]
                  if _fold(str(name)) not in folded)


def dotted(obj, path: str):
    """Follow a dotted path through nested dicts/lists. Missing → None, never a raise.

    A field that is absent from one record out of 500 is normal in an API; a
    collector that dies on it loses the other 499.
    """
    current = obj
    for part in str(path).split("."):
        if part == "":
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def rows_from_api(body: str, plan: dict) -> list[dict]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return []
    records = dotted(payload, plan["record_path"]) if plan.get("record_path") else payload
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        return []
    out = []
    for rec in records:
        row = {}
        for column, path in plan["fields"].items():
            value = dotted(rec, path)
            row[column] = "" if value is None else (
                json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list))
                else str(value))
        out.append(row)
    return out


def rows_from_html(body: str, plan: dict) -> list[dict]:
    """Regex extraction, deliberately unglamorous.

    The kit ships no HTML parser, and this does not pretend to be one: markup
    changes and a regex that matched yesterday returns zero rows today. That is
    reported as zero rows rather than papered over, and it is the reason the API
    mode is the one to prefer whenever a site offers one.
    """
    blocks = [body]
    if plan.get("row_pattern"):
        blocks = re.findall(plan["row_pattern"], body, re.S | re.I)
    out = []
    for block in blocks:
        row, hit = {}, False
        for column, pattern in plan["fields"].items():
            m = re.search(pattern, block, re.S | re.I)
            value = (m.group(1) if m and m.groups() else (m.group(0) if m else "")) or ""
            value = re.sub(r"<[^>]+>", " ", value)
            value = re.sub(r"\s+", " ", value).strip()
            row[column] = value
            hit = hit or bool(value)
        if hit:
            out.append(row)
    return out


def _state_path(out_dir: Path) -> Path:
    return out_dir / "collect-state.json"


def load_state(out_dir: Path) -> dict:
    p = _state_path(out_dir)
    if not p.is_file():
        return {"done": [], "rows": 0}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"done": [], "rows": 0}


def save_state(out_dir: Path, state: dict):
    _state_path(out_dir).write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", required=True, metavar="FILE",
                    help="the collection plan (JSON) sitting next to the protocol")
    ap.add_argument("--out", metavar="DIR", help="default analysis/data/<plan name>")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="fetch only the first N pending URLs — run a pilot first")
    ap.add_argument("--min-delay", type=float, default=DEFAULT_MIN_DELAY,
                    help=f"seconds between requests, floor (default {DEFAULT_MIN_DELAY}); "
                         f"robots.txt crawl-delay wins when it is larger")
    ap.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    ap.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES)
    ap.add_argument("--resume", action="store_true",
                    help="skip URLs already recorded as done in collect-state.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="check protocol, fields and robots; make no data request")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.plan, "--plan")
    plan = load_plan(args.plan)
    require_within_cwd(plan["protocol"], "plan.protocol")
    protocol_file = Path(plan["protocol"])
    if not protocol_file.is_file():
        die(f"protocol {plan['protocol']} does not exist — write it before collecting, "
            f"not after (/collect-data scaffolds one)")
    protocol_text = protocol_file.read_text(encoding="utf-8", errors="replace")
    completeness = check_protocol(protocol_text)
    undeclared = undeclared_fields(plan, protocol_text)
    urls = plan_urls(plan)
    out_dir = Path(args.out) if args.out else Path("analysis/data") / str(plan["name"])
    require_within_cwd(out_dir.as_posix(), "--out")

    refusals = []
    if completeness["missing"]:
        refusals.append({"kind": "protocol",
                         "detail": f"missing section(s): {', '.join(completeness['missing'])}"})
    if undeclared:
        refusals.append({"kind": "undeclared_fields", "fields": undeclared,
                         "detail": ("these fields are in the plan but nowhere in the "
                                    "protocol. Add them to the protocol's Alanlar/Fields "
                                    "section — or, better, ask whether the study needs "
                                    "them at all")})

    agent = (f"scholar-kit/1.0 (research data collection; contact: {plan['contact']})")
    hosts = sorted({urllib.parse.urlsplit(u).netloc for u in urls})
    robots, delay = {}, args.min_delay
    if requests is None:
        die("requests not installed — pip install requests")
    for host in hosts:
        sample = next(u for u in urls if urllib.parse.urlsplit(u).netloc == host)
        verdict = robots_verdict(sample, agent)
        robots[host] = verdict
        if verdict.get("allowed") is False:
            refusals.append({"kind": "robots", "host": host,
                             "detail": "robots.txt disallows this path for this agent. "
                                       "There is no override: ask the site owner in "
                                       "writing, use an API, or find another source."})
        if verdict.get("crawl_delay"):
            delay = max(delay, float(verdict["crawl_delay"]))

    pending = urls
    state = load_state(out_dir) if args.resume else {"done": [], "rows": 0}
    if args.resume:
        done = set(state.get("done", []))
        pending = [u for u in urls if u not in done]
    if args.limit:
        pending = pending[:args.limit]

    if args.dry_run or refusals:
        emit({"plan": args.plan, "name": plan["name"], "mode": plan["mode"],
              "urls": len(urls), "pending": len(pending), "into": out_dir.as_posix(),
              "protocol": completeness, "fields": sorted(plan["fields"]),
              "undeclared_fields": undeclared, "robots": robots,
              "delay_seconds": delay, "agent": agent,
              "refusals": refusals,
              "result": "REFUSED" if refusals else "DRY-RUN",
              "note": ("nothing was fetched" if args.dry_run or refusals else "")},
             args.json_out)
        sys.exit(2 if refusals else 0)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "rows.csv"
    log_path = out_dir / "request-log.jsonl"
    columns = list(plan["fields"].keys())
    new_file = not rows_path.exists()
    started = time.monotonic()
    stopped, requests_made, rows_written = None, 0, 0

    with rows_path.open("a", encoding="utf-8", newline="") as fh, \
            log_path.open("a", encoding="utf-8") as log:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        for url in pending:
            if requests_made >= args.max_requests:
                stopped = f"--max-requests ({args.max_requests}) reached"
                break
            if (time.monotonic() - started) / 60 > args.max_minutes:
                stopped = f"--max-minutes ({args.max_minutes}) reached"
                break
            if requests_made:
                time.sleep(delay)
            entry = {"url": url, "at": datetime.datetime.now().isoformat(timespec="seconds")}
            try:
                resp = requests.get(url, headers={"User-Agent": agent}, timeout=TIMEOUT)
            except requests.RequestException as e:
                entry.update({"ok": False, "reason": str(e)[:200]})
                log.write(json.dumps(entry, ensure_ascii=False) + "\n")
                requests_made += 1
                continue
            entry["status"] = resp.status_code
            if resp.status_code in STOP_STATUSES:
                entry.update({"ok": False, "reason": "server asked for a lower rate"})
                log.write(json.dumps(entry, ensure_ascii=False) + "\n")
                stopped = (f"HTTP {resp.status_code} from {urllib.parse.urlsplit(url).netloc}"
                           f" — the server asked for a lower rate. Raise --min-delay and "
                           f"resume; do not retry harder.")
                requests_made += 1
                break
            if resp.status_code >= 400:
                entry.update({"ok": False, "reason": f"HTTP {resp.status_code}"})
                log.write(json.dumps(entry, ensure_ascii=False) + "\n")
                requests_made += 1
                continue
            resp.encoding = resp.encoding or "utf-8"
            rows = (rows_from_api(resp.text, plan) if plan["mode"] == "api"
                    else rows_from_html(resp.text, plan))
            for row in rows:
                # extrasaction="ignore" is the second lock; the first is that a row
                # is built only from the plan's columns. The allowlist is enforced
                # where the bytes are written, not only where they are parsed.
                writer.writerow({c: row.get(c, "") for c in columns})
            rows_written += len(rows)
            requests_made += 1
            entry.update({"ok": True, "rows": len(rows), "bytes": len(resp.content)})
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")
            state.setdefault("done", []).append(url)

    state["rows"] = state.get("rows", 0) + rows_written
    state["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    save_state(out_dir, state)

    pii = scan_file(rows_path) if rows_path.is_file() else {}
    pii_findings = sum(pii.get("matches", {}).values()) + sum(
        1 for c in pii.get("columns", {}).values() if c.get("declared"))

    emit({"name": plan["name"], "into": out_dir.as_posix(), "requests": requests_made,
          "rows_written": rows_written, "rows_total": state["rows"],
          "delay_seconds": delay, "stopped": stopped,
          "files": {"rows": rows_path.as_posix(), "log": log_path.as_posix(),
                    "state": _state_path(out_dir).as_posix()},
          "pii_scan": {"findings": pii_findings, "matches": pii.get("matches", {}),
                       "columns": sorted(pii.get("columns", {}))},
          "next": [
              "python scripts/collection_check.py --scan " + rows_path.as_posix(),
              "python scripts/dataset_db.py add --payload '{\"name\":\"" +
              str(plan["name"]) + "\",\"source\":\"own-scraped\",…}'",
              "python scripts/dataset_db.py attach DS-000N " + rows_path.as_posix()],
          "note": ("the request log is the reproducible part: every URL, its status "
                   "and its row count, in the order they were fetched. It is what a "
                   "methods section describes and what a challenge is answered with")},
         args.json_out)
    sys.exit(2 if (stopped or pii_findings) else 0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("interrupted — rows already written are kept, and --resume skips the URLs "
            "recorded as done", code=1)
    except OSError as e:
        die(f"failed to read or write a file — {e}")
