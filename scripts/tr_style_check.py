#!/usr/bin/env python3
"""tr_style_check.py — deterministic Turkish academic-writing lint.

The kit claims Turkish and English are equal first-class targets. Until now that
claim rested entirely on prose guidance an agent may or may not follow; every
other differentiator in this kit has a script behind it. This is that script.

DESIGN RULE — inconsistency over house style. Turkish academic convention is not
uniform across fields and journals: some accept `0.95`, TDK writes `0,95`; some
departments require impersonal `-mIştIr` throughout, others tolerate first-person
plural. A linter that imposed one of those would be wrong for half its users and
would train them to ignore it. So wherever a convention is genuinely contested,
this checks that the manuscript picks ONE and holds it, and reports which form
dominates — the mixture is the defect, not the choice. Only where the rule is
settled (TDK percent placement, `v.b.` → `vb.`) does it name a correct form.

Checks (all WARN-only; `--strict` opts into blocking):
  decimal_separator  `0,95` and `0.95` both present — pick one
  percent_placement  `25%` in Turkish prose; TDK writes `%25`
  abbreviation       `v.b.` / `v.s.` / `v.b` — settled forms are `vb.` / `vs.`
  informal_register  conversational tokens that do not belong in academic prose
  term_unity         two spellings of one concept coexist (templates/tr-terminology.json)
  voice_mixing       impersonal `-mIştIr/-mAktAdIr` and first-person `-dIk` both
                     used substantially in one file
  ozet_abstract      Özet ↔ Abstract structural and numeric equivalence

WHAT IT CANNOT DO: it is not a grammar checker. It has no parser, no morphological
analyser and no lexicon, so it cannot see subject-predicate disagreement, a wrong
participle, or a mistranslated postposition. Those stay with `style-auditor`, and
the reference prose in academic-writing/reference/turkish-academic.md remains the
authority on everything not listed above.

Code fences, inline code, URLs, citation keys and math are excluded from every
text check — a `0.05` inside a code block is code, not orthography.

Usage:
  python scripts/tr_style_check.py
  python scripts/tr_style_check.py --drafts drafts --glossary templates/tr-terminology.json
  python scripts/tr_style_check.py --check term_unity,ozet_abstract --strict
Output: single JSON object. Exit codes: 0 ok · 1 error · 2 warnings (--strict only).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

ALL_CHECKS = ("decimal_separator", "percent_placement", "abbreviation",
              "informal_register", "term_unity", "voice_mixing", "ozet_abstract")

# The project's own progress log is not manuscript prose — same exemption
# consistency_check.py and failure_scan.py make.
SKIP_FILES = {"STATUS.md"}

# Stripped before any text check runs.
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# HTML comments are the kit's evidence-binding and RQ-tagging syntax — drafts
# carry them by instruction — plus author notes and commented-out drafting.
# None of it is manuscript register: a note reading "22.3 ve 18.9" made the
# decimal-separator check report a convention MIXTURE the published text does
# not contain, and the mixture is the one thing this check exists to flag.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
CITE_RE = re.compile(r"\[@[^\]]*\]|@[A-Za-z][\w:.#$%&+?<>~/-]*")
MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$", re.DOTALL)
IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")

# A number written with a decimal point. Excludes section/figure numbering
# ("Bölüm 3.1", "Şekil 2.4"), version strings and dotted lists, all of which are
# not decimals and would otherwise dominate the findings.
DECIMAL_DOT_RE = re.compile(
    r"(?<![\w.])(?<!\d\.)(\d+\.\d+)(?![.\d])")
# Turkish groups thousands with a POINT — "7.651 hasta" is seven thousand six
# hundred and fifty-one, not a decimal. Without this the check fires on every
# Turkish draft that mentions a sample size, reports the correct convention as a
# mixed-separator defect, and trains the author to stop reading its warnings.
# A decimal needs a fractional part; a group of exactly three digits that is not
# itself followed by a fraction is grouping. "1.234,56" is caught by the trailing
# comma-digit guard, so a genuine decimal riding on a grouped number still counts.
# The leading group must start 1-9: "0.809" is a decimal, never a thousands group,
# and an earlier \d{1,3} swallowed exactly that. Three-digit ambiguity ("12.345")
# resolves to grouping, which is the safe direction for a check whose whole point
# is not to cry wolf on correct Turkish.
THOUSANDS_DOT_RE = re.compile(r"(?<![\w.])[1-9]\d{0,2}(?:\.\d{3})+(?![.,]\d)")
# A DOI's registrant prefix ("10.17780/ksujes.1521858") is not a decimal number.
# Without this the check reports every cited DOI as a stray decimal point and
# then names the majority convention wrongly, because those hits inflate the
# dot side of a count whose whole purpose is to decide which form dominates.
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>,;)\]}]+")
DECIMAL_COMMA_RE = re.compile(r"(?<![\w,])(\d+,\d+)(?![,\d])")
# A SOFTWARE VERSION is not a decimal either, and a review of tools names them
# constantly: "IDx-DR 2.0", "EyeArt system v2.0", "RetCAD v.2.2.0", "AIRS MIRA
# 4.0". Two shapes, both unambiguous:
#   * a `v`/`v.`/`ver.`/`sürüm`/`versiyon` marker directly before the number —
#     NUMBERING_CONTEXT_RE already covers the spelled-out Turkish words, but not
#     the `v2.0` / `v.2.2.0` forms where the marker is glued to the digit;
#   * a MODEL NAME directly before it: the preceding token carries an internal
#     capital or a hyphen between letters ("IDx-DR", "RetCAD", "MIRA"), which a
#     Turkish sentence introducing a decimal never does.
# Without this the check counts each product version on the dot side of the very
# tally that decides which convention dominates, and then reports a manuscript
# whose own numbers are uniformly comma-written as mixing separators. The
# manuscript cannot fix it either: the strings are quoted verbatim from the
# sources, and rewriting a source's product name to "2,0" would be worse.
# Two patterns, and the second is deliberately NOT case-insensitive: with
# IGNORECASE a "capital letter" class matches lowercase too, so the model-name
# branch degenerates into "any word followed by a dotted number" and swallows
# every real decimal in the manuscript. Verified in both directions by the tests.
VERSION_MARKED_RE = re.compile(r"\bv(?:er)?\.?\s?\d+(?:\.\d+)+", re.IGNORECASE)
# A model name: at least one capital at position >= 1 ("IDx-DR", "RetCAD",
# "MIRA", "EyeArt"). A Turkish sentence-initial word is capitalised only at
# position 0, so "Duyarlılık 0.905" does not match. The number must then look
# like a version rather than a measurement — three or more components (2.2.0),
# or a `.0` tail, which is how versions are written and how measurements are
# not (a measurement of two is written "2" or "2,0", never "2.0").
VERSION_MODEL_RE = re.compile(
    r"(?<![\w.])[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*[A-Z][A-Za-z0-9-]*\s"
    r"(?:\d+(?:\.\d+){2,}|\d+\.0)(?!\d)")
NUMBERING_CONTEXT_RE = re.compile(
    r"(?:bölüm|şekil|sekil|tablo|denklem|çizelge|cizelge|ek|madde|sürüm|surum|"
    r"versiyon|section|figure|table|equation|eq\.?|fig\.?)\s*$", re.IGNORECASE)

PERCENT_AFTER_RE = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)\s*%")
PERCENT_BEFORE_RE = re.compile(r"%\s*\d")

# `\s*` around the period lets this span a sentence boundary, and IGNORECASE lets a
# capital V start it — so a Roman-numeral heading, "# V. Sonuç", matched as "v.s.".
# Every Turkish manuscript with numbered sections has one. Two guards: the letters
# must be lowercase (nobody writes "V.B." for "vb."), and the match may not start a
# markdown heading, where "V." is a section number.
ABBREV_RE = re.compile(r"(?<!^#)\bv\s*\.\s*[bs]\s*\.?")
HEADING_START_RE = re.compile(r"^#{1,6}\s*[IVXLC]+\s*\.", re.MULTILINE)

# Conversational tokens. Deliberately short and unambiguous: every entry here is
# informal in ANY academic register, so the check needs no context model. Words
# that are merely weak ("başarılı", "ilgili") are style advice, not defects, and
# stay with style-auditor where a human reads the sentence.
INFORMAL = ("bayağı", "baya", "epey", "epeyce", "gayet", "falan", "filan",
            "hani", "bir sürü", "birsürü", "haliyle", "malum", "zaten ki",
            "şöyle ki", "e tabii", "tabii ki", "yok yani")

# Two entries above are informal only as DISCOURSE MARKERS, at the start of a
# clause. Elsewhere they are ordinary nouns doing ordinary work, and Turkish
# gives them no other spelling:
#   "hâliyle"  — marker: "naturally, as one would expect"
#                noun:   "ham hâliyle" = "in its raw form"   ← perfectly academic
#   "malum"    — marker: "as we all know"
#                noun:   "malum olan" / "malumat" senses
# Flagging the noun sense reports correct academic Turkish as conversational,
# which is exactly the cry-wolf failure this file's design rule forbids. The
# marker sense sits at a clause boundary; the noun sense is preceded by its
# modifier, so the boundary test separates them without a parser.
CLAUSE_INITIAL_ONLY = frozenset({"haliyle", "malum"})
_CLAUSE_BREAK = frozenset(".,;:!?()[]{}—–-*_\"'")


def _at_clause_start(folded: str, pos: int) -> bool:
    """Is `pos` the first word of a clause — start of text, or after a break?"""
    i = pos - 1
    while i >= 0 and folded[i] in " \t":
        i -= 1
    return i < 0 or folded[i] in _CLAUSE_BREAK or folded[i] == "\n"

# Impersonal academic predicate endings vs first-person plural past.
IMPERSONAL_RE = re.compile(
    r"\w+(?:m[ıiuü][şs]t[ıiuü]r|maktad[ıi]r|mektedir|[ıiuü]lm[ıiuü][şs]t[ıiuü]r"
    r"|[ıiuü]lmaktad[ıi]r|[ıiuü]lmektedir)\b", re.IGNORECASE)
# -dık/-dik/-duk/-dük and the voiceless-harmony -tık/-tuk/-tük are first-person
# plural past. Bare -tik is NOT included here: it is the ending of every borrowed
# -ic adjective in the academic register ("diyabetik", "sistematik", "otomatik",
# "pratik", "kritik", "analitik"), so matching it wholesale reported a purely
# impersonal manuscript as register-mixed — and a check that fires on correct
# prose is a check its author learns to skip.
#
# Two traps make this check impossible to write against the folded text the rest
# of this file uses, and both silently destroy the ı/i distinction the Turkish
# morphology depends on:
#   1. `_fold` maps ı -> i, so "yaptık" and "diyabetik" both end in "tik".
#   2. `re.IGNORECASE` treats ı and i as THE SAME LETTER, because both uppercase
#      to U+0049 "I" — so even unfolded text, matched case-insensitively, cannot
#      tell -tık from -tik.
# So this check lowercases Turkish-correctly (I -> ı, İ -> i) and matches
# case-sensitively, on text that still has its dotless i.
FIRST_PERSON_RE = re.compile(r"\w+(?:d[ıiuü]k|t[ıuü]k)\b")
# -tik is the collision: it ends both first-person verbs ("ettik", "seçtik",
# "eğittik") and borrowed -ic adjectives ("diyabetik", "kritik", "analitik").
# Two morphological facts separate them without a verb lexicon:
#
#   1. The verb form attaches -tik to a stem ending in a voiceless CONSONANT, so
#      a consonant sits immediately before the suffix: eğit-tik, seç-tik,
#      kes-tik, geç-tik. Borrowed adjectives put a VOWEL there: diyabe-tik,
#      kri-tik, anali-tik, e-tik, gene-tik.
#   2. Turkish vowel harmony requires -tik only after e/i. A word ending -tik
#      whose preceding vowel is a/ı/o/u/ö/ü cannot be a first-person verb:
#      sistematik, otomatik, pratik, romantik, dramatik.
#
# What survives both rules is the "-stik/-ntik with an i" family, which is a
# small closed set of loans; those are listed.
TIK_VOWELS = "aeıioöuü"
FRONT_UNROUNDED = "ei"
LOAN_TIK_EXCEPTIONS = {
    "istatistik", "lojistik", "karakteristik", "holistik", "balistik",
    "stilistik", "artistik", "linguistik", "heuristik", "sofistik",
}
FIRST_PERSON_TIK_RE = re.compile(r"\w+tik\b")


def _is_first_person_tik(word: str) -> bool:
    """Decide whether a word ending in -tik is a first-person plural verb rather
    than a borrowed -ic adjective. See the comment on LOAN_TIK_EXCEPTIONS for
    the two rules; this returns False whenever either says "loan"."""
    if word in LOAN_TIK_EXCEPTIONS:
        return False
    stem = word[:-3]                       # everything before "tik"
    if not stem:
        return False
    if stem[-1] in TIK_VOWELS:             # rule 1: vowel before the suffix
        return False
    vowels = [ch for ch in stem if ch in TIK_VOWELS]
    if vowels and vowels[-1] not in FRONT_UNROUNDED:   # rule 2: vowel harmony
        return False
    return True


def _tr_lower(text: str) -> str:
    """Turkish-correct lowercasing: I -> ı and İ -> i, then ordinary lower().
    Python's str.lower() maps I -> i, which would turn "YAPTIK" into "yaptik"
    and put it back in the loan-adjective bucket this check exists to leave
    alone."""
    return text.replace("I", "ı").replace("İ", "i").lower()
# Nouns/adverbs ending in -tık/-dık that are not first-person verbs. Without
# these, "artık" alone makes almost every Turkish manuscript look first-person.
FIRST_PERSON_EXCEPTIONS = {
    "artık", "yırtık", "katık", "yatık", "çatık", "batık", "atık", "kırtık",
    "sıkıntık", "bıçtık", "dik", "sadık", "fındık", "sandık", "kandık",
    "aydınlık", "bıyık",
}
# Glossary variants that are also ordinary Turkish words. Folded, because that is
# how check_term_unity compares them. Kept deliberately short: each entry weakens
# a real check, so a word earns a place here only when its everyday sense is the
# one a reader meets first — "nitelik" (quality), "özellik" (property/trait),
# "sonuç" (consequence), "anma" (commemoration).
VOICE_MIN_TOTAL = 8      # below this a ratio says nothing
VOICE_MIX_FLOOR = 0.20   # both forms above 20% of predicates = genuine mixing

NUM_TOKEN_RE = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)(?![\w])")
KEYWORD_LINE_RE = re.compile(
    r"^\s*\**\s*(?:anahtar\s*(?:söz|soz)c[üu]kler|anahtar\s*kelimeler|keywords?)\s*\**\s*[::]",
    re.IGNORECASE)
OZET_NAMES = ("ozet", "özet", "oz", "öz")
ABSTRACT_NAMES = ("abstract",)
WORD_RATIO_BAND = (0.60, 1.70)  # Turkish is agglutinative: fewer words for the
                                # same content, so the band is asymmetric.


# A generated-file banner, in the two spellings the kit's own generators write
# (and the plain-ASCII Turkish one, since a banner is a comment and comments in
# generated files are routinely written without diacritics).
_GENERATED_BANNER_RE = re.compile(
    r"URET[İI]LM[İI][ŞS]\s+DOSYA|OTOMAT[İI]K\s+ÜRET[İI]LM[İI][ŞS]|"
    r"GENERATED\s+FILE|DO\s+NOT\s+EDIT|AUTO-?GENERATED",
    re.IGNORECASE)


def _is_generated(path: Path, lookahead_lines: int = 6) -> bool:
    """Does this file announce itself as machine-generated?

    Reads the file itself rather than taking read_drafts()'s text, and that is
    the whole reason this takes a Path. A generated banner is an HTML comment,
    and strip_noise() removes HTML comments before any check sees the text — so
    a version of this that inspected the processed string found no banner in
    any file and silently excluded nothing, while every unit test on the raw
    string passed.

    Head only: a banner belongs at the top, and scanning the whole body would
    match a sentence that merely DISCUSSES generated files, which the Methods
    section of a kit-built manuscript regularly does."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            head = "".join(next(fh, "") for _ in range(lookahead_lines))
    except OSError:
        return False
    return bool(_GENERATED_BANNER_RE.search(head))


def _is_english_abstract(path: Path) -> bool:
    """The manuscript's English Abstract file — not Turkish prose.

    Matched on the filename the same way `_find_section` matches it, so the two
    cannot drift apart: a file this returns True for is exactly the one
    check_ozet_abstract will pick up as the Abstract side of the pair. An Özet
    file is never matched, even though "ozet" and "abstract" can both appear in
    a name (`ozet-abstract.md`): the Özet is Turkish and stays in scope.
    """
    stem = _fold(path.stem)
    if any(n in stem for n in (_fold(x) for x in OZET_NAMES)):
        return False
    return any(n in stem for n in ABSTRACT_NAMES)


def _fold(text: str) -> str:
    """Lowercase and strip diacritics.

    ASCII-folded Turkish is everywhere — quick typing, filenames, tools that
    strip diacritics. A check that only matched `çalışma` and missed `calisma`
    would report CLEAR for the wrong reason.
    """
    lowered = text.replace("I", "ı").replace("İ", "i").lower()
    stripped = "".join(c for c in unicodedata.normalize("NFD", lowered)
                       if not unicodedata.combining(c))
    # NFD handles ğ ş ç ö ü (letter + combining mark), but dotless ı (U+0131) is
    # an atomic codepoint with no decomposition, so it survives the strip. Left
    # alone, `_fold("bayağı")` == "bayagı" never matches a user's "bayagi" and
    # the whole diacritic-insensitive design fails on the one letter most
    # commonly lost when Turkish is typed without a Turkish keyboard.
    return stripped.replace("ı", "i")


def strip_noise(text: str) -> str:
    """Blank out code, comments, URLs, citations, math and images, keeping line count."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    # COMMENT_RE runs first: a comment may CONTAIN a fence, a URL or a citation,
    # and blanking the inner match first would leave the comment's own delimiters
    # behind as prose.
    for pattern in (COMMENT_RE, FENCE_RE, MATH_RE, IMG_RE, INLINE_CODE_RE, URL_RE, CITE_RE):
        text = pattern.sub(blank, text)
    return text


def read_drafts(drafts_dir: Path) -> list[tuple[Path, str]]:
    if not drafts_dir.is_dir():
        return []
    out = []
    for path in sorted(drafts_dir.rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        out.append((path, strip_noise(path.read_text(encoding="utf-8", errors="replace"))))
    return out


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# ---------- individual checks ----------

def check_decimal_separator(files: list[tuple[Path, str]]) -> list[dict]:
    dots, commas = [], []
    for path, text in files:
        grouped = {m.span() for m in THOUSANDS_DOT_RE.finditer(text)}
        dois = [m.span() for m in DOI_RE.finditer(text)]
        versions = [m.span() for m in VERSION_MARKED_RE.finditer(text)]
        versions += [m.span() for m in VERSION_MODEL_RE.finditer(text)]
        for m in DECIMAL_DOT_RE.finditer(text):
            head = text[max(0, m.start() - 40):m.start()]
            if NUMBERING_CONTEXT_RE.search(head):
                continue
            # A thousands group ("7.651", "1.234.567") is the correct Turkish form,
            # not a decimal point competing with the comma.
            if any(s <= m.start() and m.end() <= e for s, e in grouped):
                continue
            # Neither is a DOI's registrant prefix a decimal.
            if any(s <= m.start() and m.end() <= e for s, e in dois):
                continue
            # Nor a software version ("IDx-DR 2.0", "RetCAD v.2.2.0").
            if any(s <= m.start() and m.end() <= e for s, e in versions):
                continue
            dots.append({"file": path.name, "line": _line_of(text, m.start()),
                         "text": m.group(1)})
        for m in DECIMAL_COMMA_RE.finditer(text):
            commas.append({"file": path.name, "line": _line_of(text, m.start()),
                           "text": m.group(1)})
    if not dots or not commas:
        return []
    dominant, minority = ("comma", dots) if len(commas) >= len(dots) else ("dot", commas)
    return [{
        "check": "decimal_separator",
        "message": (f"both decimal separators are in use: {len(commas)} with a comma "
                    f"(0,95) and {len(dots)} with a point (0.95). TDK writes a comma, "
                    f"but many Turkish journals accept the point — the defect is the "
                    f"mixture, not the choice. Dominant form: {dominant}."),
        "dominant": dominant,
        "comma_count": len(commas), "dot_count": len(dots),
        "minority_examples": minority[:10],
    }]


def check_percent_placement(files: list[tuple[Path, str]]) -> list[dict]:
    hits = []
    for path, text in files:
        for m in PERCENT_AFTER_RE.finditer(text):
            hits.append({"file": path.name, "line": _line_of(text, m.start()),
                         "text": m.group(0).strip(),
                         "suggest": "%" + m.group(1)})
    if not hits:
        return []
    return [{
        "check": "percent_placement",
        "message": (f"{len(hits)} occurrence(s) write the percent sign after the number "
                    f"(25%). Turkish orthography places it before, without a space: %25. "
                    f"This one is settled, not a matter of house style."),
        "occurrences": hits[:20], "total": len(hits),
    }]


def check_abbreviation(files: list[tuple[Path, str]]) -> list[dict]:
    hits = []
    for path, text in files:
        # Spans of Roman-numeral section headings ("## V. Sonuç"), whose "V." is a
        # section number rather than the first half of "v.s.".
        headings = [m.span() for m in HEADING_START_RE.finditer(text)]
        for m in ABBREV_RE.finditer(text):
            if any(s <= m.start() < e for s, e in headings):
                continue
            raw = m.group(0)
            correct = "vb." if raw.lower().replace(" ", "").replace(".", "").endswith("b") \
                else "vs."
            hits.append({"file": path.name, "line": _line_of(text, m.start()),
                         "text": raw, "suggest": correct})
    if not hits:
        return []
    return [{"check": "abbreviation",
             "message": f"{len(hits)} abbreviation(s) written with internal periods; "
                        f"the standard forms are `vb.` and `vs.`",
             "occurrences": hits[:20], "total": len(hits)}]


def check_informal_register(files: list[tuple[Path, str]]) -> list[dict]:
    hits = []
    for path, text in files:
        folded = _fold(text)
        for token in INFORMAL:
            for m in re.finditer(r"(?<![\w])" + re.escape(_fold(token)) + r"(?![\w])",
                                 folded):
                if token in CLAUSE_INITIAL_ONLY and not _at_clause_start(folded, m.start()):
                    continue
                hits.append({"file": path.name, "line": _line_of(text, m.start()),
                             "text": token})
    if not hits:
        return []
    hits.sort(key=lambda h: (h["file"], h["line"]))
    return [{"check": "informal_register",
             "message": f"{len(hits)} conversational token(s) in academic prose",
             "occurrences": hits[:25], "total": len(hits)}]


def load_glossary(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    concepts = data.get("concepts") if isinstance(data, dict) else data
    return [c for c in (concepts or []) if isinstance(c, dict) and c.get("concept")]


def _count_variants(corpus: str, variants: list[str]) -> dict[str, int]:
    """Count each variant, longest first, masking matched spans as we go.

    The mask is what keeps nested variants from double-counting. `corpus` is
    already folded; the mask character is one that cannot occur in folded text.
    """
    return _count_across({"_": variants}, corpus)["_"]


def _count_across(by_concept: dict[str, list[str]], corpus: str) -> dict[str, dict[str, int]]:
    """One longest-first pass over EVERY concept's variants at once.

    Masking per concept was not enough: nesting crosses concept boundaries too.
    "evrişimli sinir ağı" is a convolutional network, not a spelling of "sinir
    ağı" — but while counting the `neural network` entry in isolation, the bare
    "sinir ağı" still matched inside it, and the checker reported one concept
    written two ways in a manuscript that had used two different terms
    correctly. Consuming the longest term anywhere in the glossary first fixes
    the class, not the instance.
    """
    remaining = corpus
    ordered = sorted(((c, v) for c, vs in by_concept.items() for v in vs),
                     key=lambda cv: len(cv[1]), reverse=True)
    counts: dict[str, dict[str, int]] = {c: {} for c in by_concept}
    for concept, variant in ordered:
        needle = _fold(variant)
        if not needle:
            continue
        pattern = re.compile(r"(?<![\w])" + re.escape(needle) + r"(?![\wğüşöç])")
        found = list(pattern.finditer(remaining))
        if found:
            counts[concept][variant] = len(found)
            remaining = pattern.sub(lambda m: "\x00" * len(m.group(0)), remaining)
    return counts


def check_term_unity(files: list[tuple[Path, str]], glossary: list[dict]) -> list[dict]:
    if not glossary:
        return []
    corpus = "\n".join(_fold(t) for _, t in files)
    # The ENGLISH variants are matched against the UNFOLDED text, and that is
    # not a detail. _fold strips Turkish diacritics, which is right for Turkish
    # variants and wrong for English ones: in an agglutinative language a
    # correctly inflected Turkish word can fold onto an English term exactly.
    # "literatüre" (dative of literatür) folds to "literature" — so a manuscript
    # that never wrote an English word was told it used the English name twice,
    # and the same collision class waits for every glossary entry whose English
    # form differs from a suffixed Turkish form only by diacritics. English
    # carries no Turkish diacritics, so it loses nothing by skipping the fold.
    en_corpus = "\n".join(t.lower() for _, t in files)
    # Longest variant first across the WHOLE glossary, masking what it consumes.
    # Variants nest both inside one concept ("sinir ağı" inside "yapay sinir ağı")
    # and across concepts ("sinir ağı" inside "evrişimli sinir ağı", which is a
    # different concept entirely). Counted naively, a manuscript that used its
    # terms correctly reports drift, and the check fires hardest on exactly the
    # work it should pass.
    # An entry's `tr_ambiguous` variants are not counted at all. Some glossary
    # words are ordinary Turkish before they are technical terms — "nitelik"
    # means quality, "özellik" means a property of anything, "anma" means
    # remembrance — and counting them reported term drift in a draft whose
    # terminology never drifted.
    #
    # This used to be a set in this file, suppressed only when the word appeared
    # ONCE. That condition had it backwards: polysemy is a property of the word,
    # not of how often it is used, so the suppression stopped working on exactly
    # the words a manuscript leans on. Three occurrences of "özellik", all of
    # them ordinary, were enough to raise the flag.
    #
    # It lives in the glossary now because that is the file a project edits.
    # Terminology is domain-specific: a clinical review may use "nitelik"
    # unambiguously, and it can say so by moving the word back into `tr`. A
    # hardcoded set here could not be told that.
    tr_all = _count_across({e["concept"]: e.get("tr", []) for e in glossary}, corpus)
    en_all = _count_across({e["concept"]: e.get("en", []) for e in glossary}, en_corpus)
    findings = []
    for entry in glossary:
        counts = tr_all[entry["concept"]]
        # A single occurrence is the standard first-mention parenthetical
        # ("yapay sinir ağı (artificial neural network)") and is correct.
        en_counts = {k: v for k, v in en_all[entry["concept"]].items() if v > 1}
        if len(counts) < 2 and not (counts and en_counts):
            continue
        merged = {**counts, **{f"{k} (EN)": v for k, v in en_counts.items()}}
        dominant = max(sorted(merged), key=lambda k: merged[k])
        findings.append({
            "concept": entry["concept"], "variants": merged, "dominant": dominant,
            "message": (f"'{entry['concept']}' appears under "
                        f"{len(merged)} different names; term unity requires one. "
                        f"Most used: '{dominant}'."),
        })
    if not findings:
        return []
    findings.sort(key=lambda f: -sum(f["variants"].values()))
    return [{"check": "term_unity",
             "message": f"{len(findings)} concept(s) written under more than one name",
             "concepts": findings}]


def check_voice_mixing(files: list[tuple[Path, str]]) -> list[dict]:
    out = []
    for path, text in files:
        folded = _fold(text)
        impersonal = len(IMPERSONAL_RE.findall(folded))
        # Matched on ı-preserving text, not on `folded` — see FIRST_PERSON_RE.
        lowered = _tr_lower(text)
        blocked = {_tr_lower(w) for w in FIRST_PERSON_EXCEPTIONS}
        first = [m.group(0) for m in FIRST_PERSON_RE.finditer(lowered)
                 if m.group(0) not in blocked]
        first += [m.group(0) for m in FIRST_PERSON_TIK_RE.finditer(lowered)
                  if m.group(0) not in blocked and _is_first_person_tik(m.group(0))]
        total = impersonal + len(first)
        if total < VOICE_MIN_TOTAL:
            continue
        share = len(first) / total
        if VOICE_MIX_FLOOR <= share <= 1 - VOICE_MIX_FLOOR:
            out.append({"file": path.name, "impersonal": impersonal,
                        "first_person": len(first),
                        "first_person_share": round(share, 3),
                        "examples": sorted(set(first))[:8]})
    if not out:
        return []
    return [{"check": "voice_mixing",
             "message": (f"{len(out)} file(s) mix impersonal (-mıştır/-maktadır) and "
                         f"first-person plural (-dık) predicates. Either register is "
                         f"defensible; alternating between them inside one section is "
                         f"not. Check your department's guideline, then hold it."),
             "files": out}]


def _numbers(text: str) -> set[str]:
    """Numeric tokens, decimal separator normalized so 94,2 == 94.2."""
    return {m.group(1).replace(",", ".").rstrip("0").rstrip(".") or "0"
            for m in NUM_TOKEN_RE.finditer(text)}


def _keywords(text: str) -> list[str]:
    """Every keyword in the list, including the ones on continuation lines.

    A hard-wrapped keyword list is ordinary Markdown, and reading only the
    matched line truncated it at the first newline: two lists holding the same
    six terms were reported as 3 vs 4 because they happened to wrap in
    different places. The check then names a keyword mismatch that does not
    exist — and, worse, would stay silent about a real one hiding past the
    wrap. Continuation stops at a blank line or at anything that starts a new
    block (heading, bold run-in label, list item, blockquote).
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not KEYWORD_LINE_RE.match(line):
            continue
        tail = re.split(r"[::]", line, maxsplit=1)[1]
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                break
            if re.match(r"\s*(?:#{1,6}\s|>|[-*+]\s|\d+[.)]\s|\*\*)", nxt):
                break
            tail += " " + nxt
        return [k.strip(" *_.") for k in re.split(r"[,;]", tail) if k.strip(" *_.")]
    return []


def _find_section(files: list[tuple[Path, str]], names: tuple[str, ...]) -> tuple | None:
    for path, text in files:
        if _fold(path.stem) in {_fold(n) for n in names}:
            return path, text
    return None


def check_ozet_abstract(files: list[tuple[Path, str]]) -> list[dict]:
    ozet = _find_section(files, OZET_NAMES)
    abstract = _find_section(files, ABSTRACT_NAMES)
    if not ozet and not abstract:
        return []
    if not ozet or not abstract:
        present = "Abstract" if abstract else "Özet"
        missing = "Özet" if abstract else "Abstract"
        return [{"check": "ozet_abstract", "status": "incomplete",
                 "message": (f"{present} exists but {missing} does not. A Turkish thesis "
                             f"requires both, and they must say the same thing — this "
                             f"cannot be checked until both are drafted.")}]
    (op, ot), (ap, at) = ozet, abstract
    issues = []
    on, an = len(ot.split()), len(at.split())
    ratio = on / an if an else 0.0
    if an and not (WORD_RATIO_BAND[0] <= ratio <= WORD_RATIO_BAND[1]):
        issues.append({"issue": "length", "ozet_words": on, "abstract_words": an,
                       "ratio": round(ratio, 2),
                       "detail": (f"Turkish is agglutinative, so an equivalent Özet is "
                                  f"normally shorter; a ratio outside "
                                  f"{WORD_RATIO_BAND[0]}–{WORD_RATIO_BAND[1]} usually "
                                  f"means one of them says more than the other.")})
    o_nums, a_nums = _numbers(ot), _numbers(at)
    only_ozet, only_abstract = sorted(o_nums - a_nums), sorted(a_nums - o_nums)
    if only_ozet or only_abstract:
        issues.append({"issue": "numbers", "only_in_ozet": only_ozet,
                       "only_in_abstract": only_abstract,
                       "detail": ("a figure reported in one summary and not the other — "
                                  "or reported differently — is the single most common "
                                  "Özet/Abstract defect, and reviewers do compare them. "
                                  "Decimal separators are normalized before comparison, "
                                  "so 94,2 and 94.2 count as the same number.")})
    o_kw, a_kw = _keywords(ot), _keywords(at)
    if o_kw and a_kw and len(o_kw) != len(a_kw):
        issues.append({"issue": "keywords", "ozet_keywords": len(o_kw),
                       "abstract_keywords": len(a_kw),
                       "detail": "keyword lists must correspond one-to-one"})
    elif bool(o_kw) != bool(a_kw):
        issues.append({"issue": "keywords",
                       "detail": f"keywords present in "
                                 f"{'Özet' if o_kw else 'Abstract'} only"})
    if not issues:
        return []
    return [{"check": "ozet_abstract", "status": "mismatch",
             "ozet_file": op.name, "abstract_file": ap.name,
             "message": f"{len(issues)} Özet↔Abstract discrepancy/ies",
             "issues": issues}]


# ---------- orchestration ----------

def check(drafts_dir: Path, glossary_path: Path, which: tuple[str, ...]) -> dict:
    files = read_drafts(drafts_dir)
    if not files:
        return {"status": "no-drafts", "checks_run": [], "warnings": [],
                "files_scanned": 0,
                "note": f"no .md files under {drafts_dir} — nothing to check"}
    glossary = load_glossary(glossary_path)
    warnings: list[dict] = []
    # A Turkish paper's English Abstract is required by nearly every Turkish
    # journal and by the YÖK thesis rules, and it is written in ENGLISH
    # orthography: the decimal point, and the percent sign AFTER the number.
    # Linting it against Turkish convention reports correct work as wrong — and
    # does something worse than that. decimal_separator and term_unity are
    # corpus-wide TALLIES that name the dominant form, so an English abstract's
    # numbers and its English terms are counted on the minority side of a vote
    # about the Turkish body. In this kit's own example review that turned a
    # correct Turkish body plus a correct English abstract into "both decimal
    # separators are in use" and five percent-placement errors, none of which
    # was a defect. Same failure shape as a DOI being read as a decimal: foreign
    # material inflating the count that decides the convention.
    # ozet_abstract is the exception and must keep the full list — comparing the
    # two is its entire job.
    # GENERATED files leave for the same reason, one step further out. A table
    # emitted by a build script carries a banner telling the author not to edit
    # it, and its cells quote source strings verbatim — English product names,
    # English grader descriptions, English target-condition labels. Those are
    # the source's words, not the author's register, and they were being counted
    # on the minority side of the same corpus-wide vote. Worse, the warning was
    # unactionable by construction: the only place to "fix" it is a file the
    # banner forbids editing. A lint must point at text its reader can change.
    tr_files = [(p, t) for p, t in files
                if not _is_english_abstract(p) and not _is_generated(p)]

    for name in which:
        if name == "decimal_separator":
            warnings += check_decimal_separator(tr_files)
        elif name == "percent_placement":
            warnings += check_percent_placement(tr_files)
        elif name == "abbreviation":
            warnings += check_abbreviation(tr_files)
        elif name == "informal_register":
            warnings += check_informal_register(tr_files)
        elif name == "term_unity":
            warnings += check_term_unity(tr_files, glossary)
        elif name == "voice_mixing":
            warnings += check_voice_mixing(tr_files)
        elif name == "ozet_abstract":
            warnings += check_ozet_abstract(files)
    out = {
        "status": "ok",
        "checks_run": list(which),
        "files_scanned": len(files),
        "files": [p.name for p, _ in files],
        "warnings": warnings,
        "warning_count": len(warnings),
        "limits": ("Not a grammar checker: no parser, no morphology, no lexicon. "
                   "Subject-predicate agreement, participle formation and postposition "
                   "errors are invisible here and stay with style-auditor."),
    }
    if "term_unity" in which and not glossary:
        out["note"] = (f"term_unity skipped: no glossary at {glossary_path}. "
                       f"Copy templates/tr-terminology.json into the project.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--glossary", default="templates/tr-terminology.json")
    ap.add_argument("--check", default="all",
                    help=f"comma list of {', '.join(ALL_CHECKS)} (default all)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.drafts, "--drafts")
    require_within_cwd(args.glossary, "--glossary")
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    if args.check.strip().lower() == "all":
        which = ALL_CHECKS
    else:
        which = tuple(c.strip() for c in args.check.split(",") if c.strip())
        unknown = [c for c in which if c not in ALL_CHECKS]
        if unknown:
            die(f"unknown check(s): {', '.join(unknown)} — pick from {', '.join(ALL_CHECKS)}")
    try:
        result = check(Path(args.drafts), Path(args.glossary), which)
    except json.JSONDecodeError as e:
        die(f"could not parse the glossary {args.glossary} — {e}")
    emit(result, True)
    sys.exit(2 if (args.strict and result.get("warnings")) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
