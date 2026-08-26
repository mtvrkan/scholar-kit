#!/usr/bin/env python3
"""deposit_pack.py — the preprint deposit, and the correction nobody plans for.

WHY THIS EXISTS
Two moments sit either side of publication and neither had a command.

**The preprint.** arXiv, SSRN, TechRxiv and OSF each have their own abstract
limit, category taxonomy and licence menu, and each asks a question the author
usually answers by guessing: does the target journal permit posting, and under
which licence. Getting the licence wrong is close to irreversible — a preprint
server will not un-CC-BY a posted paper — and the disclosure the journal then
requires in the cover letter gets forgotten because nothing recorded that a
preprint exists.

**The correction.** An error is found in a published paper. The letter is the
easy half. The hard half is the question nobody asks in the right order: what
else did that number touch — which figure, which table, which claim, which run,
which evidence card. A corrigendum that fixes the abstract and leaves the
discussion standing on the old value is a second correction waiting.

WHAT IT REFUSES
- **To know a server's limits or a journal's preprint policy.** Both come from
  files you fill, with the URL you read them at. "arXiv allows 1920 characters"
  is a remembered limit; the policy question is surfaced, never answered.
- **To choose your licence.** The options are listed with what each permits; the
  choice is recorded as yours or left blank.
- **To decide that a correction is needed, or that it is enough.** It reports
  everywhere the wrong value appears. Whether the paper needs a corrigendum, an
  erratum or a retraction is between the authors and the editor.

USAGE
  python scripts/deposit_pack.py --preprint arxiv
  python scripts/deposit_pack.py --corrigendum --error exports/deposit/erratum.json

Exit codes: 0 clean · 1 error · 2 findings, open questions, or UNCHECKED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import translation_check as tc
from lib_common import die, emit, read_jsonl, require_within_cwd
from submission_pack import check_abstract, check_keywords, title_of

DEFAULT_LIMITS = "exports/deposit/server-limits.json"
DEFAULT_ERROR = "exports/deposit/erratum.json"
SERVERS = ("arxiv", "ssrn", "techrxiv", "osf", "biorxiv", "other")

# The questions a deposit form asks that no register can answer. Surfaced as
# questions — a tool that silently picks a licence has made a decision the author
# cannot take back.
OPEN_QUESTIONS = [
    ("target_journal_policy",
     "Does your target journal permit posting a preprint of this version, and at "
     "which stage (submitted / accepted / published)? Read the journal's OWN "
     "policy — this is not recalled here, and it differs between imprints of the "
     "same publisher."),
    ("licence",
     "Which licence? CC-BY permits redistribution and adaptation with attribution; "
     "CC-BY-NC forbids commercial reuse; arXiv's non-exclusive licence permits "
     "distribution only. A posted licence is effectively irreversible."),
    ("category",
     "Which primary category/subject class? Wrong classification is the single "
     "most common reason a preprint is quietly unread."),
    ("version_posted",
     "Which version is this — the submitted manuscript, the accepted manuscript, "
     "or the published version? Only one of the three is usually permitted."),
    ("coauthor_consent",
     "Have all co-authors agreed to posting? A preprint is a publication act."),
]


def load_json_file(path: Path, what: str, required_keys: tuple[str, ...]) -> dict | None:
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    if not spec.get("source_url"):
        die(f"{path} has no 'source_url' — {what} with no source is a remembered "
            f"{what}, and this file exists so nothing is remembered")
    missing = [k for k in required_keys if not spec.get(k)]
    if missing:
        die(f"{path} is missing {', '.join(missing)}")
    return spec


def preprint(drafts: Path, project: Path, server: str, limits: dict | None) -> dict:
    title, title_source = title_of(drafts, project)
    abstract_file = drafts / "abstract.md"
    abstract_text = (abstract_file.read_text(encoding="utf-8", errors="replace")
                     if abstract_file.is_file() else "")
    abstract = check_abstract(drafts, None)
    keywords = check_keywords(drafts, project, None)

    problems = []
    measured = {
        "title_chars": len(title),
        "abstract_chars": len(abstract_text.strip()),
        "abstract_words": abstract.get("words", 0),
        "keywords": keywords.get("count", 0),
    }
    if not title:
        problems.append("no title found in PROJECT.md or drafts/")
    if not abstract_text:
        problems.append("drafts/abstract.md not found — a deposit form asks for it verbatim")

    checked = {}
    if limits:
        for key, field in (("title_chars", "title_max_chars"),
                           ("abstract_chars", "abstract_max_chars"),
                           ("abstract_words", "abstract_max_words")):
            cap = limits.get(field)
            if cap:
                checked[key] = {"value": measured[key], "limit": cap,
                                "over": measured[key] > cap}
                if measured[key] > cap:
                    problems.append(f"{key.replace('_', ' ')} is {measured[key]}, "
                                    f"{limits.get('server', server)} allows {cap}")
        categories = limits.get("categories")
        if categories:
            checked["categories_available"] = categories

    # The five questions are answered in the limits file or they are open. An
    # earlier version only PRINTED them and exited 0, which made a deposit with
    # five undecided questions indistinguishable from a checked one — the
    # silence-reads-as-pass shape this kit refuses everywhere else.
    decisions = (limits or {}).get("decisions") or {}
    questions = [{"key": k, "question": q, "answer": decisions.get(k)}
                 for k, q in OPEN_QUESTIONS]
    unanswered = [q["key"] for q in questions if not q["answer"]]
    if limits and unanswered:
        problems.append(f"undecided before posting: {', '.join(unanswered)} — record "
                        f"each under 'decisions' in the limits file. A posted licence "
                        f"is effectively irreversible, and a journal policy read after "
                        f"posting is read too late")

    report = {
        "server": server,
        "limits_source": (limits or {}).get("source_url"),
        "title": {"text": title, "source": title_source},
        "measured": measured,
        "checked": checked,
        "keywords": keywords.get("keywords", []),
        "open_questions": questions,
        "undecided": unanswered,
        "disclosure_sentence": (
            "A preprint of this manuscript has been posted at <server> under "
            "<licence> (<URL>). Fill the three placeholders after posting and add "
            "the sentence to exports/submission/cover-letter.md — most venues "
            "require the letter to disclose an existing preprint."),
        "problems": problems,
    }
    report["result"] = "OK" if not problems else "FINDINGS"
    if limits is None:
        report["result"] = "UNCHECKED"
        report["note"] = (
            f"no {DEFAULT_LIMITS} — the numbers above were MEASURED but checked "
            f"against nothing. Fill it from {server}'s own submission help page; "
            f"this kit will not recall a character limit.")
    return report


def _drafts_hits(drafts: Path, canonical: str) -> list[dict]:
    """Every line of every draft whose quantities include this value. Matched on
    the canonical form, so 0,91 in a Turkish section and 0.91 in an English one
    are one hit rather than two misses."""
    hits = []
    for path in sorted(drafts.glob("*.md")) if drafts.is_dir() else []:
        for i, line in enumerate(path.read_text(encoding="utf-8",
                                                errors="replace").splitlines(), 1):
            if canonical in tc.numbers(line):
                hits.append({"file": path.as_posix(), "line": i,
                             "text": line.strip()[:160]})
    return hits


def _artefact_refs(text: str) -> list[str]:
    return sorted({m.group(0) for m in re.finditer(
        r"(?:Table|Tablo|Figure|Şekil|Sekil|Fig\.?|Eq\.?|Denklem)\s*\d+", text,
        re.IGNORECASE)})


def corrigendum(spec: dict, drafts: Path, runs_path: str, cards_path: str) -> dict:
    wrong = tc.normalise_number(str(spec["wrong_value"]))
    correct = tc.normalise_number(str(spec["correct_value"]))
    if wrong is None:
        die(f"wrong_value {spec['wrong_value']!r} is not a number this script can "
            f"normalise — for a non-numeric correction, write the letter by hand")

    hits = _drafts_hits(drafts, wrong)
    artefacts = sorted({ref for h in hits for ref in _artefact_refs(h["text"])})

    runs = []
    for rec in read_jsonl(runs_path):
        metrics = rec.get("metrics")
        if not isinstance(metrics, dict):
            continue
        for name, value in metrics.items():
            if tc.normalise_number(str(value)) == wrong:
                runs.append({"run": rec.get("id"), "metric": name, "value": value,
                             "dataset": rec.get("dataset"), "seed": rec.get("seed")})

    cards = []
    for card in read_jsonl(cards_path):
        blob = json.dumps(card.get("metrics") or {}, ensure_ascii=False) + " " + \
            str(card.get("claim", "")) + " " + str(card.get("detail", ""))
        if wrong in tc.numbers(blob):
            cards.append({"id": card.get("id"), "type": card.get("type"),
                          "claim": str(card.get("claim", ""))[:120]})

    still_correct = _drafts_hits(drafts, correct) if correct else []

    problems = []
    if not hits and not runs and not cards:
        problems.append(f"the value {spec['wrong_value']} was not found in drafts/, "
                        f"the run register or the evidence cards — check that it is "
                        f"written the way the paper writes it")
    if runs:
        problems.append(f"{len(runs)} run record(s) hold this value — a corrigendum "
                        f"that leaves the register saying the old number makes the "
                        f"replication package disagree with the correction")

    return {
        "wrong_value": spec["wrong_value"],
        "correct_value": spec["correct_value"],
        "what_happened": spec.get("what_happened"),
        "found_in_drafts": hits,
        "artefacts_named_nearby": artefacts,
        "run_records": runs,
        "evidence_cards": cards,
        "correct_value_already_present_at": still_correct,
        "letter_skeleton": [
            "1. What the published paper states (quote it, with its location).",
            "2. What the correct value is, and what produced it — name the run.",
            "3. Why it happened, in one sentence, without minimising it.",
            "4. What changes as a result: every item in `found_in_drafts` and "
            "`artefacts_named_nearby` above, listed explicitly.",
            "5. What does NOT change — state it, because a reader's first question "
            "is whether the conclusion survives.",
            "6. Who found it. If a reader did, say so.",
        ],
        "problems": problems,
        "result": "FINDINGS" if problems else "OK",
        "note": ("this lists everywhere the value appears. Whether the paper needs a "
                 "corrigendum, an erratum or a retraction is between the authors and "
                 "the editor, and no part of that judgement is here"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preprint", choices=SERVERS, help="assemble a preprint deposit")
    ap.add_argument("--corrigendum", action="store_true", help="a published-paper correction")
    ap.add_argument("--error", default=DEFAULT_ERROR, help="the erratum description (JSON)")
    ap.add_argument("--limits", default=DEFAULT_LIMITS)
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--runs", default="analysis/runs.jsonl")
    ap.add_argument("--cards", default="evidence/cards.jsonl")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if bool(args.preprint) == bool(args.corrigendum):
        die("pick exactly one: --preprint <server> or --corrigendum")
    for flag, value in (("--limits", args.limits), ("--drafts", args.drafts),
                        ("--project", args.project), ("--error", args.error),
                        ("--runs", args.runs), ("--cards", args.cards)):
        require_within_cwd(value, flag)

    if args.preprint:
        limits = load_json_file(Path(args.limits), "a server limit", ())
        report = preprint(Path(args.drafts), Path(args.project), args.preprint, limits)
        emit(report, args.json_out)
        sys.exit(0 if report["result"] == "OK" else 2)

    spec = load_json_file(Path(args.error), "a correction",
                          ("wrong_value", "correct_value", "what_happened"))
    if spec is None:
        die(f"{args.error} does not exist — describe the error in it first:\n"
            f'  {{"source_url": "<the published paper\'s DOI>", '
            f'"wrong_value": 0.91, "correct_value": 0.87, '
            f'"what_happened": "the held-out split was reported before the leakage fix"}}')
    report = corrigendum(spec, Path(args.drafts), args.runs, args.cards)
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
