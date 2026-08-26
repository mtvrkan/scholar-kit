#!/usr/bin/env python3
"""submission_pack.py — the submission portal's fields, checked against the venue's own limits.

WHY THIS EXISTS
The manuscript is finished and then there is a second document nobody talks
about: the submission form. Title length, abstract word count, keyword count,
highlights (3-5 bullets, ≤85 characters each), the ethics/funding/competing-
interests/data-availability statements, the cover letter. Every one of those has
a hard limit set by the venue, every one is checked by an editorial assistant
before a reviewer ever sees the paper, and a desk rejection at that stage costs
weeks for a reason that took ten seconds to check.

Every limit here is arithmetic. None of it needs a model.

WHAT IT REFUSES
- **To know a journal's limits.** They come from `limits.json`, which YOU fill
  from that journal's own author guidelines, with the URL you read them at. The
  kit will not recall "Elsevier abstracts are 250 words" from memory — a
  remembered limit is the same error class as a remembered DOI, and it is wrong
  often enough to cause exactly the desk rejection this script exists to prevent.
  With no limits file, it reports what it measured and says plainly that nothing
  was checked against anything.
- **To write your statements from nothing.** `--manifest` assembles the portal
  fields from what exists on disk. A missing ORCID, funder, or data-availability
  source is listed as TODO, never filled with plausible text — "Data are available
  from the corresponding author on reasonable request" is a sentence that must be
  true, and only you know whether it is.
- **To count what it cannot see.** A limit the venue states in pages, characters
  including spaces, or "excluding references" is measured the way it is written
  here or reported as unchecked. It never converts pages to words.

USAGE
  python scripts/submission_pack.py --check          # everything, against limits.json
  python scripts/submission_pack.py --highlights exports/submission/highlights.md
  python scripts/submission_pack.py --manifest       # the portal fields, assembled

Exit codes: 0 nothing over a limit · 1 error · 2 something is over, missing, or
required-but-undeclared.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd
from word_budget import count_words

DEFAULT_LIMITS = "exports/submission/limits.json"
DEFAULT_DRAFTS = "drafts"
DEFAULT_HIGHLIGHTS = "exports/submission/highlights.md"

# The statements a journal form asks for, and where a truthful one comes from.
# The mapping is the point: each is generated from a record, or declared missing.
STATEMENT_SOURCES = {
    "ethics": "PROJECT.md 'Ethics approval' / analysis/datasets.jsonl ethics.irb",
    "funding": "compliance_gen.py funding",
    "competing_interests": "compliance_gen.py (declared by you; never assumed absent)",
    "credit": "compliance_gen.py credit",
    "data_availability": "compliance_gen.py availability (reads the dataset register)",
    "ai_disclosure": "compliance_gen.py ai-disclosure",
}


def load_limits(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        limits = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(limits, dict):
        die(f"{path} must hold a JSON object")
    if not limits.get("source_url"):
        die(f"{path} has no 'source_url' — a limit with no source is a remembered "
            f"limit, and this file exists precisely so nothing is remembered")
    return limits


def _text_of(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def title_of(drafts: Path, project: Path) -> tuple[str, str]:
    """The title, and where it was found. PROJECT.md is authoritative; a first
    H1 in drafts/title.md is the fallback, because both exist in real projects
    and disagreeing about which is the title is its own defect."""
    text = _text_of(project)
    m = re.search(r"\*\*Title \(working\):\*\*\s*(.+)", text)
    if m:
        # PROJECT.md carries decision history in trailing HTML comments, and a
        # long one turned a 118-character title into 788. That number then gets
        # compared against the venue's title limit and, worse, is what a person
        # would paste into the portal's title field.
        # Closed comments first, then any comment left open at the end of the
        # line — `.` does not cross newlines here, so a multi-line comment
        # reaches this function already truncated and would survive a
        # `<!--.*?-->` pass unchanged.
        title = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
        title = re.sub(r"<!--.*", "", title, flags=re.S).strip()
        if title not in ("", "TBD"):
            return title, "PROJECT.md"
    for name in ("title.md", "abstract.md"):
        head = _text_of(drafts / name)
        h1 = re.search(r"^#\s+(.+)$", head, re.M)
        if h1:
            return h1.group(1).strip(), f"drafts/{name}"
    return "", "not found"


def parse_highlights(text: str) -> list[str]:
    """Bullets only. A highlights file that is a paragraph is not highlights, and
    counting its sentences would invent a structure the author did not write."""
    return [m.group(1).strip() for m in re.finditer(r"^\s*[-*+]\s+(.+?)\s*$", text, re.M)]


def check_highlights(text: str, limits: dict | None) -> dict:
    items = parse_highlights(text)
    spec = (limits or {}).get("highlights", {})
    max_chars = spec.get("max_chars")
    count_min, count_max = spec.get("count_min"), spec.get("count_max")
    too_long = [{"index": i + 1, "chars": len(h), "text": h[:60]}
                for i, h in enumerate(items) if max_chars and len(h) > max_chars]
    with_citations = [i + 1 for i, h in enumerate(items) if re.search(r"\[@[^\]]+\]", h)]
    problems = []
    if count_min and len(items) < count_min:
        problems.append(f"{len(items)} highlights, the venue asks for at least {count_min}")
    if count_max and len(items) > count_max:
        problems.append(f"{len(items)} highlights, the venue allows at most {count_max}")
    if too_long:
        problems.append(f"{len(too_long)} over {max_chars} characters")
    if with_citations:
        problems.append(f"highlights {with_citations} carry citations — highlights are "
                        f"read standalone, and a [@key] renders as literal text in the form")
    return {"count": len(items), "chars": [len(h) for h in items],
            "over_limit": too_long, "problems": problems,
            "limits_applied": bool(spec)}


# A bilingual manuscript has TWO abstracts, and venues routinely give them
# different limits (this kit's own convention is ozet.md + abstract.md, and
# tr_style_check already pairs them). Checking only abstract.md against a single
# number applied the manuscript-language limit to the translation: a Turkish
# review whose 250-word limit is met, and whose English abstract is allowed 15%
# more by the venue's own sentence, was reported as over the limit. Per-file
# limits are opt-in via `abstract_max_words_by_file`; `abstract_max_words`
# remains the default for any abstract file without its own entry.
ABSTRACT_FILES = ("ozet.md", "abstract.md")


def check_abstract(drafts: Path, limits: dict | None) -> dict:
    spec = (limits or {}).get("abstract_max_words_by_file") or {}
    default_max = (limits or {}).get("abstract_max_words")
    found = [(n, _text_of(drafts / n)) for n in ABSTRACT_FILES]
    found = [(n, t) for n, t in found if t]
    if not found:
        return {"present": False,
                "problem": "no abstract found (looked for %s in drafts/)"
                           % ", ".join(ABSTRACT_FILES)}

    per_file, problems = {}, []
    for name, text in found:
        words = count_words(text)
        cap = spec.get(name, default_max)
        entry = {"words": words, "limit": cap}
        if cap and words > cap:
            entry["problem"] = f"{name} is {words} words, the venue allows {cap}"
            problems.append(entry["problem"])
        per_file[name] = entry

    primary = "abstract.md" if "abstract.md" in per_file else found[0][0]
    out = {"present": True, "files": per_file,
           "words": per_file[primary]["words"], "limit": per_file[primary]["limit"]}
    if problems:
        out["problem"] = "; ".join(problems)
    # Structured abstracts are a venue property, not a preference: reporting the
    # heading count lets the author see at a glance whether theirs matches.
    out["structured_headings"] = re.findall(
        r"\*\*([A-ZÇĞİÖŞÜ][^:*]{2,20}):?\*\*", dict(found)[primary])[:8]
    return out


# The colon usually sits INSIDE the bold ("**Keywords:** a; b"), so the closing
# `**` has to be allowed after it as well as before — otherwise the asterisks
# fall into the captured group and the first keyword comes back as
# "** diabetic retinopathy". And the list routinely wraps: `(.+)` stops at the
# newline and silently drops every keyword after the first line, which
# under-counts against the venue's minimum. Read to the blank line instead.
_KEYWORD_LINE = re.compile(
    r"(?:\*\*)?(?:Keywords|Anahtar (?:kelimeler|sözcükler))\s*:?\s*(?:\*\*)?\s*"
    r"(.+?)(?:\n\s*\n|\Z)", re.I | re.S)


def _keywords_in(text: str) -> list[str] | None:
    m = _KEYWORD_LINE.search(text)
    if not m:
        return None
    return [k for k in (w.strip().strip("*").strip()
                        for w in re.split(r"[;,·]", m.group(1).replace("\n", " ")))
            if k]


def check_keywords(drafts: Path, project: Path, limits: dict | None) -> dict:
    # A bilingual manuscript carries the list twice, and reading only
    # abstract.md meant a Turkish paper had its ENGLISH keywords validated while
    # ozet.md was never opened — the venue requires both. Both are read, and
    # they are compared to each other: two lists of different length is a defect
    # no single-file check can see, because each one is individually fine.
    per_file: dict[str, dict] = {}
    for name in ABSTRACT_FILES:
        words = _keywords_in(_text_of(drafts / name))
        if words is not None:
            per_file[name] = {"count": len(words), "keywords": words}
    if not per_file:
        words = _keywords_in(_text_of(project))
        if words is None:
            return {"present": False,
                    "problem": "no keyword line found in %s or PROJECT.md"
                               % ", ".join("drafts/" + n for n in ABSTRACT_FILES)}
        per_file["PROJECT.md"] = {"count": len(words), "keywords": words}

    spec = (limits or {}).get("keywords", {})
    problems = []
    for name, entry in per_file.items():
        n = entry["count"]
        if spec.get("min") and n < spec["min"]:
            problems.append(f"{name}: {n} keywords, the venue asks for at least {spec['min']}")
        elif spec.get("max") and n > spec["max"]:
            problems.append(f"{name}: {n} keywords, the venue allows at most {spec['max']}")
    counts = {e["count"] for e in per_file.values()}
    if len(counts) > 1:
        problems.append("the keyword lists do not correspond: "
                        + ", ".join(f"{n} has {e['count']}" for n, e in per_file.items()))

    primary = "abstract.md" if "abstract.md" in per_file else next(iter(per_file))
    out = {"present": True, "files": per_file,
           "count": per_file[primary]["count"],
           "keywords": per_file[primary]["keywords"]}
    if problems:
        out["problem"] = "; ".join(problems)
    return out


def check_statements(limits: dict | None, statements_dir: Path) -> dict:
    required = (limits or {}).get("required_statements", [])
    text = "\n".join(_text_of(p).lower() for p in statements_dir.glob("*.md")) if \
        statements_dir.is_dir() else ""
    present, missing = [], []
    for name in required:
        (present if name.replace("_", " ") in text or name in text else missing).append(name)
    return {"required": required, "present": sorted(present), "missing": sorted(missing),
            "where_each_comes_from": {n: STATEMENT_SOURCES.get(n, "declared by you")
                                      for n in missing}}


# STATUS.md is the drafting progress log, not manuscript text — the kit's own
# verify-citations skill excludes it for the same reason. Counting it inflates
# the number that gets compared against the venue's limit with words no reader
# of the paper will ever see.
NON_MANUSCRIPT = {"STATUS.md"}


def check_manuscript(drafts: Path, limits: dict | None) -> dict:
    files = [p for p in (sorted(drafts.glob("*.md")) if drafts.is_dir() else [])
             if p.name not in NON_MANUSCRIPT]
    per_file = {p.name: count_words(_text_of(p)) for p in files}
    # Appendices are counted, but separately: a venue's manuscript word limit is
    # about the main text, and a long appendix silently added to the body total
    # makes a submittable paper look unsubmittable (or the reverse, if the author
    # then cuts the body to compensate for words the body does not contain).
    appendix = {n: w for n, w in per_file.items() if n.startswith("ek-") or n.startswith("appendix")}
    body = {n: w for n, w in per_file.items() if n not in appendix}
    total = sum(body.values())
    max_words = (limits or {}).get("manuscript_max_words")
    out = {"files": per_file, "body_words": total, "total_words": total,
           "appendix_words": sum(appendix.values()), "appendix_files": sorted(appendix),
           "excluded_from_count": sorted(NON_MANUSCRIPT & {p.name for p in drafts.glob("*.md")})
           if drafts.is_dir() else [],
           "limit": max_words}
    if max_words and total > max_words:
        out["problem"] = (f"{total} words in the body, the venue allows {max_words}. "
                          f"Appendices ({out['appendix_words']} words) are reported "
                          f"separately and are NOT in this figure. If the venue also "
                          f"excludes references or the abstract, subtract them yourself "
                          f"rather than assuming this number is the one the form wants")
    return out


def run_check(drafts: Path, project: Path, limits: dict | None, highlights: Path,
              statements_dir: Path) -> dict:
    title, title_source = title_of(drafts, project)
    title_max = (limits or {}).get("title_max_chars")
    title_report = {"title": title, "source": title_source, "chars": len(title),
                    "limit": title_max}
    if not title:
        title_report["problem"] = "no title found in PROJECT.md or drafts/"
    elif title_max and len(title) > title_max:
        title_report["problem"] = f"title is {len(title)} characters, the venue allows {title_max}"

    report = {
        "limits_file": str(limits and limits.get("source_url") or None),
        "venue": (limits or {}).get("venue"),
        "title": title_report,
        "abstract": check_abstract(drafts, limits),
        "keywords": check_keywords(drafts, project, limits),
        "highlights": check_highlights(_text_of(highlights), limits) if highlights.is_file()
        else {"present": False},
        "manuscript": check_manuscript(drafts, limits),
        "statements": check_statements(limits, statements_dir),
    }
    problems = []
    for key, section in report.items():
        if isinstance(section, dict):
            if section.get("problem"):
                problems.append({key: section["problem"]})
            problems.extend({key: p} for p in section.get("problems", []))
    if report["statements"]["missing"]:
        problems.append({"statements": f"required but not found: "
                                       f"{report['statements']['missing']}"})
    report["problems"] = problems
    report["result"] = "OK" if not problems else "FINDINGS"
    if limits is None:
        # UNCHECKED, not OK — and a non-zero exit. "No problems found" and
        # "nothing was checked" are the same output otherwise, which is the
        # silence-reads-as-pass failure this kit refuses everywhere else.
        report["result"] = "UNCHECKED"
        report["note"] = ("no limits file — every number above was MEASURED but "
                          "checked against nothing. Fill exports/submission/limits.json "
                          "from the venue's own author guidelines; this kit will not "
                          "recall them from memory.")
    return report


def build_manifest(drafts: Path, project: Path, limits: dict | None,
                   highlights: Path, statements_dir: Path) -> dict:
    """The portal fields, assembled from what exists. What is absent is a TODO
    with the command that produces it — never a plausible sentence."""
    title, _ = title_of(drafts, project)
    abstract = _text_of(drafts / "abstract.md")
    kw = check_keywords(drafts, project, limits)
    todo = []
    if not title:
        todo.append("title — set PROJECT.md 'Title (working)'")
    if not abstract:
        todo.append("abstract — /draft abstract")
    if not kw.get("present"):
        todo.append("keywords — add a 'Keywords:' line to drafts/abstract.md")
    if not highlights.is_file():
        todo.append(f"highlights — write {highlights.as_posix()} as 3-5 bullets")
    for name in check_statements(limits, statements_dir)["missing"]:
        todo.append(f"{name} statement — {STATEMENT_SOURCES.get(name, 'declare it yourself')}")
    return {
        "venue": (limits or {}).get("venue"),
        "title": title,
        "abstract_words": count_words(abstract) if abstract else 0,
        "keywords": kw.get("keywords", []),
        "highlights": parse_highlights(_text_of(highlights)) if highlights.is_file() else [],
        "todo": todo,
        "note": ("assembled from files on disk. Nothing here was written to fill a "
                 "blank: an ORCID, a funder or a data-availability sentence that is "
                 "not in your project is listed as TODO, because each of those has "
                 "to be true and only you know whether it is"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check everything against limits.json")
    ap.add_argument("--manifest", action="store_true", help="assemble the portal fields")
    ap.add_argument("--highlights", nargs="?", const=DEFAULT_HIGHLIGHTS,
                    help="check only the highlights file")
    ap.add_argument("--limits", default=DEFAULT_LIMITS)
    ap.add_argument("--drafts", default=DEFAULT_DRAFTS)
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--statements", default="exports/submission",
                    help="directory holding the declaration files")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--limits", args.limits), ("--drafts", args.drafts),
                        ("--project", args.project), ("--statements", args.statements)):
        require_within_cwd(value, flag)
    limits = load_limits(Path(args.limits))
    drafts, project = Path(args.drafts), Path(args.project)
    statements_dir = Path(args.statements)

    if args.highlights:
        require_within_cwd(args.highlights, "--highlights")
        p = Path(args.highlights)
        if not p.is_file():
            die(f"{args.highlights} does not exist — write it as 3-5 bullets, one per line")
        result = check_highlights(_text_of(p), limits)
        result["file"] = p.as_posix()
        emit(result, args.json_out)
        sys.exit(2 if result["problems"] else 0)

    if args.manifest:
        emit(build_manifest(drafts, project, limits, Path(DEFAULT_HIGHLIGHTS), statements_dir),
             args.json_out)
        return

    if not drafts.is_dir():
        die(f"{args.drafts} does not exist — nothing to check")
    report = run_check(drafts, project, limits, Path(DEFAULT_HIGHLIGHTS), statements_dir)
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
