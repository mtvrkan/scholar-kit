---
name: find-dataset
description: "Find data for a research question that has none yet. Dispatches dataset-scout across HuggingFace, Kaggle, OpenML, UCI, Zenodo, PhysioNet, Dataverse and Turkish sources (TÜİK, Açık Veri Portalı, TR Dizin), reads each candidate's own licence and citation page rather than assuming, and registers the shortlist in analysis/datasets.jsonl with version, licence and citation DOI. Downloads the chosen one with approval through dataset_fetch.py — which refuses until the licence has actually been read, hashes every file as it arrives, and exits BLOCKED rather than working around a credential wall. Use when the author needs a dataset; use /analyze-data when they already have one."
disable-model-invocation: true
argument-hint: "[<task or research question>] [--verify] [--lang tr|en|both]"
---

# /find-dataset — Data for a Question That Has None

## Gate: Abort if Failed

1. **Check:** `PROJECT.md` exists and its **topic** and **RQs** are not TBD.
   - If missing or TBD: abort with "Which question is this data for? Run
     `/new-project` first — a dataset search with no research question returns
     everything and decides nothing."

2. **Check:** does the author already have data? Read PROJECT.md's *Own data* field
   and list `analysis/data/`.
   - If data is already there: say so and ask whether they want a *comparison*
     dataset (a second corpus, a baseline benchmark) or whether they meant
     `/analyze-data`. Do not search on top of an answered question.

## Procedure

### Step 1: State the constraints before searching

Ask, in one block, and do not skip it — every one of these disqualifies candidates:

```
Görev türü: (sınıflandırma | regresyon | segmentasyon | öngörü | NLP | ikincil analiz)
Modalite:   (tablo | görüntü | metin | sinyal | ses | video | çok-modlu)
En az boyut: (örnek sayısı / süre / sınıf başına örnek)
Dil / bölge kısıtı: (TR verisi gerekli mi? İngilizce yeterli mi?)
Lisans kısıtı: (ticari kullanım gerekiyor mu? türetme? yeniden dağıtım?)
Mahremiyet: (insan verisi kabul edilebilir mi? kurum onayı var mı?)
```

### Step 2: Dispatch dataset-scout

Pass the constraints verbatim, plus the RQs and the output language. The agent
searches hosts **and** the project's own `sources/registry.jsonl` — a dataset the
reviewed literature already used is one the reviewers already accept.

It returns a ranked shortlist, already registered as `DS-####` records, plus the
search narrative and any blockers.

### Step 3: Present the shortlist with the licence in the first line

```
DS-0001  CWRU Bearing Data Center · UCI · v1.0
         2 048 örnek · 12 sınıf · titreşim sinyali (12 kHz)
         Lisans: CC-BY-4.0 ✓ okundu   Atıf: 10.xxxx/yyyy
         Neden uyuyor: RQ1'in arıza sınıflandırması ile birebir; literatürdeki
                       4 kaynağınız da bunu kullanmış (EV-0012, EV-0031)
         Risk: sınıf dengesizliği 6:1; kayıt süresi kısa

DS-0002  ...
```

**Never present a dataset without its licence line.** If the licence is `unknown`,
say `Lisans: BİLİNMİYOR — izin değil` and treat it as a blocker, not a detail:
an unlicensed dataset is legally closer to all-rights-reserved than to public
domain, and a thesis built on one is a thesis with a problem at the end.

### Step 4: Download — only with approval, only what was chosen

Ask which record to use. Then fetch it **from the register**, so that what lands
on disk carries the URL, the date, the HTTP status and a digest computed as the
bytes arrived:

```bash
python scripts/dataset_fetch.py --id DS-0001 --plan            # what would happen
python scripts/dataset_fetch.py --id DS-0001 --url <direct file url> --attach
```

Two refusals to expect and to report as they are written:

- **the licence was never read** → the fetch stops. `license: unknown` is not
  permission, and a licence recorded but not verified is a different claim from a
  licence read. Read the source's own licence page, then
  `dataset_db.py set-field DS-0001 license_verified true`. This friction is the
  point: downloading is the moment the licence starts to matter;
- **the host needs credentials** (Kaggle's API token, a PhysioNet data-use
  agreement, a gated HuggingFace repo) → BLOCKED, with that host's own documented
  path. The kit does not hold credentials and will not work around a wall; the
  author downloads through their account and attaches the files.

`--extract` unpacks zip/tar with path-escape and size guards. For anything fetched
outside this command:

```bash
python scripts/dataset_db.py attach DS-0001 analysis/data/<files...>
python scripts/dataset_db.py verify --id DS-0001
```

`attach` measures the bytes — SHA-256, size, and row count for delimited files.
That measurement is what makes the methods section's "N = 2 048" a number with a
file behind it, and what lets `verify` say months later whether the data that
produced the results is still the data on disk.

### Step 5: Put it in the bibliography

A dataset is cited like any other source, through the one sanctioned path:

```bash
python scripts/doi2bib.py --doi <dataset DOI> --append bib/references.bib --json
python scripts/dataset_db.py set-field DS-0001 citation '{"doi":"…","bib_key":"…"}'
```

If the host gives no DOI, do **not** hand-write a bibliography entry. Record the
citation the host asks for in `notes`, leave `citation.doi` empty, and tell the
author that `verify` will keep reporting it as incomplete until a citable record
exists — which is the honest state, not a nuisance.

### Step 6: Record it in PROJECT.md

Set *Own data* to the register path and the chosen `DS-####`, so every later
command reads the same fact.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Veri seti kaydedildi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DS-0001 · CWRU Bearing Data Center · UCI · v1.0
  Dosyalar: 3 (toplam 41.2 MB) · SHA-256 kayıtlı
  Satır:    2 048 (ölçüldü, beyan edilmedi)
  Lisans:   CC-BY-4.0 (okundu: <url>)
  Atıf:     [@cwru1998] — references.bib'e eklendi
  Etik:     insan verisi yok · PII yok

Sonraki: /analyze-data DS-0001   veya   /experiment
```

State plainly what is still open: an unverified licence, a missing DOI, an
access application in progress. `dataset_db.py verify` will keep saying so, and
`/submit-check` reads it.

## Notes

- **Nothing here judges whether the licence permits the author's use.** The
  register records the licence and where it was read; matching it to the intended
  use (commercial? redistribution? derivative models?) is the author's call, and
  for a thesis often the institution's.
- **A famous dataset is not a licensed dataset.** Do not fill a licence field
  from memory — that is the same error class as writing a BibTeX entry from
  memory, which Invariant 2 forbids.
- **No data exists for this question** is a real outcome. Report it, and offer the
  two honest continuations: `/collect-data` (collect it yourself, with a protocol)
  or reshaping the RQ around data that does exist.

## Reference

- **Subagent:** dataset-scout (searches hosts + your own registry; no Write tool)
- **Scripts:** `python scripts/dataset_db.py` (the register's only writer) ·
  `python scripts/dataset_fetch.py` (downloads from the register, licence-gated,
  hashes on arrival) · `python scripts/doi2bib.py` (the dataset's bibliography
  entry) · `python scripts/collection_check.py --scan` (before any human-subject
  data is used)
- **Writes:** `analysis/datasets.jsonl` (through dataset_db.py), `bib/references.bib`
  (through doi2bib.py)
- **Related:** `/collect-data` (when nothing suitable exists), `/analyze-data`
  (once the data is registered), `/experiment` (training runs bound to a DS id)

---
*A dataset with no licence and no citation is not a shortcut. It is a methods section that cannot be written.*
