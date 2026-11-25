# Reading `provenance.py --verify` in a submission check

`python scripts/provenance.py --verify` answers a question about the RECORD, not
about the manuscript. Read it that way when reporting, or it will be quoted as
something it is not.

## The three outcomes, reported differently

| Field | Meaning | How to report it |
|---|---|---|
| `chain: broken`, `broken_at: N` | A record was rewritten in place, or one was removed. Every hash after seq N no longer links. | **Advisory, with the seq number.** This is the only alarming finding here. Say which record and that the history — not the manuscript — is what failed. |
| `drift: [...]` | The chain is intact and an attested file has changed since it was attested. | One line, no alarm. An outline revised after approval, a `verify-status.json` superseded by a later run, a PDF rebuilt — all ordinary. Worth reporting only so the author can confirm the build being submitted is the attested one. |
| `missing: [...]` | An attested file is gone. | One line. Usually a cleaned `build/`; occasionally a real loss. |
| `status: absent` | The project has no ledger: nothing was ever attested. | **"Not run" — never "no problems".** This is the same rule the rest of the kit follows: "I found nothing" and "I did not look" are different statements (CONTRIBUTING.md). |

## What the chain proves, and what it does not

It proves a record was **not rewritten**. It does not prove a record was
**earned**.

There is no key. An orchestrator that never showed the outline to anyone can run
the sanctioned writer and produce a perfectly valid `outline-approved` record;
`--verify` will call that chain intact, correctly, because it is. Deleting the
ledger and re-attesting from scratch also verifies clean — the chain detects
editing, not replacement, and the only thing standing against replacement is the
read-only bit plus the hook, i.e. the layers `SECURITY.md` already says are not a
security boundary.

Both limits are pinned by name in `tests/test_provenance.py`
(`test_the_chain_cannot_detect_a_freshly_forged_record`,
`test_a_wholesale_rechained_history_verifies_clean`), so no future summary can
quietly upgrade the claim.

What it changes is the shape of the gap: an attestation that used to leave no
trace is now a dated, hashed, ordered line that a co-author, a supervisor or a
journal can hold against the artifacts on disk. That is a smaller promise than
prevention, and it is the whole of what is available without a secret the model
cannot read.

## What it says about the research

Nothing. A chain over fabricated data is an intact chain over fabricated data —
`POSITIONING.md`'s honest-failure-shape section applies here unchanged.
