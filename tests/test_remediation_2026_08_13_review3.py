"""Third external review (2026-08-13): the findings, bound to tests.

Two defects and one measurement property, all reproduced against the shipped
artifacts before anything was changed. See DECISIONS.md (D-087).

  * `registry_db.py add --stdin` decoded through the locale codepage, so every
    source title `literature-scout` ingests was written mojibake'd into
    sources/registry.jsonl on a non-UTF-8 console. evidence_db.py had fixed
    exactly this for cards.jsonl; the sibling ingest path never got it.
  * `claim_check.py`'s ladder was verb-anchored, so nominalized claims ("the
    effect of X on Y", "X'in Y üzerindeki etkisi") scored rung-None — exempt —
    and the gap was worse in Turkish, which had no accidental noun coverage.
  * A fixed threshold over a POOLED gold set is a decaying guarantee: growing
    claim_strength silently revived three mutations that had been dying.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claim_check  # noqa: E402
import run_evals as ev  # noqa: E402

GOLD = ROOT / "eval" / "gold"

# A console codepage that is NOT UTF-8 — the default on Turkish Windows, and the
# condition under which the corruption was reproduced.
NON_UTF8_ENV = {"PYTHONIOENCODING": "cp1254", "PYTHONUTF8": "0"}


# ---------- registry_db.py --stdin: UTF-8, not the console codepage ----------

def _add_via_stdin(tmp_path, payload_bytes):
    reg = tmp_path / "registry.jsonl"
    reg.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "registry_db.py"), "--file", str(reg),
         "add", "--stdin"],
        input=payload_bytes, capture_output=True, cwd=tmp_path,
        env={**os.environ, **NON_UTF8_ENV}, timeout=60)
    return proc, reg


def test_registry_db_stdin_preserves_turkish_under_non_utf8_locale(tmp_path):
    """The finding, exactly: a Turkish title through the scout's only ingest
    path. Before the fix this stored "Derin Ã¶ÄŸrenme…" permanently, in a
    hook-protected file a user cannot repair without unprotecting it first."""
    payload = {"bib_key": "ozturk2026",
               "title": "Derin öğrenme ile çeşitli yöntemlerin karşılaştırılması",
               "authors": ["Öztürk, Ş."], "year": 2026}
    proc, reg = _add_via_stdin(
        tmp_path, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    stored = json.loads(reg.read_text(encoding="utf-8").strip())
    assert stored["title"] == payload["title"]
    assert stored["authors"] == payload["authors"]
    assert "Ã" not in reg.read_text(encoding="utf-8"), "mojibake reached the register"


def test_registry_db_stdin_preserves_math_symbols_under_non_utf8_locale(tmp_path):
    """The same class evidence_db.py's own test pins for cards.jsonl."""
    payload = {"bib_key": "kaya2026", "title": "Bounds on ξ, π and σ (Ω, Σ)",
               "year": 2026}
    proc, reg = _add_via_stdin(
        tmp_path, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    stored = json.loads(reg.read_text(encoding="utf-8").strip())
    assert stored["title"] == payload["title"]


@pytest.mark.parametrize("script", ["registry_db.py", "evidence_db.py"])
def test_stdin_tolerates_a_utf8_bom(tmp_path, script):
    """PowerShell's `$json | python …` idiom — the natural spelling on the kit's
    Windows half — prefixes a BOM. Strict utf-8 left U+FEFF at the front and
    json.loads rejected the whole payload with "Unexpected UTF-8 BOM"."""
    target = tmp_path / ("registry.jsonl" if script == "registry_db.py" else "cards.jsonl")
    target.write_text("", encoding="utf-8")
    if script == "registry_db.py":
        payload = {"bib_key": "bom2026", "title": "A title behind a BOM", "year": 2026}
    else:
        payload = {"source": "bom2026", "type": "finding", "claim": "A claim behind a BOM"}
    raw = b"\xef\xbb\xbf" + json.dumps(payload, ensure_ascii=False).encode("utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--file", str(target), "add", "--stdin"],
        input=raw, capture_output=True, cwd=tmp_path,
        env={**os.environ, **NON_UTF8_ENV}, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert target.read_text(encoding="utf-8").strip(), "nothing was written"


def test_both_ingest_scripts_share_one_stdin_reader():
    """The defect was a fix applied to one of two identical --stdin contracts.
    Binding them to the same helper is what stops that recurring."""
    for name in ("registry_db.py", "evidence_db.py"):
        src = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "read_stdin_text()" in src, f"{name} no longer uses the shared reader"
        # Comments are stripped first: both files explain in prose what they no
        # longer DO, and a substring search over the whole source would read
        # that explanation as the defect it describes.
        code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
        assert "sys.stdin.read()" not in code, (
            f"{name} reads stdin directly again — that decodes with the locale codepage")


# ---------- claim_check.py: nominalized claims carry a rung ----------

NOMINAL_OVERCLAIMS = [
    ("en", "The effect of smoking on lung capacity is substantial.", 4),
    ("en", "The impact of smoking on lung capacity is well established.", 4),
    ("en", "Smoking is the primary driver of reduced lung capacity.", 4),
    ("tr", "Sigaranın akciğer kapasitesi üzerindeki etkisi belirgindir.", 4),
    ("tr", "Bu düşüşün nedeni sigara kullanımıdır.", 5),
    ("tr", "Gözlenen düşüş sigara kullanımından kaynaklanmaktadır.", 5),
    ("tr", "Sigaranın bu düşüşe katkısı yadsınamaz.", 3),
]


@pytest.mark.parametrize("lang,sentence,expected", NOMINAL_OVERCLAIMS)
def test_nominalized_claims_carry_a_rung(lang, sentence, expected):
    rung, phrase = claim_check.rung_of(sentence)
    assert rung == expected, f"{lang}: {sentence!r} scored {rung} ({phrase!r})"


NOT_CLAIMS = [
    # This kit generates meta-analysis vocabulary elsewhere; none of it is a claim.
    "The effect size was 0.42 in the pooled analysis.",
    "A random-effects model was fitted to the twelve studies.",
    "Effect estimates were pooled using inverse-variance weighting.",
    "Etki büyüklüğü 0,42 olarak hesaplanmıştır.",
    # Turkish privative -siz asserts the ABSENCE of an effect.
    "Uygulanan müdahale bu örneklemde etkisiz bulunmuştur.",
    "İkinci modelde düzeltme etkisizdir.",
    # Bare "neden" is the interrogative "why".
    "Bu sonucun neden ortaya çıktığı belirsizliğini korumaktadır.",
]


@pytest.mark.parametrize("sentence", NOT_CLAIMS)
def test_near_miss_vocabulary_carries_no_rung(sentence):
    rung, phrase = claim_check.rung_of(sentence)
    assert rung is None, f"{sentence!r} wrongly scored rung {rung} on {phrase!r}"


def test_turkish_nominal_coverage_is_not_weaker_than_english():
    """The finding was an ASYMMETRY, not just a gap: English caught its nominal
    causal by accident ('cause' spans noun and verb) where Turkish had no such
    accident. Pin both halves so a future edit cannot restore the imbalance."""
    en = claim_check.rung_of("Smoking is the cause of reduced lung capacity.")[0]
    tr = claim_check.rung_of("Bu düşüşün nedeni sigaradır.")[0]
    assert en == tr == 5, f"nominal causation scores EN={en}, TR={tr}"


# ---------- the pooled-threshold property ----------

def test_claim_strength_thresholds_are_held_at_the_stricter_line():
    """A single threshold over a pooled set is a decaying guarantee: a mutation
    dies only while its behaviour is more than (1 - threshold) of the set. This
    set grew from 38 cases to 71, which revived three mutations on its own.

    It was the first set moved to 0.95 and, for one round, the only one; the
    other eight followed once the same arithmetic was measured on them rather
    than predicted (D-089). The floor for all nine is asserted in
    `test_run_evals.py`; this one stays because it pins the case that produced
    the rule, and the exact pair rather than a lower bound."""
    manifest = json.loads(
        (GOLD / "claim_strength" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["thresholds"] == {"precision": 0.95, "recall": 0.95}


def test_every_nominal_behaviour_has_enough_cases_to_kill_its_mutation():
    """Not "a mutation exists" (test_run_evals.py already asserts that) but that
    each still DIES with margin. Four behaviours were added; if any one of them
    is later trimmed to a single illustrative case, the mutation survives
    silently and the set gets bigger while measuring less."""
    report = ev.run_mutations(GOLD / "claim_strength" / "manifest.json")
    by_id = {r["id"]: r for r in report["results"]}
    nominal = [m for m in by_id if m.startswith("nominal-")]
    assert len(nominal) >= 6, f"nominal mutations went missing: {sorted(by_id)}"
    for mid in nominal:
        assert by_id[mid]["caught"], f"{mid} survives — its behaviour lost its cases"


def test_decisions_contents_index_matches_the_entries():
    """DECISIONS.md is 200 KB and navigated almost entirely through its collapsed
    contents index, which states its own entry count in prose. The review that
    added this asked whether the file should be split into an archive; it should
    not — hook modules cite D-numbers and `test_hook_change_records.py` resolves
    them against this one file, so splitting makes provenance ambiguous to save
    bytes nobody reads linearly. What was genuinely unbound was the index: an
    entry added without a matching line, or the stated count drifting from
    either, degrades the only navigation the file has, silently."""
    import re
    doc = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    headings = re.findall(r"(?m)^## ", doc)
    links = re.findall(r"(?m)^- \[20", doc)
    stated = re.search(r"Contents \((\d+) entries", doc)
    assert stated, "DECISIONS.md no longer states its entry count"
    assert len(headings) == len(links) == int(stated.group(1)), (
        f"DECISIONS.md index is stale: {len(headings)} entries, {len(links)} index "
        f"lines, prose says {stated.group(1)}")


def test_measurement_doc_prose_totals_match_the_harness():
    """The results TABLE is bound (test_run_evals.py); the prose totals beside it
    were not, and had drifted to a different pair of numbers than the table's own
    total row. Bind them to the same source."""
    import re
    doc = (ROOT / "eval" / "MEASUREMENT.md").read_text(encoding="utf-8")
    tasks = ev.run_all(GOLD)["tasks"]
    cases = sum(t["cases"] for t in tasks)
    pos = sum(t["positive_cases"] for t in tasks)
    neg = sum(t["negative_cases"] for t in tasks)
    # The SET COUNT is spelled out in the prose, and pinning the English word
    # here is how this assertion went stale the moment a tenth gold set landed:
    # it failed for the word, not for the number it exists to guard. Derived
    # from the harness instead, so adding a set updates the expectation.
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
             12: "twelve"}
    spelled = words.get(len(tasks), str(len(tasks)))
    assert re.search(rf"\b{cases} cases across {spelled}\b", doc), (
        f"MEASUREMENT.md prose no longer states {cases} cases across {spelled}")
    assert re.search(rf"carry {neg} negatives against {pos} positives", doc), (
        f"MEASUREMENT.md prose no longer states {neg} negatives / {pos} positives")
