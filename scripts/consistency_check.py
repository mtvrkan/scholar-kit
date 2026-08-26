#!/usr/bin/env python3
"""consistency_check.py — numeric-consistency lint for the draft manuscript.

Catches the "narrated ≠ presented" defect class: a section states a count in
prose ("we trained four models", "21 features", "80 findings") that contradicts
either (a) the machine-readable analysis manifest the data-scientist emits, or
(b) the same quantity as stated elsewhere in the manuscript.

Two independent checks, both WARN-only by default (never blocks — a number can
legitimately be approximate; a human adjudicates):

  * manifest-mismatch: a prose number bound to a canonical quantity (features,
    models, samples, XAI methods, findings, …) differs from analysis/counts.json.
  * cross-section-drift: the same canonical quantity is stated with two or more
    DIFFERENT numbers across the drafts (e.g. Abstract "four models" vs Results
    "three models"). Fires even with no manifest present.

The manifest gates WHICH quantities are checked for (a): only keys present in
analysis/counts.json with an integer value AND a known noun mapping are
reconciled, so a project that emits no counts.json simply skips check (a).

Manifest schema (analysis/counts.json, written by the data-scientist agent):
  {"n_samples":5110,"n_features":21,"n_models":4,"n_test":1022,
   "n_positive":249,"n_xai_methods":3,"n_findings":80, ...}

Usage:
  python scripts/consistency_check.py [--drafts drafts/] [--manifest analysis/counts.json] [--json]
  python scripts/consistency_check.py --strict   # exit 2 if any warning (opt-in blocking)
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# \n excluded — see cite_audit.py: `[^`]*` spans paragraphs and two stray
# backticks silently blank out every number between them.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# Spelled-out numbers routinely appear in prose ("four models", "three methods").
WORDNUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
# Grouped thousands, in BOTH conventions. This is not cosmetic: without it the
# pattern below matched only the tail of a grouped number and bound the wrong
# value to a quantity. "1,572 records" was read as 572, "12,345 records" as 345,
# and — worse, because this checker's first language is Turkish — "1.572 kayıt"
# was read as the DECIMAL 1.572. A checker whose job is to catch a number the
# manuscript states two ways cannot itself misread the number; it would report a
# manifest mismatch that does not exist, or silently agree with a figure nobody
# wrote. The disambiguation rule is the one tr_style_check already uses for the
# same shape: a separator that repeats in groups of exactly three is the
# THOUSANDS separator, and the other one is then the decimal. A leading group
# starting 1-9 keeps "0.809" a decimal. "1.5" has no three-digit group and stays
# a decimal too.
_GROUPED_EN = r"[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?"     # 1,572   12,345.67
_GROUPED_TR = r"[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?"     # 1.572   12.345,67
_NUM = (r"(?P<num>" + _GROUPED_EN + r"|" + _GROUPED_TR
        + r"|\d{1,7}(?:\.\d+)?|" + "|".join(WORDNUM) + r")")

# Canonical manifest key -> the prose nouns that denote it. A prose number is
# bound to a key when it sits immediately before one of these nouns (allowing up
# to two modifier words in between, e.g. "four machine learning models").
NOUN_MAP = {
    "n_features": r"features?|predictors?|covariates?|input\s+variables?|attributes?",
    "n_models": r"models?|classifiers?|learners?|algorithms?",
    "n_samples": r"samples?|instances?|records?|observations?|data\s+points?|rows",
    # Same list without `records?`, used when a PRISMA flow is being checked —
    # see check(). Kept beside the original so the two cannot drift apart.
    "n_test": r"test\s+(?:samples?|instances?|cases?|examples?|rows|records?)",
    "n_xai_methods": (r"(?:xai|explanation|explainability|interpretability|attribution)"
                      r"\s+(?:methods?|techniques?)|explainers?"),
    "n_findings": r"findings?|evidence\s+cards?|extracted\s+findings?",
}

FLOWLESS_N_SAMPLES = r"samples?|instances?|observations?|data\s+points?|rows"


# PRISMA flow stage -> phrases that name it in prose (TR and EN). The flow's
# numbers are DERIVED from the register and drawn into the diagram by
# prisma_flow.py, but a manuscript also narrates them in sentences, and nothing
# compared the two. On the reference review the Methods section said
# "34 could not be retrieved ... 19 assessed ... 12 excluded" while the diagram,
# the abstract and the results all said 35/18/11 — the prose had been left
# behind by a register correction. Four rounds of peer review missed it; an
# external reader found it in one pass. It is exactly the drift the rest of this
# script exists to catch, one layer up.
PRISMA_PHRASES = {
    "identified": [r"kay[ıi]t tan[ıi]mland[ıi]", r"records? identified"],
    "duplicates": [r"yinelenen kay[ıi]t", r"duplicates?"],
    "excluded_screening": [r"bu a[sş]amada hari[cç] tutuldu",
                           r"eleme a[sş]amas[ıi]nda d[ıi][sş]land[ıi]",
                           r"excluded at (?:title/abstract )?screening"],
    "sought": [r"rapor eri[sş]im i[cç]in arand[ıi]", r"reports? sought"],
    "not_retrieved": [r"elde edile?med[ıi]", r"could not be retrieved"],
    "fulltext": [r"de[gğ]erlendirilen rapor say[ıi]s[ıi]",
                 r"de[gğ]erlendirilen \d+ rapor",
                 r"reports? assessed for eligibility"],
    "excluded_fulltext": [r"d[ıi][sş]lanan [cç]al[ıi][sş]ma say[ıi]s[ıi]",
                          r"gerek[cç]eleriyle d[ıi][sş]land[ıi]"],
    "included": [r"[cç]al[ıi][sş]ma dahil edildi", r"studies were included"],
}
# An HTML comment is not prose. The four siblings of this check — claim_check,
# figure_check, tr_style_check, word_budget — all read one as text until it was
# fixed, and this one was never tested either way. It matters more here than it
# sounds: the kit's own evidence binding IS an HTML comment (`<!-- EV-0045 -->`),
# so every draft written the way /draft asks is full of them, and a paragraph
# commented out during revision stays in the file on purpose.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# The PRISMA bindings are read from the RAW text in check_prisma_narration,
# before this runs, so stripping comments here does not blind that check to the
# one comment shape this script is supposed to read.


def _clean(text: str) -> str:
    return COMMENT_RE.sub("", INLINE_CODE_RE.sub("", FENCE_RE.sub("", text)))


PRISMA_BIND_RE = re.compile(
    r"<!--\s*PRISMA:\s*(?P<stage>[a-z_]+)\s*=\s*(?P<value>\d{1,7})\s*-->", re.IGNORECASE)


def check_prisma_narration(files: list[Path], counts: dict,
                           source: str = "akis kaynagi") -> dict:
    """PRISMA counts narrated in prose, against the flow's own counts.

    Binding, not guessing. The first version of this check located stage
    phrases and compared whatever number sat nearest — and Turkish syntax beat
    it: "35'i elde edilemedi (34'ü YÖK tezi)" puts the *subset* closest to the
    phrase, "76 kaydın 4'ü yinelenen" puts the duplicate count closest to the
    identification phrase. It reported ten mismatches on a manuscript whose one
    real error had already been fixed, and a lint that fires on correct prose is
    a lint nobody reads.

    So the author binds the number the way every empirical claim already binds
    its evidence card — `<!-- PRISMA: not_retrieved=35 -->` beside the sentence.
    Comparison is then exact and has no false positives at all.

    A binding nobody wrote cannot be checked, so unbound stages are REPORTED
    rather than passed over: silence must not read as agreement. That is the
    same posture template_compliance.py takes with `unchecked`/`unbound`."""
    mismatches, bound_stages = [], set()
    if not counts:
        return {"mismatches": [], "bound": [], "unbound": [], "checked": False}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in PRISMA_BIND_RE.finditer(text):
            stage, stated = m.group("stage").lower(), int(m.group("value"))
            expected = counts.get(stage)
            if expected is None:
                mismatches.append({
                    "stage": stage, "stated": stated, "expected": None,
                    "where": f.as_posix(),
                    "msg": (f"PRISMA binding names '{stage}' in {f.as_posix()}, which is "
                            f"not a stage {source} carries — check the spelling "
                            f"against {sorted(counts)}")})
                continue
            bound_stages.add(stage)
            if stated != expected:
                mismatches.append({
                    "stage": stage, "stated": stated, "expected": expected,
                    "where": f.as_posix(),
                    "msg": (f"PRISMA '{stage}' is bound as {stated} in {f.as_posix()} "
                            f"but {source} says {expected}")})
    checkable = [s for s in PRISMA_PHRASES if isinstance(counts.get(s), int)]
    return {"mismatches": mismatches,
            "bound": sorted(bound_stages),
            "unbound": sorted(set(checkable) - bound_stages),
            "checked": True}


TOTAL_LABELS = ("toplam", "total", "genel toplam", "sum")
_CELLNUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _cell_int(cell: str):
    """The integer a table cell states, or None if it states something else.

    Markdown emphasis and footnote marks are stripped first, because a total
    row is exactly where an author bolds the number. A cell holding anything
    other than one number (a range, a percentage pair, prose) returns None and
    its column is skipped — a lint that guesses at "12–18" would fire on every
    interval in the paper."""
    text = re.sub(r"[*`_]", "", cell).strip()
    if not text or text in {"—", "-", "–", "n/d", "n/a"}:
        return None
    nums = _CELLNUM_RE.findall(text)
    if len(nums) != 1 or "%" in text or "," in nums[0] or "." in nums[0]:
        return None
    # Reject a cell that carries words alongside its number ("18 kayıt"): the
    # number may be a count of something other than the column's unit.
    if re.sub(_CELLNUM_RE.pattern, "", text).strip(" ()"):
        return None
    return int(nums[0])


def check_table_totals(files: list[Path]) -> list[dict]:
    """Rows and columns labelled "Toplam"/"Total" must actually sum.

    Written after a disposition table in the reference manuscript summed to 67
    while its own prose said 68 — an off-by-one that four rounds of human peer
    review missed, in a table whose caption claimed the numbers were derived
    from a register rather than typed. Every other numeric guard in this kit
    checks prose against data; nothing checked a table against ITSELF. This is
    pure arithmetic on what is printed: it needs no register, so it works on
    any table in any project, and it cannot disagree with a source it has not
    read."""
    findings = []
    for f in files:
        lines = _clean(f.read_text(encoding="utf-8", errors="replace")).split("\n")
        block: list[list[str]] = []
        for line in lines + [""]:
            if line.lstrip().startswith("|") and line.count("|") >= 3:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):  # skip the ---|--- rule
                    block.append(cells)
                continue
            # Header + one row is enough: a single-row table with a trailing
            # "Total" column is still checkable, and requiring three lines
            # silently skipped exactly that shape.
            if len(block) >= 2:
                findings += _totals_in_block(block, f)
            block = []
    return findings


def _totals_in_block(rows: list[list[str]], f: Path) -> list[dict]:
    out, width = [], max(len(r) for r in rows)
    body = [r for r in rows[1:] if len(r) == width]

    def labelled(cells: list[str]) -> bool:
        return re.sub(r"[*`_]", "", cells[0]).strip().lower() in TOTAL_LABELS

    total_rows = [r for r in body if labelled(r)]
    data_rows = [r for r in body if not labelled(r)]
    for trow in total_rows:
        for col in range(1, width):
            stated = _cell_int(trow[col])
            if stated is None:
                continue
            parts = [_cell_int(r[col]) for r in data_rows]
            if not parts or any(p is None for p in parts):
                continue
            if sum(parts) != stated:
                out.append({
                    "kind": "table-total-row", "where": f.as_posix(),
                    "column": rows[0][col] if col < len(rows[0]) else f"#{col}",
                    "stated": stated, "sums_to": sum(parts),
                    "msg": (f"a row labelled '{trow[0]}' in {f.as_posix()} states "
                            f"{stated} for column '{rows[0][col] if col < len(rows[0]) else col}' "
                            f"but its cells sum to {sum(parts)}")})
    # Same test across a trailing total COLUMN, on every row including the total row.
    head = [re.sub(r"[*`_]", "", c).strip().lower() for c in rows[0]]
    if head and head[-1] in TOTAL_LABELS and width >= 3:
        for r in body:
            stated = _cell_int(r[width - 1])
            parts = [_cell_int(c) for c in r[1:width - 1]]
            if stated is None or not parts or any(p is None for p in parts):
                continue
            if sum(parts) != stated:
                out.append({
                    "kind": "table-total-column", "where": f.as_posix(),
                    "row": r[0], "stated": stated, "sums_to": sum(parts),
                    "msg": (f"row '{r[0]}' in {f.as_posix()} states a total of {stated} "
                            f"but its cells sum to {sum(parts)}")})
    return out


_GROUPED_EN_FULL = re.compile(r"^" + r"[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?" + r"$")
_GROUPED_TR_FULL = re.compile(r"^" + r"[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?" + r"$")


def _to_num(tok: str):
    tok = tok.lower()
    if tok in WORDNUM:
        return WORDNUM[tok]
    # Normalise grouped thousands before float() sees them: the repeated
    # three-digit separator is the grouping one, so it is dropped, and whatever
    # other separator remains is the decimal point.
    if _GROUPED_EN_FULL.match(tok):
        tok = tok.replace(",", "")
    elif _GROUPED_TR_FULL.match(tok):
        tok = tok.replace(".", "").replace(",", ".")
    f = float(tok)
    return int(f) if f.is_integer() else f


# Two things a number must not be, to be read as a count of anything.
#
# The first is the far end of an interval. "a sensitivity of 61.5-76.2 records
# of the type" put **76.2** in front of a noun this script maps to `n_samples`,
# and the manifest's real sample size was **76** — so the check reported the
# same quantity carried two different values, and both of them were the paper
# being right. The character in front of the number settles it: a digit followed
# by a dash means an interval was already open.
#
# The second is a percentage. Turkish writes the sign in front (`%76,2`), so
# that form reaches the noun with nothing in between; the English form `76.2%`
# is already excluded because the sign breaks the separator this pattern needs.
# Only one of the two conventions was ever being caught.
#
# The leading `(?<![\d.,])` is not cosmetic: without it, refusing `76.2` lets
# the scan restart inside the same token and bind the `2`, which trades one
# wrong number for a worse one.
#
# The third exclusion is a letter on the left, directly or across a hyphen,
# which makes a name rather than a quantity: "COVID-19 records" is not nineteen
# of anything and "T2-weighted records" is not two, and a medical review says
# both on most pages.
_NOT_A_COUNT = r"(?<![\d.,%A-Za-z])(?<![\d][-–—])(?<![A-Za-z][-–—])"


def find_bound_numbers(text: str, noun_pattern: str) -> list[int | float]:
    """Numbers sitting just before a noun that denotes a canonical quantity.
    Up to two modifier words may intervene ("four machine learning models").

    Only whole numbers are returned. Every key this feeds is a count — samples,
    features, models, findings — and the manifest is documented as holding
    integers for exactly that reason. There is no such thing as 76.2 records,
    so a fractional match is a misread, not a disagreement to report.
    """
    pat = re.compile(_NOT_A_COUNT + _NUM
                     + r"[\s-]+(?:[A-Za-z][A-Za-z-]*[\s-]+){0,2}?(?:" + noun_pattern + r")\b",
                     re.IGNORECASE)
    found = (_to_num(m.group("num")) for m in pat.finditer(text))
    return [n for n in found if isinstance(n, int)]


def _prisma_counts(registry_path: Path, counts_path: Path | None = None) -> tuple[dict, str]:
    """Flow counts, and the NAME of where they came from.

    The register is the default and stays the default: for most reviews it is
    the only honest source, because every record that reached a decision is in
    it. But it is not always the whole flow. A two-arm review can hold one arm's
    screening decisions outside the register — the arm's own harvest and
    eligibility files — and then the register-derived flow reports fewer reports
    assessed at full text than were actually assessed, and fewer excluded. A
    real one printed "111 assessed, 11 excluded" while one of its two arms alone
    had assessed 150 and excluded 53. Comparing the manuscript against that flow
    reports the manuscript as wrong for stating the truth.

    So `--prisma-counts <file>` may supply the flow explicitly. Two guards, both
    necessary. The counts must satisfy the flow identities, which
    `prisma_flow.check()` already tests, so a hand-written file cannot say
    whatever it likes. And the source is RETURNED and printed in the report,
    because a check that can be pointed at a file of the author's choosing has
    to say when it has been — silently agreeing with a supplied number is not a
    check, it is a mirror.
    """
    if counts_path is not None and counts_path.exists():
        try:
            counts = json.loads(counts_path.read_text(encoding="utf-8"))
            if isinstance(counts, dict) and "counts" in counts:
                counts = counts["counts"]
            import prisma_flow
            # `excluded_reasons` bu denetim icin istege baglidir; eksikligi bir
            # akis hatasi degildir ve butun consistency_check'i oldurmemelidir.
            # prisma_flow.check() onu sart kosuyor, o yuzden bir kopya uzerinde
            # bosla tamamlanir — orijinal dosyaya dokunulmaz.
            probe = dict(counts)
            probe.setdefault("excluded_reasons", {})
            problems = prisma_flow.check(probe)
            if problems:
                return {}, f"{counts_path.as_posix()} REDDEDILDI: {problems}"
            return counts, counts_path.as_posix()
        except (ValueError, OSError, ImportError) as e:
            return {}, f"{counts_path.as_posix()} okunamadi: {e}"
    if not registry_path.exists():
        return {}, "kaynak yok"
    try:
        import prisma_flow
        from lib_common import read_jsonl
        return prisma_flow.derive_counts(read_jsonl(registry_path)), registry_path.as_posix()
    except Exception:
        return {}, "kaynak okunamadi"


def check(drafts_dir: Path, manifest_path: Path,
          registry_path: Path = Path("sources/registry.jsonl"),
          prisma_counts_path: Path | None = None):
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            die(f"{manifest_path} is not valid JSON — {e.msg}")

    files = sorted(p for p in drafts_dir.glob("**/*.md")
                   if p.exists() and p.name != "STATUS.md") if drafts_dir.exists() else []

    prisma_counts, prisma_source = _prisma_counts(registry_path, prisma_counts_path)

    # "records" is a PRISMA flow word before it is a dataset word, and in a review
    # it legitimately takes many values at once: one arm identifies 1,572, the
    # register holds 68 from the other arm, and both sentences are correct. The
    # drift check read them as one quantity and reported a manuscript as
    # inconsistent for saying two true things. Where the flow is actually being
    # checked — a register or a counts file resolved, bindings compared stage by
    # stage — that vocabulary already has an owner, so n_samples gives it up.
    # With no flow to check, the word goes back to meaning sample size.
    nouns = dict(NOUN_MAP)
    if prisma_counts:
        nouns["n_samples"] = FLOWLESS_N_SAMPLES

    # key -> list of (number, section-file) occurrences across the manuscript
    occ: dict[str, list[tuple]] = {k: [] for k in nouns}
    for f in files:
        text = _clean(f.read_text(encoding="utf-8", errors="replace"))
        for key, noun in nouns.items():
            for n in find_bound_numbers(text, noun):
                occ[key].append((n, f.as_posix()))

    manifest_mismatch = []
    for key, _noun in nouns.items():
        if key not in manifest:
            continue
        expected = manifest[key]
        if not isinstance(expected, (int, float)) or isinstance(expected, bool):
            continue
        for n, where in occ[key]:
            if n != expected:
                manifest_mismatch.append({
                    "quantity": key, "stated": n, "manifest": expected,
                    "where": where,
                    "msg": f"'{n}' stated for {key} in {where} but analysis/counts.json says {expected}"})

    cross_section_drift = []
    for key in nouns:
        distinct = {n for n, _ in occ[key]}
        if len(distinct) > 1:
            cross_section_drift.append({
                "quantity": key,
                "values": sorted(distinct, key=lambda x: (isinstance(x, float), x)),
                "occurrences": [{"value": n, "where": w} for n, w in occ[key]],
                "msg": f"{key} stated with differing values {sorted(distinct, key=str)} across sections"})

    # The message names the source it actually compared against. It used to say
    # "the register-derived flow" unconditionally, which was a false statement
    # whenever --prisma-counts had been used — and the whole reason that flag
    # exists is that the register is sometimes not the flow.
    prisma = check_prisma_narration(files, prisma_counts, prisma_source)
    table_totals = check_table_totals(files)

    return {
        "files_scanned": [f.as_posix() for f in files],
        "manifest_present": bool(manifest),
        "manifest_mismatch": manifest_mismatch,
        "cross_section_drift": cross_section_drift,
        "prisma": dict(prisma, source=prisma_source),
        "table_totals": table_totals,
        "warnings": (len(manifest_mismatch) + len(cross_section_drift)
                     + len(prisma["mismatches"]) + len(table_totals)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--manifest", default="analysis/counts.json")
    ap.add_argument("--registry", default="sources/registry.jsonl",
                    help="PRISMA counts are derived from here and compared with the prose")
    ap.add_argument("--prisma-counts", default=None,
                    help="explicit flow counters (JSON) when the flow is not "
                         "register-derived; must satisfy the flow identities and "
                         "the source is named in the report")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.drafts, "--drafts")
    require_within_cwd(args.manifest, "--manifest")
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    require_within_cwd(args.registry, "--registry")
    if args.prisma_counts:
        require_within_cwd(args.prisma_counts, "--prisma-counts")
    result = check(Path(args.drafts), Path(args.manifest), Path(args.registry),
                   Path(args.prisma_counts) if args.prisma_counts else None)
    emit(result, True)
    sys.exit(2 if (args.strict and result["warnings"]) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"a draft file is not valid UTF-8 — {e}")
