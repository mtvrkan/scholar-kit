import json


# ---------- bib_doctor ----------

def test_bib_doctor_clean_file_passes(run, tmp_path, sample_bib):
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib")
    report = json.loads(out)
    # demir entry has a URL-prefixed DOI -> one problem entry, exit 2
    assert code == 2
    kinds = [i["kind"] for p in report["problems"] for i in p["issues"]]
    assert "doi-prefix" in kinds


def test_bib_doctor_decodes_html_entities_from_publisher_metadata(run, tmp_path):
    """doi.org's BibTeX is generated from what the publisher registered, and
    publishers register HTML. "Diabetes Technology &amp; Therapeutics" printed
    exactly that way in a finished reference list — noticed only when the PDF was
    finally built. Ampersands in journal names are common, so this is a defect
    every manuscript with such a source inherits."""
    b = tmp_path / "bib"
    b.mkdir()
    (b / "references.bib").write_text("""@article{bhaskaranand2019value,
  title = {The Value of Automated Diabetic Retinopathy Screening},
  author = {Bhaskaranand, Malavika},
  journal = {Diabetes Technology &amp; Therapeutics},
  year = {2019},
  doi = {10.1089/dia.2019.0164},
  verified = {true},
}
""", encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib", "--fix")
    kinds = [i["kind"] for p in json.loads(out)["problems"] for i in p["issues"]]
    assert "html-entity" in kinds
    text = (b / "references.bib").read_text(encoding="utf-8")
    assert "Diabetes Technology & Therapeutics" in text
    assert "&amp;" not in text


def test_bib_doctor_leaves_a_real_ampersand_alone(run, tmp_path):
    """A correctly-decoded field legitimately contains "&". Flagging a bare
    ampersand would make the check fire on every entry it had already fixed."""
    b = tmp_path / "bib"
    b.mkdir()
    (b / "references.bib").write_text("""@article{smith2020health,
  title = {A study},
  author = {Smith, Jane},
  journal = {Health & Place},
  year = {2020},
  doi = {10.1016/j.healthplace.2020.00001},
  verified = {true},
}
""", encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib")
    kinds = [i["kind"] for p in json.loads(out)["problems"] for i in p["issues"]]
    assert "html-entity" not in kinds


def test_bib_doctor_catches_planted_bad_bib(run, tmp_path):
    bad = tmp_path / "bib"
    bad.mkdir()
    (bad / "references.bib").write_text("""@article{kaya2023deep,
  title = {Deep learning for bearing fault diagnosis},
  author = {Kaya, Ahmet},
  journal = {MSSP},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
  verified = {true},
}

@article{Kaya_2023_DUP,
  title = {Deep learning for bearing fault diagnosis},
  author = {Kaya, Ahmet},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
}
""", encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib")
    assert code == 2
    report = json.loads(out)
    dup_issues = [i["kind"] for p in report["problems"] for i in p["issues"]]
    assert "duplicate-doi" in dup_issues and "duplicate-title" in dup_issues
    assert "missing-field" in dup_issues       # journal missing
    assert "unverified" in dup_issues          # no verified={true}
    assert "key-style" in dup_issues           # Kaya_2023_DUP not normalized


def test_bib_doctor_fix_strips_doi_prefix(run, tmp_path, sample_bib):
    run("bib_doctor.py", "--bib", "bib/references.bib", "--fix")
    text = sample_bib.read_text(encoding="utf-8")
    assert "https://doi.org/" not in text
    assert "10.1016/j.jsv.2022.00002" in text


# ---------- bib_doctor --retract (the sanctioned deletion path) ----------
#
# references.bib had two sanctioned writers and both could only GROW it, so a
# citation the verifier flagged as FABRICATED or RETRACTED had no scripted way
# out and /verify-citations told the user to hand-edit a hook-protected file.
# These lock the removal path and, more importantly, its refusal.

def _cite(tmp_path, key, name="introduction.md"):
    d = tmp_path / "drafts"
    d.mkdir(exist_ok=True)
    (d / name).write_text(f"Prior work established this [@{key}].\n", encoding="utf-8")
    return d / name


def test_retract_removes_the_entry_and_keeps_the_rest(run, tmp_path, sample_bib):
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "demir2022vibration")
    assert code == 0
    payload = json.loads(out)
    assert payload["removed"] == 1 and payload["remaining"] == 1
    text = sample_bib.read_text(encoding="utf-8")
    assert "demir2022vibration" not in text
    assert "kaya2023deep" in text


def test_retract_hands_back_the_deleted_entry_as_the_only_audit_trail(run, tmp_path, sample_bib):
    _, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib",
                    "--retract", "demir2022vibration")
    trail = json.loads(out)["removed_bibtex"]
    # The bib file is script-owned and keeps no history: if this field ever goes
    # empty, a retraction becomes unrecoverable and unreviewable at once.
    assert "demir2022vibration" in trail
    assert "Vibration analysis with wavelets" in trail


def test_retract_refuses_while_the_key_is_still_cited(run, tmp_path, sample_bib):
    _cite(tmp_path, "demir2022vibration")
    code, _, err = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "demir2022vibration")
    assert code == 1
    assert "drafts/introduction.md" in err
    # Refusing is the whole point: deleting only the bib half would convert a
    # WRONG citation into a MISSING one, which cite_audit.py blocks one stage
    # later, further from the decision that caused it.
    assert "demir2022vibration" in sample_bib.read_text(encoding="utf-8")


def test_retract_force_overrides_the_refusal_and_records_that_it_did(run, tmp_path, sample_bib):
    _cite(tmp_path, "demir2022vibration")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "demir2022vibration", "--force")
    assert code == 0
    payload = json.loads(out)
    assert payload["forced"] is True
    assert payload["still_cited_in"] == ["drafts/introduction.md"]
    assert "demir2022vibration" not in sample_bib.read_text(encoding="utf-8")


def test_retract_ignores_a_citation_inside_a_code_fence(run, tmp_path, sample_bib):
    # Same extractor as the citation gate — if this file grew its own looser
    # regex the two guards would disagree about what a citation is.
    d = tmp_path / "drafts"
    d.mkdir()
    (d / "methods.md").write_text(
        "Example syntax:\n\n```\n[@demir2022vibration]\n```\n", encoding="utf-8")
    code, out, _ = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "demir2022vibration")
    assert code == 0
    assert json.loads(out)["still_cited_in"] == []


def test_retract_unknown_key_is_an_error_not_a_silent_noop(run, tmp_path, sample_bib):
    code, _, err = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "nosuchkey2099")
    assert code == 1
    assert "nosuchkey2099" in err
    assert len(sample_bib.read_text(encoding="utf-8").split("@article")) == 3


def test_retract_and_fix_together_are_refused(run, tmp_path, sample_bib):
    code, _, err = run("bib_doctor.py", "--bib", "bib/references.bib",
                       "--retract", "kaya2023deep", "--fix")
    assert code == 1
    assert "one at a time" in err


def test_force_without_retract_is_refused(run, tmp_path, sample_bib):
    code, _, err = run("bib_doctor.py", "--bib", "bib/references.bib", "--force")
    assert code == 1
    assert "--force" in err


def test_retract_leaves_the_file_read_only_like_every_sanctioned_write(run, tmp_path, sample_bib):
    import os
    run("bib_doctor.py", "--bib", "bib/references.bib", "--retract", "demir2022vibration")
    # write_text_atomic re-arms the protection bits; a deletion path that
    # skipped them would silently disarm the file it just rewrote.
    assert not os.access(sample_bib, os.W_OK) or not (sample_bib.stat().st_mode & 0o222)


# ---------- cite_audit ----------

def test_cite_audit_missing_and_orphans(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "intro.md").write_text(
        "Deep learning works [@kaya2023deep]. Ghost claim [@ghost2020missing]. "
        "Needs source [CITATION NEEDED].", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    assert code == 2
    report = json.loads(out)
    assert report["missing"] == ["ghost2020missing"]
    assert "demir2022vibration" in report["orphans"]
    assert len(report["placeholders"]) == 1


# The three gap tags mark different states and are deliberately not collapsed:
# a missing citation, a gap the writer refused to fill from model memory, and a
# fill the author authorized. Only the first two are holes in a finished draft.

def test_material_gap_tag_blocks_like_a_placeholder(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "intro.md").write_text(
        "Sample size rationale is unavailable. [MATERIAL GAP]", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    assert code == 2
    assert len(json.loads(out)["material_gaps"]) == 1


def test_turkish_material_gap_tag_recognized(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "giris.md").write_text("Örneklem gerekçesi yok. [KANIT YOK]", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    assert code == 2
    assert len(json.loads(out)["material_gaps"]) == 1


def test_llm_supplemented_tag_reported_but_never_blocks(run, tmp_path, sample_bib):
    # An author-authorized fill is a disclosure, not a defect. It must show up
    # in the report — an authorized fill leaving no trace is indistinguishable
    # from an unauthorized one — while leaving the exit code clean.
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "intro.md").write_text(
        "Background on bearing diagnostics. [LLM-SUPPLEMENTED]", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    assert code == 0
    report = json.loads(out)
    assert len(report["llm_supplemented"]) == 1
    assert report["material_gaps"] == [] and report["placeholders"] == []


def test_turkish_llm_supplemented_tag_recognized(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "giris.md").write_text("Genel arka plan. [MODEL BİLGİSİ]", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    assert code == 0
    assert len(json.loads(out)["llm_supplemented"]) == 1


def test_tags_are_reported_with_file_and_line(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "intro.md").write_text(
        "First line.\nSecond line. [MATERIAL GAP]\n", encoding="utf-8")
    _, out, _ = run("cite_audit.py")
    assert json.loads(out)["material_gaps"] == ["drafts/intro.md:2"]


def test_cite_audit_ignores_code_and_emails(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "methods.md").write_text(
        "Contact author@example.com. Code: `df @ matrix` and\n```\n@decorator\n```\n"
        "Real cite [@kaya2023deep].", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    report = json.loads(out)
    assert report["missing"] == []
    assert report["cited"] == 1


def test_cite_audit_quick_mode_never_blocks(run, tmp_path, sample_bib):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    f = drafts / "x.md"
    f.write_text("Bad [@nope2020].", encoding="utf-8")
    code, out, _ = run("cite_audit.py", "--quick", "--file", str(f))
    assert code == 0  # hook mode is visibility-only
    assert "undefined" in out


# ---------- an HTML comment is not prose ----------


def test_a_citation_inside_an_html_comment_does_not_count_as_cited(run, tmp_path, sample_bib):
    """A key commented out during revision was still counted as used.

    That is the worst direction for this particular check: the entry stops
    looking like an orphan, so the audit reports a bibliography as fully cited
    on the strength of a citation no reader will ever see. The kit's own
    evidence binding is an HTML comment, so a draft written the way /draft asks
    is full of them, and a paragraph parked in a comment during revision is
    normal work rather than a mistake to clean up.
    """
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "intro.md").write_text(
        "Deep learning works [@kaya2023deep].\n"
        "<!-- eskiden buradaydi: [@demir2022vibration] -->\n", encoding="utf-8")
    code, out, _ = run("cite_audit.py")
    report = json.loads(out)
    assert report["missing"] == []
    assert "demir2022vibration" in report["orphans"], (
        "the commented-out key was counted as cited, so a genuinely uncited "
        "entry stopped being reported as an orphan")
