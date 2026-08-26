"""Tests for claim_check.py — the epistemic-claim lint (overclaim + uncited assertion).

The defect class this closes is the one citation verification structurally cannot
see: a real, resolvable, correctly-formatted citation carrying a sentence that
says more than its source does. The comparison basis is the evidence card
extracted from that same source, so the check is anchored to the source rather
than to a previous draft revision.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claim_check as cchk  # noqa: E402
import pytest


def _project(tmp_path, drafts: dict, cards: list | None = None, registry: list | None = None):
    d = tmp_path / "drafts"
    d.mkdir(parents=True, exist_ok=True)
    for name, text in drafts.items():
        (d / name).write_text(text, encoding="utf-8")
    cpath = tmp_path / "evidence" / "cards.jsonl"
    if cards is not None:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n",
                         encoding="utf-8")
    rpath = tmp_path / "sources" / "registry.jsonl"
    if registry is not None:
        rpath.parent.mkdir(parents=True, exist_ok=True)
        rpath.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in registry) + "\n",
                         encoding="utf-8")
    return d, cpath, rpath


# ---------- rung_of: the ladder itself ----------

def test_rung_ascends_across_english_ladder():
    rungs = [cchk.rung_of(t)[0] for t in (
        "X is associated with Y",
        "X predicts Y",
        "X contributes to Y",
        "X increases Y",
        "X causes Y",
    )]
    assert rungs == [1, 2, 3, 4, 5]


def test_turkish_stems_match_through_inflection():
    # Agglutination: the same stem carries several suffixed surface forms.
    assert cchk.rung_of("X, Y ile ilişkilidir")[0] == 1
    assert cchk.rung_of("X, Y'yi etkilemektedir")[0] == 4
    assert cchk.rung_of("X, Y'ye neden olmaktadır")[0] == 5


def test_hedge_demotes_one_rung():
    assert cchk.rung_of("X causes Y")[0] == 5
    assert cchk.rung_of("X may cause Y")[0] == 4


def test_turkish_ebil_suffix_counts_as_hedge():
    assert cchk.rung_of("X, Y'yi etkileyebilir")[0] == 3  # 4 demoted to 3
    assert cchk.rung_of("X, Y'yi etkilemektedir")[0] == 4


def test_hedge_floors_at_zero():
    assert cchk.rung_of("X may be associated with Y")[0] == 0


def test_attributive_participle_is_not_a_claim_verb():
    # "reduced lung capacity" is an adjective phrase describing an outcome, not
    # a directional claim. Reading it as rung 4 made every source card that
    # merely NAMED an outcome look directional, which silenced real overclaims.
    assert cchk.rung_of("Smoking is associated with reduced lung capacity")[0] == 1
    assert cchk.rung_of("Patients showed increased risk")[0] is None


def test_passive_voice_still_counts_as_directional():
    assert cchk.rung_of("Capacity was reduced by the intervention")[0] == 4
    assert cchk.rung_of("Capacity was significantly reduced")[0] == 4


def test_turkish_attributive_participle_is_not_a_claim_verb():
    assert cchk.rung_of("azaltılmış akciğer kapasitesi ile ilişkilidir")[0] == 1
    assert cchk.rung_of("X, kapasiteyi azaltmaktadır")[0] == 4


def test_no_ladder_verb_returns_none_not_zero():
    # None means "no basis for comparison" — collapsing it to 0 would make every
    # descriptive sentence look like a maximally hedged claim and fire falsely.
    assert cchk.rung_of("The dataset contains 5110 rows.") == (None, None)


# ---------- overclaim ----------

def test_prose_stronger_than_card_is_flagged(tmp_path):
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "Smoking causes reduced lung capacity [@kaya2023]."},
        [{"id": "EV-0001", "source": "kaya2023", "type": "finding",
          "claim": "Smoking is associated with reduced lung capacity"}])
    res = cchk.check(d, c, r)
    assert len(res["overclaim"]) == 1
    hit = res["overclaim"][0]
    assert hit["draft_rung"] == 5 and hit["source_rung"] == 1
    assert hit["card"] == "EV-0001"


def test_prose_weaker_than_card_is_not_flagged(tmp_path):
    # Writing more cautiously than the source is always safe — only the upward
    # move misrepresents. This is the deliberate asymmetry vs revision-diff tools.
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "Smoking is associated with reduced lung capacity [@kaya2023]."},
        [{"id": "EV-0001", "source": "kaya2023", "type": "finding",
          "claim": "Smoking causes reduced lung capacity"}])
    assert cchk.check(d, c, r)["overclaim"] == []


def test_equal_rung_is_not_flagged(tmp_path):
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "Exercise improves outcomes [@demir2022]."},
        [{"id": "EV-0002", "source": "demir2022", "type": "finding",
          "claim": "Exercise increases functional outcomes"}])
    assert cchk.check(d, c, r)["overclaim"] == []


def test_multi_source_sentence_compares_against_strongest_card(tmp_path):
    # A synthesising sentence must not be flagged merely for exceeding the
    # weaker of the two sources it cites.
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "The intervention causes recovery [@a2020; @b2021]."},
        [{"id": "EV-0001", "source": "a2020", "type": "finding",
          "claim": "intervention is associated with recovery"},
         {"id": "EV-0002", "source": "b2021", "type": "finding",
          "claim": "the intervention causes recovery"}])
    assert cchk.check(d, c, r)["overclaim"] == []


def test_source_without_cards_is_skipped_not_guessed(tmp_path):
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "Smoking causes disease [@unknown2019]."},
        [{"id": "EV-0001", "source": "kaya2023", "type": "finding",
          "claim": "unrelated associative finding"}])
    assert cchk.check(d, c, r)["overclaim"] == []


def test_card_filed_under_registry_id_resolves_via_bib_key(tmp_path):
    # Cards are written before a bib_key exists, so `source` may hold SRC-####.
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "X causes Y [@kaya2023deep]."},
        [{"id": "EV-0001", "source": "SRC-0001", "type": "finding",
          "claim": "X is associated with Y"}],
        [{"id": "SRC-0001", "bib_key": "kaya2023deep", "status": "included"}])
    assert len(cchk.check(d, c, r)["overclaim"]) == 1


def test_alias_spellings_do_not_inflate_coverage_count(tmp_path):
    # source_rungs indexes each source under BOTH its SRC-#### id and its
    # bib_key, so a naive len() reported double the real comparison coverage.
    d, c, r = _project(
        tmp_path,
        {"discussion.md": "X causes Y [@kaya2023deep]."},
        [{"id": "EV-0001", "source": "SRC-0001", "type": "finding",
          "claim": "X is associated with Y"}],
        [{"id": "SRC-0001", "bib_key": "kaya2023deep", "status": "included"}])
    assert cchk.check(d, c, r)["sources_with_rung"] == 1


def test_overclaim_scans_own_work_sections_too(tmp_path):
    # results.md is exempt from the UNCITED check but not from overclaim: a
    # Results section still cites sources, and can still overstate them.
    d, c, r = _project(
        tmp_path,
        {"results.md": "This confirms that X causes Y [@kaya2023]."},
        [{"id": "EV-0001", "source": "kaya2023", "type": "finding",
          "claim": "X is associated with Y"}])
    res = cchk.check(d, c, r)
    assert len(res["overclaim"]) == 1
    assert "results.md" in res["files_skipped_for_uncited"][0]


# ---------- uncited assertion ----------

def test_uncited_statistic_flagged(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "Prevalence reached 47.3% in the region."}, [])
    hits = cchk.check(d, c, r)["uncited_assertions"]
    assert len(hits) == 1 and hits[0]["signal"] == "statistic"


def test_cited_statistic_not_flagged(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "Prevalence reached 47.3% [@kaya2023]."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_own_work_marker_exempts_sentence(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "We observed an accuracy of 0.87."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_turkish_own_work_marker_exempts_sentence(tmp_path):
    d, c, r = _project(tmp_path, {"giris.md": "Bu çalışmada doğruluk %87,4 olarak ölçülmüştür."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_artefact_pointer_exempts_sentence(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "Table 2 reports an F1 of 0.91."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_roman_numeral_section_pointer_exempts_sentence(tmp_path):
    """"(III.4)" is a cross-reference to this manuscript's own Results.

    Regression: the artefact pattern required a literal Section/Bölüm keyword
    plus an ARABIC digit, so a manuscript numbering its sections I./II./III./IV.
    — the convention a Turkish thesis or article most often uses — had no
    working own-work pointer at all. Every Discussion sentence restating the
    paper's own pooled estimates came back as an uncited empirical assertion:
    seventeen of them in one file, none of them a real finding.
    """
    d, c, r = _project(tmp_path, {
        "tartisma.md": "Havuzlanmış özgüllük 0,911 olarak bulunmuştur (III.4)."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


@pytest.mark.parametrize("ref", ["III.4", "IV.2", "II.4", "III.5.1", "III.6a"])
def test_roman_numeral_pointer_variants(tmp_path, ref):
    d, c, r = _project(tmp_path, {
        "tartisma.md": f"Özgüllük 0,911 bulunmuştur ({ref})."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_roman_numeral_pointer_works_in_english_too(tmp_path):
    d, c, r = _project(tmp_path, {
        "disc.md": "Pooled specificity was 0.911 (IV.2)."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


@pytest.mark.parametrize("sentence", [
    "I think the reported value of 0.911 is high.",
    "Model V reached 0.911 accuracy on the held-out split.",
    "The I. cohort scored 0.911 on the same scale.",
])
def test_bare_roman_letters_are_not_section_pointers(tmp_path, sentence):
    """The exemption must need a numeral, a dot AND a digit.

    A sentence-initial "I" or a stray "V" beside a statistic must still be
    flagged — an own-work allowance that fires on any capital Roman letter
    would silently exempt most English prose.
    """
    d, c, r = _project(tmp_path, {"intro.md": sentence}, [])
    assert len(cchk.check(d, c, r)["uncited_assertions"]) == 1


def test_causal_claim_without_statistic_flagged(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "Automation causes widespread job displacement."}, [])
    hits = cchk.check(d, c, r)["uncited_assertions"]
    assert len(hits) == 1 and hits[0]["signal"] == "causal-claim"


def test_associative_claim_without_statistic_not_flagged(tmp_path):
    # Below the rung-4 threshold and carrying no number: too often a framing
    # sentence to be worth the false-positive cost.
    d, c, r = _project(tmp_path, {"intro.md": "Automation is associated with labour change."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_bare_integer_is_not_an_empirical_signal(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "The survey covered 3 regions."}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_own_work_filenames_skipped_by_default(tmp_path):
    d, c, r = _project(tmp_path, {"methods.md": "Accuracy reached 91.2% overall."}, [])
    res = cchk.check(d, c, r)
    assert res["uncited_assertions"] == []
    assert res["files_scanned"] == []


def test_a_reviews_synthesis_file_is_own_work_like_any_other_results_section(tmp_path):
    """A review's results section has to be called `synthesis`: word_budget.py's
    review proportions key on that name, so the file cannot also be called
    `results` to land in this skip list. With only `results|bulgular|findings`
    listed, a systematic review's central section was the one own-work file still
    scanned, and its own synthesis sentences ("the reported points span 87.0% to
    99.3%") came back as uncited assertions. Two kit scripts disagreeing about
    one filename should not cost the author a page of false findings."""
    for name in ("synthesis.md", "sentez.md"):
        d, c, r = _project(tmp_path / name[:-3], {name: "Duyarlılık %87,0 ile %99,3 arasındadır."}, [])
        res = cchk.check(d, c, r)
        assert res["uncited_assertions"] == [], name
        assert res["files_scanned"] == [], name


def test_status_md_is_never_scanned(tmp_path):
    # The project's own progress log is not manuscript prose. It used to be
    # exempt from the uncited half only, so a status note could still be scored
    # for overclaim; consistency_check.py and failure_scan.py both exclude it
    # outright and this now matches.
    d, c, r = _project(
        tmp_path,
        {"STATUS.md": "Round 2 confirms the method causes improvement [@kaya2023]."},
        [{"id": "EV-0001", "source": "kaya2023", "type": "finding",
          "claim": "the method is associated with improvement"}])
    res = cchk.check(d, c, r, skip_pattern="")
    assert res["overclaim"] == [] and res["uncited_assertions"] == []
    assert res["files_scanned"] == []


def test_empty_skip_pattern_scans_everything(tmp_path):
    d, c, r = _project(tmp_path, {"methods.md": "Accuracy reached 91.2% overall."}, [])
    assert len(cchk.check(d, c, r, skip_pattern="")["uncited_assertions"]) == 1


# ---------- parsing robustness ----------

def test_decimals_do_not_split_sentences():
    assert cchk.split_sentences("Accuracy was 0.87 overall.") == ["Accuracy was 0.87 overall."]


def test_abbreviation_does_not_split_sentence():
    got = cchk.split_sentences("As Kaya et al. showed, the effect holds.")
    assert got == ["As Kaya et al. showed, the effect holds."]


def test_code_fence_content_ignored(tmp_path):
    d, c, r = _project(
        tmp_path, {"intro.md": "Intro text.\n\n```\naccuracy = 0.87 causes drift\n```\n"}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_heading_not_treated_as_assertion(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "## Accuracy of 91.2%\n\nSee below.\n"}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_html_comment_is_not_prose(tmp_path):
    # The kit's OWN evidence-binding syntax. Read as prose it becomes an uncited
    # assertion carrying a statistic — the checker penalising the convention the
    # draft skill requires.
    d, c, r = _project(
        tmp_path, {"intro.md": "See below.\n<!-- 22,3 ve 18,9: EV-0031 (%99,3) -->\n"}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_html_comment_cannot_grant_an_exemption(tmp_path):
    # The same defect in the other direction: an artefact pointer hidden in a
    # comment must not excuse the sentence it sits beside.
    d, c, r = _project(
        tmp_path, {"intro.md": "<!-- Şekil 3 -->\nOtomasyon işsizliğe neden olmaktadır.\n"}, [])
    hits = cchk.check(d, c, r)["uncited_assertions"]
    assert len(hits) == 1 and hits[0]["signal"] == "causal-claim"


def test_comment_between_words_does_not_fuse_them(tmp_path):
    d, c, r = _project(tmp_path, {"intro.md": "Automation<!-- x -->causes displacement.\n"}, [])
    hits = cchk.check(d, c, r)["uncited_assertions"]
    assert len(hits) == 1 and hits[0]["signal"] == "causal-claim"


def test_a_review_calls_itself_derleme_not_calisma(tmp_path):
    # DEFAULT_SKIP already special-cases "sentez" because a review's results
    # section cannot be named "results"; the self-reference marker had the same
    # blind spot one layer over — "bu derleme" is how a review says "we".
    for phrase in ("Bu derlemenin gözlediği aralık %68,8 ile %98,5 arasındadır.",
                   "Bu inceleme altı kaynak tarayıp 7 çalışmaya ulaşmıştır.",
                   "This review searched six sources and found 7 studies."):
        d, c, r = _project(tmp_path, {"tartisma.md": phrase}, [])
        assert cchk.check(d, c, r)["uncited_assertions"] == [], phrase


def test_an_appendix_calls_itself_ek_not_derleme(tmp_path):
    # One layer further down than the "bu derleme" fix above: an APPENDIX says
    # "bu ek", a caption says "bu tablo". A reporting-checklist appendix is
    # nothing but self-reference about the manuscript's own apparatus, so
    # without these it reads as a page of uncited empirical assertions.
    for phrase in ("Bu ek, DTA'ya özgü maddelerin %40'ını kapsamamaktadır.",
                   "Bu ekte listelenen 27 maddenin tamamı bölümlere bağlanmıştır.",
                   "Bu tablo, 7 çalışmanın fon kaydını göstermektedir.",
                   "Bu protokolün 17 kuralı çıkarımdan sonra yazılmıştır."):
        d, c, r = _project(tmp_path, {"ek.md": phrase}, [])
        assert cchk.check(d, c, r)["uncited_assertions"] == [], phrase


def test_markdown_table_rows_are_not_graded_as_prose(tmp_path):
    # The splitter breaks on sentence punctuation, which no table respects: a
    # cell with no closing period is glued to the next row, so one flagged
    # fragment spans two unrelated rows. A cell also has nowhere to put a
    # citation, so the uncited lint can never be satisfied inside one.
    table = ("| # | Madde | Nerede |\n"
             "|---|---|---|\n"
             "| 7 | Bilgi kaynakları | II.3 · Scopus sorgulanmadı ve sebebi yazılı |\n"
             "| 8 | Arama stratejisi | II.3 · 36 sorgunun tamamı kayıtlı |\n")
    d, c, r = _project(tmp_path, {"ek.md": table}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] == []


def test_table_rows_are_still_checked_for_overclaim(tmp_path):
    # The table exemption is scoped to the uncited check on purpose: a cell can
    # absolutely overclaim, and silencing that would trade one blind spot for
    # a worse one.
    assert cchk.is_table_row("| a | b |")
    assert not cchk.is_table_row("Bu bir düzyazı cümlesidir.")
    # A pipe inside prose must not count as a table row.
    assert not cchk.is_table_row("Duyarlılık | özgüllük ikilisi burada anılmaktadır")


# ---------- CLI contract ----------

def test_missing_inputs_exit_zero_with_empty_report(run, tmp_path):
    code, out, _ = run("claim_check.py")
    assert code == 0
    assert json.loads(out)["warnings"] == 0


def test_strict_exits_two_on_warning(run, tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "intro.md").write_text(
        "Prevalence reached 47.3% in the region.", encoding="utf-8")
    code, out, _ = run("claim_check.py", "--strict")
    assert code == 2
    assert json.loads(out)["warnings"] == 1


def test_check_flag_isolates_one_check(run, tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "intro.md").write_text(
        "Prevalence reached 47.3% in the region.", encoding="utf-8")
    code, out, _ = run("claim_check.py", "--check", "overclaim")
    assert code == 0
    assert json.loads(out)["uncited_assertions"] == []


def test_path_outside_project_rejected(run, tmp_path):
    code, _, err = run("claim_check.py", "--drafts", "../elsewhere")
    assert code == 1 and "--drafts" in err


def test_appendices_are_own_work_by_construction(tmp_path):
    """A reporting-checklist appendix says which section answers which item; an
    own-analysis appendix reports a computation this review performed. Neither
    cites a source because neither has one, and before they were skipped a
    two-page appendix arrived as eight "uncited empirical assertions"."""
    body = ("Havuzlama burada belirsizliği azaltmamakta, görünmez kılmaktadır. "
            "Duyarlılık %94,4 ve özgüllük %93,8 çıkmıştır.")
    for name in ("ek-b-kesifsel-havuzlama.md", "ek_a.md", "appendix-a.md",
                 "supplementary-methods.md", "ekler.md"):
        d, c, r = _project(tmp_path, {name: body}, [])
        assert cchk.check(d, c, r)["uncited_assertions"] == [], name


def test_a_non_appendix_section_is_still_scanned(tmp_path):
    """The skip list is a default for document types that cannot cite, not a way
    to silence the check: a discussion section keeps facing it."""
    body = ("Derin öğrenme tabanlı tarama kaçırılan olguları %30 azaltmaktadır.")
    d, c, r = _project(tmp_path, {"tartisma.md": body}, [])
    assert cchk.check(d, c, r)["uncited_assertions"] != []


# ---------- the declarations section is own-work by construction ----------
#
# PRISMA 2020 items 25-27 and every journal's "Statements and Declarations"
# block: funding, competing interests, CRediT, data availability, registration.
# Every sentence states something about THIS manuscript, so none of them has a
# source to cite. A real one was reported as an uncited empirical assertion for
# explaining why its own PRISMA counts are not derived from the register.

_DECL = ("PRISMA akis sayilari elle yazilmamistir, ama kayit defterinden de "
         "turetilmemistir ve sebebi sudur: defter yalnizca bir karara baglanmis "
         "kaydi tutar.")


@pytest.mark.parametrize("name", [
    "beyanlar.md", "declarations.md", "statements.md", "disclosures.md",
])
def test_declarations_section_is_not_scanned_for_missing_citations(tmp_path, name):
    d, c, r = _project(tmp_path, {name: _DECL})
    res = cchk.check(d, c, r)
    assert res["uncited_assertions"] == []
    assert name in " ".join(res["files_skipped_for_uncited"])


def test_a_normal_section_with_the_same_sentence_is_still_flagged(tmp_path):
    # Mutation guard: the exemption must come from the FILENAME, not from the
    # sentence having become invisible to the causal-claim detector.
    d, c, r = _project(tmp_path, {"discussion.md": _DECL})
    res = cchk.check(d, c, r)
    assert res["uncited_assertions"]

