#!/usr/bin/env python3
"""compliance_gen.py — AI-disclosure, CRediT, funding and data-availability
statements. The first three are templated from structured input you supply; the
fourth is DERIVED from the dataset and run registers. Never invents an author, role, funder, or
AI-tool usage the caller didn't explicitly supply — every field must be given;
there is no silent default beyond the boilerplate wrapper sentences themselves.

Four modes:

  ai-disclosure --tool "Claude (Anthropic)" --uses "literature synthesis,
      citation formatting" [--venue-family icmje|ieee|generic] [--verified-by "Jane Doe"]
      [--no-ai-results]
      Produces a neutral disclosure paragraph. `--no-ai-results` adds the claim
      that no results, data or findings were AI-generated; it is OPT-IN, because
      it is a claim about your work rather than boilerplate, and it is refused
      outright when `--uses` names analysis, data or results — a disclosure that
      says the AI did the analysis and that no data was AI-generated is false on
      its face, and an inaccurate disclosure is the kind of thing venues treat as
      misconduct rather than as a formatting slip. This is a STARTING POINT, not a
      guarantee of compliance with any specific venue's exact required wording
      — no venue publishes a single canonical sentence this script could quote
      verbatim without risking misattribution, so it deliberately stays generic
      and says so; the human must still confirm against their target venue's
      actual policy (submit-check's existing AI-disclosure reminder covers that).

  credit --authors '[{"name":"Jane Doe","roles":["Conceptualization","Software"]}]'
      Produces a CRediT (Contributor Roles Taxonomy) statement. Role names are
      validated against the 14 official CRediT roles (credit.niso.org, a public
      taxonomy, not proprietary text) — an unrecognized role name is rejected,
      not silently coerced to the nearest match.

  availability [--datasets analysis/datasets.jsonl] [--runs analysis/runs.jsonl]
      The data/code availability statement, DERIVED from the dataset and run
      registers rather than templated. A dataset with no citation DOI or no
      recorded licence produces no sentence at all: "available from the
      corresponding author on reasonable request" is the sentence most often
      found to be untrue after publication, and this script will not write it.

  funding --grants '[{"funder":"...", "grant_number":"...", "recipient":"..."}]'
      or --none (explicit "no external funding" statement — must be passed
      explicitly; the script never assumes no-funding from an empty --grants).

Usage:
  python scripts/compliance_gen.py ai-disclosure --tool "..." --uses "..." [--json]
  python scripts/compliance_gen.py credit --authors '[...]' [--json]
  python scripts/compliance_gen.py funding --grants '[...]' [--json]
  python scripts/compliance_gen.py funding --none [--json]
  python scripts/compliance_gen.py availability [--json]
Exit codes: 0 ok · 1 error (missing/invalid required input).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl

CREDIT_ROLES = [
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition",
    "Investigation", "Methodology", "Project administration", "Resources",
    "Software", "Supervision", "Validation", "Visualization",
    "Writing – original draft", "Writing – review & editing",
]


def _norm_role_key(s: str) -> str:
    """Case-insensitive match, tolerant of a plain ASCII hyphen where the
    official taxonomy uses an en dash (–) — most people type "-", not the
    Unicode en dash, and rejecting an otherwise-unambiguous role name over that
    alone would be pure friction, not a real fabrication risk."""
    return s.strip().lower().replace("—", "-").replace("–", "-")


CREDIT_ROLES_NORM = {_norm_role_key(r): r for r in CREDIT_ROLES}

VENUE_FRAMING = {
    "icmje": ("Consistent with ICMJE recommendations on the use of AI in "
              "scholarly writing, the authors disclose the following:"),
    "ieee": ("Per IEEE's policy on the use of generative AI/large language "
              "model tools, the authors disclose the following:"),
    "generic": "AI Disclosure:",
}


def cmd_ai_disclosure(args) -> dict:
    if not args.tool or not args.uses:
        die("--tool and --uses are both required — this script will not guess what the AI was used for")
    framing = VENUE_FRAMING.get(args.venue_family, VENUE_FRAMING["generic"])
    verified = (f" All citations, data, and factual claims were verified by {args.verified_by}."
                if args.verified_by else
                " All citations, data, and factual claims were verified by the author(s).")

    # "No results, data, or findings were AI-generated" is a CLAIM ABOUT THE
    # WORK, not boilerplate, and it used to be emitted unconditionally — so
    # `--uses "data analysis"` produced a statement that asserted the AI did the
    # analysis and that no data was AI-generated, in the same breath. A
    # disclosure exists to be accurate; venues increasingly treat an inaccurate
    # one as misconduct rather than as a formatting slip. It is now opt-in, and
    # a claim that contradicts the stated uses is refused rather than printed.
    notes = []
    if args.no_ai_results:
        clash = sorted({w for w in ("analysis", "analyses", "analiz", "result", "results",
                                    "sonuç", "data", "veri", "statistic", "statistics",
                                    "istatistik", "finding", "findings", "bulgu")
                        if re.search(rf"\b{w}\b", args.uses, re.I)})
        if clash:
            die("--no-ai-results contradicts --uses, which names: " + ", ".join(clash) +
                ". A disclosure that claims no data or results were AI-generated, while "
                "listing exactly that among the AI's uses, is false on its face. State one "
                "or the other: drop --no-ai-results, or narrow --uses to what is true.")
        no_results = " No results, data, or findings were AI-generated."
    else:
        no_results = ""
        notes.append("No claim was made about whether results, data or findings were "
                     "AI-generated — pass --no-ai-results to assert it. It is omitted "
                     "rather than assumed, because it is a claim about your work that "
                     "only you can make. Some venues require the point to be addressed "
                     "explicitly either way.")

    statement = (
        f"{framing} This manuscript was prepared with assistance from {args.tool}, "
        f"used for: {args.uses}.{no_results}"
        f"{verified} The author(s) take full responsibility for all claims and any "
        f"errors in the final manuscript."
    )
    out = {
        "mode": "ai-disclosure",
        "statement": statement,
        "warning": ("This is a generic starting point, NOT a guarantee of compliance "
                   "with your target venue's exact required wording — confirm against "
                   "the venue's actual author guidelines before submission."),
    }
    if notes:
        out["notes"] = notes
    return out


def cmd_credit(args) -> dict:
    try:
        authors = json.loads(args.authors)
    except json.JSONDecodeError as e:
        die(f"--authors is not valid JSON — {e.msg}")
    if not isinstance(authors, list) or not authors:
        die("--authors must be a non-empty JSON array of {\"name\":..., \"roles\":[...]}")

    lines = []
    used_roles = set()
    for a in authors:
        name = a.get("name")
        roles = a.get("roles")
        if not name or not isinstance(roles, list) or not roles:
            die(f"each author needs a non-empty 'name' and a non-empty 'roles' list — got {a!r}")
        resolved = []
        for r in roles:
            norm = CREDIT_ROLES_NORM.get(_norm_role_key(str(r)))
            if not norm:
                die(f"'{r}' is not one of the 14 CRediT taxonomy roles: {', '.join(CREDIT_ROLES)}")
            resolved.append(norm)
            used_roles.add(norm)
        lines.append(f"{name}: {', '.join(resolved)}.")

    unused = [r for r in CREDIT_ROLES if r not in used_roles]
    return {
        "mode": "credit",
        "statement": "Author Contributions (CRediT): " + " ".join(lines),
        "unassigned_roles": unused,  # informational — not every project uses every role
    }


def cmd_funding(args) -> dict:
    if args.none and args.grants:
        die("--none and --grants are mutually exclusive")
    if not args.none and not args.grants:
        die("pass --grants '[...]' or explicitly --none — this script will not assume no funding")
    if args.none:
        return {"mode": "funding",
                "statement": "Funding: The author(s) received no specific funding for this work."}
    try:
        grants = json.loads(args.grants)
    except json.JSONDecodeError as e:
        die(f"--grants is not valid JSON — {e.msg}")
    if not isinstance(grants, list) or not grants:
        die("--grants must be a non-empty JSON array of {\"funder\":..., \"grant_number\":..., \"recipient\":...}")

    parts = []
    for g in grants:
        funder = g.get("funder")
        if not funder:
            die(f"each grant needs a 'funder' — got {g!r}")
        piece = f"{funder}"
        if g.get("grant_number"):
            piece += f" (Grant No. {g['grant_number']})"
        if g.get("recipient"):
            piece += f" to {g['recipient']}"
        parts.append(piece)
    statement = "Funding: This work was supported by " + "; ".join(parts) + "."
    return {"mode": "funding", "statement": statement}


def cmd_availability(args) -> dict:
    """The data/code availability statement, derived from the registers.

    The one statement on a submission form that is routinely false. "Data are
    available from the corresponding author on reasonable request" is written
    into papers whose data no longer exists, and every study of that sentence
    finds the same thing: most such requests are never fulfilled. So this mode
    does not template that sentence from nothing — it reads
    `analysis/datasets.jsonl` and `analysis/runs.jsonl` and writes what is
    actually recorded there.

    Three honest outcomes, and the script refuses to blur them:
      - a dataset with a DOI and a licence → a statement naming both;
      - a dataset that cannot be shared → a statement naming the RECORDED reason
        (a licence, an ethics restriction), which is a real restriction rather
        than a shrug;
      - nothing registered → no statement at all, and the reason why.
    """
    datasets_path, runs_path = Path(args.datasets), Path(args.runs)
    if not datasets_path.is_file():
        die(f"{datasets_path} does not exist — this statement is generated from the "
            f"dataset register, not from a template. Register the data first "
            f"(/find-dataset, /collect-data), or write the statement yourself if "
            f"this study used no data.")
    datasets = read_jsonl(datasets_path)
    if not datasets:
        die(f"{datasets_path} is empty — nothing to declare")

    shareable, restricted, incomplete = [], [], []
    for d in datasets:
        name = d.get("name", d.get("id", "?"))
        doi = (d.get("citation") or {}).get("doi")
        lic = d.get("license", "unknown")
        ethics = d.get("ethics", {})
        if ethics.get("human_subjects") or ethics.get("pii") in ("present", "pseudonymised"):
            restricted.append({"name": name, "reason": "human-subjects/personal data",
                               "irb": ethics.get("irb")})
        elif doi and lic not in ("unknown", None):
            shareable.append({"name": name, "doi": doi, "license": lic,
                              "verified": bool(d.get("license_verified"))})
        else:
            incomplete.append({"name": name,
                               "missing": [f for f, ok in (("citation DOI", doi),
                                                           ("licence", lic not in ("unknown", None)))
                                           if not ok]})

    sentences = []
    for d in shareable:
        sentences.append(f"The {d['name']} dataset is publicly available "
                         f"(https://doi.org/{d['doi']}) under {d['license']}.")
    for d in restricted:
        detail = f" (ethics approval {d['irb']})" if d.get("irb") not in (None, "", "not-declared") else ""
        sentences.append(f"The {d['name']} data cannot be shared publicly because it "
                         f"contains personal or human-subject data{detail}; access "
                         f"requires an appropriate agreement and, where applicable, "
                         f"ethics-board approval.")
    runs = read_jsonl(runs_path) if runs_path.is_file() else []
    if runs:
        sentences.append(f"Analysis code and the recorded experiment runs ({len(runs)} runs, "
                         f"with seeds and environment) are provided in the replication "
                         f"package accompanying this article.")
    return {
        "mode": "availability",
        "statement": ("Data availability: " + " ".join(sentences)) if sentences else None,
        "shareable": shareable, "restricted": restricted, "incomplete": incomplete,
        "runs_recorded": len(runs),
        "note": ("generated from analysis/datasets.jsonl and analysis/runs.jsonl. "
                 "Datasets listed under 'incomplete' produced NO sentence: a dataset "
                 "with no citation DOI or no recorded licence cannot be honestly "
                 "declared available, and 'available on request' is not a substitute "
                 "— it is the sentence most often found to be untrue after publication."),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", dest="json_out", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_av = sub.add_parser("availability")
    p_av.add_argument("--datasets", default="analysis/datasets.jsonl")
    p_av.add_argument("--runs", default="analysis/runs.jsonl")

    p_ai = sub.add_parser("ai-disclosure")
    p_ai.add_argument("--tool", required=True)
    p_ai.add_argument("--uses", required=True)
    p_ai.add_argument("--venue-family", dest="venue_family", default="generic",
                      choices=list(VENUE_FRAMING))
    p_ai.add_argument("--verified-by", dest="verified_by")
    p_ai.add_argument("--no-ai-results", action="store_true",
                      help="assert that no results, data or findings were "
                           "AI-generated; refused if --uses says otherwise")

    p_cr = sub.add_parser("credit")
    p_cr.add_argument("--authors", required=True)

    p_fn = sub.add_parser("funding")
    p_fn.add_argument("--grants")
    p_fn.add_argument("--none", action="store_true")

    args = ap.parse_args()
    result = {"ai-disclosure": cmd_ai_disclosure, "credit": cmd_credit,
             "funding": cmd_funding, "availability": cmd_availability}[args.cmd](args)
    emit(result, True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"I/O error — {e}")
