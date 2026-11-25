---
name: lit-review
description: "EXECUTE a literature review now ('literatür taraması yap', 'run a review'): dispatch literature-scout to search and screen, collect user approval, loop source-analyst over approved sources, run synthesis, and optionally generate PRISMA flow diagram. --systematic adds the PRISMA counters and the reproducible search log, so a review the user merely calls 'systematic' ('sistematik olsun') belongs HERE. Use /slr instead only when the request names that pipeline's ARTEFACTS: specific databases queried one by one, PDFs downloaded and converted to markdown, per-database Excel sheets, section extraction to JSON. Gate: PROJECT.md must be complete (no TBD values)."
disable-model-invocation: true
argument-hint: "[--systematic] [--fast] [--lang tr|en|both]"
---

# Literature Review Workflow

This skill orchestrates a full literature search → screening → extraction → synthesis cycle. It dispatches subagents (literature-scout, source-analyst) and synthesizes results in the main session.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim. This is independent of **Search languages**, which governs
> which languages the literature search itself runs in.

## GATE: PROJECT.md Complete

**Check:** Read PROJECT.md. Verify NO TBD values in these fields:
- topic ✓
- rqs ✓
- type ✓
- output_language ✓
- search_languages ✓

**If any field is TBD:**
```
❌ PROJECT.md tamamlanmamış. Eksik alan(lar):
  - [field1]
  - [field2]

Lütfen /new-project çalıştırarak PROJECT.md'yi doldurun.
```
**ABORT and stop.**

---

## PROCEDURE

### 1. Parse Arguments

- `--systematic`: enable PRISMA protocol (search-log.md, flow diagram). Default: off (exploratory mode).
- `--fast`: allow parallel source-analyst runs (3–5x, cost decision). Default: sequential.
- `--lang tr|en|both`: override PROJECT.md search_languages. Default: use PROJECT.md.

Print decision to user:
```
Mode:     [systematic|exploratory]
Speed:    [sequential|fast]
Languages:[EN|TR|both]
```

### 2. Prepare Input for literature-scout

Read PROJECT.md. Compose the subagent input contract:
```
Topic: <from PROJECT.md>
RQs: <from PROJECT.md>
Inclusion criteria:
  - Year range: [offer default: last 10 years, or ask]
  - Language: <from --lang override or PROJECT.md>
  - Study types: [empirical|review|thesis|other: ask user]
  - Peer-reviewed: yes [offer choice]
  - Exclude: predatory journals [built-in]

Mode: [systematic|exploratory]
Shortlist size: 20 [default; offer custom]
Paths: sources/registry.jsonl, search-log.md
```

Ask user:
```
Araştırmaya hangi yıl aralığını dahil edelim?
(Varsayılan: 2014–2024. Giriniz veya varsayılanı kabul edin)

Hangi çalışma türleri? (birden çok seçebilirsiniz)
1) Ampirik araştırma (experimental, observational)
2) Derleme (systematic, narrative, scoping)
3) Tez (BSc/MSc/PhD)
4) Diğer

Seçiminiz: [input]
```

### 3. Dispatch literature-scout

Call the `literature-scout` agent with:
- The topic, RQs, criteria, mode, languages, and shortlist size from step 2.
- The paths: `sources/registry.jsonl`, search-log.md location.

**Expected return:**
- JSONL shortlist: ~20 records with venue_meta and relevance scores.
- Language decision + rationale (2 lines).
- Full search-log narrative (literature-scout has no Write tool) — write it to
  `sources/search-log.md` now.
- Registry stats (added count, duplicates, total in registry).

**If blocked:** print obstacle report and offer fallback (manual search, reduced scope, etc.). **Do not advance without at least 10 candidates.**

### 4. User Screening Approval

Display the shortlist to user:
```
ADAY KAYNAKLAR (20)
───────────────────────────────────────────────────────────────
[Index] [Title]        [Year] [Venue (WoS/Scopus/TR Dizin)]    [Relevance] [Action]
───────────────────────────────────────────────────────────────
  1     Deep CNN...    2023   IEEE TPAMI (SCIE Q1)             0.95        ✓
  2     Bearing fault  2022   Mech. Eng. Journal (Scopus)      0.92        ✓
  3     Signal proc.   2021   [No index found]                 0.85        ⚠
  ...
[Instructions: type "approve 1 2 3 4..." or "exclude 5 6..." or "predatory-drop"]
```

User reviews and marks:
- ✓ Include (read full-text)
- ✗ Exclude (record reason)
- ⚠ Warn if venue index is unknown or predatory flag present.

Ask user:
```
Onaylanacak kaynakları seçin (örn. "approve 1 2 3" veya "exclude 5 6"):
[input]

Şüpheli dergilerin hepsini kaldırmak ister misiniz? (tr-dizin-unknown vb.)
[evet/hayır]
```

**Record decisions via the canonical script** (never a bare "approved" status
— `registry_db.py`'s STATUSES enum is candidate/screened/included/excluded/duplicate,
matching the /slr pipeline):
```bash
python scripts/registry_db.py set-status <id> included --reason "user approved" --stage screening
python scripts/registry_db.py set-status <id> excluded --reason "<why>" --stage screening
```

Always pass `--stage screening` on an exclusion. It is what separates "the
screener dropped this" from "it passed screening and failed at full text" —
`screening_score.py` cannot recover the distinction from a final status alone,
and without it a later full-text exclusion is charged to the screening step.

**Offer the accuracy check once per project, not every run** (skip silently if
`eval/screening/gold.jsonl` already exists, and never volunteer it twice):

> Bu taramanın *sizinle ne kadar uyuştuğunu* ölçmek isterseniz: adaylardan
> rastgele ~50 kaydı **kitin kararlarına bakmadan** kendiniz eleyin
> (`eval/screening/gold.jsonl`), sonra
> `python scripts/screening_score.py --gold eval/screening/gold.jsonl`.
> Kaçırılan dahil-edilebilir çalışma, hattın hiçbir yerinde iz bırakmayan tek
> hata türü — onu yalnızca aynı kayıtları okuyan bir insan görebilir.
> Ayrıntı: `eval/screening/README.md`.

### 5. Loop source-analyst Over Included Sources

For each source with status `included`:

**If --fast flag:** dispatch 3–5 source-analyst agents in parallel (warn user: "Parallel mode may cost more tokens").

**If sequential (default):** dispatch one at a time.

**Input per source-analyst:**
- Source ID + registry entry (doi, url, pdf_path)
- RQs from PROJECT.md
- Card types: finding, method, statistic, gap, quote (default)
- Existing card IDs (for conflicts_with tagging)

**Expected return per source:**
- Card IDs created (EV-####)
- 3-sentence source appraisal (contribution, main weakness, RQ fit)
- Rigor score 1–5

**If source blocked (unreadable/paywalled):** log as `status: "unreadable"` in registry and continue.

### 6. Report Progress

After all sources processed:
```
✅ Kaynak analizi tamamlandı.

İstatistikler:
  Toplam onaylanan kaynaklar:    [N]
  Başarıyla işlenen:             [N]
  Okunabilmeyen:                 [N]
  Oluşturulan kanıt kartları:    [M] (EV-0001..EV-00M)

Sonraki: /outline komutu ile iskelet oluşturun.
```

### 7. Synthesis (in Main Session)

Now synthesis runs in the main session (this is valuable content; moving it to a subagent is wasteful).

**Load evidence cards:**
```
python scripts/evidence_db.py query > /tmp/all_cards.json
```

**Run synthesis in context:**
1. Read all cards.
2. Group by RQ tag.
3. For each RQ: identify themes (2–5 per RQ typical).
4. Build a **thematic synthesis matrix:**
   ```
   RQ1: CNN for Bearing Fault Detection
   ─────────────────────────────────────────
   Theme 1: Deep learning architectures
     - Card EV-0001: CNN layers...
     - Card EV-0015: Attention mechanisms...
     [synthesis paragraph: 2+ sources in dialog]
   
   Theme 2: Datasets & Benchmarks
     - Card EV-0003: Bearing dataset...
     - Card EV-0008: Real-world vs lab data...
     [synthesis paragraph]
   
   Conflicts:
     - EV-0012 vs EV-0025: conflicting performance claims
   
   Gaps:
     - EV-0045: No transfer learning study found on industry datasets
   ```

5. Write `literature-synthesis.md` with:
   - Full synthesis by RQ (≥2 sources per paragraph)
   - Conflict map (what findings contradict; why suspected)
   - Gaps identified (what the literature is missing = your research opportunity)

6. **Optional — check the synthesis is reproducible from its own evidence.**
   The synthesis is model-written prose bound to a fixed evidence set, which is
   the one shape that can be measured without any labels: render it a second and
   third time into separate files (the runs must not see each other), then

   ```bash
   python scripts/draft_stability.py run-1.md run-2.md run-3.md
   ```

   Disagreement about which sources are cited, which quantities are reported or
   how strongly a source is claimed means at least one rendering put something in
   the text that did not come from the cards. Offer this; do not run it by
   default — it costs N synthesis passes. Stability is not accuracy: a synthesis
   that is consistently wrong scores 1.00.

### 8. If --systematic Mode: PRISMA Diagram & Search-Log

If `--systematic` flag was used:

```
python scripts/prisma_flow.py --registry sources/registry.jsonl --out-dir outline
# writes outline/prisma.mmd (mermaid) + outline/prisma.tex (TikZ) + consistency check
```

This generates:
- PRISMA 2020 flow diagram (mermaid or TikZ)
- Counts: identified / de-duplicated / screened / excluded (with reason) / included
- Reproducibility statement

### 9. Export to Excel (Optional)

Suggest:
```
Literatür matrisini Excel'e aktarmak ister misiniz?
(Tüm kaynaklar, çıkarım tabloları, dergi kalitesi...)

/export-excel komutu çalıştırın.
```

### 10. Final Summary

Print:
```
✅ Literatür taraması tamamlandı!

Çıktılar:
  - sources/registry.jsonl: [N] kaynağın tamamı
  - evidence/cards.jsonl: [M] kanıt kartı
  - literature-synthesis.md: tematik sentez
  [if --systematic: + search-log.md + PRISMA diyagramı]

Sonraki adımlar:
  1. /outline — tez/makale iskeletini oluştur
  2. /draft <bölüm> — bölüm taslağını yaz
  3. /export-excel — matrisler için Excel'e aktar
```

---

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| PROJECT.md TBD fields | Yes | ABORT, explain which fields need filling |
| No inclusion criteria | Skipped by user | Offer defaults (year range, peer-reviewed only) |
| Scout returns 0 candidates | Yes | ABORT, ask to revise keywords or expand year range |
| Less than 5 approved sources | Yes | WARN: synthesis will be thin; suggest manual search |
| Source-analyst blocked on all | Yes | ABORT, ask for alternative PDFs or URLs |

---

## ARGUMENT DEFAULTS

```
--systematic:  false (exploratory mode by default)
--fast:        false (sequential by default; parallel costs more)
--lang:        use PROJECT.md search_languages value
```

---

## TOKEN ECONOMY NOTES

- **Scout context:** hundreds of raw hits die here. Only shortlist returns (~100 tokens).
- **Analyst loop:** sequential by default (N × ~1500 tokens); --fast = parallel (cost ↑ but speed ↑).
- **Synthesis:** stays in main session (content is the output).
- **Parallelization cost decision:** user sees `--fast` flag; document in README that it roughly 3–5x subagent costs.

---

## ERROR MESSAGES (Turkish)

```
❌ PROJECT.md eksik: [fields]. Lütfen /new-project ile doldurun.
❌ Literatür taraması 0 sonuç döndürdü. Arama kriterlerini gözden geçirin.
❌ Kaynakların tamamı okunabilmeyen. Alternatif kaynaklar veya linkler sağlayın.
⚠️ Şüpheli dergi algılandı: [venue]. Dahil etmek istiyorsanız ise "force-include" yazın.
```

---

## FOLLOWING STEPS

After lit-review completes:
- User runs `/outline` to build paper skeleton from cards.
- User runs `/draft <section>` to draft individual sections.
- User may run `/export-excel` to see literature matrix in spreadsheet form.
