"""The ethics application and consent form (scripts/ethics_pack.py).

The check that justifies the script is the cross-document one: `/collect-data`'s
plan says which columns are written, the consent form says which data the
participant agreed to give, and nothing compared the two before this. A field
added to the plan and never added to the consent text is the finding, and these
tests pin it.

The rest pins the refusals: no board's form is known (no form-fields.json ⇒
UNCHECKED, never OK), no approval number is ever written, and a vague retention
period is reported rather than accepted.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ethics_pack as ep  # noqa: E402

FORM_FIELDS = {
    "source_url": "https://example.edu/ethics/form",
    "read_on": "2026-08-15",
    "fields": ["purpose", "participants", "data_collected", "retention_period", "contact"],
}

PLAN = {"name": "posts", "mode": "api", "protocol": "analysis/collection-protocol.md",
        "contact": "a@b.org",
        "fields": {"post_text": "$.text", "posted_at": "$.date",
                   "author_email": "$.author.email"}}

CONSENT_FULL = """# Bilgilendirilmiş Onam Formu

## Çalışmanın amacı
Sosyal medya gönderilerinde duygu analizini incelemek.

## Gönüllülük
Katılım tamamen gönüllüdür.

## Çekilme hakkı
Analiz başlayana kadar geri çekilebilirsiniz.

## Toplanan veriler
post_text, posted_at ve author_email alanları toplanır.

## Riskler
Öngörülen bir risk yoktur.

## Gizlilik
Veriler takma adla saklanır, anonim raporlanır.

## Erişim
Yalnızca araştırma ekibi erişir.

## Saklama süresi
Veriler 24 ay sonra silinir.

## Etik kurul
Örnek Üniversitesi Etik Kurulu.

## İletişim
Sorumlu araştırmacı: a@b.org
"""


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "ethics_pack.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, form_fields=FORM_FIELDS, plan=PLAN, consent=CONSENT_FULL,
             application=None):
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "exports" / "ethics").mkdir(parents=True, exist_ok=True)
    if plan is not None:
        (tmp_path / "analysis" / "collection-plan.json").write_text(
            json.dumps(plan), encoding="utf-8")
    if form_fields is not None:
        (tmp_path / "exports" / "ethics" / "form-fields.json").write_text(
            json.dumps(form_fields), encoding="utf-8")
    if consent is not None:
        (tmp_path / "exports" / "ethics" / "consent-form.tr.md").write_text(
            consent, encoding="utf-8")
    if application is not None:
        (tmp_path / "exports" / "ethics" / "application.md").write_text(
            application, encoding="utf-8")
    return tmp_path


# ---------- the cross-document check ----------

def test_a_collected_field_missing_from_the_consent_text_is_a_finding():
    """The whole reason the script exists: the plan gained a column and the
    consent form did not."""
    consent = CONSENT_FULL.replace(
        "post_text, posted_at ve author_email alanları toplanır.",
        "post_text ve posted_at alanları toplanır.")
    result = ep.check_consent(consent, ["post_text", "posted_at", "author_email"])
    assert result["fields_undisclosed"] == ["author_email"]
    assert any("not disclosed" in p for p in result["problems"])


def test_a_fully_disclosed_consent_has_no_undisclosed_fields():
    result = ep.check_consent(CONSENT_FULL, ["post_text", "posted_at", "author_email"])
    assert result["fields_undisclosed"] == []
    assert result["elements_missing"] == []


def test_vague_retention_is_reported_rather_than_accepted():
    consent = CONSENT_FULL.replace("Veriler 24 ay sonra silinir.",
                                   "Veriler gerektiği sürece saklanır.")
    result = ep.check_consent(consent, [])
    assert result["vague_retention"]
    assert any("not decided" in p for p in result["problems"])


def test_turkish_headings_are_matched_despite_the_dotted_capital_i():
    """`"İletişim".lower()` is not `"iletişim"`. A consent form reported as
    missing its contact section because of a combining character is the kind of
    false alarm that gets the whole check ignored."""
    result = ep.check_consent(CONSENT_FULL, [])
    assert "contact" in result["elements_present"]


# ---------- the application form ----------

def test_a_heading_with_a_placeholder_under_it_counts_as_unanswered():
    text = "# Application\n\n## Purpose\n<...>\n\n## Contact\na@b.org\n"
    spec = {"fields": ["purpose", "contact"], "source_url": "x"}
    result = ep.check_application(text, spec)
    assert result["answered"] == ["contact"]
    assert result["unanswered"][0]["field"] == "purpose"
    assert "placeholder" in result["unanswered"][0]["why"]


def test_a_preamble_mentioning_a_field_is_not_an_answer_to_it():
    """Sections are split on real headings, never by searching the whole text:
    a paragraph that happens to contain the word "risks" is not the risks field."""
    text = "# Application\n\nThis study has risks we describe below.\n\n## Contact\na@b.org\n"
    result = ep.check_application(text, {"fields": ["risks", "contact"], "source_url": "x"})
    assert [u["field"] for u in result["unanswered"]] == ["risks"]


def test_sections_survive_folding_that_changes_string_length():
    """The first implementation indexed the folded text and sliced the raw text.
    A ligature makes those two indices disagree; the split-on-headings version
    cannot."""
    text = "# T\n\n## Conﬁdentiality\nPseudonymised.\n"
    heads = [h for h, _ in ep.sections(text)]
    assert heads == ["T", "Conﬁdentiality"]


# ---------- the refusals ----------

def test_no_form_fields_file_reports_unchecked_not_ok(tmp_path):
    proc = _run(_project(tmp_path, form_fields=None, application="# A\n\n## Purpose\nX\n"),
                "--check", expect=2)
    report = json.loads(proc.stdout)
    assert report["result"] == "UNCHECKED"
    assert "generic" in report["note"].lower()


def test_a_form_field_list_with_no_source_is_refused(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ethics_pack.py"), "--check"],
        cwd=_project(tmp_path, form_fields={"fields": ["purpose"]}),
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "source_url" in proc.stderr


def test_a_placeholder_approval_reference_is_flagged():
    texts = {"application.md": "Approval number: XXXXX\n"}
    result = ep.check_approval_claim(texts)
    assert result["problems"]
    assert result["approval_mentions"][0]["placeholder"] is True


def test_a_real_looking_approval_reference_is_reported_but_not_asserted():
    result = ep.check_approval_claim({"application.md": "Approved by the Board, no 2026/17\n"})
    assert result["problems"] == []
    assert result["approval_mentions"]
    assert "cannot confirm" in result["note"]


# ---------- scaffold ----------

def test_scaffold_writes_placeholders_and_never_overwrites(tmp_path):
    project = _project(tmp_path, consent=None)
    first = json.loads(_run(project, "--scaffold").stdout)
    assert any(name.endswith("application.md") for name in first["written"])
    assert any(name.endswith("consent-form.tr.md") for name in first["written"])
    second = json.loads(_run(project, "--scaffold").stdout)
    assert second["written"] == []
    assert len(second["skipped_existing"]) == 3


def test_the_scaffolded_application_does_not_pass_its_own_check(tmp_path):
    """A scaffold that checks clean would be a scaffold that filled the form in."""
    project = _project(tmp_path, consent=None)
    _run(project, "--scaffold")
    report = json.loads(_run(project, "--check", expect=2).stdout)
    assert report["application"]["answered"] == []


def test_scaffold_says_when_the_field_list_is_not_your_boards(tmp_path):
    project = _project(tmp_path, form_fields=None, consent=None)
    result = json.loads(_run(project, "--scaffold").stdout)
    assert "NOT" in result["fields_source"]


# ---------- end to end ----------

def test_a_complete_pack_reports_ok(tmp_path):
    application = "# A\n\n" + "\n\n".join(
        f"## {f.replace('_', ' ').capitalize()}\nStated plainly." for f in FORM_FIELDS["fields"])
    project = _project(tmp_path, application=application)
    report = json.loads(_run(project, "--check").stdout)
    assert report["result"] == "OK", report["problems"]
