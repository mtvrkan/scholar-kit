---
name: exam
description: "Build an exam or quiz from the course's own learning outcomes and check the coverage: every outcome measured by at least one question, no question serving an outcome the syllabus does not have, points summing to the declared total, and the Bloom distribution reported so an 'apply' course does not get a recall paper. Produces the paper and the answer key. Use when setting a midterm, final or quiz; /syllabus defines the outcomes it measures and /rubric grades open-ended work."
disable-model-invocation: true
argument-hint: "[midterm|final|quiz] [--check]"
---

# /exam — questions bound to outcomes, and the coverage checked

An exam is where a syllabus finds out whether it meant what it said. The two
failures are symmetrical and both are graph problems: an outcome the paper never
measures, and a question testing something the course never promised.

## Gate

`teaching/syllabus.json` must exist with its `outcomes`. An exam written before
the outcomes is an exam the outcomes will be reverse-engineered from, which is
the thing accreditation exists to catch.

## Step 1: `teaching/exam.json`

```json
{
  "title": "EEM402 Vize",
  "date": "2026-11-12",
  "duration_minutes": 90,
  "total_points": 100,
  "questions": [
    {"id": "Q1", "points": 30, "outcomes": ["DÇ1"], "bloom": "apply",
     "text": "Verilen veri kümesi için k-NN sınıflandırıcısını …",
     "answer": "…", "rubric": "Doğru mesafe ölçütü 10p, …"},
    {"id": "Q2", "points": 40, "outcomes": ["DÇ2"], "bloom": "evaluate",
     "text": "…", "answer": "…"}
  ]
}
```

Each question declares which outcome it measures. That single field is what makes
the rest checkable.

## Step 2: write questions at the outcome's own level

The Bloom level of the outcome sets the level of the question. An outcome that
says *"uygular"* and a question that says *"tanımlayınız"* have not met:

| Outcome verb | The question asks for |
|---|---|
| tanımlar / defines | a definition, a list, a name |
| açıklar / explains | a mechanism in the student's own words |
| **uygular / applies** | a computation, a procedure carried out on new data |
| analiz eder / analyses | a comparison, a decomposition, a diagnosis |
| değerlendirir / evaluates | a judgement **with its criterion stated** |
| tasarlar / designs | something that did not exist in the question |

The reported `bloom_spread` is the honest version of "was this a fair paper":
three recall questions and one design question is a distribution, not an
accident.

## Step 3: check

```bash
python scripts/syllabus_check.py --exam teaching/exam.json
```

```
questions            2
computed_points      100  (declared 100)
unmeasured_outcomes  []
bloom_spread         {"apply": 1, "evaluate": 1}
```

| Finding | Meaning |
|---|---|
| points ≠ declared total | the arithmetic students will do first |
| `unmeasured_outcomes` | the syllabus promised it and the paper does not ask |
| unknown outcome on a question | an exam wider than the course — students are being tested on something never taught |
| a question measuring no outcome | marks with no declared purpose |

## Step 4: the paper and the key

Generated in this session from the JSON: the question paper (with points per
question and the instructions), and a separate answer key with the per-question
mark scheme. Keeping the mark scheme in the same file as the question is what
makes a re-grade defensible three weeks later.

For open-ended questions and projects, the mark scheme belongs in a proper
rubric: `/rubric`.

## What this does not do

- **It does not write the questions for you unasked**, and it does not judge
  whether a question is fair, clear or at the right difficulty. Those are
  teaching judgements; the coverage is not.
- **It does not detect that two questions test the same thing.** Both would be
  bound to the same outcome, which is visible in the report but is not a finding —
  sometimes that is deliberate.
- **It does not set a passing mark.**

## Reference

- **Script:** `python scripts/syllabus_check.py --exam <file>`
- **Reads:** `teaching/exam.json`, `teaching/syllabus.json`
- **Related:** `/syllabus` (the outcomes), `/rubric` (open-ended marking),
  `/accreditation` (where these marks become evidence)

---
*A question nobody can trace to an outcome is a question nobody can defend at an objection meeting.*
