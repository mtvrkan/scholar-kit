#!/usr/bin/env python3
"""collection_check.py — the three checkable questions before you collect data yourself.

WHY THIS EXISTS
Collecting your own data — scraping a site, running a survey — is the one part of
an empirical paper where the failure mode is not a wrong number but a wrong act:
data taken from a site that forbids it, personal data carried into a repository,
human subjects with no ethics approval. Those are not caught by any statistic
downstream, and by the time a reviewer or an ethics board asks, the collection
has already happened.

Three of those questions have deterministic answers, and this script answers
exactly those three:

  --robots     does the site's own robots.txt allow the path you are about to
               fetch, for the agent string you are about to send
  --scan       does the collected file contain personal data, and in which column
  --protocol   does your written protocol state the things every ethics board and
               every methods section asks for

WHAT IT REFUSES
- **To rule on legality.** robots.txt is a machine-readable request, not the law
  and not the site's Terms of Service. A path robots.txt allows may still be
  forbidden by the ToS, by copyright, or by data-protection law; a path it
  disallows is not thereby criminal. The script reports the rule it found, quotes
  it, and names the human decision it cannot make. Anything else would be a tool
  handing out legal advice by implication.
- **To print what it finds.** The PII scan reports counts and column names, never
  the matched values. A scanner that echoes the personal data it detected has
  copied that data into a terminal, a log and a transcript — which is the harm it
  was run to prevent.
- **To approve anything.** A complete protocol is not an approved protocol. The
  completeness check says every required section exists, and says nothing about
  whether what they say is acceptable — that judgement belongs to an ethics board
  or a data-protection officer.

USAGE
  python scripts/collection_check.py --robots <url> [--agent scholar-kit]
  python scripts/collection_check.py --scan analysis/data/collected.csv [more...]
  python scripts/collection_check.py --protocol analysis/collection-protocol.md

Exit codes: 0 nothing to report · 1 error · 2 findings (disallowed path, personal
data present, or a protocol missing a required section).
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.parse
from pathlib import Path
from urllib.robotparser import RobotFileParser

try:
    import requests
except ImportError:  # pragma: no cover - surfaced as a clean die() in main()
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, http_get_with_retry, require_within_cwd,
                        transliterate)

AGENT = "scholar-kit/1.0 (mailto:scholar-kit@example.org)"
TIMEOUT = 15

# Patterns are deliberately conservative: a false positive costs a look, a false
# negative carries a person's identifier into a repository. Each carries the name
# a protocol has to use for it, because "12 matches of pattern 3" tells an author
# nothing about what to write in the data-protection section.
PII_PATTERNS = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")),
    ("phone_intl", re.compile(r"(?<!\d)\+\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3}[\s.-]?\d{2,4}(?!\d)")),
    ("phone_tr", re.compile(r"(?<!\d)0?5\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)")),
    ("tckn", re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")),  # Turkish national id, 11 digits
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),
    ("card_like", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("ip_v4", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")),
    ("date_of_birth", re.compile(r"\b(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b")),
]

# Column names that declare intent regardless of what the values look like: an
# empty "email" column today is a column someone will fill tomorrow.
PII_COLUMN_HINTS = ("email", "e-mail", "eposta", "e-posta", "phone", "telefon", "gsm",
                    "tckn", "tc_kimlik", "ssn", "iban", "address", "adres", "name",
                    "ad", "soyad", "surname", "birth", "dogum", "doğum", "ip")

# What a protocol has to state. The list is the union of what an ethics board
# asks, what GDPR/KVKK require to be documented, and what a methods section has
# to contain for the collection to be reproducible.
REQUIRED_SECTIONS = {
    "purpose": ("purpose", "amaç", "research question", "araştırma sorusu"),
    "legal_basis": ("legal basis", "hukuki dayanak", "lawful basis", "kvkk", "gdpr",
                    "terms of service", "kullanım koşulları", "licence", "license", "lisans"),
    "source_permission": ("permission", "izin", "robots", "api terms", "rate limit",
                          "hız sınırı"),
    "sampling": ("sampling", "örnekleme", "inclusion", "dahil etme", "population", "evren"),
    "fields_collected": ("fields", "alanlar", "variables", "değişkenler", "data dictionary",
                         "veri sözlüğü"),
    "minimisation": ("minimis", "minimiz", "veri minimizasyonu", "only the fields",
                     "sadece", "anonym", "anonim", "pseudonym", "takma"),
    "retention": ("retention", "saklama", "deletion", "silme", "how long", "ne kadar süre"),
    # Deliberately NOT keyed on "not applicable": a protocol that says it once —
    # legitimately, for a scrape of public statistics with no human subjects —
    # would otherwise satisfy two different required sections with one phrase.
    # Each section is present only when its own noun is, which "consent: not
    # applicable" still satisfies.
    "consent": ("consent", "onam", "rıza", "informed", "aydınlatılmış"),
    "ethics_approval": ("ethics", "etik", "irb", "kurul"),
    "contact": ("contact", "iletişim", "responsible", "sorumlu", "data controller",
                "veri sorumlusu"),
}


def _fold(text: str) -> str:
    """Lowercase and strip diacritics for keyword matching.

    `"İletişim".lower()` is NOT `"iletişim"` in Python: the dotted capital I
    decomposes to i + COMBINING DOT ABOVE, so a plain `in` test against a
    hand-typed Turkish keyword silently misses every heading an author actually
    types. A protocol reported as missing its contact section because of a
    combining character is the kind of false alarm that gets a whole check
    ignored — and this kit's first language is the one it breaks on.
    """
    return transliterate(text).lower()


def robots_verdict(url: str, agent: str) -> dict:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        die(f"--robots needs an absolute http(s) URL, got {url!r}")
    robots_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    try:
        resp = http_get_with_retry(robots_url, retries=1, backoff=1.5, timeout=TIMEOUT,
                                   headers={"User-Agent": agent})
    except requests.RequestException as e:
        return {"robots_txt": robots_url, "reachable": False, "allowed": None,
                "reason": f"could not be fetched — {e}",
                "human_decision": "unfetchable robots.txt is not permission; decide deliberately"}
    if resp.status_code >= 400:
        # RFC 9309: 4xx means no restrictions are published. Reported as such
        # rather than as "allowed", because they are different sentences and only
        # one of them is what the site said.
        return {"robots_txt": robots_url, "reachable": True, "status": resp.status_code,
                "allowed": None, "publishes_rules": False,
                "reason": f"robots.txt returned {resp.status_code} — the site publishes "
                          f"no crawl rules. That is an absence of a rule, not a permission."}
    parser = RobotFileParser()
    resp.encoding = resp.encoding or "utf-8"
    text = resp.text
    parser.parse(text.splitlines())
    path = urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, ""))
    allowed = parser.can_fetch(agent, url)
    delay = parser.crawl_delay(agent)
    rules = [line.strip() for line in text.splitlines()
             if re.match(r"^\s*(user-agent|disallow|allow|crawl-delay)\s*:", line, re.I)]
    return {"robots_txt": robots_url, "reachable": True, "status": resp.status_code,
            "publishes_rules": True, "path": path, "agent": agent, "allowed": allowed,
            "crawl_delay": delay, "rules": rules[:40],
            "human_decision": ("robots.txt is a request, not the law: the Terms of "
                               "Service, copyright and data-protection law are separate "
                               "questions this script does not answer")}


def scan_text(text: str) -> dict[str, int]:
    hits: dict[str, int] = {}
    for name, pattern in PII_PATTERNS:
        n = len(pattern.findall(text))
        if n:
            hits[name] = n
    return hits


def scan_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    result = {"file": path.as_posix(), "matches": scan_text(text), "columns": {}}
    if path.suffix.lower() in (".csv", ".tsv"):
        delim = "\t" if path.suffix.lower() == ".tsv" else ","
        reader = csv.reader(io.StringIO(text), delimiter=delim)
        try:
            header = next(reader)
        except StopIteration:
            return result
        columns = {h: {"declared": any(_fold(k) in _fold(h) for k in PII_COLUMN_HINTS),
                       "matches": {}} for h in header}
        for row in reader:
            # strict=False: a ragged row is normal in exported CSV and the
            # scan should read the columns it has, not raise on the ones it lacks.
            for h, value in zip(header, row, strict=False):
                for name, count in scan_text(value).items():
                    columns[h]["matches"][name] = columns[h]["matches"].get(name, 0) + count
        result["columns"] = {h: v for h, v in columns.items()
                             if v["declared"] or v["matches"]}
    return result


def check_protocol(text: str) -> dict:
    folded = _fold(text)
    present, missing = [], []
    for section, keys in REQUIRED_SECTIONS.items():
        (present if any(_fold(k) in folded for k in keys) else missing).append(section)
    return {"present": sorted(present), "missing": sorted(missing),
            "note": ("completeness only — that a section exists says nothing about "
                     "whether what it says is acceptable, which is an ethics board's "
                     "judgement and not a check")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--robots", metavar="URL", help="the URL you intend to fetch")
    ap.add_argument("--agent", default=AGENT, help="the User-Agent you will send")
    ap.add_argument("--scan", nargs="+", metavar="FILE", help="collected data file(s)")
    ap.add_argument("--protocol", metavar="FILE", help="the written collection protocol")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    modes = [bool(args.robots), bool(args.scan), bool(args.protocol)]
    if sum(modes) != 1:
        die("pick exactly one: --robots <url>, --scan <file...> or --protocol <file>")

    if args.robots:
        if requests is None:
            die("requests not installed — pip install requests")
        result = robots_verdict(args.robots, args.agent)
        emit(result, args.json_out)
        sys.exit(2 if result.get("allowed") is False else 0)

    if args.scan:
        reports, findings = [], 0
        for rel in args.scan:
            require_within_cwd(rel, "--scan")
            p = Path(rel)
            if not p.is_file():
                die(f"{rel} does not exist")
            report = scan_file(p)
            findings += sum(report["matches"].values())
            findings += sum(1 for c in report["columns"].values() if c["declared"])
            reports.append(report)
        emit({"scanned": len(reports), "files": reports,
              "note": ("counts and column names only — the matched values are never "
                       "printed, because a scanner that echoes personal data has "
                       "copied it into your terminal and your logs"),
              "next": ("declare the state in the dataset register: "
                       "python scripts/dataset_db.py set-field <DS-id> ethics "
                       "'{\"pii\": \"removed\", ...}'")}, args.json_out)
        sys.exit(2 if findings else 0)

    require_within_cwd(args.protocol, "--protocol")
    p = Path(args.protocol)
    if not p.is_file():
        die(f"{args.protocol} does not exist — write the protocol before collecting, "
            f"not after (/collect-data scaffolds one)")
    result = check_protocol(p.read_text(encoding="utf-8", errors="replace"))
    result["file"] = p.as_posix()
    emit(result, args.json_out)
    sys.exit(2 if result["missing"] else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"file is not valid UTF-8 — {e}")
