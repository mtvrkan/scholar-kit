---
name: preregister
description: "Write and timestamp a preregistration before the data is analysed: hypotheses stated as directional predictions, the design, the sampling and stopping rule, the analysis plan with the exact tests, what counts as a confirmation and what would falsify it, and which analyses are exploratory. Attested through the hash-chained provenance ledger so the plan cannot be quietly revised after the results are seen. Use for empirical, RCT and observational studies, before /experiment."
disable-model-invocation: true
argument-hint: "[--attest] [--osf]"
---

# /preregister — The Plan, Written Before the Results

A preregistration is not paperwork. It is the difference between a hypothesis and
a description of what happened to be significant, and it is the one document that
has to exist **before** the analysis, which is exactly why it is the one that
gets written afterwards.

## Gate

1. `PROJECT.md` complete (topic, RQs, type).
2. **Check `analysis/runs.jsonl`.** If runs already exist, say so plainly:

   > Bu projede zaten N koşu kayıtlı. Sonuçları gördükten sonra yazılan bir plan
   > ön kayıt değildir. İki dürüst seçenek var: (a) bunu **analiz planı** olarak
   > yazıp ön kayıt demeyin, (b) yalnız *bundan sonraki* aşama için ön kayıt
   > yapın ve neyin daha önce çalıştırıldığını açıkça yazın.

   Do not offer a third option, and do not backdate anything.

## What goes in it

Write `analysis/preregistration.md`, section by section, **with** the author —
each of these is a decision, not a field to fill:

```markdown
# Preregistration — <title>
Date: <today>   ·   Status: before data analysis

## 1. Question and hypotheses
H1 (directional): <X increases Y> — not "X and Y are related". A non-directional
hypothesis cannot be wrong in an interesting way.

## 2. Design
<observational / experimental / RCT>, units, conditions, blinding, randomisation.

## 3. Sampling and stopping rule
Target N and how it was chosen (power analysis: effect size, alpha, power).
When collection stops — a date, an N, or a criterion decided NOW. "We will
collect until the effect is significant" is the failure this section prevents.

## 4. Variables
Outcome(s), predictor(s), covariates, and how each is measured/derived.
Exclusion rules for records, stated before seeing them.

## 5. Analysis plan
The exact test for each hypothesis, the model, how missing data is handled,
how multiple comparisons are corrected, and the software.

## 6. What would falsify H1
The result that would make you abandon it. If nothing would, H1 is not a
hypothesis.

## 7. Exploratory
Everything else you intend to look at, named as exploratory in advance — which
is what makes it publishable as exploratory rather than dressed up as confirmatory.

## 8. Deviations
(empty at registration; every later change is appended with its date and reason)
```

Dispatch **methodology-advisor** for sections 2-5 — power, design and the choice
of test are its subject, and getting them wrong here is expensive later.

## Attestation

```bash
python scripts/provenance.py --record preregistration --path analysis/preregistration.md
```

Appends a record carrying the SHA-256 of the file and the hash of the record
before it. Rewriting it later breaks the chain, and `provenance.py --verify` names
where.

State the limit, every time, because it is exactly the kind of claim that grows
in the retelling: **this proves the file was not rewritten afterwards, not that it
was written before the data existed.** The ledger has no key and no external
timestamp; anyone with the repository can append. For a preregistration that a
reader must be able to trust without trusting you, register it on **OSF**
(osf.io/prereg) or **AsPredicted**, where the timestamp is a third party's — and
put that registration's URL in section 0 of this file.

## Deviations, later

When the analysis departs from the plan — and it usually does, legitimately —
append to section 8 with the date and the reason, then re-attest. A deviation
recorded is a methods sentence; a deviation not recorded is what a reviewer finds
when the plan and the paper disagree.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Ön kayıt yazıldı
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dosya:  analysis/preregistration.md (8 bölüm, hepsi dolu)
Zincir: provenance.jsonl kaydı #12 — SHA-256 kayıtlı
Sınır:  bu kayıt dosyanın SONRADAN DEĞİŞTİRİLMEDİĞİNİ gösterir;
        veriden ÖNCE yazıldığını değil. Üçüncü taraf zaman damgası için OSF.

Sonraki: /experiment (plan ile koşu kaydı birbirine bakar)
```

## Reference

- **Subagent:** methodology-advisor (design, power, choice of test)
- **Scripts:** `python scripts/provenance.py --record preregistration`
- **Writes:** `analysis/preregistration.md`
- **Related:** `/experiment` (runs the plan), `/replication-package`,
  reporting-guidelines skill (CONSORT/STROBE items overlap with sections 2-5)

---
*A plan written after the results is not a plan. The kit can prove a file was not edited; only a third party can prove when it was written.*
