#!/usr/bin/env python3
"""frontmatter_check.py — a thesis's front matter: present, in order, and agreeing with the body.

WHY THIS EXISTS
A thesis is rejected at the institute's formal check far more often than at the
defence, and almost never for its science. The front matter is where it happens:
a missing ethics declaration, an approval page in the wrong position, a table of
contents that lists a chapter the thesis renamed, a list of figures that stops at
Figure 11 while the body has 14. Every one of those is mechanical, every one is
caught in a single pass by the institute's secretary, and every one costs a
resubmission cycle.

The kit already KNEW the required order (thesis-structure skill, YÖK rules). It
had nothing that checked a document against it.

WHAT IT CHECKS
  presence   every required page exists, by its own name (TR or EN)
  order      the pages appear in the required sequence
  parity     Özet and Abstract have the same keyword count
  contents   the table of contents matches the body's actual headings
  lists      the list of figures/tables matches the figures/tables in the body

WHAT IT REFUSES
- **To decide what your institute requires.** The default order is the common
  Turkish one (YÖK). If `templates/ingested/template-profile.md` or an institute
  guideline states a different order, that file wins — pass `--order` and the
  script checks against yours instead of arguing.
- **To judge whether Özet and Abstract SAY the same thing.** It compares keyword
  counts and presence; equivalence of content is `tr_style_check.py`'s subject and
  ultimately a human's.
- **To write the pages.** `/front-matter` drafts them; this only checks.

USAGE
  python scripts/frontmatter_check.py
  python scripts/frontmatter_check.py --front drafts/00-front-matter.md --drafts drafts

Exit codes: 0 clean · 1 error · 2 findings.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd, transliterate

# The YÖK-conventional order. Each entry: canonical name, then the headings that
# count as it, in either language.
DEFAULT_ORDER = [
    ("inner_cover", ("iç kapak", "inner cover", "title page", "kapak")),
    ("approval", ("onay sayfası", "approval page", "kabul ve onay", "approval")),
    ("ethics_declaration", ("etik beyan", "ethics declaration", "etik ilkelere uygunluk",
                            "declaration of ethics")),
    ("acknowledgements", ("teşekkür", "acknowledgement", "acknowledgment", "önsöz",
                          "preface")),
    ("ozet", ("özet",)),
    ("abstract", ("abstract",)),
    ("contents", ("içindekiler", "table of contents", "contents")),
    ("list_of_tables", ("tablo listesi", "tablolar listesi", "list of tables",
                        "tablolar dizini")),
    ("list_of_figures", ("şekil listesi", "şekiller listesi", "list of figures",
                         "şekiller dizini")),
    ("abbreviations", ("kısaltmalar", "simgeler ve kısaltmalar", "abbreviations",
                       "symbols and abbreviations")),
]
# Pages a thesis may legitimately not have. Everything else missing is a finding.
OPTIONAL = {"abbreviations", "list_of_tables", "list_of_figures"}

_HEADING = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*$", re.M)
_CAPTION = re.compile(r"^\s*(?:\*\*)?(Şekil|Tablo|Figure|Table)\s+(\d+(?:\.\d+)?)", re.M | re.I)
_KEYWORDS = re.compile(r"(?:anahtar (?:kelimeler|sözcükler)|keywords)\s*:?\s*(.+)", re.I)


def _norm(text: str) -> str:
    """Fold through `transliterate` before lowercasing.

    `"İçindekiler".lower()` is not `"içindekiler"` in Python — the dotted capital
    I decomposes to i + COMBINING DOT ABOVE — so a plain lowercase comparison
    misses the single most common heading in a Turkish thesis. The shared helper
    already maps the atomic Turkish letters; this is the second script to need
    it, which is why it is imported rather than re-written.
    """
    return re.sub(r"[^\w\s]", "", transliterate(text), flags=re.UNICODE).strip().lower()


def sections_of(text: str) -> list[tuple[str, str]]:
    """(heading, body) pairs, in document order."""
    out, matches = [], list(_HEADING.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1).strip(), text[m.end():end]))
    return out


def classify(headings: list[str], order: list[tuple[str, tuple[str, ...]]]) -> list[tuple[str, int]]:
    """Which required page each heading is, with its position. A heading that
    matches nothing is not an error — a thesis may carry a dedication."""
    found = []
    for index, heading in enumerate(headings):
        normalised = _norm(heading)
        for name, aliases in order:
            if any(_norm(a) in normalised for a in aliases):
                found.append((name, index))
                break
    return found


def check_order(found: list[tuple[str, int]], order) -> list[dict]:
    expected = [name for name, _ in order]
    seen = [name for name, _ in found]
    ranks = [expected.index(n) for n in seen if n in expected]
    problems = []
    for i in range(1, len(ranks)):
        if ranks[i] < ranks[i - 1]:
            problems.append({"check": "order", "page": seen[i],
                             "detail": f"{seen[i]} appears after {seen[i - 1]}, but the "
                                       f"required order puts it before"})
    return problems


def keyword_parity(sections: dict[str, str]) -> list[dict]:
    counts = {}
    for name in ("ozet", "abstract"):
        body = sections.get(name)
        if body is None:
            continue
        m = _KEYWORDS.search(body)
        counts[name] = len([k for k in re.split(r"[;,·]", m.group(1)) if k.strip()]) if m else 0
    if len(counts) < 2:
        return []
    if 0 in counts.values():
        missing = [n for n, c in counts.items() if c == 0]
        return [{"check": "keywords", "detail": f"no keyword line in {missing}"}]
    if counts["ozet"] != counts["abstract"]:
        return [{"check": "keywords",
                 "detail": f"Özet has {counts['ozet']} keywords, Abstract has "
                           f"{counts['abstract']} — the two lists are the same list in "
                           f"two languages"}]
    return []


def body_headings(drafts: Path) -> list[str]:
    out = []
    for path in sorted(drafts.glob("*.md")):
        if path.name.startswith("00"):     # the front matter itself
            continue
        out.extend(h for h, _ in sections_of(path.read_text(encoding="utf-8", errors="replace")))
    return out


def body_captions(drafts: Path) -> dict[str, set[str]]:
    figures, tables = set(), set()
    for path in sorted(drafts.glob("*.md")):
        if path.name.startswith("00"):
            continue
        for kind, number in _CAPTION.findall(path.read_text(encoding="utf-8", errors="replace")):
            (figures if kind.lower() in ("şekil", "figure") else tables).add(number)
    return {"figures": figures, "tables": tables}


def check_contents(contents_body: str, headings: list[str]) -> list[dict]:
    """Entries the table of contents lists that the body does not have, and the
    reverse. Matched on normalised text, so numbering and dot leaders do not
    produce phantom differences."""
    if not contents_body.strip():
        return []
    listed = []
    for line in contents_body.splitlines():
        cleaned = re.sub(r"\.{2,}\s*\d*\s*$", "", line)          # dot leaders + page number
        cleaned = re.sub(r"^\s*[-*+]?\s*(?:\d+(?:\.\d+)*\.?)?\s*", "", cleaned)
        if len(cleaned.strip()) > 2:
            listed.append(cleaned.strip())
    body = {_norm(h) for h in headings}
    phantom = [entry for entry in listed
               if _norm(entry) not in body and not any(_norm(entry) in b for b in body)]
    absent = [h for h in headings
              if not any(_norm(h) == _norm(e) or _norm(h) in _norm(e) for e in listed)]
    problems = []
    if phantom:
        problems.append({"check": "contents", "detail": "listed but not in the body",
                         "entries": phantom[:10]})
    if absent:
        problems.append({"check": "contents", "detail": "in the body but not listed",
                         "entries": absent[:10]})
    return problems


def check_lists(sections: dict[str, str], captions: dict[str, set[str]],
                required: set[str]) -> list[dict]:
    """Only for lists the ACTIVE order asks for. An institute whose guideline has
    no list of figures must not be told its thesis is missing one — the whole
    point of --order is that the guideline wins."""
    problems = []
    for page, kind in (("list_of_figures", "figures"), ("list_of_tables", "tables")):
        if page not in required:
            continue
        body = sections.get(page)
        if body is None:
            if captions[kind]:
                problems.append({"check": page,
                                 "detail": f"the body has {len(captions[kind])} {kind} but "
                                           f"there is no list of {kind}"})
            continue
        listed = {n for _, n in _CAPTION.findall(body)}
        missing = sorted(captions[kind] - listed, key=str)
        extra = sorted(listed - captions[kind], key=str)
        if missing or extra:
            problems.append({"check": page, "missing_from_list": missing,
                             "listed_but_absent_from_body": extra})
    return problems


def run(front_text: str, drafts: Path, order) -> dict:
    pairs = sections_of(front_text)
    headings = [h for h, _ in pairs]
    found = classify(headings, order)
    sections = {name: pairs[index][1] for name, index in found}

    required = [name for name, _ in order if name not in OPTIONAL]
    missing = [name for name in required if name not in sections]
    problems = [{"check": "presence", "page": name,
                 "detail": "required page not found in the front matter"} for name in missing]
    problems += check_order(found, order)
    problems += keyword_parity(sections)
    problems += check_contents(sections.get("contents", ""), body_headings(drafts))
    problems += check_lists(sections, body_captions(drafts),
                            {name for name, _ in order})
    return {"result": "CLEAN" if not problems else "FINDINGS",
            "pages_found": [name for name, _ in found],
            "pages_missing": missing, "problems": problems,
            "note": ("order and presence follow the YÖK-conventional sequence; if your "
                     "institute's guideline differs, pass --order and it wins. Whether "
                     "Özet and Abstract SAY the same thing is tr_style_check.py's "
                     "subject, not this script's")}


def load_order(path: Path | None):
    if path is None:
        return DEFAULT_ORDER
    import json
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, list) or not spec:
        die(f"{path} must be a JSON array of [name, [aliases…]] pairs")
    return [(item[0], tuple(item[1])) for item in spec]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--front", default="drafts/00-front-matter.md")
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--order", help="your institute's order, as JSON [[name,[aliases]],…]")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.front, "--front")
    require_within_cwd(args.drafts, "--drafts")
    if args.order:
        require_within_cwd(args.order, "--order")
    front = Path(args.front)
    if not front.is_file():
        die(f"{args.front} does not exist — /front-matter drafts it; this checks it")
    drafts = Path(args.drafts)
    if not drafts.is_dir():
        die(f"{args.drafts} does not exist")

    result = run(front.read_text(encoding="utf-8", errors="replace"), drafts,
                 load_order(Path(args.order) if args.order else None))
    result["front"] = front.as_posix()
    emit(result, args.json_out)
    sys.exit(2 if result["result"] == "FINDINGS" else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
