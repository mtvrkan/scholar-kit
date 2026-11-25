---
name: status
description: "Print a live status report: current phase, per-section word counts vs budget, open TODOs, evidence card stats, verification status, and next recommended command. Updates drafts/STATUS.md."
disable-model-invocation: true
argument-hint: ""
---

# Project Status Report

This skill gives you a live overview of your paper/thesis progress: phase, word counts, evidence cards, citations, and next steps. The report is refreshed each time you run `/status` and written to `drafts/STATUS.md`.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim.

---

## PROCEDURE

### 1. Determine Current Phase

Read PROJECT.md and check which files exist:

```python
phases = {
  "initialized": PROJECT.md exists,
  "literature_search": sources/registry.jsonl has ≥1 entry,
  "extraction": evidence/cards.jsonl has ≥1 entry,
  "outlined": outline/outline.md exists + "**Status:** approved" present,
  "drafting": ≥1 file in drafts/*.md with >100 words,
  "verification": verify-status.json exists,
  "revision": reviews/round-*.md exists,
  "finalization": build/*.pdf or build/*.docx exists,
}

current_phase = highest phase with all preconditions met
```

Print:
```
Faz: [current_phase]
```

### 2. Count Words per Section

For each section file in `drafts/`:
```bash
python scripts/word_budget.py --json
```

Output: `{section: word_count, section_budget: limit}`

Create a table:
```
Bölüm              Sözcük      Bütçe       %       Durum
───────────────────────────────────────────────────────
Introduction       1,240       1,500       82.7%   ✓
Methods            2,150       2,000       107.5%  ⚠️ OVER
Results            1,890       2,000       94.5%   ✓
Discussion         1,200       2,500       48.0%   📝 İçi boş
Conclusion           450         800       56.3%   📝 İçi boş
Abstract/Özet        210         250       84.0%   ✓
───────────────────────────────────────────────────────
TOPLAM             7,140      10,050      71.0%
```

**Status codes:**
- ✓ OK (80–100% of budget)
- ⚠️ OVER (>100% of budget)
- 📝 SPARSE (<50% of budget)
- ⭕ EMPTY (0 words)

### 3. Find Open TODOs

Grep all draft files for markers:
```bash
grep -r "\[CITATION NEEDED\]" drafts/ | wc -l
grep -r "TODO" drafts/ | wc -l
```

Print:
```
Açık Görevler:
  [CITATION NEEDED]:  5 (Introduction:1, Results:4)
  TODO markers:       2 (Methods:1, Discussion:1)
```

Suggest:
```
⚠️ 5 alıntı eksiktir. /verify-citations çalıştırarak ve
   sonra eksik kaynakları el ile araştırarak çözün.
```

### 4. Evidence Card Statistics

Query database:
```bash
python scripts/evidence_db.py --json stats
```

Parse output: total cards, by type (finding/method/gap/quote/own-result), by RQ.

Print:
```
Kanıt Kartları: 87 toplam
  - finding:     45
  - method:      12
  - statistic:    8
  - gap:          6
  - quote:        10
  - own-result:   6

RQ Dağılımı:
  RQ1 (CNN Mimarileri):      32 kart
  RQ2 (Veri Setleri):        28 kart
  RQ3 (Baseline Karşılaştırması): 27 kart

Ortalama Güç Skoru: 3.4 / 5.0
```

### 5. Citation Status

If `verify-status.json` exists, read it (real schema written by verify-citations/SKILL.md and citation-verifier):
```json
{
  "result": "PASS|FAIL",
  "checked": 45,
  "fabricated": 0,
  "retracted": 0,
  "missing": 0,
  "unresolved": 0,
  "fixable": 1,
  "timestamp": "2024-07-02T15:30:00Z"
}
```

Print:
```
Alıntı Doğrulanması:
  Status: ✅ PASS (result=PASS)
  Özet: 45 kaynak kontrol edildi — 0 uydurma, 0 geri çekilmiş, 0 eksik, 1 düzeltilebilir
```

Or if not yet verified:
```
Alıntı Doğrulanması:
  Status: ⏳ PENDING
  Önerisi: /verify-citations çalıştırın (tüm draft'lar bitmeden sonra)
```

### 6. Outline Coverage

If `outline/outline.md` exists, parse the RQ coverage table and print:

```
İskelet Kapsamı:
  RQ1 — 12 kart, 3 bölüm tarafından ele alındı ✓
  RQ2 — 8 kart, 2 bölüm tarafından ele alındı ⚠️ sparse
  RQ3 — 5 kart, 1 bölüm tarafından ele alındı ⚠️ sparse
```

### 7. Build Status

Check if build artifacts exist:
```
Derleme Durumu:
  build/paper.pdf:        ✓ exists (2024-07-02 15:30)
  build/paper.docx:       ⭕ not started
  build/paper.tex:        ✓ exists (outdated — re-run /format)
```

Suggest re-building if files are stale (modified_date < draft_modified_date).

### 8. Compile Summary to STATUS.md

Write `drafts/STATUS.md` (≤20 lines):

```markdown
# STATUS — Makale: CNN-Based Bearing Fault Diagnosis

**Proje:** CNN-tabanlı rulman arıza teşhisi
**Tür:** Ampirik makale (IMRaD)
**Hedef Dergi:** IEEE TPAMI (SCIE Q1)
**Teslim Tarihi:** 2024-08-15

---

## Faz
**Mevcut:** Taslak aşaması (5/6 bölüm taslak, alıntı doğrulanması bekleniyor)

---

## İlerleme

| Bölüm | Sözcük | Bütçe | % | Durum |
|-------|--------|-------|---|-------|
| Introduction | 1,240 | 1,500 | 82.7% | ✓ |
| Methods | 2,150 | 2,000 | 107.5% | ⚠️ |
| Results | 1,890 | 2,000 | 94.5% | ✓ |
| Discussion | 1,200 | 2,500 | 48.0% | 📝 |
| Conclusion | 450 | 800 | 56.3% | 📝 |
| **TOPLAM** | **7,140** | **10,050** | **71.0%** | |

---

## Kanıt & Alıntılar

**Kanıt Kartları:** 87 (başlıcalar:45, yöntem:12, gap:6, kendi:6)
**RQ1 kapsamı:** 32 kart ✓
**RQ2 kapsamı:** 28 kart ✓
**RQ3 kapsamı:** 27 kart ✓

**Alıntı Doğrulanması:** ✅ PASS (45 refs, tümü kontrol edildi)
**Eksik Alıntılar:** ⚠️ 5 [CITATION NEEDED] — Resolution needed

---

## Açık Görevler

1. ⚠️ Methods bölümünü 150 sözcük kısalt
2. 📝 Discussion'ı bitir (0/1250 sözcük)
3. 📝 Conclusion'ı bitir (450/800 sözcük)
4. ✅ 5 eksik alıntı bulun ([CITATION NEEDED] markers)
5. ⭕ /critique çalıştır (Major issues = 0 olana kadar)
6. ⭕ /submit-check ile son kontrol yap

---

## Sonraki Adım

**Önerilir:** /draft discussion — tüm bölümleri tamamlamak için gerekli.

**Tahmini Zaman:** 2–3 saat (sentez + yazma)

---

*Son güncelleme: 2024-07-02 15:35:42 UTC*
```

### 9. Print to User

Display the status report:
```
╔════════════════════════════════════════════════════════════╗
║ PROJE DURUMU — CNN-Based Bearing Fault Diagnosis          ║
╚════════════════════════════════════════════════════════════╝

Faz: Taslak aşaması (5/6 bölüm tamamlandı)

SÖZCÜK SAYISI
─────────────────────────────────────────────────────────────
Bölüm              Sözcük      Bütçe       %       Durum
Introduction       1,240       1,500       82.7%   ✓
Methods            2,150       2,000       107.5%  ⚠️ OVER
Results            1,890       2,000       94.5%   ✓
Discussion         1,200       2,500       48.0%   📝
Conclusion           450         800       56.3%   📝
TOPLAM             7,140      10,050      71.0%

KANıT KARTLARI: 87 toplam
├─ RQ1: 32 kart (CNN Mimarileri)
├─ RQ2: 28 kart (Veri Setleri)
└─ RQ3: 27 kart (Baseline Karşılaştırması)

ALIINTILAMA: ✅ PASS (45 refs doğrulandı)

AÇIK GÖREVLER
─────────────────────────────────────────────────────────────
⚠️ Methods bölümü bütçeden 150 sözcük fazla
📝 Discussion bölümü tamamlanmamış (1,200/2,500)
📝 Conclusion bölümü kısaca yazıldı (450/800)
🔴 5 [CITATION NEEDED] işareti bulundu
⭕ Peer review henüz yapılmadı

SONRAKI ADIM (ÖNERİLİR)
─────────────────────────────────────────────────────────────
1. /draft discussion — tüm bölümleri tamamlamak için
2. /draft conclusion — ek (bulunmaktadır)
3. /critique — makale hakemlerce gözden geçirilecek (Major=0)
4. /submit-check — son doğrulama

Tahmini Zaman: 2–3 saat

Dosya: drafts/STATUS.md (kaydedildi)
```

### 10. Suggest Next Command

Based on phase and open tasks:

```python
if [CITATION NEEDED] count > 0:
    suggest = "1. Find missing citations; 2. /verify-citations"
elif unfinished_sections:
    suggest = f"/draft {next_section}"
elif verify_status != "PASS":
    suggest = "/verify-citations"
elif critique_issues > 0:
    suggest = "/revise"
else:
    suggest = "/submit-check"
```

Print suggestion:
```
💡 Önerilir: [suggestion]
```

---

## GATES

None. This skill always runs (it's safe and informative).

---

## SCRIPT USAGE

```bash
python scripts/word_budget.py --json
python scripts/evidence_db.py --json stats
python scripts/evidence_db.py query --type own-result
grep -r "\[CITATION NEEDED\]" drafts/
grep -r "TODO" drafts/
```

---

## OUTPUT FILE

**Location:** `drafts/STATUS.md`

**Format:** Markdown table + summary. Always ≤20 lines for quick scanning.

**Purpose:** SessionStart hook prints the first 15 lines of STATUS.md → user sees context at session start without re-reading all files.

---

## TIMING

This command is cheap: pure file reading + grep + script execution. Expected runtime: <10 seconds.

---

## FOLLOWING STEPS (Based on Status)

| Status | Next Step |
|--------|-----------|
| Phase: initialized | `/lit-review` or `/analyze-data` |
| Phase: literature_search | `/outline` |
| Phase: outlined | `/draft <section>` (for each section) |
| Phase: drafting | `/verify-citations` (when all drafts done) |
| Verify: PASS | `/critique` |
| Critique: Major=0 | `/submit-check` |
| Final | `/export-excel` (optional, for sharing) |

---

## ERROR MESSAGES (Turkish)

```
⚠️ Taslak bulunamadı. Lütfen /draft komutlarını çalıştırın.
⚠️ Kanıt kartı bulunamadı. Lütfen /lit-review veya /analyze-data çalıştırın.
ℹ️ İskelet onaylanmadı. Lütfen /outline çalıştırın ve onaylayın.
```

---

## NOTES

- `/status` is fast and safe — can be run at any time.
- It's the "checkpoint" command: run it frequently to track progress.
- The SessionStart hook auto-prints STATUS.md, so users always see the state at session start.
