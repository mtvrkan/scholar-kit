---
title: "PROJECT TITLE — WORKING"
---

<!--
One `##` heading per field in proposal/call-fields.json, which YOU fill from the
call text. This file is a starting shape, not the call's structure: the call's
section names and limits win, and `python scripts/proposal_check.py --check`
compares this document against them.

Nothing below is filled in. A plausible sentence in a proposal is a commitment
somebody will be held to.
-->

## Summary
<the project in one paragraph, for a reviewer who reads nothing else>

## Purpose and scope
<the problem, the question, and what is out of scope — stating the boundary is
 what makes the scope credible>

## State of the art
<synthesis, not an annotated list: ≥2 sources in conversation per paragraph,
 every claim bound to an evidence card. The gap sentence — "no prior work
 combines X and Y under constraint Z" — will be checked against your own
 reference list, so it has to be true of the literature you registered.>

## Method
<design, data, analysis. For an empirical project this is the section
 methodology-advisor should see before it is written.>

## Work plan
<generated: python scripts/proposal_check.py --gantt markdown
 The table comes from proposal/workpackages.json so the two cannot disagree.>

## Impact
<each claimed impact bound to a named deliverable. An impact no work package
 produces is the paragraph reviewers score lowest.>

## Risks and contingencies
<see proposal/risks.md — likelihood, the work package it hits, and the fallback.
 A risk with no fallback is a reason not to fund the project.>

## Team
<who does which work package, and what in their record shows they can>

## Budget justification
<generated from proposal/budget.json; every line's justification lives there so
 the narrative and the arithmetic stay one thing>

## Data management
<generated: python scripts/dmp_gen.py --sections proposal/dmp-sections.json>

## Ethics
<if the project touches people or their data: python scripts/ethics_pack.py --check>

## References
<rendered from bib/references.bib at build — never typed here>
