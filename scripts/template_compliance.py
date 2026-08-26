#!/usr/bin/env python3
"""template_compliance.py — check a BUILT document against the ingested
template's extracted rules (CLAUDE.md Invariant 8, TEMPLATE SUPREMACY).

What was missing, and why this script exists
--------------------------------------------
`templates/ingested/template-profile.md` is written in prose by
`format-engineer` during `/ingest-template`. Prose is the right output for a
human deciding whether the analysis is correct — and it is unusable for a
machine, so until now nothing compared a build against it. The two mechanisms
that did exist check narrower things: `template_supremacy_gate.py` (PreToolUse)
catches a build INVOCATION that ignores the registered template outright, and
`docx_style_check.py` compares the built .docx against the reference .docx it
was rendered with. Neither asks the question the invariant actually makes:
does the built document match the rules that were extracted from the template?

The bridge is a machine-readable block inside the profile. `/ingest-template`
now asks format-engineer to append a fenced ```json block tagged
`template-rules` holding only the values it genuinely extracted — `null` for
anything it could not determine. This script reads that block and compares it
against the build.

Three outcomes, and the third is the point
------------------------------------------
  pass       — the rule is stated and the build honors it.
  mismatch   — the rule is stated and the build contradicts it.
  unchecked  — the rule is null (the analyzer never determined it), or the
               built document does not state the property at all (a .docx that
               inherits a font from its theme asserts nothing about that font).

`unchecked` is never folded into `pass`. A checker that reports "compliant"
for rules it did not verify is worse than no checker, because it converts an
open question into a false guarantee — the same reasoning that keeps
`verified:false` entries out of the bibliography rather than assuming them
good. For the same reason a profile with no machine-readable block reports
`status: "unbound"` and says so, rather than exiting clean.

WARN-only, by design: a build must not hard-fail over template drift without a
human decision (the choice recorded for `docx_style_check.py` in D-071c). Exit
2 marks mismatches for the caller; the build scripts surface it and continue.

Usage:
  python scripts/template_compliance.py --built build/paper.docx
  python scripts/template_compliance.py --built build/main.tex --profile templates/ingested/template-profile.md
Exit codes: 0 clean (or no template registered) · 1 error · 2 mismatches found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd  # noqa: E402

DEFAULT_PROFILE = "templates/ingested/template-profile.md"

# The fenced block the profile carries. Tagged rather than "the first json
# block" so a profile may legitimately contain other JSON examples.
RULES_BLOCK_RE = re.compile(
    r"```json\s+template-rules\s*\n(.*?)\n```", re.S)

# Page sizes in mm, portrait. Used only to NAME a size the build actually has;
# an unrecognised size is reported by its measurements rather than guessed at.
PAGE_SIZES_MM = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4),
                 "Legal": (215.9, 355.6), "A5": (148.0, 210.0)}

# Margins travel through EMU (docx) and pt (LaTeX); a rule written in whole mm
# cannot be compared for equality against either without a tolerance.
MM_TOLERANCE = 0.6
PT_TOLERANCE = 0.51
SPACING_TOLERANCE = 0.02


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_rules(profile: Path) -> tuple[dict | None, str | None]:
    """Return (rules, problem). A missing block is not an error — it is the
    'unbound' state, which the caller reports as such."""
    text = profile.read_text(encoding="utf-8-sig", errors="replace")
    m = RULES_BLOCK_RE.search(text)
    if not m:
        return None, ("no ```json template-rules block — the profile's rules "
                      "are prose only, so nothing here can be checked "
                      "mechanically. Re-run /ingest-template, or add the "
                      "block by hand (schema: agent_docs/… template-rules).")
    try:
        rules = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, f"template-rules block is not valid JSON: {e}"
    if not isinstance(rules, dict):
        return None, "template-rules block must be a JSON object"
    return rules, None


# ---------------------------------------------------------------- docx side

def docx_facts(path: Path) -> dict:
    """Everything this checker can observe in a built .docx. Values are None
    when the document does not state them — which is distinct from a value
    that disagrees with the profile, and is kept distinct downstream."""
    try:
        from docx import Document
        from docx.shared import Length
    except ImportError:
        die("python-docx not installed — pip install python-docx")
    doc = Document(str(path))
    facts: dict = {"margins_mm": {}, "page_mm": None, "styles": {},
                   "line_spacing": None}
    if doc.sections:
        s = doc.sections[0]
        for key, val in (("top", s.top_margin), ("bottom", s.bottom_margin),
                         ("left", s.left_margin), ("right", s.right_margin)):
            facts["margins_mm"][key] = round(val.mm, 2) if isinstance(val, Length) else None
        if isinstance(s.page_width, Length) and isinstance(s.page_height, Length):
            facts["page_mm"] = (round(s.page_width.mm, 1), round(s.page_height.mm, 1))
    for name in ("Normal", "Body Text", "Title", "Heading 1", "Heading 2",
                 "Heading 3", "Heading 4", "Caption", "Bibliography"):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        facts["styles"][name] = {
            "font": st.font.name,
            "size_pt": st.font.size.pt if st.font.size else None,
            "bold": st.font.bold,
            "italic": st.font.italic,
        }
    for name in ("Body Text", "Normal"):
        try:
            ls = doc.styles[name].paragraph_format.line_spacing
        except KeyError:
            continue
        if ls is not None:
            facts["line_spacing"] = float(ls)
            break
    return facts


def check_docx(rules: dict, path: Path) -> list[dict]:
    f = docx_facts(path)
    out: list[dict] = []

    page = rules.get("page") or {}
    margins = page.get("margins_mm")
    if isinstance(margins, dict):
        for side in ("top", "bottom", "left", "right"):
            want = margins.get(side)
            got = f["margins_mm"].get(side)
            out.append(_verdict(f"page.margins_mm.{side}", want, got,
                                lambda a, b: abs(a - b) <= MM_TOLERANCE,
                                numeric=True))
    else:
        out.append(_unchecked("page.margins_mm", "profile states no margins"))

    want_size = page.get("size")
    got_size = None
    if f["page_mm"]:
        w, h = f["page_mm"]
        for name, (nw, nh) in PAGE_SIZES_MM.items():
            if abs(w - nw) <= 1.0 and abs(h - nh) <= 1.0:
                got_size = name
                break
        got_size = got_size or f"{w}x{h}mm"
    out.append(_verdict("page.size", want_size, got_size,
                        lambda a, b: a.strip().lower() == b.strip().lower()))

    body = rules.get("body") or {}
    out.append(_verdict("body.font", body.get("font"), _body_prop(f, "font"),
                        _same_font))
    out.append(_verdict("body.size_pt", body.get("size_pt"), _body_prop(f, "size_pt"),
                        lambda a, b: abs(a - b) <= PT_TOLERANCE, numeric=True))
    out.append(_verdict("body.line_spacing", body.get("line_spacing"),
                        f["line_spacing"],
                        lambda a, b: abs(a - b) <= SPACING_TOLERANCE, numeric=True))

    for style_name, want in (rules.get("headings") or {}).items():
        got = f["styles"].get(style_name)
        if got is None:
            out.append(_unchecked(f"headings.{style_name}",
                                  "the built document defines no such style"))
            continue
        if not isinstance(want, dict):
            out.append(_unchecked(f"headings.{style_name}",
                                  "profile states no properties for it"))
            continue
        out.append(_verdict(f"headings.{style_name}.font", want.get("font"),
                            got.get("font"), _same_font))
        out.append(_verdict(f"headings.{style_name}.size_pt", want.get("size_pt"),
                            got.get("size_pt"),
                            lambda a, b: abs(a - b) <= PT_TOLERANCE, numeric=True))
        if want.get("bold") is not None:
            out.append(_verdict(f"headings.{style_name}.bold", want.get("bold"),
                                got.get("bold"), lambda a, b: bool(a) == bool(b)))

    cap = (rules.get("caption") or {}).get("style_name")
    out.append(_verdict("caption.style_name", cap,
                        cap if cap in f["styles"] else None,
                        lambda a, b: a == b,
                        why_missing="the built document defines no such style"))
    return out


def _same_font(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _body_prop(facts: dict, key: str):
    """Body text is not one style. Pandoc writes prose under 'Body Text' /
    'First Paragraph', both of which normally INHERIT from 'Normal' and state
    nothing themselves — so the first style that exists is the wrong answer;
    the first style that actually states the property is the right one.
    Reading `None` off an inheriting style would report 'unchecked' for a
    document that does set the font, one level up."""
    for name in ("Body Text", "Normal"):
        val = (facts["styles"].get(name) or {}).get(key)
        if val is not None:
            return val
    return None


# --------------------------------------------------------------- latex side

def latex_facts(path: Path) -> dict:
    src = path.read_text(encoding="utf-8-sig", errors="replace")
    src = re.sub(r"(?m)(?<!\\)%.*$", "", src)  # drop comments, keep \%
    cls = re.search(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}", src)
    packages = set()
    for m in re.finditer(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", src):
        packages.update(p.strip() for p in m.group(1).split(","))
    margins: dict = {}
    for m in re.finditer(r"(?:\\geometry\s*\{([^}]*)\}|\\usepackage\s*\[([^\]]*)\]\s*\{geometry\})", src):
        opts = m.group(1) or m.group(2) or ""
        for key, val, unit in re.findall(
                r"(top|bottom|left|right|margin)\s*=\s*([\d.]+)\s*(mm|cm|in|pt)", opts):
            mm = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.27}[unit] * float(val)
            if key == "margin":
                margins.update({k: round(mm, 2) for k in ("top", "bottom", "left", "right")})
            else:
                margins[key] = round(mm, 2)
    return {
        "documentclass": cls.group(2).strip() if cls else None,
        "class_options": [o.strip() for o in (cls.group(1) or "").split(",") if o.strip()] if cls else [],
        "packages": sorted(packages),
        "margins_mm": margins,
    }


def check_latex(rules: dict, path: Path) -> list[dict]:
    f = latex_facts(path)
    tex = rules.get("latex") or {}
    out: list[dict] = []
    out.append(_verdict("latex.documentclass", tex.get("documentclass"),
                        f["documentclass"], lambda a, b: a.strip() == b.strip()))

    want_opts = tex.get("class_options")
    if isinstance(want_opts, list) and want_opts:
        missing = [o for o in want_opts if o not in f["class_options"]]
        out.append({"rule": "latex.class_options", "expected": want_opts,
                    "actual": f["class_options"],
                    "verdict": "pass" if not missing else "mismatch",
                    "why": None if not missing else f"missing: {', '.join(missing)}"})
    else:
        out.append(_unchecked("latex.class_options", "profile states none"))

    want_pkgs = tex.get("required_packages")
    if isinstance(want_pkgs, list) and want_pkgs:
        missing = [p for p in want_pkgs if p not in f["packages"]]
        out.append({"rule": "latex.required_packages", "expected": want_pkgs,
                    "actual": f["packages"],
                    "verdict": "pass" if not missing else "mismatch",
                    "why": None if not missing else f"never \\usepackage'd: {', '.join(missing)}"})
    else:
        out.append(_unchecked("latex.required_packages", "profile states none"))

    margins = (rules.get("page") or {}).get("margins_mm")
    if isinstance(margins, dict):
        for side in ("top", "bottom", "left", "right"):
            out.append(_verdict(f"page.margins_mm.{side}", margins.get(side),
                                f["margins_mm"].get(side),
                                lambda a, b: abs(a - b) <= MM_TOLERANCE,
                                numeric=True,
                                why_missing="the source sets no geometry margin"))
    else:
        out.append(_unchecked("page.margins_mm", "profile states no margins"))
    return out


# ------------------------------------------------------------------ verdicts

def _unchecked(rule: str, why: str) -> dict:
    return {"rule": rule, "expected": None, "actual": None,
            "verdict": "unchecked", "why": why}


def _verdict(rule, want, got, same, numeric: bool = False,
             why_missing: str = "the built document does not state it") -> dict:
    if want is None:
        return _unchecked(rule, "profile states no value (analyzer could not "
                                "determine it — not a default)")
    if got is None:
        return {"rule": rule, "expected": want, "actual": None,
                "verdict": "unchecked", "why": why_missing}
    if numeric and not (_num(want) and _num(got)):
        return {"rule": rule, "expected": want, "actual": got,
                "verdict": "unchecked", "why": "non-numeric value, not comparable"}
    ok = same(want, got)
    return {"rule": rule, "expected": want, "actual": got,
            "verdict": "pass" if ok else "mismatch",
            "why": None if ok else "built value differs from the template rule"}


def run(built: Path, profile: Path) -> dict:
    report = {"status": "checked", "profile": str(profile), "built": str(built),
              "format": None, "results": [], "warnings": []}
    if not profile.exists():
        report.update(status="no-template", profile=None,
                      warnings=["no template registered — kit defaults apply "
                                "(Invariant 8 makes no claim here)"])
        return report
    rules, problem = load_rules(profile)
    if rules is None:
        report.update(status="unbound", warnings=[problem])
        return report
    if not built.exists():
        die(f"built document not found: {built}")
    suffix = built.suffix.lower()
    if suffix == ".docx":
        report["format"] = "docx"
        report["results"] = check_docx(rules, built)
    elif suffix in (".tex", ".ltx"):
        report["format"] = "latex"
        report["results"] = check_latex(rules, built)
    else:
        die(f"unsupported build format '{suffix}' — .docx or .tex")
    counts = {"pass": 0, "mismatch": 0, "unchecked": 0}
    for r in report["results"]:
        counts[r["verdict"]] += 1
    report["counts"] = counts
    if counts["unchecked"]:
        report["warnings"].append(
            f"{counts['unchecked']} rule(s) unchecked — NOT the same as "
            f"compliant; see each entry's 'why'")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--built", required=True,
                    help="the built document: .docx or the main .tex")
    ap.add_argument("--profile", default=DEFAULT_PROFILE,
                    help=f"template profile (default: {DEFAULT_PROFILE})")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    built = Path(require_within_cwd(args.built, "--built"))
    profile = Path(require_within_cwd(args.profile, "--profile"))
    report = run(built, profile)
    emit(report, args.json_out)
    sys.exit(2 if report.get("counts", {}).get("mismatch") else 0)


if __name__ == "__main__":
    main()
