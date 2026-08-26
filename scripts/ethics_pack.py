#!/usr/bin/env python3
"""ethics_pack.py — the ethics application and the consent form, checked against what you collect.

WHY THIS EXISTS
`/collect-data` already produces the protocol: purpose, legal basis, sampling,
fields, minimisation, retention, consent, ethics approval, contact. Every ethics
board then asks for the same material again on its own form, plus an informed
consent text — and that second document is written from memory of the first,
weeks later, by which time the field list has moved.

The gap that matters is exactly there. A collection plan gains a column
(`author_email` was right there in the response) and the consent form still says
"we collect only the post text". Nobody notices, because nothing compares the two
documents. This does: the collection plan's own field list is the authority, and
a field collected but not disclosed to the participant is the finding.

WHAT IT REFUSES
- **To know your board's form.** The field list comes from `form-fields.json`,
  which YOU fill from your institution's own application form, with the URL or
  document you read it in. No file ⇒ `UNCHECKED`, not `OK`.
- **To state that approval was obtained.** It writes no approval number, no
  decision date, no board name, and flags a placeholder left in the text. An
  application that claims its own approval is the one document nobody should be
  able to generate.
- **To print what the PII scan finds.** Counts and column names only, same rule
  as `collection_check.py --scan`, for the same reason.
- **To judge whether the study is ethical.** Every check here is presence,
  agreement or arithmetic. Whether the risk is proportionate, whether the
  population is appropriate, whether the consent is genuinely informed — that is
  the board's judgement and no part of it is mechanical.

USAGE
  python scripts/ethics_pack.py --scaffold            # skeletons, placeholders left visible
  python scripts/ethics_pack.py --check               # the audit
  python scripts/ethics_pack.py --check --scan analysis/data/collected.csv

Exit codes: 0 nothing to report · 1 error · 2 findings, or nothing was checked.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collection_check import _fold, check_protocol, scan_file
from lib_common import die, emit, require_within_cwd, write_text_atomic

DEFAULT_DIR = "exports/ethics"
DEFAULT_FIELDS = "exports/ethics/form-fields.json"
DEFAULT_PLAN = "analysis/collection-plan.json"

# What an informed-consent text has to contain. Keys are the names a board uses;
# the tuples are the words an author actually types, in both languages. Presence
# only — that a form mentions withdrawal says nothing about whether withdrawal is
# genuinely possible, which is not a checkable property of a document.
CONSENT_ELEMENTS = {
    "purpose": ("purpose", "amaç", "why this study", "çalışmanın amacı"),
    "voluntary": ("voluntary", "gönüllü", "isteğe bağlı"),
    "withdrawal": ("withdraw", "geri çek", "ayrılma", "çekilme", "vazgeç"),
    "data_categories": ("data we collect", "toplanan veri", "collected data",
                        "hangi veriler", "veri kategori"),
    "retention": ("retention", "saklama", "stored for", "ne kadar süre", "silin"),
    "access": ("access", "erişim", "who will see", "paylaş", "shared with"),
    "confidentiality": ("confidential", "gizli", "anonym", "anonim", "pseudonym", "takma ad"),
    "risks": ("risk", "discomfort", "rahatsızlık", "zarar"),
    "contact": ("contact", "iletişim", "sorumlu araştırmacı", "responsible researcher"),
    "ethics_reference": ("ethics committee", "etik kurul", "irb", "institutional review"),
}

# Retention answers that are not answers. A board reads "as long as necessary"
# as "we have not decided", and it is right.
VAGUE_RETENTION = ("as long as necessary", "gerektiği sürece", "gerektiği kadar",
                   "indefinitely", "süresiz", "belirsiz", "until no longer needed",
                   "ihtiyaç duyulduğu sürece")

# Text left where a real value belongs. Checked case-insensitively; `<...>` and
# `XXX` are what a scaffold leaves behind and what gets submitted by accident.
PLACEHOLDER_RE = re.compile(r"(<[^>\n]{2,40}>|\bTODO\b|\bTBD\b|X{3,}|\.{4,}|_{4,})")

GENERIC_FORM_FIELDS = [
    "title", "investigators", "institution", "purpose", "design", "participants",
    "sample_size", "recruitment", "data_collected", "instruments", "risks",
    "benefits", "consent_procedure", "confidentiality", "data_storage",
    "retention_period", "legal_basis", "funding", "conflicts", "contact",
]


def load_form_fields(path: Path) -> dict | None:
    """The board's own field list. Same contract as submission_pack.load_limits:
    a file with no source is a remembered form, which is the thing being refused."""
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    if not spec.get("source_url") and not spec.get("source_document"):
        die(f"{path} has no 'source_url' or 'source_document' — a form field list with "
            f"no source is a remembered form, and this file exists so nothing is remembered")
    if not isinstance(spec.get("fields"), list) or not spec["fields"]:
        die(f"{path} needs a non-empty 'fields' array — the sections your board's form asks for")
    return spec


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def plan_fields(plan_path: Path) -> list[str]:
    """The columns the collection actually writes. This is the authority the
    consent form is measured against — not the protocol prose, which is where
    the two documents drift apart in the first place."""
    if not plan_path.is_file():
        return []
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{plan_path} is not valid JSON — {e.msg}")
    fields = plan.get("fields")
    return sorted(fields) if isinstance(fields, dict) else []


def _mentions_field(folded_text: str, field: str) -> bool:
    """Is this collected field named in the consent text?

    Word-boundary matched, not `in`. A substring test reported a field called
    `id` or `e` as disclosed by any sentence containing those letters — a false
    NEGATIVE on the one check this script exists for, and the short technical
    column names (`id`, `ts`, `ip`, `e`) are exactly the ones an author forgets
    to disclose. Both spellings are tried, because a plan's `post_text` is
    written "post metni" as often as "post_text".
    """
    for variant in {field, field.replace("_", " ")}:
        needle = _fold(variant).strip()
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", folded_text):
            return True
    return False


def check_consent(text: str, collected: list[str]) -> dict:
    folded = _fold(text)
    present, missing = [], []
    for name, keys in CONSENT_ELEMENTS.items():
        (present if any(_fold(k) in folded for k in keys) else missing).append(name)
    undisclosed = [f for f in collected if not _mentions_field(folded, f)]
    vague = [phrase for phrase in VAGUE_RETENTION if _fold(phrase) in folded]
    problems = []
    if missing:
        problems.append(f"consent text has no {', '.join(sorted(missing))}")
    if undisclosed:
        problems.append(f"collected but not disclosed to the participant: "
                        f"{', '.join(undisclosed)} — the collection plan writes these "
                        f"columns and the consent text does not name them")
    if vague:
        problems.append(f"retention stated as {vague[0]!r} — a board reads that as "
                        f"'not decided'; give a period or a deletion date")
    return {"elements_present": sorted(present), "elements_missing": sorted(missing),
            "fields_collected": collected, "fields_undisclosed": undisclosed,
            "vague_retention": vague, "problems": problems}


def sections(text: str) -> list[tuple[str, str]]:
    """(heading, body) pairs for a Markdown document.

    Deliberately NOT "find the label in the folded text and slice the raw text
    at that index": `_fold` normalises through NFKD, which can change string
    length (ligatures, some pre-composed letters), so an index taken in the
    folded string does not address the same character in the original. Text
    before the first heading is ignored — a form's answer lives under its
    question, and a preamble that happens to contain the word "risks" is not an
    answer to the risks field.
    """
    parts = re.split(r"^#{1,6}[ \t]*(.+?)[ \t]*$", text, flags=re.M)
    # parts == [preamble, heading1, body1, heading2, body2, ...]
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def check_application(text: str, spec: dict | None) -> dict:
    """Every field the board's form asks for, answered or not. A heading with no
    body under it is unanswered — that is the state a submitted form is in when
    it comes back."""
    fields = (spec or {}).get("fields") or GENERIC_FORM_FIELDS
    found = [(_fold(h), b) for h, b in sections(text)]
    answered, unanswered = [], []
    for field in fields:
        label = _fold(str(field).replace("_", " "))
        body = next((b for h, b in found if label in h), None)
        if body is None:
            unanswered.append({"field": field, "why": "no heading for it"})
        elif not body.strip():
            unanswered.append({"field": field, "why": "heading present, nothing under it"})
        elif PLACEHOLDER_RE.search(body):
            unanswered.append({"field": field, "why": "still holds a placeholder"})
        else:
            answered.append(field)
    problems = []
    if unanswered:
        problems.append(f"{len(unanswered)} of {len(fields)} form fields unanswered")
    return {"fields": list(fields), "answered": answered, "unanswered": unanswered,
            "problems": problems}


def check_approval_claim(texts: dict[str, str]) -> dict:
    """The one thing this script must never help produce. A generated document
    that asserts its own approval — with a number, a date, or a board name — is
    the failure this whole file is arranged around, so it is checked explicitly
    rather than left to discipline."""
    claims = []
    pattern = re.compile(
        r"(approved by|approval (?:number|no|ref)|onay(?:lanmış|landı)|"
        r"etik kurul (?:onay|karar|izin)|karar no|decision no)[^\n]{0,80}", re.I)
    for name, text in texts.items():
        for m in pattern.finditer(text):
            snippet = m.group(0).strip()
            claims.append({"file": name, "text": snippet[:120],
                           "placeholder": bool(PLACEHOLDER_RE.search(snippet))})
    problems = [f"{c['file']}: approval reference still a placeholder — {c['text'][:60]!r}"
                for c in claims if c["placeholder"]]
    return {"approval_mentions": claims, "problems": problems,
            "note": ("this script writes no approval number and cannot confirm one. "
                     "An approval reference is true only if your board issued it")}


SCAFFOLD_APPLICATION = """# Ethics committee application

<!-- Every heading below comes from exports/ethics/form-fields.json, which you
     filled from your board's OWN form. Nothing here is filled in for you: a
     plausible sentence in an ethics application is worse than a blank one. -->

{sections}
"""

SCAFFOLD_CONSENT_TR = """# Bilgilendirilmiş Onam Formu

## Çalışmanın amacı
<tek paragraf, katılımcının anlayacağı dilde>

## Gönüllülük
Bu çalışmaya katılım tamamen gönüllüdür.

## Çekilme hakkı
<hangi ana kadar, nasıl, sonucunda ne olur>

## Toplanan veriler
<collection-plan.json'daki HER alan burada adıyla yazılmalı>

## Riskler ve rahatsızlıklar
<yoksa "öngörülen bir risk yoktur" yazın — boş bırakmayın>

## Gizlilik ve anonimlik
<anonim mi, takma adlı mı, kim çözebilir>

## Erişim ve paylaşım
<veriye kim erişecek, nereye yatırılacak>

## Saklama süresi
<somut bir süre ya da silme tarihi — "gerektiği sürece" bir cevap değildir>

## Etik kurul
<kurul adı; karar numarası ancak KURUL verdiyse yazılır>

## İletişim
<sorumlu araştırmacı, kurum, e-posta>
"""

SCAFFOLD_CONSENT_EN = """# Informed Consent Form

## Purpose of the study
<one paragraph, in language the participant will understand>

## Voluntary participation
Participation in this study is entirely voluntary.

## Right to withdraw
<until when, how, and what happens to data already given>

## Data we collect
<EVERY field in collection-plan.json, named here>

## Risks and discomforts
<if there are none, say so — do not leave it blank>

## Confidentiality
<anonymous or pseudonymous, and who can re-identify>

## Access and sharing
<who will see the data, where it will be deposited>

## Retention period
<a concrete period or deletion date — "as long as necessary" is not an answer>

## Ethics committee
<board name; a decision number goes here only if the BOARD issued it>

## Contact
<responsible researcher, institution, e-mail>
"""


def scaffold(out_dir: Path, spec: dict | None) -> dict:
    fields = (spec or {}).get("fields") or GENERIC_FORM_FIELDS
    sections = "\n\n".join(f"## {str(f).replace('_', ' ').capitalize()}\n<...>"
                           for f in fields)
    written, skipped = [], []
    targets = {
        "application.md": SCAFFOLD_APPLICATION.format(sections=sections),
        "consent-form.tr.md": SCAFFOLD_CONSENT_TR,
        "consent-form.en.md": SCAFFOLD_CONSENT_EN,
    }
    for name, body in targets.items():
        path = out_dir / name
        if path.exists():
            skipped.append(path.as_posix())
            continue
        write_text_atomic(path, body)
        written.append(path.as_posix())
    return {"written": written, "skipped_existing": skipped,
            "fields_source": ("form-fields.json" if spec else
                              "generic list — your board's form is NOT this list"),
            "next": "fill every <...>; then: python scripts/ethics_pack.py --check"}


def run_check(out_dir: Path, spec: dict | None, plan: Path, scans: list[str]) -> dict:
    application = _text(out_dir / "application.md")
    consent_files = sorted(out_dir.glob("consent-form*.md"))
    consent_text = "\n".join(_text(p) for p in consent_files)
    collected = plan_fields(plan)

    report: dict = {
        "form_fields_source": (spec or {}).get("source_url") or
                              (spec or {}).get("source_document"),
        "collection_plan": plan.as_posix() if plan.is_file() else None,
        "application": check_application(application, spec) if application else
        {"present": False, "problems": ["exports/ethics/application.md not found — "
                                        "run --scaffold"]},
        "consent": (check_consent(consent_text, collected) if consent_text else
                    {"present": False,
                     "problems": ["no consent-form*.md found — if this study has human "
                                  "participants that is the finding; if it does not, say "
                                  "so in the protocol's consent section"]}),
        "approval": check_approval_claim(
            {"application.md": application} |
            {p.name: _text(p) for p in consent_files}),
    }

    protocol = Path("analysis/collection-protocol.md")
    if protocol.is_file():
        completeness = check_protocol(_text(protocol))
        completeness["problems"] = ([f"protocol missing: {', '.join(completeness['missing'])}"]
                                    if completeness["missing"] else [])
        report["protocol"] = completeness

    if scans:
        files = []
        for rel in scans:
            require_within_cwd(rel, "--scan")
            p = Path(rel)
            if not p.is_file():
                die(f"{rel} does not exist")
            files.append(scan_file(p))
        hits = sum(sum(f["matches"].values()) for f in files)
        report["pii"] = {
            "files": files,
            "problems": ([f"{hits} personal-data matches in the collected files — the "
                          f"application must state how they are handled"] if hits else []),
            "note": "counts and column names only; matched values are never printed",
        }

    problems = []
    for key, section in report.items():
        if isinstance(section, dict):
            problems.extend({key: p} for p in section.get("problems", []))
    report["problems"] = problems
    report["result"] = "OK" if not problems else "FINDINGS"
    if spec is None:
        report["result"] = "UNCHECKED"
        report["note"] = (
            "no form-fields.json — the consent and protocol checks above ran, but the "
            "application was measured against a GENERIC field list, not your board's. "
            "Fill exports/ethics/form-fields.json from your institution's own form; "
            "this kit will not recall it.")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scaffold", action="store_true", help="write the skeleton documents")
    ap.add_argument("--check", action="store_true", help="audit what is on disk")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--fields", default=DEFAULT_FIELDS)
    ap.add_argument("--plan", default=DEFAULT_PLAN,
                    help="the collection plan whose field list the consent is checked against")
    ap.add_argument("--scan", nargs="+", metavar="FILE", default=[],
                    help="collected data file(s) to scan for personal data")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if args.scaffold == args.check:
        die("pick exactly one: --scaffold or --check")
    for flag, value in (("--dir", args.dir), ("--fields", args.fields), ("--plan", args.plan)):
        require_within_cwd(value, flag)

    spec = load_form_fields(Path(args.fields))
    out_dir = Path(args.dir)

    if args.scaffold:
        emit(scaffold(out_dir, spec), args.json_out)
        return

    report = run_check(out_dir, spec, Path(args.plan), args.scan)
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
