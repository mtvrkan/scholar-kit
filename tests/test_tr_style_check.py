"""Tests for tr_style_check.py — the deterministic Turkish academic lint.

Two things get pinned harder than usual here.

First, the design rule: where Turkish academic convention is genuinely contested
(decimal separator, impersonal vs first-person voice), the checker must flag the
MIXTURE and never the choice. A test for each confirms that a manuscript holding
one convention consistently produces no warning — a linter that fires on correct
work is worse than none, because it trains the user to ignore it.

Second, false-positive resistance. Turkish text is full of things that look like
findings to a naive regex: "artık" ends in -tık without being first-person,
"Bölüm 3.1" is not a decimal, a code fence is not prose. Each has a test.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "tr_style_check.py"
GLOSSARY = ROOT / "templates" / "tr-terminology.json"
sys.path.insert(0, str(ROOT / "scripts"))

import tr_style_check as trs  # noqa: E402


@pytest.fixture
def project(tmp_path):
    (tmp_path / "PROJECT.md").write_text("# p\n", encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "tr-terminology.json").write_text(
        GLOSSARY.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def write(project, name, text):
    (project / "drafts" / name).write_text(text, encoding="utf-8")


def run_check(project, which=trs.ALL_CHECKS):
    return trs.check(project / "drafts",
                     project / "templates" / "tr-terminology.json", tuple(which))


def warns(result, name):
    return [w for w in result["warnings"] if w["check"] == name]


def run_cli(project, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=project,
                          capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


# ---------- decimal separator: the mixture is the defect ----------

def test_consistent_comma_decimals_are_not_flagged():
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Doğruluk 0,942 ve kesinlik 0,881 olarak ölçülmüştür.")])
    assert result == []


def test_consistent_point_decimals_are_not_flagged():
    # TDK prefers the comma, but many Turkish journals require the point. A
    # linter that flagged this would be wrong for half its users.
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Doğruluk 0.942 ve kesinlik 0.881 olarak ölçülmüştür.")])
    assert result == []


def test_mixed_decimal_separators_are_flagged_with_the_dominant_form():
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Doğruluk 0,942 ve 0,881 iken AUC 0.809 bulunmuştur.")])
    assert len(result) == 1
    assert result[0]["dominant"] == "comma"
    assert result[0]["comma_count"] == 2 and result[0]["dot_count"] == 1
    assert result[0]["minority_examples"][0]["text"] == "0.809"


def test_section_numbering_is_not_read_as_a_decimal():
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Bölüm 3.1'de anlatıldığı gibi Tablo 2.4 ve Şekil 1.2 "
                        "sonuçları 0,95 olarak vermektedir.")])
    assert result == []


def test_a_doi_is_not_read_as_a_decimal():
    """A DOI's registrant prefix looks exactly like a decimal to a naive regex.

    Regression: a manuscript citing doi:10.17780/ksujes.1521858 had its "10.17780"
    counted on the dot side of the comma-vs-point tally. A review with many cited
    DOIs could have its dominant convention named wrongly on that basis alone.
    """
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Duyarlılık 0,942 olarak bildirilmiştir "
                        "(doi:10.17780/ksujes.1521858).")])
    assert result == []


def test_several_dois_do_not_outvote_the_real_convention():
    text = ("Doğruluk 0,942 bulunmuştur. Kaynaklar: 10.1038/s41433-024-03000-9, "
            "10.2196/52506, 10.1155/2023/7139560, 10.1016/j.ophtha.2021.04.027.")
    assert trs.check_decimal_separator([(Path("a.md"), text)]) == []


def test_a_genuine_stray_decimal_beside_a_doi_is_still_caught():
    """The DOI skip must not blanket-mute the line it sits on."""
    result = trs.check_decimal_separator(
        [(Path("a.md"), "Doğruluk 0,942 ve 0,881 iken AUC 0.809 idi "
                        "(doi:10.17780/ksujes.1521858).")])
    assert len(result) == 1
    assert result[0]["dot_count"] == 1
    assert result[0]["minority_examples"][0]["text"] == "0.809"


def test_numbers_inside_a_code_fence_are_not_orthography(project):
    write(project, "yontem.md", "Sonuç 0,95 bulundu.\n\n```python\nlr = 0.001\n"
                                "eps = 0.5\n```\n")
    assert warns(run_check(project, ["decimal_separator"]), "decimal_separator") == []


def test_numbers_inside_inline_code_are_ignored(project):
    write(project, "yontem.md", "Sonuç 0,95 idi; kod `alpha=0.05` biçimindedir.")
    assert warns(run_check(project, ["decimal_separator"]), "decimal_separator") == []


def test_a_citation_key_is_not_scanned(project):
    write(project, "giris.md", "Önceki çalışma [@kaya2023deep] 0,88 bildirmiştir.")
    assert run_check(project, ["decimal_separator"])["warnings"] == []


# ---------- percent placement: this rule IS settled ----------

def test_percent_after_the_number_is_flagged_with_the_correct_form():
    out = trs.check_percent_placement([(Path("a.md"), "Doğruluk 94.2% olarak ölçüldü.")])
    assert len(out) == 1
    assert out[0]["occurrences"][0]["suggest"] == "%94.2"


def test_turkish_percent_placement_passes():
    assert trs.check_percent_placement([(Path("a.md"), "Doğruluk %94,2 olarak ölçüldü.")]) == []


def test_percent_check_reports_a_total_and_caps_the_listing():
    text = " ".join(f"{i}% oran" for i in range(30))
    out = trs.check_percent_placement([(Path("a.md"), text)])
    assert out[0]["total"] == 30
    assert len(out[0]["occurrences"]) == 20


# ---------- abbreviations ----------

def test_dotted_abbreviations_get_the_standard_form():
    out = trs.check_abbreviation([(Path("a.md"), "Değişkenler v.b. ölçütler v.s. dahil.")])
    suggestions = {o["suggest"] for o in out[0]["occurrences"]}
    assert suggestions == {"vb.", "vs."}


def test_a_roman_numeral_heading_is_not_the_abbreviation_vs(project):
    """"# V. Sonuç" matched as "v.s." — the pattern allowed whitespace across the
    period and IGNORECASE let a capital V start it. Every Turkish manuscript with
    numbered sections has a "V." heading, so this fired on correct prose in the
    one place a Turkish author cannot avoid."""
    write(project, "sonuc.md", "# V. Sonuç\n\nBulgular özetlenmiştir.\n")
    assert warns(run_check(project, ["abbreviation"]), "abbreviation") == []


def test_the_real_abbreviation_is_still_caught_next_to_a_heading(project):
    """The heading guard must not swallow a genuine v.b. in the body under it."""
    write(project, "sonuc.md", "# V. Sonuç\n\nModeller v.b. yöntemler denenmiştir.\n")
    out = warns(run_check(project, ["abbreviation"]), "abbreviation")
    assert out and out[0]["total"] == 1
    assert out[0]["occurrences"][0]["suggest"] == "vb."


def test_correct_abbreviations_pass():
    assert trs.check_abbreviation([(Path("a.md"), "Değişkenler vb. ölçütler vs. dahil.")]) == []


# ---------- informal register ----------

def test_conversational_tokens_are_flagged():
    out = trs.check_informal_register(
        [(Path("a.md"), "Sonuçlar gayet iyi çıktı ve bir sürü değişken vardı.")])
    found = {o["text"] for o in out[0]["occurrences"]}
    assert "gayet" in found and "bir sürü" in found


def test_informal_check_matches_ascii_folded_turkish():
    # A manuscript typed without diacritics must not read as clean.
    out = trs.check_informal_register([(Path("a.md"), "Sonuclar bayagi iyi cikti.")])
    assert out and out[0]["total"] == 1


def test_a_word_merely_containing_an_informal_token_is_not_flagged():
    assert trs.check_informal_register([(Path("a.md"), "Epeyi bir kavram değildir.")]) == []


def test_formal_prose_produces_no_register_warning():
    assert trs.check_informal_register(
        [(Path("a.md"), "Veriler toplanmış ve istatistiksel olarak "
                        "çözümlenmiştir.")]) == []


# ---------- term unity ----------

def test_two_turkish_spellings_of_one_concept_are_flagged(project):
    write(project, "yontem.md",
          "Veri seti hazırlanmıştır. Ardından veri kümesi bölünmüştür. "
          "Veri seti dengesizdir.")
    out = warns(run_check(project, ["term_unity"]), "term_unity")
    concepts = {c["concept"] for c in out[0]["concepts"]}
    assert "dataset" in concepts
    entry = next(c for c in out[0]["concepts"] if c["concept"] == "dataset")
    assert entry["dominant"] == "veri seti"
    assert entry["variants"] == {"veri seti": 2, "veri kümesi": 1}


def test_a_single_english_parenthetical_is_correct_not_a_defect(project):
    # First-mention "yapay sinir ağı (artificial neural network)" is the
    # prescribed convention; flagging it would contradict the kit's own guidance.
    write(project, "giris.md",
          "Yapay sinir ağı (artificial neural network) kullanılmıştır. "
          "Yapay sinir ağı katmanlıdır.")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_a_repeated_english_term_alongside_the_turkish_one_is_flagged(project):
    write(project, "giris.md",
          "Aşırı öğrenme gözlenmiştir. Overfitting riski yüksektir. "
          "Overfitting engellenmiştir.")
    out = warns(run_check(project, ["term_unity"]), "term_unity")
    assert any(c["concept"] == "overfitting" for c in out[0]["concepts"])


def test_a_compound_term_is_not_read_as_the_bare_one_it_contains(project):
    """"evrişimli sinir ağı" is a convolutional network — a different concept, not
    a second spelling of "yapay sinir ağı". Masking used to run per concept, so
    while counting `neural network` the bare "sinir ağı" still matched inside the
    compound and the checker reported drift in a manuscript that used both terms
    correctly. Nesting crosses concept boundaries, so the mask has to as well."""
    write(project, "giris.md", "Dokuz evrişimli sinir ağı modeli eğitilmiştir.")
    write(project, "yontem.md", "Sığ yapay sinir ağı kapsam dışı bırakılmıştır.")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_consistent_terminology_produces_no_warning(project):
    write(project, "yontem.md", "Veri seti bölünmüştür. Veri seti dengelenmiştir.")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_term_unity_spans_files_because_unity_is_a_document_property(project):
    write(project, "yontem.md", "Veri seti hazırlanmıştır.")
    write(project, "bulgular.md", "Veri kümesi çözümlenmiştir.")
    assert warns(run_check(project, ["term_unity"]), "term_unity")


def test_a_missing_glossary_is_reported_as_skipped_not_as_clean(project):
    (project / "templates" / "tr-terminology.json").unlink()
    write(project, "yontem.md", "Veri seti ve veri kümesi.")
    result = run_check(project, ["term_unity"])
    assert result["warnings"] == []
    assert "skipped" in result["note"]


def test_the_shipped_glossary_parses_and_has_no_duplicate_concepts():
    entries = trs.load_glossary(GLOSSARY)
    assert len(entries) > 20
    names = [e["concept"] for e in entries]
    assert len(names) == len(set(names))
    for e in entries:
        assert e.get("tr"), f"{e['concept']} has no Turkish variants"


# ---------- voice mixing ----------

def test_consistently_impersonal_prose_is_not_flagged():
    text = ("Veriler toplanmıştır. Model eğitilmiştir. Sonuçlar sunulmaktadır. "
            "Analiz yapılmıştır. Değerler hesaplanmıştır. Bulgular tartışılmaktadır. "
            "Yöntem açıklanmıştır. Sınırlılıklar belirtilmiştir. Öneriler verilmiştir.")
    assert trs.check_voice_mixing([(Path("a.md"), text)]) == []


def test_consistently_first_person_prose_is_not_flagged():
    text = ("Verileri topladık. Modeli eğittik. Sonuçları sunduk. Analizi yaptık. "
            "Değerleri hesapladık. Bulguları tartıştık. Yöntemi açıkladık. "
            "Sınırlılıkları belirttik. Önerileri verdik.")
    assert trs.check_voice_mixing([(Path("a.md"), text)]) == []


def test_mixed_voice_within_one_file_is_flagged():
    text = ("Veriler toplanmıştır. Modeli eğittik. Sonuçlar sunulmaktadır. "
            "Analizi yaptık. Değerler hesaplanmıştır. Bulguları tartıştık. "
            "Yöntem açıklanmıştır. Sınırlılıkları belirttik.")
    out = trs.check_voice_mixing([(Path("a.md"), text)])
    assert len(out) == 1
    assert out[0]["files"][0]["impersonal"] >= 3
    assert out[0]["files"][0]["first_person"] >= 3


def test_artik_is_not_read_as_a_first_person_verb():
    # "artık" ends in -tık without being a verb, and it is one of the most
    # common words in Turkish prose. Untreated it makes every manuscript look
    # first-person and buries the real signal.
    text = ("Veriler toplanmıştır. Artık model eğitilmiştir. Artık sonuçlar "
            "sunulmaktadır. Artık analiz yapılmıştır. Artık değerler "
            "hesaplanmıştır. Artık bulgular tartışılmaktadır. Artık yöntem "
            "açıklanmıştır. Artık öneriler verilmiştir.")
    assert trs.check_voice_mixing([(Path("a.md"), text)]) == []


def test_borrowed_ic_adjectives_are_not_read_as_first_person_verbs():
    """"diyabetik", "sistematik", "otomatik", "pratik", "kritik", "analitik" all
    end in -tik. A Turkish medical or ML manuscript is saturated with them, so
    counting them as first-person plural reported a purely impersonal draft as
    register-mixed. Two separate things had to be fixed for this to pass: the
    fold that maps ı->i (making "yaptık" and "diyabetik" identical), and
    re.IGNORECASE, which treats ı and i as one letter because both uppercase to
    U+0049."""
    text = ("Diyabetik retinopati sistematik olarak incelenmiştir. Otomatik "
            "tarama uygulanmıştır. Pratik sonuçlar raporlanmaktadır. Kritik "
            "değerler hesaplanmıştır. Analitik yöntem açıklanmıştır. Semantik "
            "ayrım belirtilmiştir. İstatistik hesaplanmıştır. Genetik etken "
            "dışlanmıştır. Model eğitilmiştir. Bulgular sunulmaktadır.")
    assert trs.check_voice_mixing([(Path("a.md"), text)]) == []


def test_first_person_verbs_ending_in_tik_are_still_counted():
    """The rule that clears loan adjectives must not clear real verbs with the
    same ending. "eğittik"/"belirttik"/"seçtik" have a consonant before the
    suffix and harmonic e/i, which is exactly what a borrowed -ic adjective
    never has."""
    text = ("Veriler toplanmıştır. Model eğitilmiştir. Analiz yapılmaktadır. "
            "Sonuçlar sunulmuştur. Yöntem açıklanmaktadır. "
            "Modeli eğittik. Sınırlılıkları belirttik. Örneklemi seçtik.")
    out = trs.check_voice_mixing([(Path("a.md"), text)])
    assert out and out[0]["files"][0]["first_person"] == 3


def test_uppercase_first_person_is_still_counted():
    """The Turkish-correct lowercasing the fix depends on must not lose real
    findings: str.lower() maps I->i, which would drop "YAPTIK" into the
    loan-adjective bucket. I->ı is the rule."""
    text = ("Veriler toplanmıştır. Model eğitilmiştir. Analiz yapılmaktadır. "
            "Sonuçlar sunulmuştur. Yöntem açıklanmaktadır. "
            "BU VERİYİ TOPLADIK. MODELİ KULLANDIK. SONUÇLARI GÖRDÜK.")
    out = trs.check_voice_mixing([(Path("a.md"), text)])
    assert out and out[0]["files"][0]["first_person"] == 3


def test_voice_check_stays_silent_on_too_few_predicates():
    # A ratio over three sentences is noise, not a register finding.
    assert trs.check_voice_mixing(
        [(Path("a.md"), "Veriler toplanmıştır. Modeli eğittik.")]) == []


# ---------- Özet ↔ Abstract ----------

def test_equivalent_ozet_and_abstract_pass(project):
    write(project, "ozet.md",
          "Bu çalışmada inme riski tahmini için dört model karşılaştırılmıştır. "
          "En iyi ROC-AUC değeri 0,809 olarak elde edilmiştir.\n\n"
          "**Anahtar sözcükler:** inme, makine öğrenmesi, açıklanabilirlik")
    write(project, "abstract.md",
          "In this study four models were compared for stroke risk prediction "
          "across a large clinical cohort of patients. The best ROC-AUC value "
          "obtained was 0.809 in the held-out evaluation.\n\n"
          "**Keywords:** stroke, machine learning, explainability")
    assert warns(run_check(project, ["ozet_abstract"]), "ozet_abstract") == []


def test_a_number_reported_in_only_one_summary_is_flagged(project):
    write(project, "ozet.md", "Dört model karşılaştırılmış, ROC-AUC 0,809 bulunmuştur.")
    write(project, "abstract.md", "Four models were compared and ROC-AUC was 0.815.")
    out = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    issue = next(i for i in out[0]["issues"] if i["issue"] == "numbers")
    assert "0.809" in issue["only_in_ozet"]
    assert "0.815" in issue["only_in_abstract"]


def test_decimal_separators_are_normalized_before_comparing_numbers(project):
    # 0,809 and 0.809 are the same result written in two orthographies. Reporting
    # them as a mismatch would make the check unusable on real Turkish theses.
    write(project, "ozet.md", "ROC-AUC 0,809 elde edilmiştir ve dört model vardır.")
    write(project, "abstract.md", "ROC-AUC of 0.809 was obtained with four models.")
    out = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    assert not any(i["issue"] == "numbers" for i in out[0]["issues"]) if out else True


def test_keyword_count_mismatch_is_flagged(project):
    write(project, "ozet.md", "Özet metni buradadır.\n\n"
                              "**Anahtar sözcükler:** inme, makine öğrenmesi")
    write(project, "abstract.md", "Abstract text is here.\n\n"
                                  "**Keywords:** stroke, machine learning, XAI")
    out = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    issue = next(i for i in out[0]["issues"] if i["issue"] == "keywords")
    assert issue["ozet_keywords"] == 2 and issue["abstract_keywords"] == 3


def test_a_wildly_different_length_is_flagged(project):
    write(project, "ozet.md", "Kısa özet.")
    write(project, "abstract.md", " ".join(["word"] * 200))
    out = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    assert any(i["issue"] == "length" for i in out[0]["issues"])


def test_one_summary_without_the_other_is_reported_as_incomplete(project):
    write(project, "abstract.md", "Only the English abstract exists.")
    out = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    assert out[0]["status"] == "incomplete"
    assert "Özet" in out[0]["message"]


def test_a_project_with_neither_summary_is_silent(project):
    write(project, "yontem.md", "Yöntem bölümü.")
    assert warns(run_check(project, ["ozet_abstract"]), "ozet_abstract") == []


def test_the_ozet_file_is_found_under_its_diacritic_free_spelling(project):
    write(project, "özet.md", "Özet metni. ROC-AUC 0,80 bulunmuştur.")
    write(project, "abstract.md", "Abstract text. ROC-AUC was 0.80.")
    assert warns(run_check(project, ["ozet_abstract"]), "ozet_abstract") == []


# ---------- orchestration ----------

def test_the_project_status_log_is_never_scanned(project):
    # Same exemption the sibling checkers make: STATUS.md is the kit's own
    # progress log, not manuscript prose.
    write(project, "STATUS.md", "Durum: gayet iyi, bir sürü iş bitti. 0,5 ve 0.5")
    result = run_check(project)
    assert result["files_scanned"] == 0
    assert result["status"] == "no-drafts"


def test_no_drafts_is_reported_not_treated_as_clean(project):
    result = run_check(project)
    assert result["status"] == "no-drafts"
    assert "nothing to check" in result["note"]


def test_the_output_states_what_the_checker_cannot_see(project):
    write(project, "yontem.md", "Veriler toplanmıştır.")
    assert "Not a grammar checker" in run_check(project)["limits"]


def test_checks_can_be_selected_individually(project):
    write(project, "yontem.md", "Doğruluk 94% ve gayet iyi sonuç.")
    only_percent = run_check(project, ["percent_placement"])
    assert only_percent["checks_run"] == ["percent_placement"]
    assert {w["check"] for w in only_percent["warnings"]} == {"percent_placement"}


# ---------- CLI ----------

def test_cli_is_warn_only_by_default(project):
    write(project, "yontem.md", "Doğruluk 94% olarak ölçülmüştür.")
    code, out, err = run_cli(project, "--json")
    assert code == 0, err
    assert json.loads(out)["warning_count"] >= 1


def test_cli_strict_exits_two_on_a_warning(project):
    write(project, "yontem.md", "Doğruluk 94% olarak ölçülmüştür.")
    assert run_cli(project, "--strict")[0] == 2


def test_cli_strict_exits_zero_on_clean_prose(project):
    write(project, "yontem.md", "Doğruluk %94,2 olarak ölçülmüştür.")
    code, out, err = run_cli(project, "--strict")
    assert code == 0, out + err


def test_cli_rejects_an_unknown_check_name(project):
    code, out, err = run_cli(project, "--check", "helyazim")
    assert code != 0
    assert "unknown check" in (out + err)


def test_cli_rejects_a_path_outside_the_project(project):
    assert run_cli(project, "--drafts", "../escape")[0] != 0


def test_cli_reports_a_corrupt_glossary_cleanly(project):
    (project / "templates" / "tr-terminology.json").write_text("{not json",
                                                               encoding="utf-8")
    write(project, "yontem.md", "Veri seti.")
    code, out, err = run_cli(project, "--check", "term_unity")
    assert code != 0
    assert "glossary" in (out + err)


def test_html_comment_is_not_manuscript_register(project):
    # Drafts carry HTML comments by instruction (evidence binding, RQ tags) and
    # authors leave notes in them. A note written with English decimals made the
    # decimal-separator check report a MIXTURE the published text never had —
    # and the mixture is precisely what that check exists to flag.
    write(project, "giris.md",
          "Doğruluk %87,4 olarak bulunmuştur.\n"
          "<!-- not: 22.3 ve 18.9; accuracy 91.2% -->\n"
          "Son.\n")
    result = run_check(project)
    assert warns(result, "decimal_separator") == []
    assert warns(result, "percent_placement") == []


def test_comment_stripping_preserves_line_numbers(project):
    # strip_noise blanks rather than deletes, so a real finding after a
    # multi-line comment keeps the line number the author has to navigate to.
    write(project, "giris.md",
          "<!-- çok\nsatırlı\nnot -->\nBu cümlede 25% yanlış yazılmıştır.\n")
    hits = warns(run_check(project), "percent_placement")
    assert hits, "the real error after a multi-line comment must still be seen"
    assert any(occ["line"] == 4 for h in hits for occ in h["occurrences"])


# --- the English Abstract is not Turkish prose -------------------------------
# Regression: a Turkish paper's English Abstract is required by nearly every
# Turkish journal and by the YÖK thesis rules, and it uses ENGLISH orthography
# — decimal point, percent sign after the number. Linting it against Turkish
# convention reports correct work as wrong, and worse: decimal_separator and
# term_unity are corpus-wide tallies naming the dominant form, so the English
# abstract votes in an election about the Turkish body.

def test_english_abstract_percent_form_is_not_a_turkish_error(project):
    write(project, "bulgular.md", "Duyarlılık %94,2 olarak ölçülmüştür.\n")
    write(project, "abstract.md", "Sensitivity was 94.2% in the pooled analysis.\n")
    assert warns(run_check(project, ["percent_placement"]), "percent_placement") == []


def test_english_abstract_decimals_do_not_make_the_body_look_mixed(project):
    write(project, "bulgular.md", "Duyarlılık 0,942 ve özgüllük 0,881 bulunmuştur.\n")
    write(project, "abstract.md", "Sensitivity 0.942 and specificity 0.881.\n")
    assert warns(run_check(project, ["decimal_separator"]), "decimal_separator") == []


def test_english_abstract_terms_do_not_break_term_unity(project):
    write(project, "bulgular.md", "Derin öğrenme tabanlı sistemler derin öğrenme "
                                  "yöntemleriyle derin öğrenme uygular.\n")
    write(project, "abstract.md", "Deep learning systems apply deep learning here.\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_a_real_mixture_in_the_turkish_body_is_still_caught(project):
    """The exemption must not blanket-mute the corpus."""
    write(project, "bulgular.md", "Duyarlılık 0,942 ve 0,881 iken AUC 0.809 idi.\n")
    write(project, "abstract.md", "Sensitivity was 0.942.\n")
    hits = warns(run_check(project, ["decimal_separator"]), "decimal_separator")
    assert len(hits) == 1
    assert hits[0]["dot_count"] == 1          # only the body's stray point
    assert hits[0]["minority_examples"][0]["text"] == "0.809"


def test_ozet_is_turkish_and_stays_in_scope(project):
    """Özet is the Turkish half of the pair — it must still be linted."""
    write(project, "bulgular.md", "Duyarlılık 0,942 olarak ölçülmüştür.\n")
    write(project, "ozet.md", "Duyarlılık 0.942 olarak ölçülmüştür.\n")
    hits = warns(run_check(project, ["decimal_separator"]), "decimal_separator")
    assert len(hits) == 1 and hits[0]["dot_count"] == 1


def test_ozet_abstract_pair_check_still_reads_the_abstract(project):
    """The equivalence check must keep the full file list — that is its job."""
    write(project, "ozet.md",
          "**Amaç.** Duyarlılık %94,2 bulunmuştur.\n\n"
          "**Anahtar sözcükler:** tarama; derin öğrenme\n")
    write(project, "abstract.md",
          "**Objective.** Sensitivity was 99.9%.\n\n"
          "**Keywords:** screening; deep learning\n")
    hits = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    assert hits, "a number present in only one of the pair must still be reported"


# --- a wrapped keyword list is one list --------------------------------------
def test_wrapped_keyword_list_is_read_whole():
    """Reading only the matched line truncated the list at the first newline.

    Two lists holding the same six terms were reported as 3 vs 4 because they
    wrapped in different places — a mismatch that did not exist, and a check
    that would equally have stayed silent about a real one hiding past the wrap.
    """
    text = ("**Anahtar sözcükler:** diyabetik retinopati; derin öğrenme; tanısal doğruluk;\n"
            "tarama; sistematik derleme; gri literatür\n")
    assert len(trs._keywords(text)) == 6


def test_wrapped_keyword_list_stops_at_a_blank_line():
    text = ("**Keywords:** alpha; beta;\ngamma\n\nThis is the next paragraph; not a keyword.\n")
    assert trs._keywords(text) == ["alpha", "beta", "gamma"]


def test_wrapped_keyword_list_stops_at_a_new_block():
    text = ("**Keywords:** alpha; beta\n"
            "**Registration.** Not registered; no protocol id.\n")
    assert trs._keywords(text) == ["alpha", "beta"]


def test_single_line_keyword_list_still_works():
    assert trs._keywords("**Keywords:** alpha; beta; gamma\n") == ["alpha", "beta", "gamma"]


def test_ozet_abstract_keyword_counts_match_when_both_wrap(project):
    write(project, "ozet.md",
          "**Amaç.** Duyarlılık %94,2 bulunmuştur.\n\n"
          "**Anahtar sözcükler:** bir; iki; üç;\ndört; beş; altı\n")
    write(project, "abstract.md",
          "**Objective.** Sensitivity was 94.2%.\n\n"
          "**Keywords:** one; two; three; four;\nfive; six\n")
    hits = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    kw = [i for h in hits for i in h.get("issues", []) if i["issue"] == "keywords"]
    assert kw == [], f"both lists hold six keywords: {kw}"


def test_a_real_keyword_count_mismatch_is_still_caught(project):
    write(project, "ozet.md",
          "**Amaç.** Duyarlılık %94,2 bulunmuştur.\n\n"
          "**Anahtar sözcükler:** bir; iki; üç;\ndört\n")
    write(project, "abstract.md",
          "**Objective.** Sensitivity was 94.2%.\n\n"
          "**Keywords:** one; two; three; four;\nfive; six\n")
    hits = warns(run_check(project, ["ozet_abstract"]), "ozet_abstract")
    kw = [i for h in hits for i in h.get("issues", []) if i["issue"] == "keywords"]
    assert len(kw) == 1 and kw[0]["ozet_keywords"] == 4 and kw[0]["abstract_keywords"] == 6


# --- a suffixed Turkish word can fold onto an English term -------------------
def test_turkish_dative_is_not_counted_as_the_english_term(project):
    """"literatüre" folds to exactly "literature" once diacritics are stripped.

    Regression: term_unity matched BOTH the Turkish and the English variants
    against the folded corpus, so a manuscript that never wrote an English word
    was told it had used the English name twice. The collision class is
    systematic in an agglutinative language — any glossary entry whose English
    form differs from a suffixed Turkish form only by diacritics.
    """
    write(project, "giris.md",
          "Türkçe literatüre bakıldığında literatür taraması yetersizdir. "
          "Bu literatüre ek olarak literatür incelenmiştir.\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_a_genuine_english_term_is_still_counted(project):
    """The fix must not blind the check to real English intrusion."""
    write(project, "giris.md",
          "Derin öğrenme yöntemleri derin öğrenme ile derin öğrenme uygular. "
          "Ancak deep learning ve yine deep learning terimi de geçmektedir.\n")
    hits = warns(run_check(project, ["term_unity"]), "term_unity")
    assert hits, "two occurrences of the English name must still be reported"
    dl = [c for c in hits[0]["concepts"] if c["concept"] == "deep learning"]
    assert dl and dl[0]["variants"].get("deep learning (EN)") == 2


# ---------- a software version is not a decimal ----------
# A review of tools names them constantly ("IDx-DR 2.0", "RetCAD v.2.2.0"), and
# each one landed on the dot side of the very tally that decides which
# separator dominates. The manuscript could not fix it either: those strings are
# quoted verbatim from the sources.

def test_product_version_numbers_do_not_count_as_decimals(project):
    write(project, "yontem.md",
          "Duyarlılık 0,905 ve özgüllük 0,931 bulunmuştur. Değerlendirilen "
          "sistemler IDx-DR 2.0 (IDx LLC), EyeArt system v2.0 (Eyenuk) ve "
          "RetCAD v.2.2.0 (Thirona) idi.")
    assert warns(run_check(project, ["decimal_separator"]), "decimal_separator") == []


def test_a_real_decimal_point_is_still_caught_next_to_versions(project):
    # Mutation guard: the version exemption must not disarm the check itself.
    write(project, "yontem.md",
          "Duyarlılık 0,905 bulunmuştur ama özgüllük 0.931 yazılmıştır. "
          "Sistem IDx-DR 2.0 idi.")
    hits = warns(run_check(project, ["decimal_separator"]), "decimal_separator")
    assert hits and hits[0]["minority_examples"][0]["text"] == "0.931"


# ---------- generated files are not the author's register ----------

def test_generated_appendix_is_excluded_from_the_corpus_tally(project):
    write(project, "yontem.md", "Derin öğrenme yöntemi kullanılmıştır.")
    write(project, "ek-d.md",
          "<!-- URETILMIS DOSYA — elle duzenlemeyin. -->\n\n"
          "| deep learning | deep learning | deep learning |\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_a_hand_written_file_with_the_same_content_is_still_counted(project):
    write(project, "yontem.md", "Derin öğrenme yöntemi kullanılmıştır.")
    write(project, "tartisma.md",
          "| deep learning | deep learning | deep learning |\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity")


def test_generated_banner_is_found_even_though_comments_are_stripped(project):
    # The banner is an HTML comment and strip_noise() removes those before any
    # check sees the text, so the detector must read the file, not the string.
    write(project, "ek-e.md", "<!-- URETILMIS DOSYA -->\n\n| x |\n")
    assert trs._is_generated(project / "drafts" / "ek-e.md") is True
    assert trs._is_generated(project / "drafts" / "yok.md") is False


# ---------- "hâliyle"/"malum" are informal only as discourse markers ----------

def test_raw_form_haliyle_is_not_conversational(project):
    write(project, "yontem.md",
          "Ham hâliyle sayıldığında aynı ürün birden çok aile görünür; model "
          "kendi hâliyle bırakılmıştır.")
    assert warns(run_check(project, ["informal_register"]), "informal_register") == []


def test_clause_initial_haliyle_is_still_conversational(project):
    write(project, "yontem.md", "Hâliyle sonuç değişmiştir. Bu, malum, bilinen bir sorundur.")
    hits = warns(run_check(project, ["informal_register"]), "informal_register")
    assert hits and hits[0]["total"] == 2


def test_the_other_informal_tokens_are_unaffected_by_the_boundary_rule(project):
    write(project, "yontem.md", "Sonuç gayet iyi ve epey belirgindir.")
    hits = warns(run_check(project, ["informal_register"]), "informal_register")
    assert hits and hits[0]["total"] == 2


# ---------- polysemy: a property of the word, not of how often it is used ----


def test_an_ordinary_word_listed_as_a_technical_variant_is_never_counted(project):
    """"özellik" means a property of anything, and a review says it constantly.

    The suppression used to be conditional on the word appearing exactly ONCE,
    which had it backwards: it stopped working on precisely the words a
    manuscript leans on. Three ordinary uses of "özellik" alongside two
    technical uses of "öznitelik" — no drift anywhere — raised the flag.
    """
    write(project, "tartisma.md",
          "Çalışmaların özellikleri incelendi. Ayırt edici bir özellik bulundu. "
          "Üçüncü bir özellik daha vardır. Modelde öznitelik seçimi yapıldı; "
          "öznitelik sayısı azaltıldı.\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity") == []


def test_the_ambiguous_words_are_declared_in_the_glossary_not_in_the_script(project):
    """The project edits the glossary; it cannot edit the script it installed.

    Terminology is domain-specific — a clinical review may use "nitelik"
    unambiguously — so the list of words too ordinary to count belongs in the
    file a project owns. This pins the mechanism, not just its current answer:
    put the word back under `tr` and the checker must count it again.
    """
    path = project / "templates" / "tr-terminology.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    feature = next(c for c in data["concepts"] if c["concept"] == "feature")
    assert "özellik" in feature["tr_ambiguous"]
    assert "özellik" not in feature["tr"]

    feature["tr"] = feature["tr"] + feature.pop("tr_ambiguous")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write(project, "tartisma.md",
          "Çalışmaların özellikleri incelendi. Ayırt edici bir özellik bulundu. "
          "Üçüncü bir özellik daha vardır. Modelde öznitelik seçimi yapıldı; "
          "öznitelik sayısı azaltıldı.\n")
    assert warns(run_check(project, ["term_unity"]), "term_unity"), (
        "with the word moved back under `tr` the checker must count it — "
        "otherwise the suppression is hardcoded somewhere else and the "
        "glossary is decoration")


def test_an_unambiguous_pair_still_flags_at_one_occurrence_each(project):
    """The fix must not be silence dressed up as precision.

    "veri seti" and "veri kümesi" are both only ever the dataset, so a single
    occurrence of each is already the inconsistency this check exists for.
    """
    write(project, "yontem.md",
          "Veri seti bölündü. Veri kümesi dengesizdi.\n")
    found = warns(run_check(project, ["term_unity"]), "term_unity")
    assert found, "an unambiguous two-name concept must still be reported"
    concepts = {c["concept"] for c in found[0]["concepts"]}
    assert "dataset" in concepts
