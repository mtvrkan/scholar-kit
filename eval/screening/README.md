# Screening accuracy — measured with your labels, or not at all

`scripts/screening_score.py` scores the kit's title/abstract include/exclude
decisions against a gold set **you** produce. No gold set ships here, and none
will: a label file written by the model whose decisions it scores measures
agreement with itself, and one written for a topic that is not yours measures
someone else's inclusion criteria.

This is the same refusal `eval/MEASUREMENT.md` records for reviewer gold labels,
applied one stage earlier in the pipeline.

## Why this layer and not the others

Of everything the model decides — screening, extraction, synthesis, drafting —
screening is the one whose errors are both consequential and **invisible**. A
study wrongly excluded at title/abstract never reaches full text, never becomes
an evidence card, and never appears in any downstream report. `cite_audit`,
`evidence_funnel` and `qa-auditor` all work on what survived; none of them can
see what did not. Only a human reading the same records can.

Drafting and synthesis are deliberately not scored here. They have no discrete
correct answer to label, and a rubric score produced by a model is not a
measurement of a model.

## Producing the gold set

1. Draw a **random, blinded** sample — not the interesting ones, not the ones
   you remember. 50 records is a reasonable pilot; the script reports counts
   only below 20 and says why.

   ```bash
   python scripts/screening_score.py --sample 50
   ```

   This writes `eval/screening/worksheet.csv` with `id, title, year, venue,
   label, reason` — and **not** the kit's decision, its exclusion reason or its
   stage. Open it in Excel or LibreOffice (it carries a BOM, so Turkish titles
   survive) and fill the `label` column with `include` or `exclude`.

   The blinding is the point. Labelling next to the answer measures your
   agreement with a suggestion, which is a known and large effect in dual
   screening — this README used to ask you not to look, and a sheet the answer
   is not on is the version that survives being in a hurry. The seed is printed
   with the sample so the same draw can be regenerated rather than quietly
   redrawn; an existing worksheet is never overwritten without `--force`.

2. Convert the filled sheet into the gold set:

   ```bash
   python scripts/screening_score.py --from-worksheet eval/screening/worksheet.csv
   ```

   Blank rows are skipped and reported, never read as exclusions: a record you
   made no judgement about has no label, and inventing one here would invent
   exactly what this layer refuses to invent. An unreadable label ("maybe") is
   refused rather than guessed.

   The result is `eval/screening/gold.jsonl`, one object per line — the format
   you can also write by hand if you prefer:

   ```json
   {"id": "SRC-0007", "label": "include"}
   {"id": "SRC-0012", "label": "exclude", "reason": "wrong population"}
   ```

   `id` may also be a `doi` or a `bib_key`. `reason` is for you; the script
   passes it through and never scores it.

3. Nothing stops you from opening the register alongside the worksheet, and no
   script can detect that you did. What the kit can refuse is the mechanical
   version — a decisions file carrying the labels — which it does.

## Running it

```bash
python scripts/screening_score.py --gold eval/screening/gold.jsonl
```

Reports recall (of the studies you would include, the share the kit kept),
precision, Cohen's κ, and the two error classes by name. It does **not** report
accuracy: at a 5–10% inclusion rate, excluding everything scores 90–95% while
finding nothing.

Read `missed_includes` first. It is the list nothing else in the kit can produce.

`gold.example.jsonl` is a five-line shape reference. It is not a gold set, it is
not scoreable, and the ids in it are fictional.
