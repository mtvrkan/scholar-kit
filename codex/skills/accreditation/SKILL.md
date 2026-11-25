---
name: accreditation
description: "Build and audit the programme outcome ↔ course outcome ↔ assessment matrix an accreditation review asks for (MÜDEK, ABET, or an institutional review that copies them): every programme outcome served by some course, every course outcome mapped to something, and every declared contribution backed by an assessment that actually produces a number. The programme's outcome list comes from your programme's own document — no MÜDEK or ABET list ships with the kit. Renders the matrix in Markdown or LaTeX."
disable-model-invocation: true
argument-hint: "[--matrix markdown|latex] [--syllabus <files...>]"
---

# /accreditation — the matrix, checked in both directions

Every accreditation review asks one question in three forms:

1. Is each **programme outcome** measured somewhere?
2. Is each **course outcome** serving something?
3. Is each **declared contribution** backed by an assessment that produces a
   number?

Departments answer with a spreadsheet filled in once, left to drift as courses
change, and repaired the week before the visit. All three questions are graph
problems, and the third is the one that fails a visit: a course claiming a level-3
contribution to `PÇ4` with nothing in its assessment scheme that measures the
outcome behind it.

## Step 1: the programme's own outcomes

```json
{
  "programme": "Elektrik-Elektronik Mühendisliği (Lisans)",
  "source_document": "Program çıktıları, Bölüm Kurulu Kararı 2026/3",
  "read_on": "2026-08-15",
  "contribution_scale": [1, 2, 3],
  "outcomes": [
    {"id": "PÇ1", "text": "Mühendislik problemlerini tanımlar, modeller ve çözer"},
    {"id": "PÇ2", "text": "Deney tasarlar, veri toplar ve sonuçları yorumlar"}
  ]
}
```

**No MÜDEK or ABET outcome list ships with this kit.** They are revised, they
differ by discipline, and your programme has adapted them — a remembered outcome
text on an accreditation form is worse than a blank one. Copy them from the
board decision or programme document your department actually approved, and
record where you got them. No file ⇒ `UNCHECKED`.

## Step 2: map in the syllabi, not in a separate sheet

The mapping lives on the course outcome in `teaching/syllabus.json`:

```json
{"id": "DÇ1", "text": "Sınıflandırma algoritmalarını uygular", "bloom": "apply",
 "programme_outcomes": [{"id": "PÇ1", "level": 3}]}
```

Keeping it there rather than in a separate matrix file is the whole point: the
sheet cannot drift from the syllabus when there is no sheet.

## Step 3: run it over every course

```bash
python scripts/outcome_matrix.py --syllabus teaching/eem402.json teaching/eem305.json
python scripts/outcome_matrix.py --syllabus teaching/*.json --matrix markdown
python scripts/outcome_matrix.py --syllabus teaching/*.json --matrix latex
```

```
| Course | PÇ1 | PÇ2 |
|---|---|---|
| EEM402 | 3 (DÇ1) | 2 (DÇ2) |
| EEM305 | 2 (DÇ1) |  |
```

The findings:

| Finding | What a reviewer does with it |
|---|---|
| `uncovered_programme_outcomes` | asks which course measures it — and there is no answer |
| a course outcome mapping to nothing | asks why the course teaches it |
| **a contribution with no assessment behind it** | asks for the evidence, and the file has none |
| a level outside the declared scale | a data-entry error that reads as carelessness |

## Step 4: the evidence, not just the map

A matrix is a claim. What a visit asks for next is the evidence behind one cell:
the exam questions that measured `DÇ1`, the marks they produced, the rubric that
graded the project.

```bash
python scripts/syllabus_check.py --syllabus teaching/eem402.json
python scripts/syllabus_check.py --exam teaching/eem402-final.json
python scripts/syllabus_check.py --rubric teaching/eem402-project-rubric.json
```

A cell whose course fails its own coverage check is a cell that will not survive
being asked about.

## What this does not do

- **It does not compute an achievement percentage.** An average of contribution
  levels is a number with no unit; producing one would make the matrix look
  measured when it is only mapped. Achievement comes from marks, and marks come
  from the assessments — which is what step 4 is for.
- **It does not rate a contribution.** Whether a course's contribution to `PÇ1`
  is a 2 or a 3 is the department's declaration.
- **It does not know the accreditation body's criteria** — only your programme's
  own outcome list, from your own document.
- **It does not fill a form.** No portal, no template, no submission.

## Reference

- **Script:** `python scripts/outcome_matrix.py [--syllabus …] [--programme]
  [--matrix markdown|latex]`
- **Reads:** `teaching/program-outcomes.json`, one or more `teaching/*.json` syllabi
- **Related:** `/syllabus`, `/exam`, `/rubric`

---
*The matrix is not the evidence. It is the index to the evidence — and a visit reads it in order to find out which cell to ask about.*
