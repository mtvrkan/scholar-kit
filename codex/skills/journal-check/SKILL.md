---
name: journal-check
description: "Look up ONE named journal/venue (by name or ISSN) and report its index status: WoS/Scopus/TR Dizin/DOAJ, quartile, SJR, predatory flag. Use when a SPECIFIC journal is named ('is X a good journal', 'check ISSN Y'). Called with --fit and NO venue name, instead derives a candidate target-venue shortlist from the project's own reference list ('where should I submit', 'hangi dergiye gönderelim') and flags cited sources sitting in predatory or unindexed venues. For a CONCEPTUAL question about what these index classes mean (e.g. 'what is the difference between SCIE and ESCI'), use the literature-review skill instead. No gate."
disable-model-invocation: true
argument-hint: "<name|issn> | --fit"
---

# Journal/Venue Quality Check

This skill looks up journal/conference venue metadata to help you screen sources and choose submission targets.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim.

## PROCEDURE

### 1. Parse Input

User provides either:
- Journal/venue name: "IEEE Transactions on Pattern Analysis and Machine Intelligence"
- ISSN: "0162-8828"
- Conference name: "NeurIPS 2024"

### 2. Lookup via Script

Run:
```bash
python scripts/venue_check.py --title "<name>" [--json] [--offline]
```

Or if ISSN provided:
```bash
python scripts/venue_check.py --issn "<issn>" [--json]
```

**Expected output:**
```json
{
  "issn": "0162-8828",
  "title": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
  "abbrev": "IEEE TPAMI",
  "venue_meta": {
    "wos_index": "SCIE",
    "wos_class": ["Computer Science, Artificial Intelligence"],
    "scopus": true,
    "scopus_class": "Computer Science",
    "quartile": "Q1",
    "sjr": "13.2",
    "tr_dizin": false,
    "doaj": false,
    "predatory_flag": false,
    "checked_at": "2024-06-15",
    "source": "scimago"
  }
}
```

### 3. If WoS Index Unknown

If `wos_index: "unknown"`, the script will have tried Clarivate Master Journal List via cache. If still unknown:
- WebFetch the MJL search page: `mjl.clarivate.com` with the venue name
- Check if the venue appears in SCIE, SSCI, AHCI, or ESCI collections
- Update the local `sources/venues.jsonl` cache:
  ```
  python scripts/venue_check.py --title "..." --set-wos "SCIE|SSCI|AHCI|ESCI|none"
  ```

### 4. Display Venue Profile (Human-Readable)

Print to user:
```
══════════════════════════════════════════════════════════════
VENUE PROFILE: IEEE Transactions on Pattern Analysis & Machine Intelligence
──────────────────────────────────────────────────────────────

Indexing Status:
  ✓ Web of Science (SCIE)        Tier: Q1
  ✓ Scopus                        Class: Computer Science
  ✗ TR Dizin (Turkish Index)
  ✗ DOAJ (Open Access)

Quality Metrics:
  SJR: 13.2  (Impact measure)
  H-Index: 500+
  Predatory Flag: ✓ SAFE

Last Checked: June 15, 2024
Source: SCImago data

Recommendation:
  ✅ EXCELLENT TARGET
  Önerim: Yüksek kaliteli bir dergidir. Makale gönderimi için ideal.
  En yüksek titizlik standardı (Impact Factor ~13).

Last 5 Years' CiteScore: [if available]
  2023: X.X  |  2022: Y.Y  |  2021: Z.Z

Impact Factor (JCR): [if available]
  2023: A.A
```

### 5. Recommendation Logic

Based on venue_meta fields, return one of:

| Condition | Recommendation |
|-----------|---|
| WoS Q1 or Q2 + not predatory | ✅ **EXCELLENT TARGET** — This is a top-tier publication venue. High selectivity expected. |
| WoS Q3 or Q4 + not predatory | ✅ **GOOD TARGET** — Solid venue with peer review. Suitable for most research. |
| Scopus-only (not WoS) + not predatory | ✅ **ACCEPTABLE TARGET** — Peer-reviewed via Scopus. Check scope fit carefully. |
| TR Dizin (Turkey-indexed) | ✅ **GOOD FOR TR AUDIENCE** — Türkçe akademik camiaya göre saygın. |
| DOAJ open-access | ⚠️ **CAUTION** — Open-access only; verify actual review standards. Many low-quality open-access journals exist. |
| Predatory flag = true | ❌ **AVOID** — This journal shows signs of predatory practices (fabricated IF, rapid publication, email spam). Do NOT submit. |
| WoS index = "none" + checked_at recent | ⚠️ **VERIFY QUALITY** — Not indexed in major indices. Verify peer review directly on journal website. |
| No metadata found anywhere | ⚠️ **UNKNOWN** — Venue may be new, niche, or not tracked by major databases. Request user to verify on journal website. |

### 6. Additional Context

If user is sourcing literature, add:
```
USE IN LITERATURE REVIEW:
Evidence from [VENUE] venues is weighted as:
  • SCIE Q1–Q2: High credibility (weight: 1.0)
  • SCIE Q3–Q4: Moderate credibility (weight: 0.8)
  • Scopus-only: Lower weight (0.6) — verify peer review
  • TR Dizin: Credible for Turkish context (0.7–0.9)
  • Predatory: DO NOT CITE

This informs evidence card strength scoring.
```

If user is choosing submission venue, add:
```
SUBMISSION STRATEGY:
1. Check scope: Does your paper fit this journal's focus?
2. Check recent articles: Are they similar to yours?
3. Read the journal's OWN published figures (acceptance rate, time-to-first-
   decision) from its About/Statistics page. Do NOT state a rate from memory or
   infer one from the quartile — quartile measures citation impact, not
   selectivity, and a fabricated percentage is exactly the defect class this kit
   exists to prevent. If the journal publishes no figure, say it publishes none.
4. Run `/journal-check --fit` to see how many of this project's own sources this
   venue published — measured scope proximity, from the registry.
```

### 7. Cache Result

Always cache lookup to `sources/venues.jsonl` (append/update):
```json
{
  "issn": "...",
  "title": "...",
  "venue_meta": {...},
  "user_query": "<user-input>",
  "checked_at": "<ISO timestamp>"
}
```

### 8. Final Output

Print summary:
```
✅ Dergi bilgisi güncellendi: sources/venues.jsonl

Tıklayın / Kopyalayın:
  - Dergi web sitesi: [if available]
  - SCImago profil: [if available]
  - Journal Citation Reports: [if JCR link available]
```

---

## MODE B — `/journal-check --fit` (no venue named)

Answers "where does this work belong?" from the project's own register instead of
from a named journal. Runs when the user passes `--fit`, or asks where to submit
without naming a venue.

### B1. Derive the distribution

```bash
python scripts/venue_fit.py --json
```

Reads `sources/registry.jsonl` and the `venue_check.py` cache. Fetches nothing.
Counts `included` sources by default; with none yet, it falls back to `screened`
and says so in `status_note` — repeat that caveat to the user, do not drop it.

### B2. Resolve what is unknown

Every shortlist entry with `index_provenance: "unknown"` carries a
`resolve_with` command. Run it for the top entries the user cares about, then
re-run B1. Never present an unresolved venue as un-flagged: `unknown` means the
lookup never happened, not that nothing was found.

### B3. Present the shortlist

```
══════════════════════════════════════════════════════════════
HEDEF DERGİ ADAYLARI — kendi kaynak listenizden türetildi
──────────────────────────────────────────────────────────────
Sayılan kaynak: 41 / 47   ·   Farklı mekân: 22

  1. IEEE Trans. Medical Imaging      6 kaynak (%14.6)  SCIE · Q1
     en yeni 2025 · medyan 2022
  2. Medical Image Analysis           5 kaynak (%12.2)  SCIE · Q1
     en yeni 2024 · medyan 2021
  3. Computers in Biology & Medicine  4 kaynak (%9.8)   SCIE · Q2
     ...

Bu sayı NEYİ ölçer: derginin, sizin okuduğunuz literatürle konu yakınlığını.
Bu sayı NEYİ ölçmez: kabul olasılığını, dergi kalitesini, gönderim tavsiyesini.
```

Reproduce the `measures` field's both halves every time. A ranked list of
journals is read as a recommendation unless it explicitly says it is not one.

### B4. Report the concerns — the list read backwards

`concerns` holds venues **you cite** that are predatory-flagged or in no index.
This is the half of the output nobody asks for and the more actionable one:

```
⚠️ Kaynak listenizde dikkat gerektiren mekânlar:
  • Fast Publish Journal — 2 kaynak — predatory_flag
    Gönderim öncesi bu kaynakları yeniden değerlendirin.
  • Local Bulletin — 1 kaynak — hiçbir indekste görünmüyor
    Sorun kanıtı değil; bilinçli bir karar olması gerekiyor.
```

Never silently drop a flagged venue from the shortlist — that hides the fact
that the project's own literature leans on it.

### B5. What NOT to do

- Do not turn the counts into a composite "fit score". The count is auditable;
  a weighted score is not, and `POSITIONING.md` refuses it.
- Do not add journals the user's registry does not support "because they seem
  relevant". This mode reports a measured distribution; a remembered journal
  list is a different (and unverifiable) thing. If you want to suggest one, say
  plainly that it is a suggestion from general knowledge, outside the measurement.
- Do not merge or split venues by hand. Check `merged_variants`: if a reported
  merge is wrong, tell the user, do not correct the number silently.

---

## GATES

None. This skill runs without preconditions.

---

## ARGUMENT EXAMPLES

```
/journal-check "IEEE Transactions on Pattern Analysis"
/journal-check 0162-8828
/journal-check "Computer Vision and Image Understanding"
/journal-check "Mühendislik Fakültesi Dergisi"  [Turkish journal name]
/journal-check NeurIPS  [conference shorthand]
```

---

## SCRIPT USAGE

```bash
python scripts/venue_check.py --title "..." [--json] [--offline]
python scripts/venue_check.py --issn "..." [--json]
python scripts/venue_check.py --title "..." --set-wos "SCIE"  # update cache
python scripts/venue_fit.py --json [--status included] [--top 20]  # Mode B
```

---

## ERROR MESSAGES (Turkish)

```
❌ Dergi bulunamadı: "[input]". Adı veya ISSN'yi kontrol edin.
⚠️ Dergi kalitesi belirsiz. Dergi web sitesinde hakem incelemesi politikasını doğrulayın.
✅ Şüpheli dergi algılandı: "[venue]". Makale gönderimi önerilmez.
```

---

## FOLLOWING STEPS

After `/journal-check`:
- If choosing a submission target: note the venue for PROJECT.md or decision log.
- If screening sources: use the confidence score (Q-tier, Scopus/WoS status) to weight evidence cards.
- If unsure: show user the journal's website for manual verification.
