#!/usr/bin/env python3
"""prisma_flow.py — PRISMA 2020 flow diagram (mermaid + TikZ) from search-log counters.

Input (one of):
  * --counts JSON, e.g. '{"identified":341,"duplicates":58,"screened":283,
      "excluded_screening":231,"fulltext":52,"excluded_fulltext":32,
      "excluded_reasons":{"predatory venue":3,"no metrics":12},"included":20}'
  * --counts-file PATH â the same object read from a UTF-8 file. Prefer this
      whenever a reason string is non-ASCII: argv is re-encoded by the shell and
      the console codepage, and a mangled reason reaches the diagram silently.
      A file with a top-level "counts" object is unwrapped, so the counters may
      live beside the prose fields that explain where they came from.
  * --registry sources/registry.jsonl â derives counts from record statuses
      (candidate/screened/excluded/included) + "reason" fields.

Output: <out-dir>/prisma.mmd (mermaid) and <out-dir>/prisma.tex (TikZ), plus a JSON
consistency check (identified - duplicates = screened, etc.).

--verify writes nothing. It re-renders from the counters and compares the numbers
in the artefacts ALREADY on disk against them. The consistency check validates the
counters; it says nothing about the file the typesetter will actually read, and
those two drift the moment anything copies a diagram from one directory to another.

Usage:
  python scripts/prisma_flow.py --registry sources/registry.jsonl [--out-dir outline]
  python scripts/prisma_flow.py --counts-file analysis/data/prisma-counts.json --out-dir exports
  python scripts/prisma_flow.py --counts-file <file> --out-dir exports --verify
Exit codes: 0 ok · 1 error · 2 counters inconsistent or artefact out of date.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd, write_text_atomic


def derive_counts(registry: list[dict]) -> dict:
    """Derive PRISMA counters from record statuses. Exclusion stage comes from the
    record's "stage" field ("fulltext" vs anything else = title/abstract screening).
    Records still in progress (candidate/screened) make the flow inconsistent by
    design — check() surfaces that instead of guessing."""
    # A review needs citations that were never screening candidates: the
    # epidemiological background, a reporting guideline, a prior review cited for
    # contrast. Invariant 1 says nothing may be cited unless it is in the register,
    # so they have to be recorded — but counting them as "records identified"
    # inflates the flow with sources the search never returned, and every downstream
    # box with it. `scope: "background"` marks them out of the flow. The default is
    # in-flow, so no existing project's numbers move.
    background = [r for r in registry if r.get("scope") == "background"]
    registry = [r for r in registry if r.get("scope") != "background"]
    identified = len(registry)
    dup = sum(1 for r in registry if r.get("status") == "duplicate")
    excluded = [r for r in registry if r.get("status") == "excluded"]
    included = sum(1 for r in registry if r.get("status") == "included")
    excluded_screening = sum(1 for r in excluded if r.get("stage") != "fulltext")
    excluded_fulltext = sum(1 for r in excluded if r.get("stage") == "fulltext")
    not_retrieved = sum(1 for r in registry if r.get("status") == "unretrieved")
    screened = identified - dup
    sought = screened - excluded_screening
    fulltext = sought - not_retrieved
    # Two dicts, because two different questions are being asked of them.
    # "excluded_reasons" stays every exclusion's reason: it is the reported
    # payload, and a review may legitimately want screening reasons too.
    # The DIAGRAM's box is a different matter — it announces the full-text
    # count and then lists reasons underneath, so filling it from every stage
    # made it contradict its own number (on the reference manuscript: "Excluded
    # (n = 11)" above reasons covering 30 records). PRISMA 2020 asks for
    # "reports excluded, with reasons" at the full-text stage; screening is
    # reported as a bare count, which is why the flow has one reason box.
    # A third consideration on top of the stage split: PRISMA asks for reasons
    # GROUPED with counts, and a register holds one free-text reason per record.
    # A conscientious screener writes a distinct sentence for every exclusion,
    # so the diagram ends up listing eleven categories for eleven records —
    # which is a register dump, not a flow diagram. An optional
    # `reason_category` field lets the record carry both: the short category the
    # figure groups on, and the full text the register keeps. Records without
    # one fall back to the free text, so no existing project's diagram changes.
    reasons, reasons_fulltext = {}, {}
    for r in excluded:
        key = r.get("reason", "unspecified")
        reasons[key] = reasons.get(key, 0) + 1
        if r.get("stage") == "fulltext":
            group = r.get("reason_category") or key
            reasons_fulltext[group] = reasons_fulltext.get(group, 0) + 1
    # Reported, not silently dropped: a reader comparing the flow against the
    # register must be able to see why the two totals differ.
    return {"identified": identified, "duplicates": dup, "screened": screened,
            "background_excluded_from_flow": len(background),
            "excluded_screening": excluded_screening, "sought": sought,
            "not_retrieved": not_retrieved, "fulltext": fulltext,
            "excluded_fulltext": excluded_fulltext,
            "excluded_reasons": reasons,
            "excluded_reasons_fulltext": reasons_fulltext, "included": included}


REQUIRED_COUNT_KEYS = ("identified", "duplicates", "screened", "excluded_screening",
                       "fulltext", "excluded_fulltext", "included")

# PRISMA 2020 splits "sought for retrieval" from "assessed for eligibility"; the gap
# between them is "reports not retrieved". Both keys stay OPTIONAL so a --counts JSON
# written before this existed still validates: with not_retrieved defaulting to 0 the
# sought box collapses onto fulltext and every equation below reduces to the old three.
OPTIONAL_COUNT_KEYS = ("not_retrieved", "sought")


def check(c: dict) -> list[str]:
    missing = [k for k in REQUIRED_COUNT_KEYS if k not in c]
    if missing:
        die(f"--counts is missing required key(s): {missing} — "
            f"expected all of {list(REQUIRED_COUNT_KEYS)}")
    c.setdefault("not_retrieved", 0)
    c.setdefault("sought", c["fulltext"] + c["not_retrieved"])
    present = REQUIRED_COUNT_KEYS + OPTIONAL_COUNT_KEYS
    bad_type = [k for k in present
                if isinstance(c[k], bool) or not isinstance(c[k], int)]
    if bad_type:
        die(f"--counts key(s) must be integers, not {[type(c[k]).__name__ for k in bad_type]}: {bad_type}")
    negative = [k for k in present if c[k] < 0]
    if negative:
        die(f"--counts key(s) must be non-negative, got negative {negative} — "
            f"a PRISMA flow can't have a negative record count")
    if not isinstance(c.get("excluded_reasons"), dict):
        die(f"--counts \"excluded_reasons\" must be a JSON object, "
            f"got {type(c.get('excluded_reasons')).__name__}")
    errs = []
    if c["identified"] - c["duplicates"] != c["screened"]:
        errs.append("identified - duplicates != screened")
    if c["screened"] - c["excluded_screening"] != c["sought"]:
        errs.append("screened - excluded_screening != sought")
    # An optional fourth outlet from "sought". PRISMA 2020 has no such box, and
    # a review that needs one is declaring a deviation — but the alternative is
    # worse. A review carrying studies forward from an earlier phase (an update,
    # a living review, or a first pass whose full texts are no longer reachable)
    # otherwise has to either count those records twice — once under "not
    # retrieved" and again under "included" — or withdraw an eligibility
    # judgement that was actually made. Both corrupt the flow; a named box does
    # not. Absent or zero, the identity is exactly PRISMA's.
    carried = int(c.get("carried_forward_unretrieved") or 0)
    if c["sought"] - c["not_retrieved"] - carried != c["fulltext"]:
        errs.append("sought - not_retrieved - carried_forward_unretrieved != fulltext"
                    if carried else "sought - not_retrieved != fulltext")
    if c["fulltext"] - c["excluded_fulltext"] != c["included"]:
        errs.append("fulltext - excluded_fulltext != included")
    return errs


def _mermaid_escape(s) -> str:
    """Registry "reason" free-text flows unescaped into a quoted mermaid edge
    label — a reason containing '"' breaks the quoted-string syntax, and
    '<'/'>' could inject stray HTML alongside the deliberately-used
    <br/> tags. Escape per-segment (not the joined string) so the structural
    <br/> this function itself inserts stays intact."""
    return (str(s).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


REASON_MAX = 90
REASON_MAX_ITEMS = 3


def _reason_items(reasons: dict) -> tuple[list, int, int]:
    """The reasons a flow box shows, plus what it defers, plus the deferred count.

    PRISMA expects grouped reasons with counts, and a register stores one
    free-text reason per record — so a review whose screener wrote a distinct
    sentence for every exclusion arrives here with as many categories as
    exclusions. Show the largest few, and report the remainder as a count so
    the arithmetic still closes: a reader adding the box's numbers must reach
    the box's own total, whether or not every category is named.

    Sorted by count then name — deterministic, so regenerating the diagram
    from an unchanged register produces an unchanged file."""
    items = sorted(reasons.items(), key=lambda kv: (-kv[1], str(kv[0])))
    shown = items[:REASON_MAX_ITEMS]
    hidden = items[REASON_MAX_ITEMS:]
    return shown, len(hidden), sum(n for _, n in hidden)


def _short_reason(text: str, limit: int = REASON_MAX) -> str:
    """Shorten one exclusion reason to something a flow-diagram box can hold.

    A PRISMA box lists reasons as short phrases with counts; the full text
    belongs in the register, which is where the reader is sent. Registers do
    not enforce that, though — registry_db.py takes whatever `--reason` string
    the screener typed, and a conscientious screener writes a paragraph. On the
    reference manuscript one reason ran 400+ characters and the TikZ node,
    fixed at text width 4.6cm, grew tall enough to squeeze the ENTIRE diagram
    into an unreadable ribbon: LaTeX reported the float overrunning the page by
    ~3500pt and still emitted it, so the failure arrived as a silently
    illegible figure rather than as an error.

    Cut at a word boundary where one is available, so the truncation reads as a
    phrase rather than a severed word."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,;:.") + "…"



# Kutu etiketleri. PRISMA's own diagram is English, and a review written in
# another language ends up printing English box labels around its own-language
# exclusion reasons — the kit's example manuscript rendered "Records identified"
# above "indeks test derin öğrenme değil". The figure is part of the manuscript,
# so it follows the manuscript's language. --labels takes a JSON file overriding
# any subset of these keys; unnamed keys keep the English default, so a partial
# file is valid and a typo'd key is reported rather than silently ignored.
DEFAULT_LABELS = {
    "identified": "Records identified",
    "after_duplicates": "Records after duplicates removed",
    "duplicates_removed": "Duplicates removed",
    "screened": "Records screened (title/abstract)",
    "excluded_screening": "Excluded",
    "sought": "Reports sought for retrieval",
    "not_retrieved": "Reports not retrieved",
    "carried_forward": ("Carried forward from an earlier phase, full text not "
                        "retrieved this round"),
    "assessed": "Reports assessed for eligibility",
    "excluded_fulltext": "Excluded",
    "included": "Studies included",
    "further_reasons": "further reason(s)",
    "records_word": "record(s) — see register",
    "see_log": "see log",
}


def resolve_labels(path: str | None) -> dict:
    """DEFAULT_LABELS + kullanicinin dosyasi. Bilinmeyen anahtar HATA verir."""
    labels = dict(DEFAULT_LABELS)
    if not path:
        return labels
    p = Path(path)
    if not p.is_file():
        die(f"--labels not found: {path}")
    try:
        user = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"--labels is not valid JSON — {e.msg}")
    if not isinstance(user, dict):
        die(f"--labels must be a JSON object, got {type(user).__name__}")
    unknown = sorted(set(user) - set(DEFAULT_LABELS))
    if unknown:
        die(f"--labels has unknown key(s) {unknown} — known keys are "
            f"{sorted(DEFAULT_LABELS)}. A typo'd key would silently leave the "
            f"English default in the figure, so it is refused here.")
    labels.update({k: str(v) for k, v in user.items()})
    return labels


def mermaid(c: dict, labels: dict | None = None) -> str:
    L = labels or DEFAULT_LABELS
    # The diagram box carries the FULL-TEXT count, so it may list only
    # FULL-TEXT reasons. There is deliberately NO fallback to the all-stage
    # dict: that dict's stage is unknown to this function, and borrowing it put
    # SCREENING reasons under a box labelled "Excluded (n = 53)" — three counts
    # summing to 1328 printed beneath a 53. A reader cannot tell a mislabelled
    # box from a correct one, so an absent reason list is the safer output and
    # the caller is told the box is bare.
    shown, n_more, n_records = _reason_items(
        c.get("excluded_reasons_fulltext") or {})
    parts = [_mermaid_escape(f"{_short_reason(k)}: {v}") for k, v in shown]
    if n_more:
        parts.append(_mermaid_escape(
            f"+{n_more} {L['further_reasons']}, {n_records} {L['records_word']}"))
    # Bir kutu: PRISMA'da yok, ama sifirsa hic basilmaz.
    _carried = int(c.get("carried_forward_unretrieved") or 0)
    carried_mermaid = (
        f'S -- "{L["carried_forward"]}<br/>(n = {_carried})" --> X5[" "]'
        if _carried else "")
    reasons = "<br/>".join(parts) or L["see_log"]
    return f"""flowchart TD
    A["{L['identified']}<br/>(n = {c['identified']})"] --> B["{L['after_duplicates']}<br/>(n = {c['screened']})"]
    A -. "{L['duplicates_removed']}<br/>(n = {c['duplicates']})" .-> X1[" "]
    B --> C["{L['screened']}<br/>(n = {c['screened']})"]
    C -- "{L['excluded_screening']}<br/>(n = {c['excluded_screening']})" --> X2[" "]
    C --> S["{L['sought']}<br/>(n = {c['sought']})"]
    S -- "{L['not_retrieved']}<br/>(n = {c['not_retrieved']})" --> X4[" "]
    {carried_mermaid}
    S --> D["{L['assessed']}<br/>(n = {c['fulltext']})"]
    D -- "{L['excluded_fulltext']} (n = {c['excluded_fulltext']})<br/>{reasons}" --> X3[" "]
    D --> E["{L['included']}<br/>(n = {c['included']})"]
    style X1 fill:none,stroke:none
    style X2 fill:none,stroke:none
    style X3 fill:none,stroke:none
    style X4 fill:none,stroke:none
"""


_TEX_SPECIAL = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$",
    "&": r"\&", "#": r"\#", "^": r"\textasciicircum{}", "_": r"\_",
    "%": r"\%", "~": r"\textasciitilde{}",
}


def _tex_escape(s) -> str:
    """Same rationale as _mermaid_escape but for LaTeX: a registry "reason"
    like "cost > 30%" or "no_full_text" injects raw %/_/&/# into the
    generated .tex and breaks the build — these are exactly the free-text
    fields the kit lets agents write via registry_db.py set-status --reason."""
    return "".join(_TEX_SPECIAL.get(ch, ch) for ch in str(s))


def tikz(c: dict, labels: dict | None = None) -> str:
    L = labels or DEFAULT_LABELS
    # The diagram box carries the FULL-TEXT count, so it lists full-text
    # reasons. NO fallback to the all-stage dict — see the mermaid renderer
    # above for why borrowing it mislabels the box.
    shown, n_more, n_records = _reason_items(
        c.get("excluded_reasons_fulltext") or {})
    parts = [f"{_tex_escape(_short_reason(k))}: {v}" for k, v in shown]
    if n_more:
        parts.append(_tex_escape(
            f"+{n_more} {L['further_reasons']}, {n_records} {L['records_word']}"))
    # Bir kutu: PRISMA'da yok, ama sifirsa hic basilmaz.
    _carried = int(c.get("carried_forward_unretrieved") or 0)
    carried_tex = ((
        r"\node[side, below=0.35cm of nret] (carr) {%s (n = %d)};"
        "\n"
        r"\draw[->] (sought) -- (carr);")
        % (_tex_escape(L["carried_forward"]), _carried)) if _carried else ""
    reasons = "; ".join(parts) or L["see_log"]
    return f"""% PRISMA 2020 flow diagram — generated by prisma_flow.py; requires tikz
\\begin{{tikzpicture}}[node distance=1.1cm,
  box/.style={{draw, rectangle, text width=6.2cm, align=center, minimum height=1cm}},
  side/.style={{draw, rectangle, text width=4.6cm, align=center}}]
\\node[box] (id)   {{{L['identified']} (n = {c['identified']})}};
\\node[box, below=of id] (dedup) {{{L['after_duplicates']} (n = {c['screened']})}};
\\node[side, right=1cm of dedup] (dups) {{{L['duplicates_removed']} (n = {c['duplicates']})}};
\\node[box, below=of dedup] (screen) {{{L['screened']} (n = {c['screened']})}};
\\node[side, right=1cm of screen] (exs) {{{L['excluded_screening']} (n = {c['excluded_screening']})}};
\\node[box, below=of screen] (sought) {{{L['sought']} (n = {c['sought']})}};
\\node[side, right=1cm of sought] (nret) {{{L['not_retrieved']} (n = {c['not_retrieved']})}};
{carried_tex}
\\node[box, below=of sought] (ft) {{{L['assessed']} (n = {c['fulltext']})}};
% Anchored by its TOP-left rather than centred on ft: this is the only box whose
% height depends on free text, and a centred one grows UPWARD as well, overlapping
% the exclusion and not-retrieved boxes above it. Growing downward keeps the
% collision out of the diagram whatever the reasons happen to say.
\\node[side, anchor=north west] at ([xshift=1cm]ft.north east) (exf) {{{L['excluded_fulltext']} (n = {c['excluded_fulltext']}); {reasons}}};
\\node[box, below=of ft] (inc) {{{L['included']} (n = {c['included']})}};
\\draw[->] (id) -- (dedup); \\draw[->] (dedup) -- (screen);
\\draw[->] (screen) -- (sought); \\draw[->] (sought) -- (ft); \\draw[->] (ft) -- (inc);
\\draw[->] (dedup) -- (dups); \\draw[->] (screen) -- (exs);
\\draw[->] (sought) -- (nret); \\draw[->] (ft) -- (exf);
\\end{{tikzpicture}}
"""


_N_RE = re.compile(r"\(n = (\d+)\)")


def verify_artifacts(c: dict, out: Path, labels: dict | None = None) -> list[str]:
    """Compare the numbers in the artefacts on disk against a fresh render.

    check() answers "do the counters add up"; this answers "is the file the
    typesetter reads the file these counters produce". A build step that copies
    a diagram from another directory satisfies the first and fails the second,
    and nothing else in the kit looks. Reported per file, by number, because
    "prisma.tex is stale" does not tell an author which box moved.
    """
    errs = []
    for name, render in (("prisma.tex", tikz), ("prisma.mmd", mermaid)):
        path = out / name
        if not path.is_file():
            errs.append(f"{name}: not on disk — nothing verifies the printed figure")
            continue
        on_disk = _N_RE.findall(path.read_text(encoding="utf-8"))
        expected = _N_RE.findall(render(c, labels))
        if on_disk != expected:
            errs.append(f"{name}: counters on disk {on_disk} != counters these "
                        f"counts produce {expected}")
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--counts", help="JSON object of PRISMA counters")
    ap.add_argument("--counts-file", dest="counts_file",
                    help="the same object read from a UTF-8 file (argv-safe)")
    ap.add_argument("--registry", help="derive counters from registry.jsonl")
    ap.add_argument("--out-dir", default="outline")
    ap.add_argument("--labels", default=None,
                    help="JSON file overriding the diagram's box labels "
                         "(a review in another language should not print "
                         "English labels around its own-language reasons)")
    ap.add_argument("--verify", action="store_true",
                    help="write nothing; check the artefacts on disk against these counters")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.out_dir, "--out-dir")
    if args.registry:
        require_within_cwd(args.registry, "--registry")
    if args.counts_file:
        require_within_cwd(args.counts_file, "--counts-file")
    if args.labels:
        require_within_cwd(args.labels, "--labels")
    if args.counts and args.counts_file:
        die("pass --counts or --counts-file, not both")
    if args.counts or args.counts_file:
        if args.counts_file:
            path = Path(args.counts_file)
            if not path.is_file():
                die(f"--counts-file not found: {args.counts_file}")
            raw = path.read_text(encoding="utf-8")
            label = "--counts-file"
        else:
            raw, label = args.counts, "--counts"
        try:
            c = json.loads(raw)
        except json.JSONDecodeError as e:
            die(f"{label} is not valid JSON — {e.msg}")
        if not isinstance(c, dict):
            die(f"{label} must be a JSON object, got {type(c).__name__}")
        # A counts file usually keeps the counters beside the prose that says
        # where they came from; unwrap so the provenance does not have to be
        # split into a second file to be usable.
        if isinstance(c.get("counts"), dict):
            c = c["counts"]
        c.setdefault("excluded_reasons", {})
    elif args.registry:
        reg = read_jsonl(args.registry)
        if not reg:
            die(f"{args.registry} is empty")
        c = derive_counts(reg)
    else:
        die("pass --counts '<json>', --counts-file <file>, or --registry <file>")
    errs = check(c)
    labels = resolve_labels(args.labels)
    out = Path(args.out_dir)
    if args.verify:
        stale = verify_artifacts(c, out, labels)
        emit({"counts": c, "consistency_errors": errs, "verified": args.out_dir,
              "artifact_errors": stale, "written": []}, args.json_out)
        sys.exit(2 if (errs or stale) else 0)
    write_text_atomic(out / "prisma.mmd", mermaid(c, labels))
    write_text_atomic(out / "prisma.tex", tikz(c, labels))
    emit({"counts": c, "consistency_errors": errs, "artifact_errors": [],
          "written": [f"{args.out_dir}/prisma.mmd", f"{args.out_dir}/prisma.tex"]}, args.json_out)
    sys.exit(2 if errs else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to write the output file — {e}")
