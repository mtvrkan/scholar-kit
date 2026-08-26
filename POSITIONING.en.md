# Positioning — what Scholar-Kit does, what it does not, and what it deliberately refuses

[Türkçe](POSITIONING.md) · **English**

> This document is a **record of scope boundaries**. Its purpose is to write a
> decision down once, so that the absence of a feature is a settled question
> rather than an argument to be had again, and so later changes have something
> to be measured against. Crossing a boundary listed here is not "adding a
> feature" — it is **amending this record**.

## What this is

Scholar-Kit is an end-to-end academic research, paper and thesis production kit
for Claude Code: specialist subagents, a deterministic Python tool layer,
hook-protected state that lives on disk, and a zero-fabrication citation
discipline. It also covers the work that surrounds a paper — grant proposals and
reports, ethics-committee applications, data management plans, referee reports,
promotion dossiers, course syllabi and accreditation matrices — under the same
discipline: **no limit, criterion, form field or programme outcome ever comes
from the model's memory.** It is **MIT licensed** — open source in the full sense:
commercial use, institutional redistribution and derivative work are all permitted.

It treats Turkish and English academic writing as **equally** first-class: YÖK
thesis structure, Özet↔Abstract equivalence, TR Dizin / DergiPark / YÖK Thesis
Center searching, and Turkish academic register are part of the design, not
translations bolted on afterwards.

## What this is not

It is not an autonomous paper-writing system. It does not stand in for the
researcher, it claims no authorship, and its output is not submission-ready
without human review. The kit is an **assistant, not an author** — and that is
not a marketing line, it is the reason the phase gates exist.

## Refused mechanisms

These are not "out of scope" footnotes. They are load-bearing boundaries that
define what the kit is. Each was refused not because it is technically hard, but
because building it would destroy the one thing the kit provides.

**Unapproved end-to-end production.** A flow that carries a question all the way
to a submission-ready paper without user approval at each stage. Refused: the
researcher stops being the author of their own work and becomes the reviewer of
AI output. The gates (outline approval → verify=PASS → Major=0) exist precisely
to prevent that; making them skippable with an `--auto` flag is not a
convenience, it is the end of their being gates.

**Bibliographic data from memory.** BibTeX comes only from `doi2bib.py`'s DOI
content negotiation; anything else carries a `verified:false` stamp. Refused: a
reference the model remembers goes unnoticed when it is wrong, precisely because
it looks right — and citation fabrication is the primary defect this kit exists
to solve.

**A similarity / plagiarism score.** Refused: a WebSearch-based heuristic
comparison is **not** a plagiarism rate, but it will be read as one. Your
institution's Turnitin/iThenticate check is your responsibility, and
`/submit-check` says so every time. We would rather give nothing than give a
misleading percentage.

**AI-detection evasion.** Style calibration and the writing audit target
**quality**, not evading detection. Refused: a "humanizer" encourages the user to
violate a disclosure obligation. `/disclosures` does the exact opposite — it
makes producing the disclosure easy.

**Processing a manuscript that is under review by you.** When a journal sends you
a paper to referee, that text is given to you under a confidentiality undertaking
— Elsevier, Springer and NIH say so explicitly. Refused: handing it to a tool is
the **referee's** breach, not the author's, and no amount of report quality undoes
it. `/review-paper` therefore does the opposite — it **never reads the paper**.
You read it; the kit turns your notes into a structured referee report and audits
that report's own defects: a Major with no section reference, a recommendation
outside the journal's own option set, a sentence that reveals your identity. The
hard part of refereeing is not reading — it is writing up what you read, and that
is the part that can be lifted.

**Fabricated reviewer gold labels.** The kit ships no labelled papers for
`/critique --calibrate --gold`. Refused: a label is a claim about what a real
journal actually decided; inventing one for the sake of producing a number
destroys the only thing calibration provides. The gold set is yours.

**A specific institution's template content.** The kit **gives** you generic
TR/EN thesis templates and the `/ingest-template` mechanism; it does **not** give
you one particular university's font/margin/heading rules. Refused: binding the
kit to one institution's guidelines turns it into a silent error for everybody
else. The template is supplied by the user, not carried in the repository.

**Cross-paper memory.** The kit holds no state outside the project directory:
there is no ledger of your past claims, no limitations list carried forward, no
reviewer history profile. Refused: every run starts from material explicitly
declared in that run. A gate that judges a state nobody declared in this run is
not a gate.

This boundary also defines what `/dossier` (promotion dossier, academic CV) is:
**you supply the publication list and the scoring criteria in each run**, the kit
stores neither between sessions and writes not one line outside the project
directory. Being a dossier tool was assumed to require keeping a permanent
record; it does not. What the kit adds there is not memory but arithmetic — and
re-verifying every publication's index claim through `venue_check.py`, because a
dossier's most frequent error is an ESCI paper counted as SCIE.

### What is deliberately *inside* the boundary

Unlike most competing systems, this kit **analyzes the user's own data**
(`/analyze-data`, the `data-scientist` agent, hook-scoped to `analysis/`). That
is a choice, not an oversight: the gap between where numbers are produced and
where they are written is the source of failure modes M3 (fabricated result) and
M6 (fabricated methodology), and it is exactly this integration that lets
`failure_scan.py` check prose against `analysis/` artefacts at all.

**The boundary that moved on 2026-08-14 (D-097).** Until the previous version this
document said the kit **collects no data**, and what it meant was: the author
writes the scraper, the kit supplies only the protocol and the checks. The reason
was that deciding whether a collection is permissible belongs to the author, not
to a tool — and that reason still holds. What changed is the recognition that the
**mechanism did not carry the reason**: withholding a collector never stopped the
scraping, it only moved it somewhere with no robots check, no field allowlist, no
rate limit and no request log — into a single-use file rewritten from scratch
every session.

The line now sits here: the decision is still the author's and is still made
**before the request** — the protocol is written, the robots verdict is read, the
field list is declared. The execution is the kit's, under conditions it will not
relax: an incomplete protocol is refused, a robots disallow has **no override
flag**, a field absent from the protocol is never collected, the User-Agent
honestly names the kit and the author's contact address, there is a request
ceiling and a rate limit, and every request is logged. The same line governs
downloading: `dataset_fetch.py` fetches only a **registered** dataset and refuses
until its **licence has actually been read**.

Today's boundary in one sentence: the kit **downloads registered data**, **runs
the collection its protocol describes**, and **analyzes your data**; it does not
**generate** data, does not **fabricate synthetic** data, does not **get past an
access wall** (it holds no credentials, carries no cookies, renders no JS, solves
no CAPTCHA), does not **collect from human participants** (a survey runs on the
institution's platform), does not **rule that a collection is lawful**, and does
not **certify** that an analysis is scientifically correct.

**The scope that widened on 2026-08-15 (D-098).** Until now the kit covered one
axis of an academic's job — producing papers and theses. The same person also
writes grant proposals, files ethics applications, referees for journals,
assembles a promotion dossier and teaches. What those share is precisely what the
kit is already good at: each has an **authority document** (the call text, the
ethics form, the ÜAK criteria table, the programme outcome list, the journal's
referee form) and an **arithmetic** to be done against it. That is where the kit
widened, and what stays out is unchanged: it remembers none of their contents.

## The authority-file rule

Every new axis rests on one rule: **a limit, criterion, form field or outcome list
set by an outside authority is read only from a file you filled in** — carrying
its `source_url` and `read_on`. The kit does not produce the sentences "Elsevier
abstracts are 250 words", "the TÜBİTAK 1001 budget ceiling is X", "associate
professorship requires N points". Those are the same error class as a remembered
DOI, and they cause exactly the rejection they were meant to prevent.

The consequence is friction worth keeping: with no authority file the result is
`UNCHECKED`, not `OK`. "Nothing was checked" and "no problems" must not read the
same, and that distinction is applied identically across every axis of the kit.

## The limit of the integrity checks — the honest failure shape

The kit audits **the text and the reported process**: whether a citation exists,
whether a claim matches its source, whether numbers agree with `analysis/`
artefacts, figure/table integrity, reporting-standard compliance. Some of that is
sampling-based; some depends on the coverage of external indexes.

The kit does not verify that the work **was actually done**. It cannot prove that
a procedure was followed, that the raw data is real, that the analyses reproduce,
or that an intervention happened as described.

The honest failure shape is explicit: **a study built on fabricated data passes
every gate in this kit, as long as the fabrication is reported consistently.**

That is not a gap to be closed by adding more checks. It is where tooling ends
and human, institutional and reproducibility review begins.

## Measurement honesty

The kit's claims about its own accuracy are written down, with their limits, in
[`eval/MEASUREMENT.md`](eval/MEASUREMENT.md). In short: the deterministic
checkers are measured against labelled gold sets and gated on every `pytest`
run; reviewer accuracy can only be measured against **your own** gold set; and
drafting and synthesis are **not measured** — and say so.

The question to ask before publishing any number is: what did this number
measure, and does it say what it did not measure?

## Appropriate use

- Research support: literature search, source verification, citation auditing
- Analysis of your own data and transparent reporting of the results
- Thesis production (YÖK structure, defence preparation included)
- Project work: proposals, work-package/budget consistency, progress and final reports
- Compliance documents: ethics application, consent form, data management plan
- Service: structuring the referee report you wrote (you read the paper), and the
  supervision-committee report skeleton
- Career: the arithmetic and index verification behind a promotion dossier, academic CV
- Course work: syllabus, exam–outcome coverage, rubrics, accreditation matrices
- Teaching: demonstrating research method, peer review and academic writing
- Institutional / commercial use — the MIT license permits it

## Uses we advise against

- Presenting work as entirely human-written without disclosing AI assistance
- Producing a paper without engaging with its content (the gates exist to make
  exactly this harder)
- Substituting simulated reviewer feedback for real peer review
- Presenting the kit's integrity gates as proof that the underlying research is
  correct

## Changing these boundaries

A proposal that crosses one of the items above is not a feature request — it is a
**scope change** request. The process: update the relevant item in this document
together with the reasoning for why it no longer holds; record the decision as a
dated entry in [`DECISIONS.md`](DECISIONS.md); only then write code.

What matters as much as the boundary itself is the record of **why** it was drawn
there — a boundary whose reasoning was never written down looks arbitrary six
months later, and gets crossed quietly.
