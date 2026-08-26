"""Tests for compliance_gen.py — AI-disclosure, CRediT, and funding statement
templating. Never fabricates: every mode requires its inputs explicitly."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))



def _run(*args):
    p = subprocess.run([sys.executable, str(SCRIPTS / "compliance_gen.py"), *args],
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return p.returncode, p.stdout, p.stderr


# ---------- ai-disclosure ----------

def test_ai_disclosure_requires_tool_and_uses():
    code, out, err = _run("ai-disclosure", "--tool", "Claude", "--uses", "")
    assert code == 1 and "ERROR" in err


def test_ai_disclosure_produces_statement_with_given_facts():
    code, out, err = _run("ai-disclosure", "--tool", "Claude (Anthropic)",
                          "--uses", "literature synthesis")
    assert code == 0
    result = json.loads(out)
    assert "Claude (Anthropic)" in result["statement"]
    assert "literature synthesis" in result["statement"]
    assert "warning" in result  # always flags this is not venue-verified wording


def test_ai_disclosure_venue_family_changes_framing():
    code1, out1, _ = _run("ai-disclosure", "--tool", "X", "--uses", "Y", "--venue-family", "icmje")
    code2, out2, _ = _run("ai-disclosure", "--tool", "X", "--uses", "Y", "--venue-family", "ieee")
    assert json.loads(out1)["statement"] != json.loads(out2)["statement"]


def test_ai_disclosure_verified_by_included_when_given():
    code, out, err = _run("ai-disclosure", "--tool", "X", "--uses", "Y", "--verified-by", "Jane Doe")
    assert "Jane Doe" in json.loads(out)["statement"]


# ---------- credit ----------

def test_credit_requires_nonempty_authors():
    code, out, err = _run("credit", "--authors", "[]")
    assert code == 1 and "ERROR" in err


def test_credit_rejects_unrecognized_role():
    code, out, err = _run("credit", "--authors",
                          json.dumps([{"name": "A", "roles": ["Made-up Role"]}]))
    assert code == 1 and "not one of the 14 CRediT" in err


def test_credit_accepts_hyphen_variant_of_writing_roles():
    code, out, err = _run("credit", "--authors",
                          json.dumps([{"name": "A", "roles": ["Writing - original draft"]}]))
    assert code == 0
    assert "Writing – original draft" in json.loads(out)["statement"]


def test_credit_case_insensitive_role_match():
    code, out, err = _run("credit", "--authors",
                          json.dumps([{"name": "A", "roles": ["conceptualization"]}]))
    assert code == 0
    assert "Conceptualization" in json.loads(out)["statement"]


def test_credit_multiple_authors_all_included():
    code, out, err = _run("credit", "--authors", json.dumps([
        {"name": "Jane Doe", "roles": ["Software"]},
        {"name": "John Smith", "roles": ["Supervision"]},
    ]))
    result = json.loads(out)
    assert "Jane Doe" in result["statement"] and "John Smith" in result["statement"]


def test_credit_author_missing_roles_rejected():
    code, out, err = _run("credit", "--authors", json.dumps([{"name": "A", "roles": []}]))
    assert code == 1 and "ERROR" in err


def test_credit_unassigned_roles_reported():
    code, out, err = _run("credit", "--authors",
                          json.dumps([{"name": "A", "roles": ["Software"]}]))
    result = json.loads(out)
    assert "Software" not in result["unassigned_roles"]
    assert "Supervision" in result["unassigned_roles"]


def test_credit_invalid_json_rejected():
    code, out, err = _run("credit", "--authors", "not json")
    assert code == 1 and "ERROR" in err


# ---------- funding ----------

def test_funding_none_and_grants_mutually_exclusive():
    code, out, err = _run("funding", "--none", "--grants", "[]")
    assert code == 1 and "mutually exclusive" in err


def test_funding_requires_none_or_grants():
    code, out, err = _run("funding")
    assert code == 1 and "ERROR" in err


def test_funding_none_produces_no_funding_statement():
    code, out, err = _run("funding", "--none")
    assert code == 0
    assert "no specific funding" in json.loads(out)["statement"]


def test_funding_grants_produces_statement_with_facts():
    code, out, err = _run("funding", "--grants", json.dumps(
        [{"funder": "TUBITAK", "grant_number": "123456", "recipient": "Jane Doe"}]))
    result = json.loads(out)
    assert "TUBITAK" in result["statement"]
    assert "123456" in result["statement"]
    assert "Jane Doe" in result["statement"]


def test_funding_multiple_grants_joined():
    code, out, err = _run("funding", "--grants", json.dumps(
        [{"funder": "A"}, {"funder": "B"}]))
    result = json.loads(out)
    assert "A" in result["statement"] and "B" in result["statement"]


def test_funding_grant_missing_funder_rejected():
    code, out, err = _run("funding", "--grants", json.dumps([{"grant_number": "1"}]))
    assert code == 1 and "ERROR" in err


# ---------- ai-disclosure: the honesty claim is a claim, not boilerplate ----------

NO_AI_RESULTS = "No results, data, or findings were AI-generated"


def test_ai_disclosure_omits_the_no_results_claim_unless_asserted():
    # This sentence used to be printed unconditionally, so `--uses "data
    # analysis"` produced a statement saying the AI did the analysis AND that no
    # data was AI-generated. A disclosure exists to be accurate; that one
    # contradicted itself inside a single sentence pair.
    code, out, err = _run("ai-disclosure", "--tool", "T", "--uses", "data analysis")
    assert code == 0
    result = json.loads(out)
    assert NO_AI_RESULTS not in result["statement"]
    assert any("only you can make" in n for n in result.get("notes", []))


def test_ai_disclosure_asserts_the_claim_when_asked_and_uses_do_not_clash():
    code, out, err = _run("ai-disclosure", "--tool", "T",
                          "--uses", "language editing", "--no-ai-results")
    assert code == 0
    result = json.loads(out)
    assert NO_AI_RESULTS in result["statement"]
    assert "notes" not in result


def test_ai_disclosure_refuses_a_claim_that_contradicts_the_stated_uses():
    code, out, err = _run("ai-disclosure", "--tool", "T",
                          "--uses", "data analysis; drafting", "--no-ai-results")
    assert code == 1
    both = out + err
    assert "contradicts" in both
    # names the words that clashed, so the author can see what triggered it
    assert "analysis" in both and "data" in both
