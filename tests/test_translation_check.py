"""What a translation must not change (scripts/translation_check.py).

The tests are shaped by the script's own boundary: it must catch a citation that
vanished, a digit that moved and a cross-reference that shifted, and it must stay
silent about prose — two honest translations of one paragraph share no sentence,
so a checker that compared wording would report nothing but noise.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import translation_check as tc  # noqa: E402


def _pair(tmp_path, source, target):
    (tmp_path / "a.md").write_text(source, encoding="utf-8")
    (tmp_path / "b.md").write_text(target, encoding="utf-8")
    return "a.md", "b.md"


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "translation_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _checks(out):
    return {f["check"] for f in out["findings"]}


# ---------- the invariants ----------

def test_a_faithful_translation_is_clean(tmp_path):
    a, b = _pair(tmp_path,
                 "# Bulgular\n\nDoğruluk %92,4 idi [@kaya2023deep]. Tablo 2 özetler.\n",
                 "# Results\n\nAccuracy was 92.4% [@kaya2023deep]. Table 2 summarises.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b).stdout)
    assert out["result"] == "CLEAN", out["findings"]


def test_prose_is_never_compared(tmp_path):
    """Completely different wording, same facts — nothing to report."""
    a, b = _pair(tmp_path,
                 "Yöntem üç aşamadan oluşur ve her aşama ayrı değerlendirilir [@a2020].\n",
                 "Three distinct stages make up the approach; each is assessed on its "
                 "own terms [@a2020].\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b).stdout)
    assert out["findings"] == []


def test_a_dropped_citation_is_caught(tmp_path):
    a, b = _pair(tmp_path, "Bir [@a2020] ve iki [@b2021].\n", "One [@a2020].\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    lost = next(f for f in out["findings"] if f["check"] == "citation_lost")
    assert lost["keys"] == ["b2021"]


def test_a_citation_that_appeared_only_in_translation_is_caught(tmp_path):
    a, b = _pair(tmp_path, "Bir [@a2020].\n", "One [@a2020] and two [@c2022].\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    assert "citation_added" in _checks(out)


def test_a_moved_digit_is_caught(tmp_path):
    a, b = _pair(tmp_path, "Değer 0,809 idi.\n", "The value was 0.089.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    assert {"number_missing", "number_added"} <= _checks(out)


def test_rounding_is_reported_separately_from_a_moved_digit(tmp_path):
    """Collapsing the two would teach the author to ignore both."""
    a, b = _pair(tmp_path, "Süre 1.250,75 saniyedir.\n", "It took 1,250.8 seconds.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    assert _checks(out) == {"number_rounded"}


def test_a_shifted_cross_reference_is_caught(tmp_path):
    a, b = _pair(tmp_path, "Tablo 2 ve Şekil 1.\n", "Table 3 and Figure 1.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    mismatch = next(f for f in out["findings"] if f["check"] == "crossref_mismatch")
    assert mismatch["kind"] == "table" and mismatch["target"] == ["3"]


def test_evidence_ids_must_survive(tmp_path):
    a, b = _pair(tmp_path, "Kanıt EV-0012 ve EV-0013.\n", "Evidence EV-0012.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    ev = next(f for f in out["findings"] if f["check"] == "evidence_ids")
    assert ev["lost"] == ["EV-0013"]


def test_a_pasted_turkish_paragraph_in_an_english_target_is_flagged(tmp_path):
    a, b = _pair(tmp_path,
                 "Kısa bir cümle.\n\nBu paragraf çevrilmeden bırakılmış olabilir çünkü "
                 "tekrar gibi görünmektedir.\n",
                 "A short sentence.\n\nBu paragraf çevrilmeden bırakılmış olabilir çünkü "
                 "tekrar gibi görünmektedir.\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    assert "untranslated_lines" in _checks(out)


def test_a_lost_heading_is_reported(tmp_path):
    a, b = _pair(tmp_path, "# Bir\n\nx\n\n# İki\n\ny\n", "# One\n\nx\n\ny\n")
    out = json.loads(_run(tmp_path, "--source", a, "--target", b, expect=2).stdout)
    assert "section_count" in _checks(out)


# ---------- number normalisation across the two conventions ----------

def test_both_decimal_conventions_normalise_to_one_value():
    assert tc.normalise_number("0,85") == tc.normalise_number("0.85")
    assert tc.normalise_number("1.250,75") == tc.normalise_number("1,250.75")
    assert tc.normalise_number("1.250,75") == "1250.75"


def test_a_thousands_group_is_not_read_as_a_decimal():
    assert tc.normalise_number("1,234") == "1234"


def test_the_same_language_pair_is_refused(tmp_path):
    a, b = _pair(tmp_path, "x\n", "x\n")
    proc = _run(tmp_path, "--source", a, "--target", b, "--source-lang", "tr",
                "--target-lang", "tr", expect=1)
    assert "same" in (proc.stderr + proc.stdout)
