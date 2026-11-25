---
name: replication-package
description: "Assemble the deposit-ready replication package a journal asks for — code, figures, tables, the dataset and run registers, an environment file, a checksum manifest and a generated README — from records this project already holds. Data that must not be redistributed (human subjects, personal data, a restrictive licence) is named with its access route rather than copied. Also produces the data/code availability statement, derived rather than templated. Use before submission or on an editor's request."
disable-model-invocation: true
argument-hint: "[--build] [--deposit zenodo|osf|institutional]"
---

# /replication-package — What You Deposit, Assembled From What You Recorded

The usual replication package is a zip of whatever was on the desktop: three
scripts, a CSV, no environment, no run order, and a README written the night
before submission. Everything a good package needs is already in this project.

## Gate

1. `analysis/` exists, or `analysis/datasets.jsonl` does. Otherwise there is no
   analysis to package — say so and stop.
2. Recommend `dataset_db.py verify` and `experiment_db.py verify` first: a
   package built on data that drifted, or runs with no environment, is a package
   whose README will have to say so.

## Step 1: Plan before building

```bash
python scripts/replication_pack.py
```

Lists what would go in — code, figures, tables, registers — what would be
*referenced but not copied*, and the gaps. Show this to the author before writing
anything: the exclusions are the part they need to agree with.

## Step 2: What is excluded, and why it is not negotiable

The script never copies data whose record says human subjects, personal data, or
a licence that forbids redistribution. Do not offer to override it. A package is
public the moment it is deposited, and a DOI makes a data-protection incident
permanent. What goes in instead is the access route: the dataset's DOI, its
licence, its host, and — for restricted data — what a reader has to do to get it.

If the author believes an exclusion is wrong, the fix is the **record**: correct
the licence in `dataset_db.py` (with the URL it was read at), or the ethics
fields. Not a flag on this command.

## Step 3: Build

```bash
python scripts/replication_pack.py --build
```

Writes `exports/replication/`: the code, the figures and tables, `runs.jsonl`,
`datasets.jsonl`, `ENVIRONMENT.json`, `MANIFEST.json` (SHA-256 of every included
file, plus the checksums of the data files that were *not* included), and a
`README.md` generated from the registers — including a "what this package does
not establish" section when there are gaps.

## Step 4: The availability statement

```bash
python scripts/compliance_gen.py availability
```

Derived from the same registers. A dataset with no citation DOI or no recorded
licence produces **no sentence**, and you must not write one for it either — see
`/submission-pack` step 3 for why "available on request" is the sentence to avoid.

## Step 5: Depositing

The kit does not upload anything. Tell the author what to do, in their own
choice of archive:

- **Zenodo**: new upload → attach `exports/replication/` → the DOI it mints goes
  into the paper's availability statement, and the concept DOI (not the version
  DOI) is the one to cite.
- **OSF**: a component under the project, with the same files.
- **Institutional repository**: usually required for a thesis in Türkiye; check
  the institute's own deposit rules for embargo options.

After the DOI exists, record it and re-run the availability statement so the
paper's sentence names the archive rather than a promise.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Replikasyon paketi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Kod:      6 dosya · Şekil/tablo: 11 · Künye: references.bib
Kayıtlar: 24 koşu (5 tohum) · 2 veri seti · 1 ortam parmak izi
Manifest: 19 dosya SHA-256 · dahil edilmeyen 3 veri dosyasının özeti de içeride

Dahil edilmeyen: DS-0002 — insan verisi (etik kurul 2026/117); erişim yolu README'de

Eksikler: (varsa her biri tek satır, README'ye de yazıldı)
```

## Reference

- **Scripts:** `python scripts/replication_pack.py` ·
  `python scripts/compliance_gen.py availability` · `dataset_db.py verify` ·
  `experiment_db.py verify`
- **Writes:** `exports/replication/`
- **Related:** `/experiment` (what fills the run register), `/find-dataset`,
  `/submission-pack`, `/preregister`

---
*A replication package is a claim about what someone else can redo. This one states exactly how much of that claim is backed by a record.*
