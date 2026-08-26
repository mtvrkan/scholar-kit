#!/usr/bin/env python3
"""claim_check.py — epistemic-claim lint for the draft manuscript (TR + EN).

Catches two defect classes that survive citation verification. A citation can be
real, resolvable and correctly formatted while the sentence built on it still
misrepresents its source — `cite_audit.py`/`doi2bib.py --verify` answer "does
this reference exist?", never "does it say that?".

  * overclaim: the prose states a STRONGER epistemic relation than the evidence
    card extracted from that same source does. "X causes Y [@kaya2023]" written
    on top of a card whose claim reads "X is associated with Y" is an
    unauthorized move up the claim-strength ladder.
  * uncited-assertion: a sentence carrying an empirical signal (a statistic, or
    a causal/directional verb) with no citation key and no own-work marker —
    an assertion attributable to neither the literature nor this study.

Both are WARN-only by default (never block — hedging is field-relative and a
human adjudicates); `--strict` exits 2 for callers that want a gate.

The claim-strength ladder (rungs 0-5, ascending):

    0  is consistent with / may suggest      ← hedged
    1  is associated with / correlates with
    2  predicts
    3  contributes to
    4  affects / increases / reduces
    5  causes / proves / determines

Direction matters and only ONE direction is a defect here. Prose weaker than its
card is not flagged: writing more cautiously than the source is always safe. The
reverse — prose stronger than the source it cites — is the misrepresentation.
(Contrast revision-diff tools, which flag silent movement in BOTH directions
because their baseline is the author's own prior text, not the source.)

Comparison needs a basis: a cited source with no evidence card, or cards with no
detectable rung, is skipped rather than guessed at. Uncarded sources therefore
weaken this check silently by design — `evidence_funnel.py` is what surfaces
those.

Usage:
  python scripts/claim_check.py [--drafts drafts/] [--cards evidence/cards.jsonl]
                                [--registry sources/registry.jsonl] [--json]
  python scripts/claim_check.py --strict          # exit 2 if any warning
  python scripts/claim_check.py --check overclaim # run one check only
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# \n excluded: `[^`]*` spans paragraphs, so two stray backticks in ordinary
# prose swallow every sentence between them and this checker stops seeing them
# at all. See cite_audit.py for the full note.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# Whole heading LINE, not just its "## " marker — stripping only the marker
# leaves "Accuracy of 91.2%" behind as apparent prose, and a section title is a
# label, not an assertion anyone owes a citation for.
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s.*$", re.MULTILINE)
# HTML comments are the kit's own evidence-binding syntax (`<!-- EV-0045 -->`,
# `<!-- RQ: rq1 | Cards: ... -->`) — the draft skill REQUIRES them. Left in the
# stream they are read as prose, and they fail in both directions at once: a
# comment carrying a card id and a percentage becomes an "uncited assertion with
# a statistic", while `<!-- Şekil 3 -->` would exempt the sentence it is glued to
# from a check it should have faced. Replaced with a space rather than "" so a
# comment sitting mid-sentence does not fuse the words on either side of it.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Pandoc citation syntax: [@key], [-@key], [@a; @b, p. 4], and bare @key.
CITE_RE = re.compile(r"@([A-Za-z][\w:.#$%&+?<>~/-]*)")

# ---------- claim-strength ladder ----------
# (rung, pattern). A sentence's rung is the MAXIMUM matched rung, minus one if a
# hedge is present (floor 0). Patterns are deliberately stem-based on the Turkish
# side: TR verbs inflect heavily ("etkilemektedir" / "etkilediği" / "etkiler"),
# so matching a stem is the only way to stay agglutination-proof without a
# morphological analyser.
# NOMINALIZED CLAIMS. Formal academic prose states relations as noun phrases at
# least as often as verbs — "the effect of X on Y" asserts exactly what "X
# affects Y" asserts — and a purely verb-anchored ladder read every one of them
# as rung-None, i.e. exempt from comparison entirely. Found by probing the
# shipped checker with sentences deliberately absent from the gold set: six of
# six nominal phrasings over an associative card were silent while their verb
# twins all fired. The gap was also ASYMMETRIC — English rung 5 caught its
# nominal ("the cause of") only because `caus(e|al|ation)` happens to span noun
# and verb, so Turkish, which had no such accident, was the weaker half. That is
# the same class as the ARTEFACT_RE asymmetry recorded in eval/MEASUREMENT.md.
# Every nominal pattern below requires FRAMING rather than the bare noun, so the
# meta-analysis vocabulary this kit generates elsewhere ("effect size",
# "random-effects model", "etki büyüklüğü") is not swept up as a claim.
LADDER_EN = [
    (1, r"\bassociat(?:ed|ion)\b|\bcorrelat(?:e[sd]?|ion)\b|\brelated to\b|\blinked to\b|\bco-?occur"),
    (2, r"\bpredict(?:s|ed|or|ive)?\b|\bforecast(?:s|ed)?\b"),
    (3, r"\bcontribut(?:e[sd]?|ion)\b|\bplays? an? (?:key |major |central )?role\b"),
    # Change-of-state verbs need positional care: their -ed forms are far more
    # often ATTRIBUTIVE adjectives than verbs ("reduced lung capacity",
    # "increased risk"), and reading those as claims made every source card
    # describing an outcome look rung-4. Finite and infinitive forms match
    # anywhere; -ed forms only behind an auxiliary (passive) or a modal.
    (4, r"\b(?:affects?|influences?|leads? to|led to|shapes?|improves?|reduces?"
        r"|increases?|decreases?|enhances?|drives?)\b"
        r"|\b(?:is|are|was|were|be|been|being|has|have|had)\s+(?:\w+ly\s+)?"
        r"(?:affected|influenced|shaped|improved|reduced|increased|decreased|enhanced|driven)\b"
        r"|\b(?:to|may|might|can|could|will|would|should)\s+(?:\w+ly\s+)?"
        r"(?:affect|influence|shape|improve|reduce|increase|decrease|enhance|drive)\b"
        # Nominal, framed: "the effect of X on Y", "its impact on Y",
        # "the primary driver of Y".
        r"|\b(?:effects?|impacts?|influences?)\s+(?:of|on)\b"
        r"|\bdrivers?\s+of\b"),
    (5, r"\bcaus(?:e[sd]?|al|ation)\b|\bprov(?:e[sd]?|es)\b|\bdetermin(?:e[sd]?|es)\b"
        r"|\bdemonstrates? that\b|\bestablishes? that\b|\bconfirms? that\b"),
]
# Turkish patterns are written DIACRITIC-INSENSITIVE ([sş], [ıi], [oö], [uü],
# [gğ], [cç]). ASCII-folded Turkish is common in practice — filenames, quick
# typing, editors without a TR layout, text round-tripped through tools that
# strip diacritics — and a pattern that only matched "çalışma" silently stopped
# recognising "calismada", turning every own-work exemption into a false
# positive. The kit already folds Turkish elsewhere (lib_common.transliterate);
# these patterns must tolerate the folded form on the way in.
LADDER_TR = [
    (1, r"ili[sş]ki|ba[gğ]lant[ıi]l[ıi]|korelasyon|birlikte de[gğ]i[sş]"),
    (2, r"[oö]ng[oö]r|yorda|tahmin et"),
    # "katkısı" as a bare noun ("X'in Y'ye katkısı büyüktür") carries the claim
    # without either of the light verbs the original two patterns required.
    (3, r"katk[ıi]\w* bulun|rol oyna|katk[ıi] sa[gğ]la|katk[ıi]s[ıi]"),
    # Same attributive-participle problem as the English rung 4: "azaltılmış
    # kapasite" / "artırılmış risk" are adjectives, not claims. The Turkish
    # passive-participle suffix chain (-Il- + -mIş) is regular enough to exclude
    # with a lookahead, which an inflecting language makes cheaper than the
    # English positional rule.
    (4, r"(?:etkile|art[ıi]r|azalt|yol a[cç]|iyile[sş]tir|d[uü][sş][uü]r"
        r"|y[uü]kselt|geli[sş]tir|k[oö]t[uü]le[sş])"
        r"(?!\w*[ıiuü]l(?:m[ıi][sş]|m[uü][sş]))"
        # "etkisi" (+ its case suffixes: etkisini, etkisinin, etkisiyle) is the
        # nominal form and shares no prefix with the verb stem "etkile-", so it
        # matched nothing at all. The plural "etkileri" already matched via
        # "etkile" by accident. Two exclusions: "-siz" is the PRIVATIVE
        # ("etkisiz" = ineffective, the opposite claim), and bare "etki" is left
        # out so "etki büyüklüğü" (effect size) stays clear.
        r"|etkis[ıi](?!z)"),
    # Nominal causation: "nedeni" / "sebebi" / "kaynaklanmaktadır" are how the
    # claim behind "neden ol-" is written when the sentence is built around a
    # noun instead of a verb.
    # "neden" requires a suffix here: bare "neden" is the interrogative "why"
    # ("bu sonucun neden ortaya çıktığı"), which asserts nothing.
    (5, r"neden ol|kan[ıi]tla|ispatla|yol a[cç]t[ıi][gğ][ıi]n[ıi] g[oö]ster|nedensel"
        r"|neden(?:i|ler)|sebeb(?:i|iyle)|sebepler|kaynaklan"),
]
# A modal/epistemic hedge demotes the rung by one. Turkish -ebil-/-abil- is a
# suffix, not a word, hence the \w+ prefix.
HEDGE_RE = re.compile(
    r"\bmay\b|\bmight\b|\bcould\b|\bappears? to\b|\bseems? to\b|\bsuggest(?:s|ed|ing)?\b"
    r"|\bpotentially\b|\bpossibly\b|\blikely\b|\bconsistent with\b"
    r"|\w+[ae]bil(?:ir|ece|mekte|ece[gğ])|olabilir|muhtemelen|g[oö]r[uü]nmekte"
    r"|d[uü][sş][uü]nd[uü]r|i[sş]aret edebil",
    re.IGNORECASE)

# ---------- uncited-assertion signals ----------
# A statistic is the least ambiguous empirical signal: a percentage, a p-value,
# an n=, a CI, or a bare decimal (0.87 accuracy). Integers alone are excluded —
# "3 sections", "2 raters" are not empirical claims.
STAT_RE = re.compile(
    r"%\s?\d|\d\s?%|\bp\s?[<=>]\s?\.?\d|\bn\s?=\s?\d|\bN\s?=\s?\d"
    r"|\b\d+[.,]\d+\b|\b(?:95|99)\s?%?\s?(?:CI|GA)\b|\bAUC\b|\bF1\b|\br\s?=\s?[.\-\d]",
    re.IGNORECASE)
# First-person / this-study markers. A sentence carrying one is reporting OWN
# work and needs no external citation.
OWNWORK_RE = re.compile(
    r"\bwe\b|\bour\b|\bthis (?:study|paper|work|article|analysis|section|review)\b"
    r"|\bthe present (?:study|work|paper|review)\b|\bhere,? we\b"
    r"|\b[cç]al[ıi][sş]mam\w*|\bbulgular[ıi]m[ıi]z"
    # "derleme"/"inceleme"/"review" are here for the same reason DEFAULT_SKIP
    # carries "sentez": a REVIEW does not call itself "bu çalışma", it calls
    # itself "bu derleme", so the self-reference the whole exemption rests on
    # was invisible for exactly the paper type the kit is most used for.
    # "ek"/"protokol"/"tablo"/"şekil" extend the same point one level down: an
    # APPENDIX says "bu ek", a caption says "bu tablo". Those sentences describe
    # the manuscript's own apparatus — what a checklist row covers, why a column
    # is blank — and are no more empirical claims about the literature than
    # "bu derleme" is. Without them a reporting-checklist appendix, which is
    # nothing BUT self-reference, reads as a page of uncited assertions.
    # No trailing \b: Turkish suffixes the noun ("bu çalışmanın", "bu ekte"),
    # and anchoring the end drops exactly those inflected forms.
    r"|\bbu (?:[cç]al[ıi][sş]ma|makale|b[oö]l[uü]m|ara[sş]t[ıi]rma|derleme|inceleme"
    r"|ek|protokol|tablo|[sş]ekil|kontrol listesi)"
    r"|\by[oö]ntemimiz|\bmodelimiz|\b[oö]nerdi[gğ]imiz|\bkulland[ıi][gğ][ıi]m[ıi]z"
    r"|\belde edilen",
    re.IGNORECASE)
# A pointer to an in-manuscript artefact is also own-work evidence.
# The abbreviated forms are listed on BOTH sides deliberately. This pattern
# accepted the English "Fig." but none of the Turkish abbreviations a Turkish
# author actually writes (Şek., Denk., Böl., Tbl.), so the own-work allowance
# was quietly weaker in Turkish than in English — the exact asymmetry the kit
# claims not to have. Every abbreviation here is also protected in _PROTECT
# below, or the sentence splitter breaks the pointer off its own statistic.
ARTEFACT_RE = re.compile(
    r"\b(?:Table|Tbl\.|Figure|Fig\.|Section|Sec\.|Eq\.|Equation"
    r"|Algorithm|Alg\.)\s*\d"
    r"|\b(?:Tablo|Tbl\.|[SŞ]ekil|[SŞ]ek\.|B[oö]l[uü]m|B[oö]l\."
    r"|Denklem|Denk\.)\s*\d"
    # A bare Roman-numeral section cross-reference — "(III.4)", "(IV.2)",
    # "(III.6a)", "(II.4)". Numbering sections I./II./III./IV. is a mainstream
    # convention (and the one a Turkish thesis or article most often uses), but
    # the keyword forms above all require a literal "Section"/"Bölüm" plus an
    # ARABIC digit, so a manuscript that numbers this way had NO working
    # own-work pointer: every Discussion sentence restating the paper's own
    # Results came back as an uncited empirical assertion. The keyword is
    # implicit in the numbering here, not absent.
    # Anchored tightly on purpose — Roman numeral, a dot, then at least one
    # digit — so a sentence-initial "I" or a stray "V" cannot match.
    r"|\b(?:I{1,3}|IV|VI{0,3}|IX|XI{0,3}|X)\.\d+(?:\.\d+)*[a-z]?\b",
    re.IGNORECASE)
# Files whose content is own-work by construction — scanning them for missing
# citations produces noise, not signal.
DEFAULT_SKIP = r"^(?:\d+[-_])?(?:(?:results?|bulgular|findings|synthesis|sentez|" \
               r"methods?|methodology|y[oö]ntem|" \
               r"materyal|abstract|[oö]zet|conclusion|sonu[cç]|STATUS|" \
               r"beyanlar|declarations?|disclosures?|statements?|" \
               r"ekler|appendix|appendices|supplement(?:ary|al)?)\b" \
               r"|ek[-_])"
# "ek[-_]" sits outside the \b group on purpose: `\b` does not hold between an
# underscore and a letter (both are word characters), so an `ek_a.md` slipped
# through a version that anchored the whole alternation.
# The declarations section (funding, competing interests, CRediT, data
# availability, registration — PRISMA 2020 items 25-27, and the "Statements and
# Declarations" block most journals now require) is on the list for the same
# reason. Every sentence in it is a statement ABOUT this manuscript: what was
# funded, what was deposited, when the analysis rules were written. There is
# nothing to cite because there is no source — the author IS the source — and a
# real one duly arrived as an "uncited empirical assertion" for explaining why
# its own PRISMA counts are not derived from the register.
# Appendices join the list for the same reason Methods is on it: they are
# own-work by construction. A reporting-checklist appendix says which section
# answers which item; an own-analysis appendix reports a computation this review
# performed. Neither cites a source because neither has one to cite, and before
# they were skipped a two-page appendix arrived as eight "uncited empirical
# assertions" — the exact noise this list exists to prevent, one document type
# further out than the sections already named.
# "synthesis"/"sentez" are here because a REVIEW's results section has to be
# called that: word_budget.py's review proportions key on `synthesis`, so the
# file cannot also be named `results` to satisfy this list. Two kit scripts
# disagreeing about one section's filename left a systematic review's central
# section as the only own-work file still scanned for missing citations, and it
# duly reported the review's own synthesis sentences as uncited assertions.

# Sentence splitting: mask the dots inside decimals and common abbreviations so
# "0.87" / "et al." / "vs." / "Fig. 2" don't fabricate sentence boundaries. The
# mask is a control byte that cannot occur in a Markdown draft, restored verbatim
# after the split — masking must be REVERSIBLE, because these sentences are then
# pattern-matched for statistics and echoed back to the user in the report.
_DOT = "\x00"
_PROTECT = [
    (re.compile(r"(\d)\.(\d)"), r"\1" + _DOT + r"\2"),
    # Every abbreviation ARTEFACT_RE is willing to recognise must be protected
    # here too, or the artefact allowance defeats itself: "the threshold is
    # derived in Eq. 4 and equals 0.63" split at "Eq." into two sentences, and
    # the fragment carrying the statistic no longer carried the pointer that
    # exempts it — a false uncited-assertion on a sentence any ML paper writes.
    # Fig/Tab were protected; Eq/Sec/Alg/Tbl and the Turkish Şek./Denk. were not.
    (re.compile(r"\b(et al|vs|cf|e\.g|i\.e|Fig|Tab|Tbl|Eq|Sec|Alg"
                r"|[sş]ek|denk|b[oö]l"
                r"|No|pp|Dr|Prof|approx|yak|bkz|ss|s)\.",
                re.IGNORECASE), r"\1" + _DOT),
]
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _clean(text: str) -> str:
    """Drop code fences, inline code, HTML comments and headings — none are prose."""
    text = INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))
    return HEADING_RE.sub("", COMMENT_RE.sub(" ", text))


def split_sentences(text: str) -> list[str]:
    for pat, repl in _PROTECT:
        text = pat.sub(repl, text)
    out = []
    for raw in _SENT_SPLIT.split(text):
        s = raw.replace(_DOT, '.').strip()
        if s:
            out.append(s)
    return out


_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


def is_table_row(sent: str) -> bool:
    """True when this 'sentence' is really one or more markdown table rows.

    A row is not prose and must not be graded as one. The splitter breaks on
    sentence punctuation, which no table respects: a cell ending without a
    period is glued to the next row, so one flagged fragment can span two rows
    of unrelated content and name a phrase from neither. A cell also has no
    room for a citation — its source is the row's own study column, or the
    section the row points at — so the uncited-assertion lint, whose whole
    premise is "this assertion should have carried a key", cannot be satisfied
    inside one however true the cell is. Surfaced by a reporting-checklist
    appendix, which is nothing but table.

    Deliberately consulted by the uncited check only. Overclaiming inside a
    table cell is entirely possible and stays in scope.
    """
    lines = [l for l in sent.splitlines() if l.strip()]
    return bool(lines) and all(_TABLE_ROW_RE.match(l) for l in lines)


def rung_of(text: str) -> tuple[int, str] | tuple[None, None]:
    """Highest claim-strength rung expressed in `text`, and the phrase that hit.

    Returns (None, None) when no ladder verb is present — the caller must treat
    that as "no basis for comparison", never as rung 0.
    """
    best, phrase = None, None
    for ladder in (LADDER_EN, LADDER_TR):
        for rung, pat in ladder:
            m = re.search(pat, text, re.IGNORECASE)
            if m and (best is None or rung > best):
                best, phrase = rung, m.group(0)
    if best is None:
        return None, None
    if HEDGE_RE.search(text):
        best = max(0, best - 1)
    return best, phrase


def cited_keys(sentence: str) -> list[str]:
    return [m.group(1).rstrip(".,;:") for m in CITE_RE.finditer(sentence)]


def build_source_rungs(cards: list[dict], registry: list[dict]) -> dict:
    """Map every source identifier to the strongest rung its cards express.

    A card's `source` may hold a bib_key OR the registry id (SRC-####) — cards
    are written before a bib_key exists. Index both spellings so a draft citing
    `[@kaya2023deep]` still resolves to cards filed under `SRC-0007`.
    """
    alias = {}
    for r in registry:
        bib, sid = r.get("bib_key"), r.get("id")
        if bib and sid:
            alias[sid] = bib
            alias[bib] = bib
    out: dict[str, dict] = {}
    for c in cards:
        src = c.get("source")
        if not src:
            continue
        key = alias.get(src, src)
        text = " ".join(str(c.get(f) or "") for f in ("claim", "detail"))
        rung, phrase = rung_of(text)
        if rung is None:
            continue
        cur = out.get(key)
        if cur is None or rung > cur["rung"]:
            out[key] = {"rung": rung, "phrase": phrase, "card": c.get("id"),
                        "claim": (c.get("claim") or "")[:160]}
    # Make every alias spelling resolve to the same record.
    for sid, bib in alias.items():
        if bib in out and sid not in out:
            out[sid] = out[bib]
    return out


RUNG_NAME = {0: "hedged", 1: "associative", 2: "predictive", 3: "contributory",
             4: "directional", 5: "causal"}


def scan_overclaim(sentences: list[tuple[str, str]], source_rungs: dict) -> list[dict]:
    hits = []
    for sent, where in sentences:
        keys = cited_keys(sent)
        if not keys:
            continue
        draft_rung, draft_phrase = rung_of(sent)
        if draft_rung is None:
            continue
        # Most generous reading: compare against the STRONGEST rung available
        # among the cited sources, so a sentence synthesising two sources is not
        # flagged for exceeding the weaker one.
        basis = [source_rungs[k] for k in keys if k in source_rungs]
        if not basis:
            continue
        best = max(basis, key=lambda b: b["rung"])
        if draft_rung > best["rung"]:
            hits.append({
                "where": where,
                "sentence": sent[:240],
                "draft_rung": draft_rung,
                "draft_rung_name": RUNG_NAME[draft_rung],
                "draft_phrase": draft_phrase,
                "source_rung": best["rung"],
                "source_rung_name": RUNG_NAME[best["rung"]],
                "source_phrase": best["phrase"],
                "card": best["card"],
                "card_claim": best["claim"],
                "cited": keys,
                "msg": (f"prose is {RUNG_NAME[draft_rung]} ('{draft_phrase}') but "
                        f"{best['card']} is only {RUNG_NAME[best['rung']]} "
                        f"('{best['phrase']}') — {where}"),
            })
    return hits


def scan_uncited(sentences: list[tuple[str, str]]) -> list[dict]:
    hits = []
    for sent, where in sentences:
        if (cited_keys(sent) or OWNWORK_RE.search(sent) or ARTEFACT_RE.search(sent)
                or is_table_row(sent)):
            continue
        rung, phrase = rung_of(sent)
        has_stat = bool(STAT_RE.search(sent))
        # Require a hard empirical signal: a statistic, or a rung-4+ claim.
        # Associative/predictive prose without a number is too often a framing
        # sentence to be worth the false positives.
        if not has_stat and (rung is None or rung < 4):
            continue
        hits.append({
            "where": where,
            "sentence": sent[:240],
            "signal": "statistic" if has_stat else f"{RUNG_NAME[rung]}-claim",
            "phrase": phrase,
            "msg": (f"empirical assertion with no citation and no own-work marker "
                    f"({'statistic' if has_stat else phrase}) — {where}"),
        })
    return hits


def collect_sentences(drafts_dir: Path, skip_re) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    scanned, skipped = [], []
    sentences = []
    if not drafts_dir.exists():
        return sentences, scanned, skipped
    for f in sorted(drafts_dir.glob("**/*.md")):
        # STATUS.md is the project's own progress log, not manuscript prose —
        # excluded outright, matching consistency_check.py and failure_scan.py.
        # It was previously only exempt from the uncited-assertion half, so a
        # status note could still be scored for overclaim.
        if f.name == "STATUS.md":
            continue
        if skip_re and skip_re.search(f.stem):
            skipped.append(f.as_posix())
            continue
        scanned.append(f.as_posix())
        text = _clean(f.read_text(encoding="utf-8", errors="replace"))
        for s in split_sentences(text):
            sentences.append((s, f.as_posix()))
    return sentences, scanned, skipped


def check(drafts_dir: Path, cards_path: Path, registry_path: Path,
          which: str = "all", skip_pattern: str = DEFAULT_SKIP) -> dict:
    try:
        skip_re = re.compile(skip_pattern, re.IGNORECASE) if skip_pattern else None
    except re.error as e:
        die(f"--skip is not a valid regular expression — {e}")

    cards = read_jsonl(cards_path) if cards_path.exists() else []
    registry = read_jsonl(registry_path) if registry_path.exists() else []
    source_rungs = build_source_rungs(cards, registry)

    sentences, scanned, skipped = collect_sentences(drafts_dir, skip_re)
    # Overclaim needs every sentence including own-work sections (Results cite
    # sources too); uncited-assertion is the check that skipping protects.
    all_sentences, _, _ = collect_sentences(drafts_dir, None)

    overclaim = scan_overclaim(all_sentences, source_rungs) if which in ("all", "overclaim") else []
    uncited = scan_uncited(sentences) if which in ("all", "uncited") else []

    return {
        "files_scanned": scanned,
        "files_skipped_for_uncited": skipped,
        # Distinct cards, not index entries: `source_rungs` deliberately holds
        # every alias spelling (bib_key AND SRC-####) of the same source, so
        # len() there double-counts and would overstate comparison coverage.
        "sources_with_rung": len({v["card"] for v in source_rungs.values()}),
        "sentences_examined": len(all_sentences),
        "overclaim": overclaim,
        "uncited_assertions": uncited,
        "warnings": len(overclaim) + len(uncited),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--cards", default="evidence/cards.jsonl")
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--check", choices=("all", "overclaim", "uncited"), default="all")
    ap.add_argument("--skip", default=DEFAULT_SKIP,
                    help="regex over draft filename stems exempted from the "
                         "uncited-assertion check (own-work sections); pass '' to scan all")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.drafts, "--drafts")
    require_within_cwd(args.cards, "--cards")
    require_within_cwd(args.registry, "--registry")
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    result = check(Path(args.drafts), Path(args.cards), Path(args.registry),
                   args.check, args.skip)
    emit(result, True)
    sys.exit(2 if (args.strict and result["warnings"]) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"a draft file is not valid UTF-8 — {e}")
