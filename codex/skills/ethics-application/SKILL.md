---
name: ethics-application
description: "Produce the ethics committee application and the informed consent form for a study that collects data from people or about them — mapped to YOUR board's own form fields, with the consent text checked against the collection plan's actual field list. Use when an ethics/IRB submission is due, when a survey or interview study needs a consent form, or when a reviewer asks for the ethics statement's backing. Not /disclosures (that is the manuscript's funding/CRediT/AI boilerplate) and not /collect-data (that writes the collection protocol this one is built from)."
disable-model-invocation: true
argument-hint: "[--scaffold|--check] [--scan <data-file>]"
---

# /ethics-application — the second time you write the same protocol

`/collect-data` already made you write the protocol: purpose, legal basis,
sampling, fields, minimisation, retention, consent, ethics approval, contact.
Your board then asks for all of it again, on its own form, plus a consent text
written for a participant rather than for a reviewer.

That second writing is where studies drift. The collection plan gains a column —
`author_email` was right there in the response — and the consent form still says
"we collect only the post text". Nobody notices, because until now nothing
compared the two documents. This command does.

## Gate

None, but two things make it useful rather than ceremonial:

1. `analysis/collection-plan.json` (from `/collect-data`) — its `fields` map is
   the authority the consent text is checked against.
2. `exports/ethics/form-fields.json` — **your board's own field list**, which you
   fill. Without it the run reports `UNCHECKED`, not `OK`.

## Step 1: the form-fields file — what the kit will not remember

```bash
cat exports/ethics/form-fields.json
```

```json
{
  "board": "Örnek Üniversitesi Sosyal ve Beşeri Bilimler Etik Kurulu",
  "source_url": "https://example.edu/etik-kurul/basvuru-formu",
  "read_on": "2026-08-15",
  "fields": ["title", "investigators", "purpose", "design", "participants",
             "sample_size", "recruitment", "data_collected", "instruments",
             "risks", "benefits", "consent_procedure", "confidentiality",
             "data_storage", "retention_period", "legal_basis", "funding",
             "conflicts", "contact"]
}
```

**Ask the author to open their board's actual form and read the section headings
off it.** Ethics forms differ between universities, between faculties of the same
university, and between the medical and the social-sciences boards. A remembered
field list produces an application that is returned for revision — which is the
same cost this command exists to avoid, arriving later.

## Step 2: scaffold

```bash
python scripts/ethics_pack.py --scaffold
```

Writes `exports/ethics/application.md`, `consent-form.tr.md` and
`consent-form.en.md` with every section present and **every answer left as
`<...>`**. Existing files are never overwritten.

The scaffold deliberately does not pass its own check. Filling an ethics
application with plausible text is worse than leaving it blank: a board reads the
answers as the researcher's own commitments, and a sentence nobody meant is a
commitment nobody will keep.

## Step 3: write the consent form for the participant

This is the part that is genuinely writing, and it stays here in the session —
with three rules:

- **Name every field.** Every column in `collection-plan.json` appears in "toplanan
  veriler" / "data we collect", by name. If naming a field in plain language
  embarrasses the study, that is information about the study.
- **Retention is a number.** "Gerektiği sürece" / "as long as necessary" is
  flagged, and rightly: a board reads it as "not decided".
- **Never write an approval reference.** The board issues it. The kit writes no
  decision number and flags a placeholder left where one belongs.

Turkish and English versions are structurally equivalent — the same discipline
`/front-matter` applies to Özet↔Abstract.

## Step 4: check

```bash
python scripts/ethics_pack.py --check
python scripts/ethics_pack.py --check --scan analysis/data/collected.csv
```

What it reports:

| Check | Finding it produces |
|---|---|
| Application vs the board's fields | which sections are missing, empty, or still `<...>` |
| Consent vs the collection plan | **a field collected but not disclosed** |
| Consent completeness | which of the ten elements is absent (purpose, voluntary, withdrawal, data categories, retention, access, confidentiality, risks, contact, ethics reference) |
| Retention | vague phrasing, named |
| Approval reference | a placeholder left where a decision number belongs |
| Protocol | `collection_check.py`'s completeness, re-run here |
| `--scan` | personal-data counts and column names — **never the values** |

Exit 0 clean · 2 findings or `UNCHECKED`.

## What this does not do

- **It does not approve anything.** Every check is presence, agreement or
  arithmetic. Whether the risk is proportionate, whether the population is
  appropriate, whether consent is genuinely informed — that is the board's
  judgement, and no part of it is mechanical.
- **It does not decide legality.** `collection_check.py`'s line holds: robots.txt
  is not the law, and KVKK/GDPR compliance is not a script's verdict.
- **It does not run the study.** A survey runs on the institution's platform.

## Reference

- **Script:** `python scripts/ethics_pack.py` (`--scaffold`, `--check`, `--scan`)
- **Writes:** `exports/ethics/` — `application.md`, `consent-form.tr.md`,
  `consent-form.en.md`, and the `form-fields.json` you filled
- **Related:** `/collect-data` (the protocol and plan this reads), `/dmp` (the data
  management plan, from the same registers), `/disclosures` (the manuscript's own
  ethics statement), `/submission-pack` (which asks whether the statement exists)

---
*A board does not check whether your answers are true. It checks whether you have thought about the question — which is why an answer nobody wrote is worse than an answer that is hard.*
