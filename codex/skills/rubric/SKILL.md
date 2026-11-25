---
name: rubric
description: "Build an analytic rubric for a project, presentation, report or thesis assessment — criteria × performance levels, weights summing to 100 — and check the thing that makes a rubric a rubric: that the levels differ by an observable behaviour rather than by an adverb. 'Mükemmel / iyi / orta / zayıf' is a grade with extra steps, and it is reported as one. Use when marking open-ended work, or when a rubric has to be defensible at an objection meeting."
disable-model-invocation: true
argument-hint: "[<what is being assessed>] [--check]"
---

# /rubric — levels that differ by behaviour, not by adverb

Most rubrics fail the same way. Four columns headed *excellent / good / adequate
/ poor*, and four descriptors that are the same sentence with the adverb swapped:

> **Mükemmel:** Yöntem çok iyi seçilmiş.
> **İyi:** Yöntem iyi seçilmiş.
> **Zayıf:** Yöntem zayıf seçilmiş.

That is not a rubric. It is a grade with extra steps, it gives a student nothing
to act on, and at an objection meeting it cannot be defended — because "iyi" and
"çok iyi" were never distinguished anywhere.

The check strips the intensity adverbs and looks at what is left. If two levels
say the same thing, or if a level says nothing at all, that is the finding.

## Step 1: `teaching/rubric.json`

```json
{
  "title": "EEM402 dönem projesi",
  "criteria": [
    {"name": "Yöntem seçimi", "weight": 40, "outcomes": ["DÇ1"],
     "levels": [
       {"label": "3", "points": 40,
        "descriptor": "Yöntem seçimi verinin yapısıyla ve en az bir alternatifin reddiyle gerekçelendirilmiş"},
       {"label": "2", "points": 25,
        "descriptor": "Yöntem gerekçelendirilmiş ama alternatif tartışılmamış"},
       {"label": "1", "points": 10,
        "descriptor": "Yöntem gerekçesiz seçilmiş"}
     ]},
    {"name": "Sonuçların sunumu", "weight": 30, "outcomes": ["DÇ2"],
     "levels": [
       {"label": "3", "descriptor": "Şekiller eksen etiketli, ölçek birimli ve metinde yorumlanmış"},
       {"label": "1", "descriptor": "Şekillerde eksen etiketi veya birim eksik"}
     ]}
  ]
}
```

## Step 2: write a descriptor a second marker could apply

The test is not literary. It is: **could someone else, marking the same work
without talking to you, land on the same level?**

| Instead of | Write |
|---|---|
| "iyi bir literatür taraması" | "en az iki kaynağı birbiriyle konuşturur; hiçbiri yalnızca özetlenmemiş" |
| "figures are clear" | "every axis is labelled with its unit, and each figure is referred to in the text" |
| "yeterli analiz" | "varsayımlar sınanmış ve sınanmayanlar açıkça belirtilmiş" |

Each descriptor names something present or absent. That is what makes it
observable, and it is also what makes the rubric useful to the student *before*
they submit.

## Step 3: check

```bash
python scripts/syllabus_check.py --rubric teaching/rubric.json
```

| Finding | Meaning |
|---|---|
| weights ≠ 100 | the arithmetic |
| a criterion with fewer than two levels | nothing to distinguish |
| a level whose descriptor is only an adverb | "Mükemmel" describes no behaviour |
| two levels identical once adverbs are stripped | a student cannot tell which one they are in |

## Step 4: bind it to outcomes

Give each criterion its `outcomes`. A rubric criterion that serves no learning
outcome is marks with no declared purpose — the same finding `/exam` makes, and
the same one an accreditation visit makes when it asks what evidence supports
`PÇ3`.

## Notes on thesis and presentation rubrics

- **Thesis defence:** the criteria that survive an objection are the ones written
  as artefacts — "the method chapter states the sampling frame" beats "adequate
  methodology". `paper-types` skill's rubrics carry the same shape for reviewing.
- **Presentation:** timing and slide count are observable; "engaging" is not.
  Pick the observable proxy you actually mean.
- **Group work:** a rubric marking a group product cannot mark individual
  contribution. If that is the intent, it needs its own criterion with its own
  evidence, declared in advance.

## What this does not do

- **It does not judge whether the difference it finds is the right one.** Two
  levels that genuinely differ by an observable behaviour pass, even if that
  behaviour is the wrong thing to reward.
- **It does not set point values** or convert levels to marks.
- **It does not mark anything.**

## Reference

- **Script:** `python scripts/syllabus_check.py --rubric <file>`
- **Reads/writes:** `teaching/rubric.json`
- **Related:** `/syllabus` (the outcomes), `/exam`, `/accreditation`,
  `paper-types` (review rubrics, same discipline for a different reader)

---
*A rubric is defensible exactly to the extent that a second marker, given only the rubric, would grade the same work the same way.*
