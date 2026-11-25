# Bilingual Search Strategy — EN/TR Dual-Matrix Discipline

## The Decision Matrix: When to Search EN, TR, or Both

| Topic Type | Trigger | Search Strategy | Expected Yield |
|---|---|---|---|
| **International scientific** (ML, climate, COVID, physics) | Topic exists in global literature; venue availability test shows abundant SCI-E/Scopus | EN primary; TR optional for background | 80%+ EN, <20% TR (if any) |
| **Turkey-local phenomena** (Turkish education system, TR policy, Turkish NLP) | Topic-locality test triggers: "is this specific to Turkey/Turkish?" | EN + TR mandatory; TR Dizin + DergiPark required | 60–40% split or heavier TR |
| **Turkish language/literature** (Turkish dialect, Ö zmir poetry, 19th-century Ottoman) | Topic is inherently Turkish | EN + TR; specialized Turkish literature databases | Heavy TR weighting |
| **Comparative (e.g., education policy: TR vs EU)** | Multiple regions in RQ | EN primary for international + EU literature; TR mandatory for Turkish case | EN majority + targeted TR for TR component |
| **Bilingual papers on international topics** | Paper is *written in Turkish* but addresses international topic (e.g., COVID-19 pandemic in Turkey) | EN for international evidence; TR for Turkish-context findings | 70%+ EN + 30%+ TR for context |

**Rule: Always build both EN and TR keyword matrices** — matrix-building is
cheap (it's a planning table, not a search) and surfaces gaps even when one
language will dominate. This is unconditional and independent of the
*execution* decision below.

**Execution is a separate, overridable decision.** PROJECT.md's `search
languages` field (or `/lit-review --lang`, or `/slr`'s per-topic call) sets
which language(s) are actually **searched** — this may legitimately be
EN-only or TR-only. literature-scout still builds both matrices per the rule
above, but may search only the configured language(s); if it judges the
configured choice wrong for a specific topic (e.g. user set `en` but the
topic-locality test below says TR is mandatory), it may deviate — but MUST
log the deviation and the one-line rationale (see literature-scout.md's
LANGUAGE DECISION step). Silent scope-narrowing is never acceptable; a
logged, reasoned override is.

## Keyword Matrix Template

```
Concept 1: [concept name]
  EN: term1, term2, variant1, variant2, broader term, narrower term
  TR: terim1, terim2, varyant1, varyant2, geniş terim, dar terim

Concept 2: [concept name]
  EN: …
  TR: …

Concept 3 (Context): [context name]
  EN: …
  TR: …
```

### Example: Bearing Fault Diagnosis

```
Concept 1: Detection Methods
  EN: deep learning, convolutional neural network, CNN, autoencoder, LSTM, 
      recurrent neural network, machine learning, anomaly detection, 
      signal processing, wavelet, Fourier transform
  TR: derin öğrenme, evrişimli sinir ağı, otokoder, sinir ağı, makine 
      öğrenmesi, anormallik tespiti, sinyal işleme, dalgacık dönüşümü

Concept 2: Bearing Types / Faults
  EN: bearing fault, rolling-element bearing, ball bearing, roller bearing, 
      inner race fault, outer race fault, cage fault, failure mode, 
      degradation, remaining useful life, RUL
  TR: rulman arızası, yuvarlanmalı rulman, top rulman, makara, iç ring arızası, 
      dış ring arızası, hasar modu, bozulma, kalan yaşam ömrü

Concept 3: Application Context
  EN: condition monitoring, predictive maintenance, IoT, industrial, 
      vibration analysis, acoustic emission, health monitoring
  TR: durumsal izleme, öngörülü bakım, IoT, endüstriyel, titreşim analizi, 
      akustik emisyon, sağlık izleme
```

## Transliteration Pitfalls (Common Errors)

| Mistake | Example | Rule |
|---------|---------|------|
| Romanizing Turkish names in EN search | Searching "Sezai Kaya" when author publishes in TR as "Sezai Kaya" | Never romanize author names; use exact spelling |
| Missing diacritics (ç, ğ, ı, ö, ş, ü) | Searching "basit" (simple) instead of "baskı" (press) | Diacritics change meaning; include them if database supports |
| Over-romanizing institutional names | Searching "Tubitak" instead of "TÜBITAK" | Use official acronyms/transliterations: TÜBITAK, TÜİK, YÖK |
| Assuming "Mimar Sinan" is the same as "Sinan, Mimar" | Author order varies EN vs TR | Check both orders; some Turkish journals use "Surname, Given" in EN abstracts |
| Translating author names into EN | Searching "John Smith" when Turkish author publishes as "Yusuf Yılmaz" | Never translate; use original name exactly |

## De-Duplication Rules (For Multilingual Result Sets)

When you search both EN and TR, the same paper will appear twice. De-duplicate via:

### Step 1: DOI-First Match (Highest Confidence)

If both results have a DOI, normalize to lowercase and compare:
```
  Result 1: doi = 10.1234/example
  Result 2: doi = 10.1234/example  ← MATCH → merge, keep EN version (usually has full metadata)
```

Exit 0 on DOI match; they are the same paper. Dedup on DOI is definitive.

### Step 2: Title-Normalized Match (If No DOI)

Normalize both titles (whitespace collapse, diacritic removal, case-insensitive) and compute similarity:
```
  Title 1: "Deep Learning for Bearing Fault Diagnosis"
  Title 2: "Rulman Arızası Teşhisinde Derin Öğrenme"
  
  Normalized title 1: "deeplearningforbearingfaultdiagnosis"
  Normalized title 2: "rulmanarızasıtesişisindederenoğrenme"
  
  Similarity check: these are translations, not duplicates. Keep both.
```

Normalized-title similarity only works for:
- Literal translations (English title + Turkish title of same paper)
- Very minor wording differences in same language (e.g., "A Study of X" vs "Studying X")

**Threshold: ≥95% similarity on normalized title + same authors (first author match) + same year = duplicate. Merge, keep higher-quality version (prefer DOI'd entry, prefer EN if quality is equal).**

### Step 3: Author + Year Overlap (If Ambiguous)

If two results have:
- Same first author
- Same publication year (within 1)
- Similar title (≥70% similarity after normalization)
- Different but related languages (EN and TR)

→ **Likely the same paper translated / published in both languages. Merge.**

Keep:
- The entry with a DOI (if one has it)
- The entry with higher venue quality (SCI-E > Scopus > TR Dizin > no index)
- The EN version (larger metadata, more complete abstract)

### Step 4: Language Diversity Check

After dedup, check: Did I drop important TR-only papers? Re-review the "likely duplicate" list. If a paper is in TR Dizin and nowhere else, it may be a genuine Turkish contribution (not a translated international paper). Keep it.

## Multi-Database Search Strategy

### Database Selection by Topic

| Topic | Primary DB | Secondary | Tertiary |
|---|---|---|---|
| **ML / Computer Science** | Semantic Scholar, arXiv | Google Scholar, DBLP | IEEE Xplore, ACM DL |
| **Biomedical / Health** | PubMed, PubMed Central | Scopus, Web of Science | EMBASE, ProQuest |
| **Engineering / Physics** | IEEE Xplore, arXiv | Scopus, Google Scholar | DBLP (if computation-heavy) |
| **Social Sciences / Psychology** | PsycINFO, ERIC | Google Scholar, ProQuest | Scopus, JSTOR |
| **General academic** | Google Scholar (start here, often fastest) | Crossref, OpenAlex | Institution library proxy |

### Turkish-Specific Additions

Always add (in addition to above):
- **TR Dizin** (site-scoped WebSearch)
- **DergiPark** (site-scoped WebSearch; many open-access)
- **YÖK Thesis Center** (for thesis content)

## Search Query Formulation

### Boolean Operators (Database-Dependent)

Most academic databases support:
- **AND:** both terms required (narrow results). `bearing AND fault`
- **OR:** either term (broad results). `CNN OR "convolutional neural network"`
- **NOT:** exclude term (refine). `bearing NOT ball-bearing` (exclude ball bearings, study only roller)
- **Phrase search:** `"deep learning"` (exact string, not separate words)
- **Truncation:** `fault*` matches `fault`, `faults`, `faulty` (varies by DB)
- **Nested:** `(deep OR machine) AND (learning OR inference)`

### Example Queries (per Database)

**Semantic Scholar / Google Scholar:**
```
deep learning bearing fault diagnosis
CNN vibration analysis
```
(Simple natural language; databases do keyword extraction)

**PubMed (medical/health):**
```
("deep learning" OR CNN) AND (bearing fault* OR fault diagnosis)
```

**IEEE Xplore:**
```
("Deep Learning" OR CNN OR RNN) AND ("Bearing Fault" OR "Fault Diagnosis" OR "Condition Monitoring")
```

**TR Dizin (site-scoped web search):**
```
site:trdizin.gov.tr "derin öğrenme" "rulman arızası"
site:trdizin.gov.tr "teşhis" "titreşim"
```

**DergiPark:**
```
site:dergipark.org.tr "derin öğrenme" rulman
site:dergipark.org.tr anomali tespiti
```

## Documenting Searches (for Systematic Reviews)

Create a **search-log.md** file:

```markdown
# Search Log — [Project Title]

## EN Search Strategy

### Semantic Scholar
- Query: "deep learning bearing fault diagnosis"
- Date: 2024-01-15
- Filters: peer-reviewed, 2015–present
- Results: 1,247
- Noted: high noise (bearing in geological sense, etc.)

### IEEE Xplore
- Query: ("Deep Learning" OR CNN) AND ("Bearing Fault" OR "Condition Monitoring")
- Date: 2024-01-15
- Filters: conferences + journals, 2015–present
- Results: 234
- Noted: strong signal; 80% relevant in first 50

### arXiv
- Query: deep learning fault diagnosis
- Date: 2024-01-15
- Results: 156
- Noted: preprints; many not in other databases yet

## TR Search Strategy

### TR Dizin
- Query: site:trdizin.gov.tr "derin öğrenme" "rulman arızası"
- Date: 2024-01-15
- Results: 23
- Noted: lower volume; quality varies

### DergiPark
- Query: site:dergipark.org.tr "derin öğrenme" anomali
- Date: 2024-01-15
- Results: 47
- Noted: open-access; some low-impact journals

### YÖK Thesis Center
- Query: site:tez.yok.gov.tr "derin öğrenme" OR "makine öğrenmesi" rulman
- Date: 2024-01-15
- Results: 12 theses
- Noted: recent MSc/PhD work; full texts available

## De-duplication Results
- Total raw hits: 1,719
- After DOI-based dedup: 1,450
- After title-normalized dedup: 1,380
- Final candidate set: 1,380
```

---

## Language Tag in Registry/Cards

In `sources/registry.jsonl`, every entry includes `lang: "en" | "tr"`.

In synthesis and discussion, note:
- "These findings are consistent across EN and TR literature…"
- "Interestingly, this technique is studied primarily in Turkish-language theses; I found only one SCI-E publication…"
- "The following finding appears only in TR sources (translated title: '…')…"

This transparency is part of bilingual research discipline.
