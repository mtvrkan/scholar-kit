import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import doi2bib  # noqa: E402
from lib_common import parse_bibtex  # noqa: E402

FAKE_BIB = """@article{Kaya_2023, title={Deep learning for bearing fault diagnosis},
 author={Kaya, Ahmet}, journal={MSSP}, year={2023}, doi={10.1016/j.ymssp.2023.00001}}"""

FAKE_CSL = {"title": "Deep learning for bearing fault diagnosis",
            "author": [{"family": "Kaya", "given": "Ahmet"}],
            "issued": {"date-parts": [[2023]]}}


class FakeResp:
    def __init__(self, text="", js=None, status=200):
        self.text, self._js, self.status_code = text, js, status
        self.encoding = "utf-8"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._js


def test_fetch_and_key_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(doi2bib.requests, "get", lambda *a, **k: FakeResp(text=FAKE_BIB))
    bib = doi2bib.fetch_bibtex("10.1016/j.ymssp.2023.00001")
    entry = parse_bibtex(bib)[0]
    key = doi2bib.make_key(entry["fields"], "fallback")
    assert key == "kaya2023deep"


def test_backfill_still_fetches_csl_when_only_year_is_missing():
    # Regression: the early-return guard only checked title+author, so an
    # entry with BOTH already present but year missing never even attempted
    # the CSL fetch — the year-backfill code a few lines below was
    # unreachable in exactly the case (title+author present, year absent)
    # it exists to handle.
    entry = {"fields": {"title": "Deep learning for bearing fault diagnosis",
                        "author": "Kaya, Ahmet"}}  # no year
    calls = []

    def fake_fetch_csl(doi):
        calls.append(doi)
        return FAKE_CSL

    import doi2bib as _mod
    orig = _mod.fetch_csl
    _mod.fetch_csl = fake_fetch_csl
    try:
        _mod._backfill_from_csl(entry, "10.1016/j.ymssp.2023.00001")
    finally:
        _mod.fetch_csl = orig

    assert calls == ["10.1016/j.ymssp.2023.00001"]
    assert entry["fields"]["year"] == "2023"


def test_backfill_skips_csl_fetch_when_all_three_fields_present():
    entry = {"fields": {"title": "x", "author": "y", "year": "2020"}}

    def fail_if_called(doi):
        raise AssertionError("fetch_csl should not be called when title/author/year all present")

    import doi2bib as _mod
    orig = _mod.fetch_csl
    _mod.fetch_csl = fail_if_called
    try:
        _mod._backfill_from_csl(entry, "10.1016/j.ymssp.2023.00001")
    finally:
        _mod.fetch_csl = orig


def test_verify_catches_fabrication(monkeypatch, tmp_path, capsys):
    """A bib entry whose title doesn't match its DOI's authoritative record → FABRICATED."""
    bad_bib = tmp_path / "refs.bib"
    bad_bib.write_text("""@article{fake2023quantum,
  title = {Quantum consciousness in neural fields},
  author = {Nobody, X},
  journal = {Imaginary Letters},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
  verified = {true},
}""", encoding="utf-8")
    monkeypatch.setattr(doi2bib, "fetch_csl", lambda doi: FAKE_CSL)
    with pytest.raises(SystemExit) as exc:
        doi2bib.cmd_verify(type("A", (), {"bib": str(bad_bib), "entry": None, "json_out": True})())
    assert exc.value.code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["fabricated"] == 1
    assert "title mismatch" in report["entries"][0]["reason"]


def test_verify_passes_good_entry(monkeypatch, tmp_path, capsys):
    good = tmp_path / "refs.bib"
    good.write_text("""@article{kaya2023deep,
  title = {Deep learning for bearing fault diagnosis},
  author = {Kaya, Ahmet},
  journal = {MSSP},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
  verified = {true},
}""", encoding="utf-8")
    monkeypatch.setattr(doi2bib, "fetch_csl", lambda doi: FAKE_CSL)
    with pytest.raises(SystemExit) as exc:
        doi2bib.cmd_verify(type("A", (), {"bib": str(good), "entry": None, "json_out": True})())
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"


def test_cmd_fetch_json_flag_wraps_bibtex_in_json(monkeypatch, capsys):
    # Regression: --json was silently a no-op on the non-append fetch path —
    # the only place in the kit where --json didn't actually produce JSON.
    args = type("Args", (), {"append": None, "json_out": True, "doi": "10.1/x", "key": None})()
    monkeypatch.setattr(doi2bib, "fetch_bibtex", lambda doi: "@article{kaya2023deep, title={x}}")
    monkeypatch.setattr(doi2bib, "_backfill_from_csl", lambda entry, doi: None)
    monkeypatch.setattr(doi2bib, "make_key", lambda fields, fallback: "kaya2023deep")

    doi2bib.cmd_fetch(args)
    result = json.loads(capsys.readouterr().out)
    assert "bibtex" in result
    assert result["key"] == "kaya2023deep"


def test_cmd_fetch_append_is_atomic_not_raw_append(monkeypatch, tmp_path, capsys):
    # Regression: --append used to open(path, "a") directly; a crash mid-write
    # could leave a torn trailing entry. It must now go through
    # write_text_atomic (temp-file + os.replace), so the destination file
    # never exists in a partially-written state.
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{existing2020test,\n  title = {Existing},\n}\n\n", encoding="utf-8")
    args = type("Args", (), {"append": str(bib), "json_out": True, "doi": "10.1/new", "key": None})()
    monkeypatch.setattr(doi2bib, "fetch_bibtex",
                         lambda doi: "@article{new2024paper, title={New}}")
    monkeypatch.setattr(doi2bib, "_backfill_from_csl", lambda entry, doi: None)
    monkeypatch.setattr(doi2bib, "make_key", lambda fields, fallback: "new2024paper")

    doi2bib.cmd_fetch(args)
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "appended"
    entries = parse_bibtex(bib.read_text(encoding="utf-8"))
    assert [e["key"] for e in entries] == ["existing2020test", "new2024paper"]
    # No leftover .tmp<pid> sidecar from write_text_atomic's temp-file step.
    assert not list(tmp_path.glob("refs.bib.tmp*"))


def test_cmd_fetch_append_duplicate_key_gets_numeric_suffix(monkeypatch, tmp_path, capsys):
    # Regression: a colliding key used to grow "keyb", "keybb", "keybbb", ...
    # — cosmetic but unreadable. Now "key2", "key3", ... instead.
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{kaya2023deep,\n  title = {First},\n}\n\n"
                    "@article{kaya2023deep2,\n  title = {Second},\n}\n\n", encoding="utf-8")
    args = type("Args", (), {"append": str(bib), "json_out": True, "doi": "10.1/dup", "key": None})()
    monkeypatch.setattr(doi2bib, "fetch_bibtex",
                         lambda doi: "@article{kaya2023deep, title={Third}}")
    monkeypatch.setattr(doi2bib, "_backfill_from_csl", lambda entry, doi: None)
    monkeypatch.setattr(doi2bib, "make_key", lambda fields, fallback: "kaya2023deep")

    doi2bib.cmd_fetch(args)
    result = json.loads(capsys.readouterr().out)
    assert result["key"] == "kaya2023deep3"


def test_main_guard_declares_unicode_decode_error_catch():
    # doi2bib.py reads bib/references.bib directly (not via lib_common.read_jsonl)
    # in both cmd_fetch's --append path and cmd_verify — a non-UTF8 byte there
    # must surface as a clean die(), not a raw traceback.
    text = Path(__file__).parent.parent.joinpath("scripts", "doi2bib.py").read_text(encoding="utf-8")
    guard = text[text.rindex('if __name__ == "__main__":'):]
    assert "except OSError as e:" in guard
    assert "except UnicodeDecodeError as e:" in guard


@pytest.mark.live
def test_live_smoke_three_dois():
    """Acceptance: doi2bib resolves 3 real DOIs against doi.org (CSL backfill for
    records whose BibTeX ships empty fields, e.g. the BERT anthology entry)."""
    for doi in ("10.1038/nature14539",          # LeCun et al., Deep learning, Nature 2015
                "10.1109/CVPR.2016.90",         # ResNet
                "10.1145/3065386"):             # AlexNet (CACM)
        bib = doi2bib.fetch_bibtex(doi)
        entries = parse_bibtex(bib)
        assert entries, f"unparseable BibTeX for {doi}"
        entry = entries[0]
        doi2bib._backfill_from_csl(entry, doi)
        assert entry["fields"].get("title"), f"no title for {doi} even after CSL backfill"


def test_fetched_bibtex_is_html_unescaped():
    # The publisher registers HTML; doi.org passes it through verbatim. Decoding
    # at fetch time is where it belongs — every later consumer (bib file, pandoc,
    # the printed reference list) then sees plain text with a real "&".
    raw = ("@article{x, journal={Diabetes Technology &amp; Therapeutics}, "
           "title={A &lt;i&gt;study&lt;/i&gt;}}")
    assert doi2bib.unescape_html_entities(raw) == (
        "@article{x, journal={Diabetes Technology & Therapeutics}, "
        "title={A <i>study</i>}}")


def test_html_unescape_runs_once_not_to_a_fixed_point():
    # "&amp;amp;" is a publisher's double-encoding mistake to report, not one to
    # silently repair: decoding twice would invent a value nobody deposited.
    assert doi2bib.unescape_html_entities("A &amp;amp; B") == "A &amp; B"


def test_html_unescape_tolerates_empty_and_plain_text():
    assert doi2bib.unescape_html_entities("") == ""
    assert doi2bib.unescape_html_entities("Health & Place") == "Health & Place"


# --- off-canon bibliography warning -----------------------------------------
# Regression: a real project ran `doi2bib --append references.bib` (root) while
# every reader in the kit defaults to bib/references.bib. 93 authoritative
# entries landed in a file no script opens; the manuscript would have built
# with 28 of the 121 references it cites, and cite_audit called those same
# citations "missing" — one cause, two unrelated-looking symptoms.

def _in_project(tmp_path, monkeypatch, *, make_bib_dir=True):
    monkeypatch.chdir(tmp_path)
    if make_bib_dir:
        (tmp_path / "bib").mkdir()
    return tmp_path


def test_off_canon_warns_for_root_level_references_bib(tmp_path, monkeypatch):
    _in_project(tmp_path, monkeypatch)
    msg = doi2bib.off_canon_bib_warning(Path("references.bib"))
    assert msg
    assert "bib/references.bib" in msg


def test_off_canon_silent_for_the_canonical_path(tmp_path, monkeypatch):
    _in_project(tmp_path, monkeypatch)
    assert doi2bib.off_canon_bib_warning(Path("bib/references.bib")) == ""


@pytest.mark.parametrize("spell", ["absolute", "dotdot"])
def test_off_canon_silent_when_canonical_path_spelled_differently(
        tmp_path, monkeypatch, spell):
    """Same file, different spelling — this must compare resolved paths.

    A plain string compare passes `./bib/references.bib` by accident, because
    Path() already collapses a leading "./". These two spellings do NOT
    collapse, so they are what actually pins resolve() down: an absolute path
    (what a caller passing tmp_path / "bib" / "references.bib" produces) and
    one routed through a parent component.
    """
    _in_project(tmp_path, monkeypatch)
    target = (tmp_path / "bib" / "references.bib") if spell == "absolute" \
        else Path("bib") / ".." / "bib" / "references.bib"
    assert str(target) != str(Path("bib") / "references.bib")   # spelling differs
    assert doi2bib.off_canon_bib_warning(target) == ""


def test_off_canon_silent_when_project_does_not_use_the_bib_layout(tmp_path, monkeypatch):
    """A project keeping its bibliography elsewhere must not be nagged."""
    _in_project(tmp_path, monkeypatch, make_bib_dir=False)
    assert doi2bib.off_canon_bib_warning(Path("refs.bib")) == ""


def test_off_canon_warns_for_a_differently_named_stray_bib(tmp_path, monkeypatch):
    _in_project(tmp_path, monkeypatch)
    assert doi2bib.off_canon_bib_warning(Path("corpus.bib"))


def test_off_canon_ignores_non_bib_targets(tmp_path, monkeypatch):
    _in_project(tmp_path, monkeypatch)
    assert doi2bib.off_canon_bib_warning(Path("notes.md")) == ""


def test_append_surfaces_off_canon_in_json(tmp_path, monkeypatch, capsys):
    """The warning must reach the caller's JSON, not just a log line."""
    _in_project(tmp_path, monkeypatch)
    monkeypatch.setattr(doi2bib, "fetch_bibtex", lambda doi: FAKE_BIB)
    monkeypatch.setattr(doi2bib, "fetch_csl", lambda doi: FAKE_CSL)

    args = type("A", (), {})()
    args.doi = "10.1016/j.ymssp.2023.00001"
    args.key = "kaya2023deep"
    args.append = "references.bib"
    args.json_out = True
    doi2bib.cmd_fetch(args)

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "appended"
    assert "off_canon_bib" in out
    assert (tmp_path / "references.bib").exists()


def test_append_to_canonical_carries_no_warning_key(tmp_path, monkeypatch, capsys):
    _in_project(tmp_path, monkeypatch)
    monkeypatch.setattr(doi2bib, "fetch_bibtex", lambda doi: FAKE_BIB)
    monkeypatch.setattr(doi2bib, "fetch_csl", lambda doi: FAKE_CSL)

    args = type("A", (), {})()
    args.doi = "10.1016/j.ymssp.2023.00001"
    args.key = "kaya2023deep"
    args.append = "bib/references.bib"
    args.json_out = True
    doi2bib.cmd_fetch(args)

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "appended"
    assert "off_canon_bib" not in out
