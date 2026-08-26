#!/usr/bin/env python3
"""translation_check.py — what a translation must not change, checked.

WHY THIS EXISTS
A Turkish manuscript becomes an English submission, or an English draft becomes a
Turkish thesis chapter, and the risk is not style. It is that something factual
moved: a citation disappeared with the paragraph it was in, `0,85` became `0.58`,
"Şekil 3" became "Figure 4", a whole subsection was skipped because it looked
like a repetition, or a number was silently re-rounded. None of these are visible
to a reader who has only the target text — which is everyone downstream, including
the reviewer.

Three classes of thing must survive a translation unchanged, and all three are
machine-checkable: the citation keys, the quantities, and the cross-references.
This checks exactly those, reports what moved, and stays out of the prose — two
honest translations of one paragraph differ in every word, and a checker that
compared wording would report nothing but noise.

WHAT IT REFUSES
- **To judge translation quality.** Fluency, register and word choice are the
  style-auditor's and the author's. This reports only invariants.
- **To pick a term for you.** The glossary reports that a concept is rendered two
  ways in the same target text; which rendering is right is a decision, and
  `tr_style_check.py` draws that line the same way.
- **To treat a rounded number as an error by itself.** `0.8091` → `0.81` is
  reported as a *rounding difference*, separately from `0.809` → `0.089`, which
  is a digit that moved. Collapsing the two would train the author to ignore both.
- **To claim completeness.** A paragraph that was dropped without taking a
  citation, a number or a cross-reference with it is invisible here, and the
  section-count and length ratio are reported so a human can see the shape.

USAGE
  python scripts/translation_check.py --source drafts/03-yontem.md \
      --target drafts/en/03-methods.md --source-lang tr --target-lang en
  python scripts/translation_check.py --source a.md --target b.md --json

Exit codes: 0 no findings · 1 error · 2 findings (WARN-only: a finding is for a
human to resolve, never a gate).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd  # noqa: E402

DEFAULT_GLOSSARY = "templates/tr-terminology.json"
CITE_RE = re.compile(r"\[([^\]]*@[^\]]+)\]")
KEY_RE = re.compile(r"@([A-Za-z0-9_:.#$%&\-+?<>~/]+)")
EV_RE = re.compile(r"\bEV-\d{4}\b")
HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.M)
# A number as a manuscript writes it, in either locale: 1.234,56 · 1,234.56 ·
# 0,85 · 95% · 3.2e-4. The sign is deliberately excluded — "-0.3" and "0.3" as
# text differ by a character that is far more often a dash in prose.
NUMBER_RE = re.compile(r"\d[\d.,]*(?:[eE][+-]?\d+)?")
FIGURE_WORDS = {"tr": ("şekil", "sekil", "tablo", "çizelge", "denklem", "eşitlik"),
                "en": ("figure", "fig.", "table", "equation", "eq.")}
XREF_RE = re.compile(
    r"\b(şekil|sekil|tablo|çizelge|cizelge|denklem|eşitlik|esitlik|figure|fig\.?|table|"
    r"equation|eq\.?)\s*(\d+(?:\.\d+)*)", re.I)
XREF_CLASS = {
    "şekil": "figure", "sekil": "figure", "figure": "figure", "fig": "figure",
    "fig.": "figure", "tablo": "table", "çizelge": "table", "cizelge": "table",
    "table": "table", "denklem": "equation", "eşitlik": "equation",
    "esitlik": "equation", "equation": "equation", "eq": "equation", "eq.": "equation",
}
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")


def read(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        die(f"{path} does not exist")
    return p.read_text(encoding="utf-8", errors="replace")


def citation_keys(text: str) -> list[str]:
    keys = []
    for m in CITE_RE.finditer(text):
        keys.extend(KEY_RE.findall(m.group(1)))
    return keys


def normalise_number(token: str) -> str | None:
    """One canonical form for a quantity written in either locale.

    `1.234,56` (TR) and `1,234.56` (EN) are the same number; `0,85` and `0.85`
    are the same number. The rule is the last separator: if a `,` and a `.` both
    appear, the rightmost is the decimal point. With only one separator kind, a
    group of exactly three digits after it is a thousands separator, anything
    else is a decimal.
    """
    token = token.strip().rstrip(".,;:")
    if not token or not token[0].isdigit():
        return None
    body = re.split(r"[eE]", token, maxsplit=1)[0]
    exp_match = re.search(r"[eE]([+-]?\d+)", token)
    exponent = str(int(exp_match.group(1))) if exp_match else None
    has_comma, has_dot = "," in body, "." in body
    if has_comma and has_dot:
        decimal = "," if body.rfind(",") > body.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        body = body.replace(thousands, "").replace(decimal, ".")
    elif has_comma or has_dot:
        sep = "," if has_comma else "."
        parts = body.split(sep)
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and
                              len(parts[0]) <= 3 and sep == ","):
            body = body.replace(sep, "")
        else:
            body = body.replace(sep, ".")
    try:
        value = float(body)
    except ValueError:
        return None
    if exponent is not None:
        value *= 10 ** int(exponent)
    text = f"{value:.10g}"
    return text


def quantity_text(text: str) -> str:
    """The prose with the spans that carry non-quantity digits removed.

    A citation key holds a year, a cross-reference holds a figure number, and an
    evidence id holds four digits. All three are checked as themselves elsewhere;
    counting them as quantities too reported one difference twice and buried the
    digit that actually moved.
    """
    text = CITE_RE.sub(" ", text)
    text = XREF_RE.sub(" ", text)
    return EV_RE.sub(" ", text)


def numbers(text: str) -> dict[str, list[str]]:
    """canonical value → the raw tokens that produced it."""
    out: dict[str, list[str]] = {}
    for m in NUMBER_RE.finditer(quantity_text(text)):
        canonical = normalise_number(m.group(0))
        if canonical is None:
            continue
        out.setdefault(canonical, []).append(m.group(0))
    return out


def _rounding_partner(value: str, pool: set[str]) -> str | None:
    """Is `value` the same quantity as something in `pool`, at fewer digits?"""
    try:
        v = float(value)
    except ValueError:
        return None
    for other in pool:
        try:
            o = float(other)
        except ValueError:
            continue
        if o == v:
            continue
        for digits in range(0, 6):
            if round(o, digits) == v or round(v, digits) == o:
                # Guard against 1 vs 2 both rounding to the same integer at 0 dp
                if abs(o - v) <= max(abs(o), abs(v)) * 0.05 + 1e-12:
                    return other
    return None


def xrefs(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in XREF_RE.finditer(text):
        word = m.group(1).lower().rstrip(".")
        kind = XREF_CLASS.get(word) or XREF_CLASS.get(word + ".")
        if not kind:
            continue
        out.setdefault(kind, []).append(m.group(2))
    return {k: sorted(v, key=lambda s: [int(p) for p in s.split(".")])
            for k, v in out.items()}


def load_glossary(path: str) -> list[dict]:
    p = Path(path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [c for c in data.get("concepts", []) if isinstance(c, dict)]


def terminology_findings(target_text: str, target_lang: str, concepts: list[dict]) -> list[dict]:
    """Two renderings of one concept inside the target text.

    The same rule tr_style_check.py applies to a Turkish manuscript, applied to
    whichever language the translation landed in: the defect is the mixture, not
    the choice.
    """
    lowered = target_text.lower()
    findings = []
    for concept in concepts:
        variants = [v for v in concept.get(target_lang, []) if v]
        used = {v: len(re.findall(r"\b" + re.escape(v.lower()) + r"\b", lowered))
                for v in variants}
        present = {v: n for v, n in used.items() if n}
        if len(present) > 1:
            findings.append({"check": "term_unity", "concept": concept.get("concept"),
                             "variants": present,
                             "detail": "one concept, two renderings in the translation — "
                                       "pick one and apply it throughout"})
    return findings


def untranslated_signal(target_text: str, target_lang: str) -> dict:
    """Cheap evidence that a passage was carried over rather than translated."""
    if target_lang == "en":
        lines = [ln for ln in target_text.splitlines()
                 if len(ln.strip()) > 40 and sum(ch in TURKISH_CHARS for ch in ln) >= 3]
        return {"check": "untranslated_lines", "count": len(lines),
                "sample": [ln.strip()[:110] for ln in lines[:5]],
                "detail": ("lines carrying Turkish-specific characters in an English "
                           "target — usually a paragraph that was pasted, not translated. "
                           "Turkish proper nouns and cited Turkish titles are legitimate "
                           "and will appear here too")} if lines else {}
    words = re.findall(r"\b(the|and|of|with|which|were|was|this|that|these)\b",
                       target_text.lower())
    if len(words) > 25:
        return {"check": "untranslated_lines", "count": len(words),
                "detail": ("a high count of English function words in a Turkish target "
                           "— check for passages that were left in English")}
    return {}


def compare(source: str, target: str, source_lang: str, target_lang: str,
            concepts: list[dict]) -> dict:
    findings = []

    src_keys, tgt_keys = citation_keys(source), citation_keys(target)
    lost = sorted(set(src_keys) - set(tgt_keys))
    gained = sorted(set(tgt_keys) - set(src_keys))
    if lost:
        findings.append({"check": "citation_lost", "keys": lost,
                         "detail": "cited in the source, absent from the translation — "
                                   "the paragraph carrying them was probably dropped"})
    if gained:
        findings.append({"check": "citation_added", "keys": gained,
                         "detail": "present only in the translation. A translation does "
                                   "not acquire sources; check where these came from"})

    src_ev, tgt_ev = set(EV_RE.findall(source)), set(EV_RE.findall(target))
    if src_ev - tgt_ev or tgt_ev - src_ev:
        findings.append({"check": "evidence_ids",
                         "lost": sorted(src_ev - tgt_ev), "added": sorted(tgt_ev - src_ev),
                         "detail": "evidence card ids differ between the two versions"})

    src_nums, tgt_nums = numbers(source), numbers(target)
    missing, rounded = [], []
    for value, raw in src_nums.items():
        if value in tgt_nums:
            continue
        partner = _rounding_partner(value, set(tgt_nums))
        (rounded if partner else missing).append(
            {"source": raw[0], "canonical": value, "target": partner} if partner
            else {"source": raw[0], "canonical": value})
    added = [{"target": raw[0], "canonical": value} for value, raw in tgt_nums.items()
             if value not in src_nums and not _rounding_partner(value, set(src_nums))]
    if missing:
        findings.append({"check": "number_missing", "count": len(missing),
                         "numbers": missing[:40],
                         "detail": "quantities in the source with no counterpart in the "
                                   "translation — a moved digit looks exactly like this"})
    if added:
        findings.append({"check": "number_added", "count": len(added),
                         "numbers": added[:40],
                         "detail": "quantities in the translation that are not in the "
                                   "source"})
    if rounded:
        findings.append({"check": "number_rounded", "count": len(rounded),
                         "numbers": rounded[:40],
                         "detail": "same quantity at a different precision. Legitimate, "
                                   "but the two versions of the paper now report "
                                   "different digits — decide which is the reported one"})

    src_x, tgt_x = xrefs(source), xrefs(target)
    for kind in sorted(set(src_x) | set(tgt_x)):
        a, b = src_x.get(kind, []), tgt_x.get(kind, [])
        if sorted(set(a)) != sorted(set(b)):
            findings.append({"check": "crossref_mismatch", "kind": kind,
                             "source": sorted(set(a)), "target": sorted(set(b)),
                             "detail": f"{kind} references differ — numbering that "
                                       f"shifts between versions is how a caption ends "
                                       f"up describing another figure"})

    findings.extend(terminology_findings(target, target_lang, concepts))
    signal = untranslated_signal(target, target_lang)
    if signal:
        findings.append(signal)

    src_words = len(re.findall(r"\w+", source))
    tgt_words = len(re.findall(r"\w+", target))
    ratio = round(tgt_words / src_words, 2) if src_words else None
    src_headings = len(HEADING_RE.findall(source))
    tgt_headings = len(HEADING_RE.findall(target))
    if src_headings != tgt_headings:
        findings.append({"check": "section_count", "source": src_headings,
                         "target": tgt_headings,
                         "detail": "the two versions have a different number of headings"})

    return {
        "result": "FINDINGS" if findings else "CLEAN",
        "findings": findings,
        "shape": {"source_words": src_words, "target_words": tgt_words,
                  "length_ratio": ratio, "source_headings": src_headings,
                  "target_headings": tgt_headings,
                  "citations": {"source": len(set(src_keys)), "target": len(set(tgt_keys))},
                  "numbers": {"source": len(src_nums), "target": len(tgt_nums)}},
        "languages": {"source": source_lang, "target": target_lang},
        "note": ("prose is never compared: two honest translations of one paragraph "
                 "differ in every word. What is compared is what a translation must "
                 "not change — who is cited, what the quantities are, and which figure "
                 "a sentence points at. A dropped paragraph that carried none of those "
                 "is invisible here; the length ratio is printed for that reason"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", required=True, help="the version translated FROM")
    ap.add_argument("--target", required=True, help="the version translated TO")
    ap.add_argument("--source-lang", default="tr", choices=("tr", "en"))
    ap.add_argument("--target-lang", default="en", choices=("tr", "en"))
    ap.add_argument("--glossary", default=DEFAULT_GLOSSARY)
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.source, "--source")
    require_within_cwd(args.target, "--target")
    if args.source_lang == args.target_lang:
        die("--source-lang and --target-lang are the same; this compares a translation "
            "against its source, not a file against itself")
    result = compare(read(args.source), read(args.target), args.source_lang,
                     args.target_lang, load_glossary(args.glossary))
    result["source"] = Path(args.source).as_posix()
    result["target"] = Path(args.target).as_posix()
    emit(result, args.json_out)
    sys.exit(2 if result["findings"] else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
