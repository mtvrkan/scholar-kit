---
name: proposal
description: "Write a research funding proposal — TÜBİTAK ARDEB/1001/1002/3501, a university BAP, Horizon Europe, COST — with the parts a reviewer checks mechanically actually checked: every objective bound to a work package, every work package to a deliverable inside the project's own duration, budget lines summing to the total, and the personnel figure following from the person-months. Section names and limits come from the call text you paste, never from memory. Produces the narrative, workpackages.json, budget.json, risks and a Gantt chart. Use when a call is open; use /preregister for a study's analysis plan and /dmp for the data management plan the call also asks for."
disable-model-invocation: true
argument-hint: "[<call name>] [--check] [--gantt markdown|latex]"
---

# /proposal — the half of a proposal that is arithmetic

A proposal is rejected for two kinds of reason. The first is that the idea did
not convince anyone; nothing here touches that, and nothing should. The second is
the kind a reviewer finds in ten minutes with a calculator:

- an objective no work package serves — a promise with no work behind it
- a work package serving no objective — work with no stated reason
- a deliverable due in month 30 of a 24-month project
- budget lines that do not sum to the declared total
- a personnel figure that does not follow from the person-months

Every one of those is checkable, and every one of them is found by reviewers
rather than by authors.

## Gate

None. But the literature the proposal argues from should come through the same
chain as a paper's: `/lit-review` first, and the state-of-the-art section written
from evidence cards. A proposal citing work nobody registered is the same
fabrication risk as a manuscript doing it.

## Step 1: the call, in a file

```bash
cat proposal/call-fields.json
```

```json
{
  "call": "TÜBİTAK ARDEB 1001 — 2026/1",
  "source_url": "https://tubitak.gov.tr/…/cagri-metni.pdf",
  "read_on": "2026-08-15",
  "duration_months": 24,
  "fields": [
    {"name": "summary", "max_words": 300},
    {"name": "purpose_and_scope", "max_words": 1500},
    {"name": "state_of_the_art"},
    {"name": "method"},
    {"name": "workplan"},
    {"name": "impact", "max_words": 800},
    {"name": "team"},
    {"name": "budget_justification"}
  ]
}
```

**Read the section names and limits off the call text itself.** They change
between rounds of the same programme. The kit will not recall a page limit or a
budget ceiling — that is the authority-file rule, and a proposal returned for a
formatting violation costs the whole round.

No file ⇒ the work packages and budget are still checked against **themselves**,
and the result is `UNCHECKED`.

## Step 2: the work plan as data

`proposal/workpackages.json` — this is the file the graph checks read:

```json
{
  "duration_months": 24,
  "objectives": [
    {"id": "O1", "text": "A model that generalises across operating loads"},
    {"id": "O2", "text": "Validation on field recordings"}
  ],
  "workpackages": [
    {"id": "WP1", "title": "Data collection", "start_month": 1, "end_month": 6,
     "objectives": ["O1"],
     "person_months": {"researcher": 6},
     "deliverables": [{"id": "D1.1", "title": "Curated dataset", "month": 6}],
     "milestones": [{"id": "M1", "title": "Data ready", "month": 6}]}
  ]
}
```

Writing it as data rather than as a table in the narrative is the whole point:
the table in the narrative is generated from it, so the two cannot disagree.

## Step 3: the budget as data

```json
{
  "currency": "TRY", "total": 400000,
  "lines": [{"item": "Personel", "amount": 300000, "justification": "18 ay araştırmacı"},
            {"item": "Sarf malzeme", "amount": 100000, "justification": "Sensörler"}],
  "personnel_rate_per_month": {"researcher": 16666.67, "pi": 0}
}
```

Every line needs a justification — an unjustified line is the first one cut, and
that is a reviewer's habit rather than a rule. State the rates and the personnel
figure gets checked against the person-months; leave them out and the check
reports that it **did not run**, rather than assuming a rate.

## Step 4: check, then write

```bash
python scripts/proposal_check.py --check
python scripts/proposal_check.py --gantt markdown   # paste into the workplan section
python scripts/proposal_check.py --gantt latex      # pgfgantt, for a LaTeX submission
```

Then write `proposal/proposal.md` with one `##` heading per field in
`call-fields.json`. Drafting stays in this session, and three sections deserve
their own discipline:

- **State of the art** — synthesis, not an annotated list. `comparative-analysis`
  skill's gap-reasoning patterns: "no prior work combines X and Y under
  constraint Z" is a claim the reviewer will check against your own reference
  list, so it has to be true of the literature you actually registered.
- **Impact / yaygın etki** — bind each claimed impact to a deliverable. An impact
  no work package produces is the paragraph reviewers score lowest.
- **Risks** — `proposal/risks.md`: each risk with its likelihood, its effect on a
  named work package, and the fallback. A risk table with no fallback is a list
  of reasons not to fund the project.

## Step 5: what the call also asks for

```bash
python scripts/dmp_gen.py --sections proposal/dmp-sections.json --write proposal/dmp.md
python scripts/ethics_pack.py --check       # if human subjects or personal data
python scripts/compliance_gen.py funding --grants '[…]'
```

## What this does not do

- **It does not judge fundability.** Whether the idea deserves money, whether the
  budget is proportionate, whether the team fits — none of that is mechanical and
  none of it is here.
- **It does not know a funder's rules.** Ceilings, eligible cost categories,
  page limits: all from the file you fill.
- **It does not invent a number.** A budget line with no amount is reported, not
  estimated.

## Reference

- **Script:** `python scripts/proposal_check.py` (`--check`, `--gantt`, `--report`)
- **Reads/writes:** `proposal/` — `call-fields.json`, `workpackages.json`,
  `budget.json`, `proposal.md`, `risks.md`
- **Template:** `templates/proposal/proposal.md`
- **Related:** `/project-report` (the same plan, at reporting time), `/dmp`,
  `/ethics-application`, `/lit-review` (the state of the art), `/preregister`
  (the analysis plan, if the project is confirmatory)

---
*Reviewers argue about the idea. They agree about the arithmetic — which is why the arithmetic is where a proposal is cheapest to lose.*
