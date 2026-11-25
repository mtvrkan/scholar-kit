---
name: syllabus
description: "Write a course syllabus (izlence) and check the parts that are arithmetic: assessment weights summing to 100, student workload against the course's ECTS, every learning outcome carrying a verb an examiner can observe, every outcome taught in some week and assessed by something, and the reading list resolved against the bibliography the same way a paper's references are. Use when preparing or revising a course; /exam and /rubric build on the same outcome list, /accreditation maps it to programme outcomes."
disable-model-invocation: true
argument-hint: "[<course code>] [--check]"
---

# /syllabus — the course, as data the rest can check

A syllabus is a contract with students and the input to every accreditation
question that follows. Its failures are boring and mechanical: weights that sum
to 95, an outcome nothing measures, a workload table that does not follow from
the ECTS, and outcomes written as states of mind — *"öğrenci konuyu anlar"* —
that nobody can build an exam question from.

So the course is written as data once, and the narrative document, the exam, the
rubric and the accreditation matrix are all checked against that one file.

## Step 1: `teaching/syllabus.json`

```json
{
  "course": {"code": "EEM402", "title": "Örüntü Tanıma", "ects": 6, "language": "tr"},
  "outcomes": [
    {"id": "DÇ1", "text": "Sınıflandırma algoritmalarını uygular", "bloom": "apply",
     "programme_outcomes": [{"id": "PÇ1", "level": 3}]},
    {"id": "DÇ2", "text": "Model başarımını uygun ölçütlerle değerlendirir",
     "bloom": "evaluate", "programme_outcomes": [{"id": "PÇ2", "level": 2}]}
  ],
  "weeks": [
    {"week": 1, "topic": "Giriş ve örüntü tanıma problemi", "outcomes": ["DÇ1"],
     "reading": "[@kaya2023deep]"}
  ],
  "assessment": [
    {"name": "Vize", "weight": 40, "outcomes": ["DÇ1"]},
    {"name": "Final", "weight": 60, "outcomes": ["DÇ1", "DÇ2"]}
  ],
  "workload": [
    {"activity": "Ders", "count": 14, "hours": 3},
    {"activity": "Bireysel çalışma", "count": 14, "hours": 8},
    {"activity": "Sınav", "count": 2, "hours": 10}
  ]
}
```

## Step 2: write outcomes an examiner can observe

The check reports the verb, it does not choose it. What it flags:

| Written as | Why it fails | Families that work |
|---|---|---|
| "konuyu **anlar**" · "**understands** X" | a state of mind — no question can measure it | remember · understand · apply · analyze · evaluate · create |
| "X'i **bilir**" · "is **aware of** X" | same | *tanımlar, açıklar, uygular, analiz eder, değerlendirir, tasarlar* |

If `bloom` is declared and the verb reads as a different level, both are reported
— **one of the two is what the exam will actually test**, and finding out which
during the exam is the expensive way.

## Step 3: check

```bash
python scripts/syllabus_check.py
```

| Check | The finding |
|---|---|
| Assessment weights | sum ≠ 100 |
| Coverage, both ways | an outcome nothing assesses · an assessment measuring no outcome · an outcome taught in no week |
| Workload vs ECTS | outside the Bologna range (25–30 h per credit). Set `ects_hours_per_credit` in the course object if your institution fixes one figure — then it is checked against that instead of a range |
| Week numbering | gaps |
| Readings | citation keys that are not in `bib/references.bib` |

Readings go through the same discipline as a paper's references. A reading list
assembled from memory has the same failure mode as a bibliography assembled from
memory: `/import-library` or `/lit-review` first, then cite by key.

## Step 4: the document

The JSON is the source; the syllabus students read is generated from it in this
session — course description, weekly plan table, assessment table, workload table,
outcome list, reading list. Anything the institution's own template requires that
is not in the JSON is asked for, not invented.

## What this does not do

- **It does not decide the outcomes.** Whether these are the right outcomes for
  this course is a teaching judgement.
- **It does not know your institution's ECTS rule.** The Bologna 25–30 range is a
  published standard applied as a range; one number is your institution's choice.
- **It does not convert.** A weight in points is not turned into a percentage.

## Reference

- **Script:** `python scripts/syllabus_check.py [--syllabus] [--bib]`
- **Reads/writes:** `teaching/syllabus.json`
- **Related:** `/exam` (questions against these outcomes), `/rubric`,
  `/accreditation` (these outcomes against the programme's), `/import-library`

---
*Every accreditation question is the syllabus asked backwards. Writing it as data once is what makes the backwards version answerable.*
