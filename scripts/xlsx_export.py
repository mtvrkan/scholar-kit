#!/usr/bin/env python3
"""xlsx_export.py — registry + cards + venues + extracts → multi-sheet styled Excel workbook.

Sheets (choose with --sheet, default all):
  screening   one row per registry record: include/exclude status + reason + db + venue class
  extraction  one row per source with method/dataset/metrics/results/limitations (from cards)
  matrix      synthesis matrix: theme (tag) × source, cells = card IDs
  venues      venue quality: ISSN, WoS class, Scopus, TR Dizin, quartile (conditionally colored)
  prisma      PRISMA counter summary (identified/dedup/screened/excluded/included)
  queries     executed search queries per database (from sources/search-log.jsonl)
  slr         detailed SLR sheet (hocamdan format): core columns + dynamic per-project
              fields from evidence/extracts/*.json + include/exclude + notes;
              PLUS one per-database sheet (db:scopus, db:wos, ...) partitioning the registry

Styling: bold header row, frozen panes (A2), auto-filter, sensible column widths,
quartile conditional fill (Q1 green → Q4 red).

Usage:
  python scripts/xlsx_export.py [--out exports/literature-matrix.xlsx] [--sheet all]
    [--registry sources/registry.jsonl] [--cards evidence/cards.jsonl]
    [--venues sources/venues.jsonl] [--extracts evidence/extracts]
    [--search-log sources/search-log.jsonl] [--json]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

# Optional dependency; guarded so a missing openpyxl surfaces as a clean
# die() message via main() instead of a raw ModuleNotFoundError before
# argparse even runs. The style constants below are only constructed when
# the import succeeds — PatternFill/Font are real classes evaluated at
# MODULE LOAD time (not inside a function), so a naive try/except around
# just the import would leave these next few lines to raise their own
# uncaught TypeError against a None class immediately after.
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    Workbook = Alignment = Font = PatternFill = get_column_letter = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd, write_bytes_atomic

if PatternFill is not None:
    HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    Q_FILL = {"Q1": PatternFill("solid", fgColor="C6EFCE"),
              "Q2": PatternFill("solid", fgColor="E2EFDA"),
              "Q3": PatternFill("solid", fgColor="FFEB9C"),
              "Q4": PatternFill("solid", fgColor="FFC7CE")}
else:
    HEADER_FILL = HEADER_FONT = None
    Q_FILL = {}


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _escape_formula(v):
    """Neutralize spreadsheet formula injection (CWE-1236): openpyxl infers a
    live formula from any string cell value starting with =/+/-/@ (or a
    leading tab/CR, which Excel also treats as a formula lead-in once
    trimmed). Registry/card/venue fields flow in from web-fetched metadata
    (Crossref, OpenAlex, scraped venue lists) that this tool never asks a
    human to type — a title or note field starting with one of these chars
    must stay literal text, not become an executable formula when opened."""
    if isinstance(v, str) and v.startswith(_FORMULA_PREFIXES):
        return "'" + v
    return v


_SCALAR_TYPES = (str, int, float, bool, type(None))


def _stringify(v):
    """Coerce a value to something openpyxl can actually write into a cell.
    openpyxl only accepts scalars (str/int/float/bool/None/datetime); a field
    that's unexpectedly a list/dict (wrong-shaped upstream data — a registry
    'title'/'authors' or an evidence card 'claim' holding a list instead of a
    string) crashes `ws.append()`/string-join calls with a raw TypeError.
    Falling back to a JSON string keeps the export running and the odd value
    visibly inspectable in the sheet, instead of aborting the whole multi-sheet
    export over one bad record."""
    if isinstance(v, _SCALAR_TYPES):
        return v
    return json.dumps(v, ensure_ascii=False)


def _safe_row(row: list) -> list:
    return [_escape_formula(_stringify(v)) for v in row]


def _textify(v):
    """Like _stringify, but for values that get "; ".join()-ed together into a
    single text cell (methods/findings/limits) rather than written as their
    own cell — there, None must become "" (join() rejects None), not stay None."""
    if isinstance(v, str):
        return v
    if v is None:
        return ""
    return json.dumps(v, ensure_ascii=False)


def _as_list(v):
    """Coerce a field expected to be a list; a non-list (hand-edited/buggy
    upstream record) becomes [] rather than crashing `for x in v`."""
    return v if isinstance(v, list) else []


def _as_dict(v):
    """Coerce a field expected to be an object; a non-dict becomes {} rather
    than crashing `v.items()`/`v.get(...)`."""
    return v if isinstance(v, dict) else {}


def _require_objects(records: list, label: str) -> list:
    """read_jsonl only guarantees each line is syntactically valid JSON, not
    that it is a JSON OBJECT — a bare array or scalar line (e.g. `["a","b"]`)
    parses fine, then crashes with a raw AttributeError the first time a field
    is read via `.get()`. Reject non-object records with a clean die() before
    any sheet builder touches them."""
    for i, r in enumerate(records, 1):
        if not isinstance(r, dict):
            die(f"{label}: record {i} is not a JSON object (got {type(r).__name__}) — fix the file")
    return records


def style_sheet(ws, n_cols: int, widths: list[int] | None = None):
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = \
            (widths[col - 1] if widths and col <= len(widths) else 18)
    ws.freeze_panes = "A2"
    if ws.max_row >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(n_cols)}{max(ws.max_row, 2)}"


SCREEN_COLS = ["id", "title", "authors", "year", "venue", "doi", "db", "lang",
               "relevance", "status", "reason", "wos_index", "quartile"]
SCREEN_WIDTHS = [10, 55, 30, 7, 30, 24, 9, 6, 9, 10, 40, 10, 8]


def _screen_row(r):
    vm = _as_dict(r.get("venue_meta"))
    return [r.get("id"), r.get("title"), _authors(r), r.get("year"), r.get("venue"),
            r.get("doi"), r.get("db"), r.get("lang"), r.get("relevance_score"),
            r.get("status"), r.get("reason") or r.get("one_line_why"),
            vm.get("wos_index"), vm.get("quartile")]


_ILLEGAL_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")


def sanitize_sheet_title(title: str, wb) -> str:
    """Excel sheet titles ban \\ / * ? : [ ] and cap at 31 chars; a registry's
    free-text `db` field (e.g. "IEEE/Xplore") would otherwise crash the whole
    export. Replace illegal chars, truncate, and disambiguate collisions that
    truncation/replacement can introduce (append -2, -3, ... )."""
    clean = _ILLEGAL_SHEET_CHARS.sub("-", title).strip() or "sheet"
    clean = clean[:31]
    existing = set(wb.sheetnames)
    candidate = clean
    n = 2
    while candidate in existing:
        suffix = f"-{n}"
        candidate = clean[: 31 - len(suffix)] + suffix
        n += 1
    return candidate


def sheet_screening(wb, registry, title="screening", subset=None):
    ws = wb.create_sheet(sanitize_sheet_title(title, wb))
    ws.append(SCREEN_COLS)
    for r in (subset if subset is not None else registry):
        ws.append(_safe_row(_screen_row(r)))
    style_sheet(ws, len(SCREEN_COLS), SCREEN_WIDTHS)


def sheet_extraction(wb, registry, cards):
    ws = wb.create_sheet("extraction")
    ws.append(["source", "title", "year", "methods", "dataset", "metrics", "key_results",
               "limitations", "card_ids"])
    by_source: dict[str, list[dict]] = {}
    for c in cards:
        by_source.setdefault(c.get("source", "?"), []).append(c)
    reg_by_key = {}
    for r in registry:
        k = r.get("bib_key") or r.get("id")
        if k:
            reg_by_key[k] = r
    for source, cs in sorted(by_source.items()):
        reg = reg_by_key.get(source, {})
        # A card's "claim" is normally a string; a wrong-shaped card (claim as
        # a list/dict) would crash "; ".join(...) with a raw TypeError since
        # the generator yields the raw value, not a coerced string.
        methods = "; ".join(_textify(c.get("claim", "")) for c in cs if c.get("type") == "method")[:500]
        metrics = "; ".join(f"{k}={v}" for c in cs for k, v in _as_dict(c.get("metrics")).items())[:500]
        findings = "; ".join(_textify(c.get("claim", "")) for c in cs
                             if c.get("type") in ("finding", "statistic"))[:500]
        limits = "; ".join(_textify(c.get("claim", "")) for c in cs if c.get("type") == "gap")[:500]
        dataset = next((str(_as_dict(c.get("metrics")).get("dataset", "")) for c in cs
                        if _as_dict(c.get("metrics")).get("dataset")), "")
        ws.append(_safe_row([source, reg.get("title", ""), reg.get("year", ""), methods, dataset,
                             metrics, findings, limits, ", ".join(c.get("id", "") for c in cs)]))
    style_sheet(ws, 9, [18, 45, 7, 45, 16, 35, 50, 40, 24])


def _tags_of(c):
    """Coerce a card's tags to a list of hashable strings — a wrong-shaped tag
    (e.g. a dict instead of a string) crashes the `{t for c in cards for t in
    ...}` set comprehension below with a raw 'unhashable type' TypeError."""
    return [t if isinstance(t, str) else json.dumps(t, ensure_ascii=False) for t in _as_list(c.get("tags"))]


def sheet_matrix(wb, cards):
    ws = wb.create_sheet("matrix")
    tags = sorted({t for c in cards for t in _tags_of(c)})
    sources = sorted({c.get("source", "?") for c in cards})
    ws.append(_safe_row(["theme \\ source"] + sources))
    for t in tags:
        row = [t]
        for s in sources:
            ids = [c.get("id", "") for c in cards if c.get("source") == s and t in _tags_of(c)]
            row.append(", ".join(ids))
        ws.append(_safe_row(row))
    style_sheet(ws, len(sources) + 1, [22] + [16] * len(sources))


def sheet_venues(wb, venues):
    ws = wb.create_sheet("venues")
    ws.append(["venue", "issn", "wos_index", "scopus", "tr_dizin", "doaj",
               "quartile", "sjr", "predatory_flag", "checked_at"])
    for v in venues:
        ws.append(_safe_row([v.get("display_name") or v.get("title_query"), v.get("issn"),
                             v.get("wos_index"), v.get("scopus"), v.get("tr_dizin"), v.get("doaj"),
                             v.get("quartile"), v.get("sjr"), v.get("predatory_flag"), v.get("checked_at")]))
    for row in ws.iter_rows(min_row=2, min_col=7, max_col=7):
        for cell in row:
            q = str(cell.value or "").strip().upper()
            if q in Q_FILL:
                cell.fill = Q_FILL[q]
    style_sheet(ws, 10, [40, 12, 10, 8, 9, 7, 9, 7, 13, 11])


def sheet_prisma(wb, registry):
    ws = wb.create_sheet("prisma")
    status = {}
    for r in registry:
        status[r.get("status", "?")] = status.get(r.get("status", "?"), 0) + 1
    ws.append(["stage", "count"])
    ws.append(["records identified", len(registry)])
    for k in sorted(status):
        ws.append([f"status: {k}", status[k]])
    excluded = [r for r in registry if r.get("status") == "excluded"]
    reasons = {}
    for r in excluded:
        reasons[r.get("reason", "unspecified")] = reasons.get(r.get("reason", "unspecified"), 0) + 1
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        ws.append(_safe_row([f"excluded — {reason}", n]))
    style_sheet(ws, 2, [45, 10])


def _authors(r):
    a = r.get("authors")
    if isinstance(a, list):
        # Each item is normally a name string; a wrong-shaped record (e.g. a
        # list of {"family":...} objects) would crash "; ".join(a) with a raw
        # TypeError before this value ever reaches _safe_row's scalar coercion.
        return "; ".join(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in a)
    return a or ""


def sheet_queries(wb, search_log):
    ws = wb.create_sheet("queries")
    ws.append(["date", "db", "query", "hits", "note"])
    for q in search_log:
        ws.append(_safe_row([q.get("date"), q.get("db"), q.get("query"), q.get("hits"), q.get("note")]))
    style_sheet(ws, 5, [11, 10, 90, 8, 30])


def sheet_slr(wb, registry, extracts):
    """Detailed SLR sheet (hocamdan literature.xlsx pattern): fixed core columns +
    the union of per-project dynamic fields found in extracts' "fields" objects,
    in first-seen order. One row per registry record that has an extract or is
    included; plus per-db partition sheets."""
    core = ["registry_id", "bib_key", "title", "year", "venue", "type", "doi", "db"]
    dyn: list = []
    by_key = {}
    for ex in extracts:
        by_key[ex.get("key")] = ex
        for f in _as_dict(ex.get("fields")):
            if f not in dyn:
                dyn.append(f)
    tail = ["abstract_summary", "key_references", "include", "notes"]

    ws = wb.create_sheet("slr")
    ws.append(_safe_row(core + dyn + tail))
    for r in registry:
        if r.get("status") == "duplicate":
            continue
        ex = by_key.get(r.get("bib_key")) or by_key.get(r.get("id")) or {}
        if not ex and r.get("status") != "included":
            continue
        sections = _as_dict(ex.get("sections"))
        refs = "; ".join(
            (kr.get("bib_key") or kr.get("doi") or kr.get("text", ""))[:60]
            for kr in _as_list(ex.get("key_references")) if isinstance(kr, dict))
        row = [r.get("id"), r.get("bib_key"), r.get("title"), r.get("year"),
               r.get("venue"), r.get("type") or "", r.get("doi"), r.get("db")]
        row += [_as_dict(ex.get("fields")).get(f, "") for f in dyn]
        row += [(sections.get("abstract") or "")[:500], refs,
                "Dahil" if r.get("status") == "included" else "Hariç",
                r.get("reason") or ""]
        ws.append(_safe_row(row))
    n = len(core) + len(dyn) + len(tail)
    style_sheet(ws, n, [10, 16, 45, 6, 25, 14, 22, 9] + [22] * len(dyn) + [60, 40, 8, 30])

    # per-database partition sheets (professor's "Scopus SLR" / "WOS SLR" pattern)
    dbs = sorted({r.get("db") for r in registry if r.get("db")})
    for db in dbs:
        subset = [r for r in registry if r.get("db") == db]
        sheet_screening(wb, registry, title=f"db-{db}", subset=subset)


def main():
    if Workbook is None:
        die("openpyxl not installed — pip install openpyxl")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="exports/literature-matrix.xlsx")
    ap.add_argument("--sheet", default="all",
                    choices=["all", "screening", "extraction", "matrix", "venues",
                             "prisma", "queries", "slr"])
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--cards", default="evidence/cards.jsonl")
    ap.add_argument("--venues", default="sources/venues.jsonl")
    ap.add_argument("--extracts", default="evidence/extracts")
    ap.add_argument("--search-log", dest="search_log", default="sources/search-log.jsonl")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.out, "--out")
    for path_str, flag in ((args.registry, "--registry"), (args.cards, "--cards"),
                           (args.venues, "--venues"), (args.extracts, "--extracts"),
                           (args.search_log, "--search-log")):
        require_within_cwd(path_str, flag)

    registry = _require_objects(read_jsonl(args.registry), args.registry)
    cards = _require_objects(read_jsonl(args.cards), args.cards)
    venues = _require_objects(read_jsonl(args.venues), args.venues)
    search_log = _require_objects(read_jsonl(args.search_log), args.search_log)
    extracts = []
    malformed_extracts = []
    extracts_dir = Path(args.extracts)
    for p in sorted(extracts_dir.glob("*.json")) if extracts_dir.exists() else []:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # A truncated/corrupt extract (e.g. from a crashed source-analyst run) must
            # not silently vanish from the export — qa-auditor's own check isn't
            # enforced by this script, so this is the only guaranteed visibility.
            malformed_extracts.append(p.name)
            continue
        # A valid-JSON-but-non-object extract (e.g. a bare array) would crash
        # sheet_slr's `ex.get(...)` with a raw AttributeError — treat it as
        # malformed (skip + warn), same as a parse failure, rather than crash.
        if not isinstance(obj, dict):
            malformed_extracts.append(p.name)
            continue
        extracts.append(obj)
    if malformed_extracts:
        print(f"WARNING: {len(malformed_extracts)} malformed extract file(s) skipped: "
              f"{', '.join(malformed_extracts)}", file=sys.stderr)
    if not registry and not cards:
        die(f"nothing to export — {args.registry} and {args.cards} are both empty")

    wb = Workbook()
    wb.remove(wb.active)
    want = args.sheet
    if want in ("all", "screening"):
        sheet_screening(wb, registry)
    if want in ("all", "extraction"):
        sheet_extraction(wb, registry, cards)
    if want in ("all", "matrix"):
        sheet_matrix(wb, cards)
    if want in ("all", "venues"):
        sheet_venues(wb, venues)
    if want in ("all", "prisma"):
        sheet_prisma(wb, registry)
    if want in ("all", "queries") and search_log:
        sheet_queries(wb, search_log)
    if want in ("all", "slr") and (extracts or any(r.get("db") for r in registry)):
        sheet_slr(wb, registry, extracts)

    if not wb.worksheets:
        die(f"nothing to export for --sheet {want} — no matching data found "
            f"(queries needs {args.search_log}; slr needs extracts or a registry 'db' field)")

    out = Path(args.out)
    buf = io.BytesIO()
    wb.save(buf)
    write_bytes_atomic(out, buf.getvalue())
    emit({"written": out.as_posix(), "sheets": wb.sheetnames,
          "rows": {ws.title: ws.max_row - 1 for ws in wb.worksheets},
          "malformed_extracts": malformed_extracts}, True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to write the xlsx file — {e}")
