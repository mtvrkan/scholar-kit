import json


def test_add_and_query(run, tmp_path):
    code, out, err = run("evidence_db.py", "add", "--json",
                         json.dumps({"source": "a2020x", "type": "finding",
                                     "claim": "test claim", "tags": ["rq1"], "strength": 4}))
    assert code == 0, err
    assert json.loads(out)["added"] == ["EV-0001"]

    code, out, _ = run("evidence_db.py", "query", "--tags", "rq1", "--min-strength", "3")
    cards = json.loads(out)
    assert len(cards) == 1 and cards[0]["claim"] == "test claim"

    code, out, _ = run("evidence_db.py", "query", "--tags", "rq9")
    assert json.loads(out) == []


def test_add_accepts_payload_flag_as_primary_alias(run, tmp_path):
    # --payload is the primary, unambiguous name for the add sub-command's
    # single-record input; --json (this file's other tests) is kept only as
    # a backward-compatible alias to the same dest, since it collides in
    # spelling (not in argparse dest, so no functional break) with the
    # top-level --json output-mode flag.
    code, out, err = run("evidence_db.py", "add", "--payload",
                         json.dumps({"source": "a2020x", "type": "finding",
                                     "claim": "test claim", "tags": ["rq1"], "strength": 4}))
    assert code == 0, err
    assert json.loads(out)["added"] == ["EV-0001"]


def test_validation_rejects_bad_cards(run, tmp_path):
    code, _, err = run("evidence_db.py", "add", "--json",
                       json.dumps({"source": "a", "type": "nonsense", "claim": "x"}))
    assert code == 1 and "type" in err

    code, _, err = run("evidence_db.py", "add", "--json",
                       json.dumps({"source": "a", "type": "quote", "claim": "x", "verbatim": True}))
    assert code == 1 and "page" in err  # verbatim quotes need page numbers


def test_stats_and_conflicts(run, tmp_path, sample_cards):
    code, out, _ = run("evidence_db.py", "stats")
    stats = json.loads(out)
    assert stats["total"] == 2 and stats["by_type"]["finding"] == 1

    code, out, _ = run("evidence_db.py", "conflicts")
    pairs = json.loads(out)
    assert pairs and sorted(pairs[0]["pair"]) == ["EV-0001", "EV-0002"]

    # id continues from existing max
    code, out, _ = run("evidence_db.py", "add", "--json",
                       json.dumps({"source": "b", "type": "gap", "claim": "y"}))
    assert json.loads(out)["added"] == ["EV-0003"]


def test_conflicts_skips_card_missing_id(run, tmp_path):
    # A hand-edited/corrupt cards.jsonl entry missing 'id' must not crash
    # `conflicts` with a raw KeyError — it's read-only inspection, not a
    # validation path, so it should skip the malformed card and still report
    # the real conflict pair among the well-formed ones.
    p = tmp_path / "evidence" / "cards.jsonl"
    p.parent.mkdir(parents=True)
    cards = [
        {"source": "x", "type": "finding", "claim": "no id here"},
        {"id": "EV-0001", "source": "x", "type": "finding", "claim": "c1", "conflicts_with": ["EV-0002"]},
        {"id": "EV-0002", "source": "x", "type": "finding", "claim": "c2"},
    ]
    p.write_text("\n".join(json.dumps(c) for c in cards) + "\n", encoding="utf-8")
    code, out, err = run("evidence_db.py", "conflicts")
    assert code == 0, err
    pairs = json.loads(out)
    assert pairs == [{"pair": ["EV-0001", "EV-0002"], "claims": ["c1", "c2"]}]


def test_rejects_non_object_payload_item_via_stdin(run):
    code, out, err = run("evidence_db.py", "add", "--stdin",
                         stdin=json.dumps(["not-an-object"]))
    assert code == 1
    assert "expected a JSON object" in err
    assert "Traceback" not in err


def test_rejects_non_object_payload_item_via_json_flag(run):
    code, out, err = run("evidence_db.py", "add", "--json", json.dumps("just a string"))
    assert code == 1
    assert "expected a JSON object" in err
    assert "Traceback" not in err


def test_rejects_bool_strength_true(run):
    code, out, err = run("evidence_db.py", "add", "--json",
                         json.dumps({"source": "x", "type": "finding", "claim": "c", "strength": True}))
    assert code == 1
    assert "strength" in err


def test_rejects_bool_strength_false(run):
    code, out, err = run("evidence_db.py", "add", "--json",
                         json.dumps({"source": "x", "type": "finding", "claim": "c", "strength": False}))
    assert code == 1
    assert "strength" in err


def test_still_accepts_real_integer_strength(run):
    code, out, err = run("evidence_db.py", "add", "--json",
                         json.dumps({"source": "x", "type": "finding", "claim": "c", "strength": 4}))
    assert code == 0, err


def test_converts_real_oserror_to_clean_die(run, tmp_path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "cards.jsonl").mkdir()  # a directory, not a file
    code, out, err = run("evidence_db.py", "add", "--json",
                         json.dumps({"source": "x", "type": "finding", "claim": "c"}))
    assert code == 1
    assert "Traceback" not in err
    assert "failed to write" in err
