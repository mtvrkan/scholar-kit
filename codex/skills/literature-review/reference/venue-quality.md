# Journal Quality & Predatory Publisher Detection

Every source's venue (journal, conference) deserves a quality assessment before inclusion in your paper. This file explains indexing classes, quartile meanings, red flags, and how to use `venue_check.py` and `/journal-check`.

## Index Classes Explained

| Index | Coverage | Standards | Use for Inclusion? | Q1 Signals Quality? |
|-------|----------|-----------|-------------------|-------------------|
| **SCI-E** (Science Citation Index Expanded, Web of Science) | ~10,000 journals; natural sciences, engineering, medicine | Strict: peer review, citation tracking, impact factors | YES — top-tier | YES; Q1 ≈ very high quality |
| **SSCI** (Social Science Citation Index, Web of Science) | ~4,000 journals; social sciences, psychology, economics | Similar rigor to SCI-E; distinct metrics | YES — top-tier | YES; Q1 ≈ high quality |
| **AHCI** (Arts & Humanities Citation Index, Web of Science) | ~1,500 journals; history, philosophy, literature, languages | Broader scope; some emphasis on regional venues | MAYBE — discipline-dependent | Less applicable (different citation patterns) |
| **ESCI** (Emerging Sources Citation Index, Web of Science) | ~6,000+ journals; pre-qualification tier below SCI/SSCI | "Emerging" = potential future SCI/SSCI inclusion; less mature | CONDITIONALLY; evaluate rigorously | Not meaningful (newly indexed) |
| **Scopus** | ~40,000 journals; broader than Web of Science | Automated indexing; includes journals, conferences, books | YES — complementary to WoS | YES; but not as rigorous as WoS quartiles |
| **TR Dizin** | ~500 Turkish journals; all disciplines | Peer-review required; Turkish-specific impact factor | YES (for Turkish research) | YES in Turkish context |
| **DOAJ** (Directory of Open Access Journals) | ~20,000 journals; all disciplines | Open-access + peer review; community-curated | YES for open-access screening | N/A (no quartiles) |

### Quartile (Q1–Q4) Interpretation

Quartiles rank journals within their subject category by impact factor (IF) or SJR (Source-Normalized Journal Impact Factor):

- **Q1 (top 25%):** Highest impact in field; very selective; strong evidence
- **Q2 (26–50%):** High impact; selective; good evidence
- **Q3 (51–75%):** Moderate impact; lower selectivity; acceptable evidence
- **Q4 (bottom 25%):** Lowest impact; minimal selectivity; use with caution

**Rule for inclusion:** Prefer Q1–Q2 for main findings; Q3–Q4 can support, but flag in text ("emerging research suggests…").

---

## Predatory Journal Red Flags

Predatory publishers exploit the pay-to-publish model (open access) by skipping peer review or faking impact factors. **Avoid these red flags:**

### Definitive Red Flags (Automatic Exclusion)

| Red Flag | Example | Action |
|----------|---------|--------|
| **Fabricated IF claim** | Journal claims "IF 5.2" when not indexed in JCR or Scopus | Exclude; verify in JCR (only source of truth for Impact Factor) |
| **Hijacked ISSN** | Journal uses another journal's ISSN | Exclude; report to ISSN center |
| **Fake indexing claim** | Journal claims "indexed in SCI-E" but Web of Science search finds nothing | Exclude; verify via https://mjl.clarivate.com/ |
| **"International" but zero visibility** | Journal has name like "International Journal of X" with no Google Scholar results, no citations | Exclude; likely fake |
| **Spam email solicitation** | Unsolicited review/article invitations from unknown journal | Exclude; predatory marker |
| **Rapid acceptance (no review)** | Journal accepted paper 1 day after submission with no review | Exclude; review is red flag only in hindsight |

### Soft Red Flags (Manual Review Required)

| Flag | Investigation |
|------|-----------------|
| **No listed peer reviewers or editorial board** | Check journal website; real journals display editorial team. If absent, escalate. |
| **High article fees ($1,000+) with no indexing** | Legitimate OA journals charge $500–1,500; if unindexed, question value. |
| **Journals from newly-registered publisher (< 2 years old)** | New publishers exist (legitimate); cross-check with DOAJ, Scopus, WoS. |
| **Unrealistic turnaround (<2 weeks to publication)** | Peer review takes time; check if review actually happened. |
| **Generic names** | "International Journal of Science" (vs. "Journal of Chemical Physics"). Generic names common in predatory lists. Check Beall's list or DOAJ. |

---

## How to Check a Venue

### Method 1: `venue_check.py` (Local Lookup)

Execute (don't read):
```bash
python scripts/venue_check.py --issn 1234-5678 [--cache sources/venues.jsonl]
python scripts/venue_check.py --title "Mechanical Systems and Signal Processing" [--cache sources/venues.jsonl]
```

Returns JSON object with:
```json
{
  "issn": "1234-5678",
  "title": "Mechanical Systems and Signal Processing",
  "wos_index": "SCIE",
  "scopus": true,
  "tr_dizin": false,
  "quartile": "Q1",
  "sjr": 2.456,
  "predatory_flag": false,
  "checked_at": "2024-01-15T10:30:00Z"
}
```

**Caching:** Results are cached for 30 days in `sources/venues.jsonl` to avoid redundant lookups.

### Method 2: `/journal-check` (User-Facing Command)

```
/journal-check "Mechanical Systems and Signal Processing"
/journal-check 0888-3270
```

Returns a human-readable report:
```
Mechanical Systems and Signal Processing
  Index Status:     SCI-E ✓ · Scopus ✓
  Quartile:         Q1 (Top 25% in category)
  Impact Factor:    7.32 (JCR 2022)
  SJR:              2.456
  TR Dizin:         No
  Predatory Flag:   No
  Last Checked:     2024-01-15
  
  Recommendation:   Excellent target venue for engineering research.
```

### Method 3: Manual Verification (if local lookup returns "unknown")

When `venue_check.py` can't find a venue (new journal, rare journal), the scout agent may WebFetch:
- **Clarivate Master Journal List** (mjl.clarivate.com) — authoritative for WoS
- **Scopus source list** — authoritative for Scopus
- **DOAJ** — open-access journals

And record via:
```bash
python scripts/venue_check.py --issn 1234-5678 --set-wos SCIE --cache sources/venues.jsonl
```

This stores the finding locally for future use.

---

## Venue Quality & Inclusion Decisions

### Tier-1 Venues (Always Include, High Weight)

- SCI-E Q1–Q2 (any field)
- SSCI Q1–Q2 (for social sciences)
- AHCI (humanities)
- Top Scopus (h-index >100)
- TR Dizin with IF >2

**Use in Introduction (motivation) and Results/Discussion (evidence for claims).** Treat findings as high-quality.

### Tier-2 Venues (Include, Medium Weight)

- SCI-E Q3, SSCI Q3
- Scopus-only (not in WoS)
- TR Dizin IF <2, but peer-reviewed
- Reputable conferences (IEEE, ACM, top domain-specific)

**Use in Methods and Discussion; support (not lead) claims.** Findings valid but may need cross-validation.

### Tier-3 Venues (Include with Caution, Lower Weight)

- SCI-E Q4
- ESCI (pre-qualification tier)
- DOAJ open-access journals
- DergiPark Turkish journals (if peer-reviewed)
- Preprints (arXiv, bioRxiv) — cite only methods/data, not findings

**Use for background, methodological detail, or emerging findings.** Always hedge: "Preliminary evidence suggests…"

### Tier-4 Venues (Exclude or Note Heavily)

- Journals on Beall's predatory list (historic; list discontinued in 2017, but entries remain useful)
- Venues with red flags (fabricated IF, hijacked ISSN, no peer review)
- Non-peer-reviewed outlets (blogs, institutional reports without review)
- Theses (unpublished; include as data source, not evidence for claims)

**Exclude from bibliography entirely, unless there's no alternative. If forced to include, use `note: "Unpublished thesis; findings not peer-reviewed."`**

---

## Turkish Venue Specifics

### TR Dizin Quality
- High-quality indexed journals (IF >2) are competitive; findings can support main claims.
- Medium-quality journals (TR Dizin, IF <2) are regional; use for context and Turkish-specific findings.
- DergiPark open-access: check peer-review process and editorial board; quality varies.

### International Venues by Turkish Authors
- Turkish authors publishing in SCI-E Q1 journals: treat as high-quality (author selection, not venue) — same weight as any Q1 journal.
- Turkish theses from top universities (Boğaziçi, METU, Istanbul Tech): high methodological rigor; cite for methods, not findings.
- Turkish journals with bilingual abstracts (Turkish article, English abstract): always prefer DOI version if exists; record TR venue in `lang: "tr"`.

---

## Marking Venue Quality in the Registry

In `sources/registry.jsonl`, every source should have:

```json
{
  "id": "SRC-0042",
  "title": "...",
  "venue": "Mechanical Systems and Signal Processing",
  "venue_meta": {
    "issn": "0888-3270",
    "wos_index": "SCIE",
    "scopus": true,
    "quartile": "Q1",
    "sjr": 2.456,
    "tr_dizin": false,
    "predatory_flag": false,
    "checked_at": "2024-01-15T10:30:00Z"
  }
}
```

This metadata feeds:
- Screening decisions (high-quality venues → higher inclusion priority)
- Evidence strength (Q1 finding → Strength 5; ESCI finding → Strength 2)
- Export reports (venue sheet in Excel export)

---

## Common Mistakes (Avoid These)

| Mistake | Fix |
|---------|-----|
| Citing impact factor from journal website | Use **only** JCR (Journal Citation Reports) as source of truth for IF; publishers sometimes inflate |
| Assuming high Scopus h-index = high quality | h-index is cumulative; old journals accumulate high scores. Cross-check quartile. |
| Including a paper just because it's open-access | Open-access ≠ quality. Use DOAJ + peer-review check; some OA venues are predatory. |
| Trusting journal name alone | "International Journal of X" could be predatory. Verify index status. |
| Ignoring Turkish venue quality | TR Dizin Q1–Q2 journals are quality venues; don't automatically downweight them vs. English-language equivalents. |
| No venue quality check in registry | Always run `venue_check.py` for every source; it takes 1 minute and catches red flags. |

---

## See Also

- **`venue_check.py`** — execute to populate venue metadata
- **JCR (Journal Citation Reports):** https://jcr.clarivate.com — authority for Impact Factor
- **Scopus Source List:** https://www.scopus.com/sources.uri (downloadable)
- **DOAJ:** https://doaj.org — directory of quality open-access journals
- **Beall's List (historical):** https://beallslist.net — predatory publisher archive
- **Web of Science Master Journal List:** https://mjl.clarivate.com
