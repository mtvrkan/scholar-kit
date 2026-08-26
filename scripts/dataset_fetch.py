#!/usr/bin/env python3
"""dataset_fetch.py — bring a registered dataset's bytes to disk, and only a registered one.

WHY THIS EXISTS
`/find-dataset` ends with a register entry: where the data lives, what its licence
says, how to cite it. Then the author opened a browser, downloaded a file by hand,
and dropped it under `analysis/` — and at that moment the one thing the register
was built to guarantee was gone. Nothing tied the file on disk to the row in
`datasets.jsonl`: not the URL it actually came from, not the day it was fetched,
not whether the bytes were the ones the licence was read for. `attach` measured
whatever happened to be there.

This closes that hop. The download starts from the register, not from a URL
someone pasted: the record has to exist, its licence has to have been read, and
the bytes are hashed as they arrive rather than measured afterwards. What lands
on disk carries a fetch log saying which URL, which day, which HTTP status and
which digest — the four things a methods section claims and a replication package
has to reproduce.

WHAT IT REFUSES
- **To fetch for an unregistered dataset.** There is no `--url` without an `--id`.
  A file with no record is the state this script exists to end, and offering a
  quick path around the register would restore it on the first busy afternoon.
- **To fetch when the licence was never read.** `license_verified: false` blocks
  the download and names the command that fixes it. Downloading is the moment the
  licence starts to matter; a tool that fetches first and asks later has already
  put the author in the position it was supposed to keep them out of.
- **To work around an access wall.** 401/403 and credential-gated hosts (Kaggle,
  gated HuggingFace repos) exit BLOCKED with the host's own documented path. No
  User-Agent games, no cookie replay, no "try again as a browser".
- **To claim a landing page is data.** An HTML body arriving where a CSV was
  expected is reported as such and the file is kept with a `.html` suffix, because
  a 12 KB "dataset" that is really a login page is a failure that otherwise
  surfaces three steps later, inside a training run.
- **To write the register itself.** `dataset_db.py` stays the only writer:
  `--attach` runs it as a subprocess, so its lock, its validation and its
  measurement are the ones that apply.

USAGE
  python scripts/dataset_fetch.py --id DS-0001 --url <direct file url> [--url ...]
  python scripts/dataset_fetch.py --id DS-0001 --url <u> --extract --attach
  python scripts/dataset_fetch.py --id DS-0001 --plan          # what would happen

Exit codes: 0 fetched · 1 error · 2 refused (no record, unread licence, size cap,
robots disallow under --respect-robots) · 3 BLOCKED (credentials required).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import tarfile
import urllib.parse
import zipfile
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - surfaced as a clean die() in main()
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd  # noqa: E402

SCRIPTS = Path(__file__).parent
DEFAULT_REGISTER = "analysis/datasets.jsonl"
# The same fixed placeholder every other networked script sends: SECURITY.md
# promises the kit transmits no identifier of yours, and a download is not an
# exception to that (collect_run.py is, deliberately, and says so).
AGENT = "scholar-kit/1.0 (mailto:scholar-kit@example.org)"
TIMEOUT = 60
CHUNK = 1 << 16
DEFAULT_MAX_MB = 512
# Zip-bomb and zip-slip guards. A dataset archive that needs more than these is a
# dataset the author should unpack deliberately, seeing what it contains.
MAX_MEMBERS = 20_000
MAX_UNCOMPRESSED_MB = 4096

# Hosts whose download endpoints need credentials the kit does not hold and will
# not ask for. Listed so the message can name the host's own documented path
# instead of reporting a bare 403 the author has to go and interpret.
CREDENTIAL_HOSTS = {
    "www.kaggle.com": "Kaggle needs an API token: create one at kaggle.com/settings, "
                      "then `pip install kaggle` and `kaggle datasets download -d <slug> "
                      "-p analysis/data/<DS-id>`. Fetch it there, then `dataset_db.py attach`.",
    "kaggle.com": "Kaggle needs an API token: create one at kaggle.com/settings, "
                  "then `pip install kaggle` and `kaggle datasets download -d <slug> "
                  "-p analysis/data/<DS-id>`. Fetch it there, then `dataset_db.py attach`.",
    "physionet.org": "PhysioNet credentialed datasets require a signed data-use "
                     "agreement tied to your account; the kit cannot sign one for you. "
                     "Download through your account, then `dataset_db.py attach`.",
}

# Content types that mean "you were served a page, not a file". Kept small and
# specific: the point is to catch a login wall or a cookie interstitial, not to
# police the long tail of MIME registrations.
PAGE_TYPES = ("text/html", "application/xhtml+xml")


def _record(register: str, ds_id: str) -> dict:
    records = read_jsonl(register)
    if not records:
        die(f"{register} holds no datasets — register the dataset first "
            f"(/find-dataset, or scripts/dataset_db.py add)")
    for rec in records:
        if rec.get("id") == ds_id:
            return rec
    die(f"dataset {ds_id!r} is not in {register} (known: "
        f"{', '.join(sorted(r.get('id', '?') for r in records)) or 'none'})")


def licence_gate(rec: dict) -> list[str]:
    """The two licence findings that block a download, as sentences.

    Separated from the fetch so `--plan` can report them without a network call:
    the author should be able to see why a fetch will refuse before spending a
    minute finding out.
    """
    problems = []
    if rec.get("license", "unknown") == "unknown":
        problems.append(
            "licence not recorded — 'unknown' is not permission. Read the dataset's "
            "own licence page, then: python scripts/dataset_db.py set-field "
            f"{rec.get('id')} license '<SPDX id or the licence's own name>'")
    elif not rec.get("license_verified"):
        problems.append(
            f"licence '{rec['license']}' is recorded but was never verified against "
            f"the source's own licence page. Read it, then: python scripts/dataset_db.py "
            f"set-field {rec.get('id')} license_verified true")
    return problems


def candidate_urls(rec: dict, explicit: list[str]) -> list[str]:
    if explicit:
        return explicit
    urls = [u for u in (rec.get("download_urls") or []) if isinstance(u, str)]
    if urls:
        return urls
    die(f"no --url given and {rec.get('id')} records no 'download_urls'. The record's "
        f"'url' field is the dataset's page, which is usually not its file — pass the "
        f"direct file URL with --url, or record the file URLs with: "
        f"python scripts/dataset_db.py set-field {rec.get('id')} download_urls "
        f"'[\"<direct file URL>\"]'")


def _filename_for(url: str, resp) -> str:
    """The name the file should carry on disk.

    Content-Disposition first (the server's own answer), then the URL path, then a
    last-resort name — never the query string, which is how a directory ends up
    with `download?id=7&format=csv` as a filename on one platform and an error on
    another.
    """
    disp = (resp.headers.get("Content-Disposition") or "") if resp is not None else ""
    for part in disp.split(";"):
        part = part.strip()
        if part.lower().startswith("filename="):
            name = part.split("=", 1)[1].strip().strip('"')
            if name:
                return Path(name).name
    path = urllib.parse.urlsplit(url).path
    name = Path(urllib.parse.unquote(path)).name
    return name or "download.bin"


def fetch_one(url: str, out_dir: Path, max_bytes: int, agent: str) -> dict:
    headers = {"User-Agent": agent}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True,
                            allow_redirects=True)
    except requests.RequestException as e:
        return {"url": url, "ok": False, "reason": f"request failed — {e}"}
    with resp:
        if resp.status_code in (401, 403):
            host = urllib.parse.urlsplit(resp.url).netloc.lower()
            return {"url": url, "ok": False, "blocked": True, "status": resp.status_code,
                    "reason": CREDENTIAL_HOSTS.get(
                        host, f"the host refused an anonymous download ({resp.status_code}). "
                              f"If the dataset requires an account or a data-use agreement, "
                              f"that agreement is yours to accept — download it through your "
                              f"account, then attach the files.")}
        if resp.status_code >= 400:
            return {"url": url, "ok": False, "status": resp.status_code,
                    "reason": f"HTTP {resp.status_code}"}
        declared = resp.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            return {"url": url, "ok": False, "status": resp.status_code,
                    "oversize": True,
                    "reason": f"server declares {int(declared) / 1e6:.1f} MB, over the "
                              f"{max_bytes / 1e6:.0f} MB cap — raise it deliberately with "
                              f"--max-mb if that is the dataset you mean to fetch"}
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        name = _filename_for(url, resp)
        is_page = ctype in PAGE_TYPES
        if is_page and not name.lower().endswith((".html", ".htm")):
            name += ".html"
        dest = out_dir / name
        tmp = dest.with_suffix(dest.suffix + ".part")
        digest = hashlib.sha256()
        written = 0
        try:
            with tmp.open("wb") as fh:
                for block in resp.iter_content(CHUNK):
                    if not block:
                        continue
                    written += len(block)
                    if written > max_bytes:
                        fh.close()
                        tmp.unlink(missing_ok=True)
                        return {"url": url, "ok": False, "oversize": True,
                                "reason": f"exceeded the {max_bytes / 1e6:.0f} MB cap while "
                                          f"downloading (the server declared no size) — "
                                          f"raise --max-mb deliberately"}
                    digest.update(block)
                    fh.write(block)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            return {"url": url, "ok": False, "reason": f"could not write {dest} — {e}"}
        tmp.replace(dest)
        result = {"url": url, "final_url": resp.url, "ok": True, "status": resp.status_code,
                  "path": dest.as_posix(), "bytes": written,
                  "sha256": digest.hexdigest(), "content_type": ctype,
                  "fetched_at": datetime.datetime.now().isoformat(timespec="seconds")}
        if is_page:
            result["warning"] = ("the server returned an HTML page, not a data file — "
                                 "this is usually a login wall, a cookie interstitial or a "
                                 "landing page. The file was kept, with an .html suffix, so "
                                 "you can look at what actually arrived.")
        return result


def _safe_members(names: list[str], out_dir: Path) -> list[str]:
    """Reject absolute paths, parent escapes and symlink-shaped names before extraction.

    A dataset archive is an untrusted input like any other download: one member
    named `../../.claude/settings.json` would write outside the project, and the
    author would have no reason to look.
    """
    bad = []
    for name in names:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or name.startswith(("/", "\\")):
            bad.append(name)
            continue
        try:
            (out_dir / p).resolve().relative_to(out_dir.resolve())
        except ValueError:
            bad.append(name)
    return bad


def extract(path: Path, out_dir: Path) -> dict:
    kind = None
    if zipfile.is_zipfile(path):
        kind = "zip"
    elif tarfile.is_tarfile(path):
        kind = "tar"
    if kind is None:
        return {"archive": path.as_posix(), "extracted": False,
                "reason": "not a zip or tar archive — nothing to extract"}
    target = out_dir / (path.stem + "-extracted")
    target.mkdir(parents=True, exist_ok=True)
    if kind == "zip":
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            names = [i.filename for i in infos]
            total = sum(i.file_size for i in infos)
            bad = _safe_members(names, target)
            if bad:
                return {"archive": path.as_posix(), "extracted": False,
                        "reason": f"refused: {len(bad)} member(s) point outside the "
                                  f"extraction directory, e.g. {bad[0]!r}"}
            if len(infos) > MAX_MEMBERS or total > MAX_UNCOMPRESSED_MB * 1_000_000:
                return {"archive": path.as_posix(), "extracted": False,
                        "reason": f"refused: {len(infos)} members / "
                                  f"{total / 1e6:.0f} MB uncompressed exceeds the guard "
                                  f"({MAX_MEMBERS} / {MAX_UNCOMPRESSED_MB} MB). Unpack it "
                                  f"yourself, having seen what it contains."}
            # nosec B202: the guard is the four checks ABOVE this line, none of
            # which a pattern matcher can see — _safe_members() rejects absolute
            # paths, `..` components and anything resolving outside `target`,
            # and the member/size ceilings refuse a zip bomb. B202 fires on the
            # call regardless, at HIGH severity, which is above CI's `-ll`
            # threshold: left unsuppressed it turns the lint job red on a clean
            # tree and blocks every pre-commit that touches scripts/. Suppressed
            # here rather than raised to the CI threshold, because the argument
            # is about THIS call site and not about ignoring B202 everywhere.
            zf.extractall(target)  # nosec B202
            files = len(infos)
    else:
        with tarfile.open(path) as tf:
            members = tf.getmembers()
            names = [m.name for m in members]
            bad = _safe_members(names, target)
            link = [m.name for m in members if m.issym() or m.islnk()]
            if bad or link:
                return {"archive": path.as_posix(), "extracted": False,
                        "reason": f"refused: {len(bad)} escaping member(s) and {len(link)} "
                                  f"link member(s) — tar links can point anywhere on disk"}
            total = sum(m.size for m in members)
            if len(members) > MAX_MEMBERS or total > MAX_UNCOMPRESSED_MB * 1_000_000:
                return {"archive": path.as_posix(), "extracted": False,
                        "reason": f"refused: {len(members)} members / {total / 1e6:.0f} MB "
                                  f"uncompressed exceeds the guard"}
            # filter="data" (3.12+) strips ownership/permission surprises; the
            # explicit member checks above stay, because the filter is a second
            # line and not the reason this is safe.
            try:
                tf.extractall(target, filter="data")
            except TypeError:  # pragma: no cover - Python < 3.12
                # nosec B202: same guards as the zip branch above, plus this
                # branch additionally refuses symlink and hardlink members
                # outright. Only the 3.11 fallback is flagged — the 3.12+ call
                # a line up carries filter="data" and bandit accepts it.
                tf.extractall(target)  # nosec B202
            files = len(members)
    return {"archive": path.as_posix(), "extracted": True, "into": target.as_posix(),
            "members": files}


def attach(ds_id: str, files: list[str], register: str) -> dict:
    """Hand the measured files to dataset_db.py — the only sanctioned writer."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dataset_db.py"), "--file", register,
         "attach", ds_id, *files],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout or "").strip()}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"dataset_db.py returned unreadable output: {proc.stdout[:120]}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", required=True, metavar="DS-0001",
                    help="the dataset register id the files belong to")
    ap.add_argument("--url", action="append", default=[], metavar="URL",
                    help="a direct file URL; repeatable. Defaults to the record's "
                         "download_urls")
    ap.add_argument("--out", metavar="DIR",
                    help="destination (default analysis/data/<DS-id>)")
    ap.add_argument("--register", default=DEFAULT_REGISTER)
    ap.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB,
                    help=f"per-file size cap (default {DEFAULT_MAX_MB} MB)")
    ap.add_argument("--extract", action="store_true",
                    help="unpack zip/tar archives, with path-escape and size guards")
    ap.add_argument("--attach", action="store_true",
                    help="register the fetched files through dataset_db.py attach")
    ap.add_argument("--respect-robots", action="store_true",
                    help="refuse a URL the host's robots.txt disallows. Off by default: "
                         "robots governs crawling, and a file you were pointed at is a "
                         "different act — but a bulk fetch is not, so the flag exists")
    ap.add_argument("--agent", default=AGENT)
    ap.add_argument("--plan", action="store_true",
                    help="report what would be fetched, and any refusal, without network")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.register, "--register")
    rec = _record(args.register, args.id)
    urls = candidate_urls(rec, args.url)
    out_dir = Path(args.out) if args.out else Path("analysis/data") / args.id
    require_within_cwd(out_dir.as_posix(), "--out")
    problems = licence_gate(rec)

    if args.plan:
        emit({"dataset": args.id, "name": rec.get("name"), "urls": urls,
              "into": out_dir.as_posix(), "would_refuse": problems,
              "license": rec.get("license"), "license_verified": rec.get("license_verified"),
              "note": "plan only — no request was made"}, args.json_out)
        sys.exit(2 if problems else 0)

    if problems:
        emit({"dataset": args.id, "result": "REFUSED", "problems": problems,
              "note": ("the licence is checked before the bytes are fetched, not after: "
                       "downloading is the moment it starts to matter")}, args.json_out)
        sys.exit(2)
    if requests is None:
        die("requests not installed — pip install requests")

    if args.respect_robots:
        from collection_check import robots_verdict
        for url in urls:
            verdict = robots_verdict(url, args.agent)
            if verdict.get("allowed") is False:
                emit({"dataset": args.id, "result": "REFUSED", "url": url,
                      "robots": verdict}, args.json_out)
                sys.exit(2)

    out_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = int(args.max_mb * 1_000_000)
    results, blocked = [], False
    for url in urls:
        result = fetch_one(url, out_dir, max_bytes, args.agent)
        blocked = blocked or bool(result.get("blocked"))
        results.append(result)

    fetched = [r for r in results if r.get("ok")]
    extracted = []
    if args.extract:
        for r in fetched:
            extracted.append(extract(Path(r["path"]), out_dir))

    # The fetch log lives next to the data, not in the register: the register
    # holds what the dataset IS, this holds what happened on the day it arrived.
    log_path = out_dir / "fetch-log.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({"dataset": args.id, **r}, ensure_ascii=False) + "\n")

    payload = {"dataset": args.id, "requested": len(urls), "fetched": len(fetched),
               "files": results, "log": log_path.as_posix()}
    if extracted:
        payload["extracted"] = extracted
    if args.attach and fetched:
        to_attach = [r["path"] for r in fetched]
        for ex in extracted:
            if ex.get("extracted"):
                to_attach += sorted(p.as_posix() for p in Path(ex["into"]).rglob("*")
                                    if p.is_file())
        payload["attach"] = attach(args.id, to_attach, args.register)
    elif fetched:
        payload["next"] = ("python scripts/dataset_db.py attach " + args.id + " " +
                           " ".join(r["path"] for r in fetched))
    payload["note"] = ("a SHA-256 computed as the bytes arrived, not measured off disk "
                       "afterwards — the two differ exactly when something else touched "
                       "the file in between")
    emit(payload, args.json_out)
    if blocked:
        sys.exit(3)
    sys.exit(0 if len(fetched) == len(urls) else 2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("interrupted — partial downloads are left as .part files and re-fetched "
            "cleanly on the next run", code=1)
    except OSError as e:
        die(f"failed to read or write a file — {e}")
