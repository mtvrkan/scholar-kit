#!/usr/bin/env python3
"""update_data.py — refresh data/ index datasets (SCImago SJR, DOAJ, Scopus sources).

Called by INSTALL.sh --update-data and INSTALL.ps1 -UpdateData; also runnable
directly: python scripts/update_data.py [--dir data]
SCImago requires a browser-like User-Agent (plain clients get HTTP 403). The Scopus
source list has no permanent URL — Elsevier republishes a dated .xlsx asset monthly
on the Scopus content page; this script scrapes the current link from that page,
downloads it, and converts the "Active" rows of the main sheet to a CSV matching
venue_check.py's expected columns (title,issn,eissn).
Exit codes: 0 all downloads ok · 1 all three failed · 2 one or two failed (partial).
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

# Imported at module level (not function-local like lib_common's own copy)
# because the test suite monkeypatches `update_data.requests.get` directly —
# but guarded so a missing `requests` package surfaces as a clean die() from
# main() instead of a raw ModuleNotFoundError before argparse even runs.
try:
    import requests
except ImportError:
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, http_get_with_retry, require_within_cwd, write_bytes_atomic, write_text_atomic  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
SCIMAGO_UA = {**UA, "Referer": "https://www.scimagojr.com/journalrank.php"}
RETRIES = 3


def _get(url: str, headers: dict, timeout: int) -> "requests.Response":
    """These downloads run for 120-300s each at install time, so a single
    dropped connection shouldn't fail the whole dataset."""
    return http_get_with_retry(url, retries=RETRIES, backoff=2.0, timeout=timeout, headers=headers)


def fetch(url: str, dest: Path, timeout: int, headers: dict = UA) -> bytes:
    r = _get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    write_bytes_atomic(dest, r.content)
    rows = r.content.count(b"\n")
    print(f"  [ok] {dest.as_posix()} ({rows} rows)", file=sys.stderr)
    return r.content


def fetch_scopus(dest_dir: Path, timeout: int) -> None:
    """Discover this month's Scopus source-list .xlsx from the content page,
    download it, and convert the main sheet's Active rows to scopus.csv."""
    page = _get("https://www.elsevier.com/products/scopus/content",
                headers=UA, timeout=timeout)
    page.raise_for_status()
    m = re.search(r'href="(//downloads\.ctfassets\.net/[^"]*ext_list[^"]*\.xlsx)"', page.text)
    if not m:
        raise RuntimeError("could not find 'ext_list*.xlsx' link on the Scopus content page "
                           "(page layout may have changed)")
    url = "https:" + m.group(1)
    xlsx = dest_dir / "_scopus_raw.xlsx"
    fetch(url, xlsx, timeout)

    from openpyxl import load_workbook
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]  # "Scopus Sources <Month Year>" — title/ISSN/EISSN/status
        rows = ws.iter_rows(values_only=True)
        header = [str(h or "").strip().lower() for h in next(rows)]
        try:
            i_title = header.index("source title")
            i_issn = header.index("issn")
            i_eissn = header.index("eissn")
            i_status = header.index("active or inactive")
        except ValueError as e:
            raise RuntimeError(f"unexpected Scopus sheet columns: {header}") from e

        out = dest_dir / "scopus.csv"
        n = 0
        # Build the whole CSV in memory first — writing directly to `out` with
        # a truncating file handle means an exception partway through this
        # loop (a malformed row, an interrupted process) leaves `out` holding
        # only a header + partial rows, permanently overwriting the previously
        # complete scopus.csv. Only touch the destination once the full
        # conversion has succeeded, via an atomic write.
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["title", "issn", "eissn"])
        for row in rows:
            if not row or len(row) <= i_status:
                continue
            if str(row[i_status] or "").strip().lower() != "active":
                continue
            w.writerow([row[i_title] or "", row[i_issn] or "", row[i_eissn] or ""])
            n += 1
    finally:
        wb.close()
    write_text_atomic(out, buf.getvalue())
    xlsx.unlink(missing_ok=True)
    print(f"  [ok] {out.as_posix()} ({n} active sources, source: {url.rsplit('/', 1)[-1]})",
          file=sys.stderr)


def main():
    if requests is None:
        die("requests not installed — pip install requests")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="data")
    args = ap.parse_args()
    require_within_cwd(args.dir, "--dir")
    d = Path(args.dir)
    d.mkdir(parents=True, exist_ok=True)
    results = {}
    try:
        fetch("https://www.scimagojr.com/journalrank.php?out=xls", d / "scimago.csv", 120,
              headers=SCIMAGO_UA)
        results["scimago"] = "ok"
    except Exception as e:
        print(f"  [fail] SCImago download: {e}", file=sys.stderr)
        results["scimago"] = f"fail: {e}"
    try:
        fetch("https://doaj.org/csv", d / "doaj.csv", 300)
        results["doaj"] = "ok"
    except Exception as e:
        print(f"  [fail] DOAJ download: {e}", file=sys.stderr)
        results["doaj"] = f"fail: {e}"
    try:
        fetch_scopus(d, 120)
        results["scopus"] = "ok"
    except Exception as e:
        print(f"  [fail] Scopus download: {e}", file=sys.stderr)
        print("         manual fallback: https://www.elsevier.com/products/scopus/content ->", file=sys.stderr)
        print("         download the 'Scopus Sources' .xlsx, save Active rows as", file=sys.stderr)
        print("         title,issn,eissn -> data/scopus.csv", file=sys.stderr)
        results["scopus"] = f"fail: {e}"
    print("  [note] WoS MJL has no bulk export — venue_check reports 'unknown'; the agent", file=sys.stderr)
    print("         WebFetches mjl.clarivate.com and records via venue_check.py --set-wos", file=sys.stderr)

    failures = sum(1 for v in results.values() if v != "ok")
    emit({"results": results, "failures": failures}, True)
    if failures == 3:
        print("  [fail] all three index downloads failed — venue_check.py will report "
              "'unknown' for everything until this is re-run or fixed manually", file=sys.stderr)
        sys.exit(1)
    elif failures:
        print(f"  [warn] {failures} of 3 index downloads failed — venue_check.py "
              f"coverage will be partial until this is re-run", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
