#!/usr/bin/env python3
"""temporal_check.py — implausible dates and anachronistic-citation lint.

Two independent, deterministic (no-network) checks, both WARN-only by default
(a human adjudicates; `--strict` opts into blocking):

  * bib temporal sanity: a references.bib entry with a publication year in the
    future (typo protection — a transposed digit like 2026 vs 2016 is a real,
    otherwise-invisible error class), or a `fetched_at` date earlier than the
    entry's own `year` (impossible: metadata cannot have been fetched for a
    paper before it existed — a sign of hand-tampered or corrupted data, since
    doi2bib.py always stamps fetched_at at write time).
  * card-vs-source year mismatch: an evidence card whose claim/detail text
    mentions an explicit year Y that postdates its own cited source's
    publication year by more than one year (a one-year allowance covers the
    ordinary preprint-then-journal-version lag). A card cannot truthfully
    attribute a Y-dated finding to a source published long before Y — either
    the claim describes something the source didn't actually report, or the
    card is bound to the wrong source. This mirrors the "anachronistic
    citation" failure mode (citing a source as evidence for something that
    postdates it) documented in AI-assisted-research failure-mode literature,
    reimplemented here as a plain text/year cross-check rather than requiring
    any external tool.

This does NOT attempt full semantic anachronism detection (e.g. tense/deictic
misuse, causal inversion) — that requires reading comprehension no regex can
do; a human (or reviewer-critic) still owns that judgment. This script only
catches the arithmetic-checkable subset.

Usage:
  python scripts/temporal_check.py [--bib bib/references.bib] [--cards evidence/cards.jsonl]
      [--registry sources/registry.jsonl] [--strict] [--json]
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, parse_bibtex, read_jsonl, require_within_cwd

# 21xx is deliberately NOT a year here. No bibliography carries a 22nd-century
# publication date, and no plausible typo produces one (a transposed 2016 gives
# 2061 or 2106-shaped digits that 20xx already covers), while the range is full
# of ordinary quantities: a card reporting a dataset of 2111 images was being
# read as a claim about the year 2111 and flagged as an anachronism.
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")

# The 21xx exclusion above is a range hack for one instance of a general class:
# a four-digit number is only a year when its CONTEXT says so. Two contexts say
# it is not, and both occur constantly in the literature this kit is built for.
#
# 1. A quantity or a tensor dimension. "2048 features" is the Global Average
#    Pooling width of ResNet-50 — the single most common feature dimension in
#    computer vision, and the only power of two inside the retained 20xx range.
#    A DL systematic review meets it in almost every extraction card. Likewise
#    "2016 images", "1998 patients", "2020 eyes".
QUANTITY_AFTER_RE = re.compile(
    r"^\s*(?:-\s*(?:d|boyut\w*)\b|[x×]\s*\d"
    r"|(?:features?|dimension\w*|channels?|units?|neurons?|filters?|weights?"
    r"|images?|photographs?|scans?|samples?|records?|observations?|instances?"
    r"|patients?|participants?|subjects?|eyes?|epochs?|iterations?|steps?"
    r"|öznitelik\w*|ozellik\w*|özellik\w*|boyut\w*|kanal\w*|nöron\w*|noron\w*"
    r"|görüntü\w*|goruntu\w*|foto\w*|hasta\w*|katılımcı\w*|katilimci\w*"
    r"|göz\w*|goz\w*|örnek\w*|ornek\w*|kayıt\w*|kayit\w*|adım\w*|adim\w*)\b)",
    re.IGNORECASE)
# 2. An author-year citation. A card may legitimately name ANOTHER study —
#    "this mirrors Polater & Işık 2024" inside a card whose own source is from
#    2021 is a cross-reference, not a claim the 2021 paper made about 2024.
#    Anchored on a capitalised surname (optionally a two-author pair) so an
#    ordinary sentence ending in a capitalised word plus a year does not match.
CITATION_BEFORE_RE = re.compile(
    r"(?P<surname>[A-ZÇĞİÖŞÜ][\wçğıöşü'’-]+)"            # Surname
    r"(?:\s*(?:&|and|ve)\s*[A-ZÇĞİÖŞÜ][\wçğıöşü'’-]+)?"  # optional second author
    r"(?:\s+et\s+al\.?)?"                                # or "et al."
    r"[,\s]+$")
# A capital letter is not enough to make a word a surname, and a sentence
# usually starts with one. "The 2022 recalibration protocol is applied" would
# otherwise be exempted as a citation — an over-broad exemption is the same
# defect as the false positive it was meant to remove, pointing the other way.
NOT_A_SURNAME = {
    "the", "this", "that", "these", "those", "a", "an", "its", "their", "our",
    "his", "her", "we", "they", "it", "in", "on", "at", "by", "for", "from",
    "since", "until", "during", "after", "before", "between", "both", "all",
    "each", "every", "no", "only", "same", "first", "second", "third", "last",
    "new", "recent", "current", "early", "late", "one", "two", "three",
    # "her" is already listed above as the English possessive; the same string
    # is Turkish for "every", so one entry covers both languages.
    "bu", "şu", "o", "bir", "aynı", "ayni", "ilk", "son", "yeni",
    "hiç", "hic", "tüm", "tum", "bütün", "butun", "iki", "üç", "uc", "dört",
    "yalnız", "yalniz", "sadece", "ancak", "ayrıca", "ayrica", "böylece",
    "boylece", "dolayısıyla", "dolayisiyla", "buna", "bunun", "onun",
}


def _is_a_year_here(text: str, m: re.Match) -> bool:
    """False when the surrounding words say this number is not a year."""
    if QUANTITY_AFTER_RE.match(text[m.end():m.end() + 40]):
        return False
    cm = CITATION_BEFORE_RE.search(text[max(0, m.start() - 60):m.start()])
    if cm and cm.group("surname").lower() not in NOT_A_SURNAME:
        return False
    return True


def _bib_year(fields: dict) -> int | None:
    m = re.search(r"\d{4}", fields.get("year", "") or "")
    return int(m.group(0)) if m else None


def check_bib_temporal(bib_path: Path, today: datetime.date) -> list[dict]:
    if not bib_path.exists():
        return []
    entries = parse_bibtex(bib_path.read_text(encoding="utf-8"))
    problems = []
    for e in entries:
        fields = e["fields"]
        year = _bib_year(fields)
        if year is not None and year > today.year:
            problems.append({
                "kind": "future-year", "key": e["key"], "year": year,
                "msg": f"{e['key']}: publication year {year} is in the future "
                       f"(today is {today.isoformat()}) — check for a transposed digit"})
        fetched_at = fields.get("fetched_at", "").strip()
        if fetched_at and year is not None:
            try:
                fetched_year = datetime.date.fromisoformat(fetched_at).year
                if fetched_year < year:
                    problems.append({
                        "kind": "fetched-before-published", "key": e["key"],
                        "year": year, "fetched_at": fetched_at,
                        "msg": f"{e['key']}: fetched_at {fetched_at} predates its own "
                               f"publication year {year} — impossible, data may be corrupted"})
            except ValueError:
                pass  # malformed fetched_at is bib_doctor's concern, not this check's
    return problems


def check_card_year_anachronism(cards_path: Path, registry_path: Path) -> list[dict]:
    if not cards_path.exists():
        return []
    cards = read_jsonl(cards_path)
    registry = read_jsonl(registry_path) if registry_path.exists() else []
    # any source identifier (bib_key or SRC id) -> registry year, if recorded
    year_of: dict[str, int] = {}
    for r in registry:
        y = r.get("year")
        if not isinstance(y, int):
            continue
        if r.get("bib_key"):
            year_of[r["bib_key"]] = y
        if r.get("id"):
            year_of[r["id"]] = y

    problems = []
    for c in cards:
        src = c.get("source")
        if not src or src not in year_of:
            continue
        src_year = year_of[src]
        text = " ".join(str(c.get(f, "")) for f in ("claim", "detail"))
        for m in YEAR_RE.finditer(text):
            if not _is_a_year_here(text, m):
                continue
            mentioned = int(m.group(0))
            if mentioned - src_year > 1:
                problems.append({
                    "kind": "card-year-anachronism", "card": c.get("id"), "source": src,
                    "source_year": src_year, "mentioned_year": mentioned,
                    "msg": f"{c.get('id')}: mentions year {mentioned}, but its source "
                           f"'{src}' was published in {src_year} — confirm this claim is "
                           f"actually attributable to that source, not a later development"})
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--cards", default="evidence/cards.jsonl")
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    for label, val in (("--bib", args.bib), ("--cards", args.cards), ("--registry", args.registry)):
        require_within_cwd(val, label)

    bib_problems = check_bib_temporal(Path(args.bib), datetime.date.today())
    card_problems = check_card_year_anachronism(Path(args.cards), Path(args.registry))

    result = {
        "bib_problems": bib_problems,
        "card_problems": card_problems,
        "warnings": len(bib_problems) + len(card_problems),
    }
    emit(result, True)
    sys.exit(2 if (args.strict and result["warnings"]) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"an input file is not valid UTF-8 — {e}")
