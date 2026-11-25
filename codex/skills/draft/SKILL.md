---
name: draft
description: "Draft a single section by loading outline slice, querying section's evidence cards, drafting in main session, running style-auditor, and applying safe fixes. Gate: outline must be approved."
disable-model-invocation: true
argument-hint: "<section>"
---

# Draft a Section

This skill drafts a single section (Introduction, Methods, Results, Discussion, Conclusion, etc.). The draft binds every empirical claim to evidence cards, and runs style audit before finalizing.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim. This is independent of **Output language**, which governs
> the drafted manuscript prose itself, not these gate/status messages.

## GATE: Outline Must Be Approved

**Check:** Read `outline/outline.md` header.
```
if "**Status:** approved" not in header:   # /outline writes this exact bullet on approval
    ABORT with:
      "❌ İskelet henüz onaylanmadı.
       Lütfen /outline komutunu çalıştırarak ve 'evet' yazarak onaylayın."
```

**If gate passes:** continue.

---

## PROCEDURE

### 1. Parse Section Argument

User provides section name (case-insensitive):
- `introduction` / `intro` / `background`
- `methods` / `methodology`
- `results`
- `discussion`
- `conclusion` / `concluding-remarks`
- `abstract` / `özet`
- `literature-review` / `lit-review`
- `related-work`

Normalize to canonical heading name from `outline/outline.md`.

**If section not found:** print options:
```
❌ Bölüm "[input]" bulunamadı.

Kullanılabilir bölümler:
  - introduction
  - methods
  - results
  - discussion
  - conclusion

Lütfen bölüm adını girin: /draft methods
```

### 2. Load Outline Slice

Query `outline/outline.md` for the chosen section. Extract:
- Full heading hierarchy (e.g., "I. Introduction", "I.1. Background", "I.2. Existing Work")
- RQ tags from HTML comments (e.g., `<!-- RQ: rq1, rq2 | Cards: EV-0001... -->`)
- Card IDs bound to this section

Example extraction:
```
Section: Introduction
Headings: I, I.1, I.2, I.3, I.4, I.5
RQ Tags: background, rq1, rq2, rq3
Card IDs: EV-0001, EV-0002, EV-0003, EV-0010, EV-0011, ...
```

### 3. Query Evidence Cards

For each RQ tag in the section, query cards:

```bash
python scripts/evidence_db.py query --tags "rq1" --min-strength 3
```

Load all returned cards into context (typically 5–15 per section). Extract:
- Claim (1 sentence)
- Detail (2–4 sentences, justification)
- Page (for quotes)
- Verbatim (if quote)
- Metrics (if quantitative finding)
- Source key (bib_key for citation)

**Print progress:**
```
✅ Bölüm kartları yüklendi: [N] kanıt kartı
   Örneğin: EV-0001 (strength: 4), EV-0002 (strength: 3), ...
```

### 4. Draft in Main Session

Now draft the section using the outline as skeleton and cards as evidence. Each sub-heading gets:

**Sub-heading text:** typically 3–6 paragraphs.

**Paragraph structure (from academic-writing skill):**
- **Sentence 1:** Claim / topic sentence
- **Sentence 2–3:** Evidence (cite card[s] via [@bib_key]) + detail from card
- **Sentence 4:** Interpretation / connection to RQ
- **Sentence 5:** Bridge to next paragraph or idea

**Citation discipline:**
- For every empirical claim: bind to a card ID via HTML comment after the sentence.
  ```
  Example: "CNNs have shown 95% accuracy on bearing fault detection [@Li2022DeepLearning]."
           <!-- EV-0045 -->
  ```
- For uncardable claims (general background, your own reasoning): tag `[CITATION NEEDED]`.
  ```
  Example: "Bearing fault detection is critical for industrial safety. [CITATION NEEDED]"
  ```

**Knowledge isolation — the three tags are not interchangeable:**

Write factual content from the session's materials (evidence cards, `analysis/`
outputs, PROJECT.md, user-supplied text), not from model memory. This restricts
FACTUAL CONTENT only — claims, numbers, citations, procedures. Academic
conventions, argument structure, register and phrasing are yours to supply
freely; that is the writing, not the evidence.

| Tag | When | Blocks finalization |
|---|---|---|
| `[CITATION NEEDED]` | the claim is sound, a source for it isn't attached yet | yes |
| `[MATERIAL GAP]` | the outline needs content **no session material covers** | yes |
| `[LLM-SUPPLEMENTED]` | the user explicitly authorized filling a gap from model knowledge | no — reported |

When the outline calls for something the materials do not cover, tag
`[MATERIAL GAP]` and move on. **Do not fill it from memory**, and do not quietly
soften the outline to avoid the hole — a plausible invented sentence is
indistinguishable from a sourced one once written, which is precisely why the
gap has to be marked at writing time rather than discovered later.

Surface every gap at the end of the section (Step 6 already reports counts). The
user then either supplies material, or authorizes a fill — in which case replace
the tag with `[LLM-SUPPLEMENTED]` so the decision leaves a trace. An authorized
fill that leaves no trace is indistinguishable from an unauthorized one.

`cite_audit.py` counts all three; `[LLM-SUPPLEMENTED]` is reported and never
blocks. Turkish drafts may use `[KANIT YOK]` and `[MODEL BİLGİSİ]` — both are
recognized.

**Tense discipline (per section):**
- **Introduction:** present tense (literature facts), past tense (prior work)
- **Methods:** past tense (what you did)
- **Results:** past tense (what was found)
- **Discussion:** present/past mixed (interpret findings, position vs literature)
- **Conclusion:** present tense (implications, future)

**Hedging examples (from academic-writing skill):**
```
Strong: "X demonstrates..." / "X shows..." (experimental findings, high confidence)
Moderate: "X indicates..." / "X suggests..." (multiple studies, convergent evidence)
Weak: "X may suggest..." / "X may imply..." (single study, preliminary)
```

### 4a. Methods-Specific Completeness Check (Methods/Methodology Only)

Every other section drafts adequately from outline-skeleton + bound cards alone
— Methods does not. A thin card set produces a thin Methods ("we trained four
models" and nothing else), and the generic GATES SUMMARY warning ("no cards →
synthesis-only, continue if user agrees") is not strong enough for a section
whose whole job is enabling replication. Before drafting Methods prose, work
through this checklist and draft to fill every applicable row — most rows are
answerable from your own analysis scripts/RUNLOG.md (own-data studies) or from
the bound method-type cards (literature-derived methodology), not from new
research:

| Checklist item | Source to check | If missing |
|---|---|---|
| **Design** — experimental / observational / quasi-experimental / simulation / secondary-analysis, stated explicitly | Outline + PROJECT.md Type | Ask the user; do not infer silently |
| **Data/participants** — N, source, inclusion/exclusion criteria, missingness handling | `analysis/RUNLOG.md`, own-result cards, PROJECT.md "Own data" | If a data-scientist ran the analysis, this MUST already be recorded — pull it, don't re-derive |
| **Measures/variables** — what each variable is, how it was operationalized/encoded | `analysis/*.py` scripts, method-type cards | Flag as a gap; do not guess an encoding scheme |
| **Procedure** — exact steps in the order performed (preprocessing → split → train → evaluate) | `analysis/*.py` filenames/order, RUNLOG.md | Reconstruct from script order; note if scripts are missing |
| **Analysis plan / statistical tests** — which test, why it fits the data/hypothesis, assumptions checked | data-scientist's numeric-results digest (Statistics discipline step) | If the data-scientist agent did not report this, ask it to before drafting, rather than writing the test name from memory |
| **Reproducibility** — seeds, package versions, hyperparameters, code/data availability | `analysis/RUNLOG.md` (data-scientist writes this every run) | Missing RUNLOG.md for an own-data study is a real gap — flag it, do not draft "results are reproducible" without the seed/version record backing it |

For deeper guidance on any row, consult (read only the rows you need, not the
whole file): `.claude/skills/ml-research/reference/experiment-design.md`
(design + analysis-plan guidance) and `reference/reproducibility.md`
(reproducibility checklist detail). For a second opinion on whether the Methods
design fits the stated RQs/hypotheses, dispatch `methodology-advisor` (read-only,
opus) — it is not normally in the `/draft` dispatch chain, so do this explicitly
when the design is non-trivial or you're unsure a test/split choice is
defensible, not by default for a routine comparison.

If a checklist row is genuinely inapplicable to this study (e.g. "participants"
for a synthetic-data simulation), say so explicitly in a code comment in the
draft rather than silently omitting the row — a reviewer should see it was
considered, not guess whether it was missed.

**Example draft section (Introduction):**

```markdown
## I. Introduction
<!-- RQ: background, rq1, rq2, rq3 | Cards: EV-0001, EV-0002, EV-0010, EV-0011 -->

### I.1. Background

Bearing components are among the most critical elements in rotating machinery, and their failure can cascade into catastrophic system shutdowns. Condition-based maintenance strategies rely on early fault detection to prevent unplanned downtime. <!-- EV-0001 -->
<!-- EV-0001: "Bearing failure costs industry $X billion annually..." -->

Modern approaches to bearing fault diagnosis employ signal processing and machine learning techniques. Traditional methods such as Fourier transform analysis and envelope analysis have been widely adopted. <!-- EV-0002 -->
<!-- EV-0002: Method card citing classical papers -->

### I.2. Existing Work

Deep learning has emerged as a powerful paradigm for time-series anomaly detection. [@Li2022DeepLearning] demonstrates that convolutional neural networks (CNNs) can outperform classical baselines on bearing fault datasets, achieving 94–97% accuracy across multiple benchmarks.
<!-- EV-0010 -->

However, questions remain about generalization to real industrial settings, where data distributions shift and labeled examples are scarce. [@Chen2023TransferLearning] suggests that transfer learning can address this gap, though validation remains limited.
<!-- EV-0011 -->

### I.3. Research Gap

Existing work has not comprehensively compared CNN architectures under realistic conditions: noisy, imbalanced, multi-bearing datasets typical of industrial deployments. [CITATION NEEDED] Furthermore, reproducibility concerns persist: most published models lack code availability statements or environment specifications.

### I.4. Research Questions

This work addresses three interconnected questions:
1. Which CNN architectures are most robust to noise and class imbalance in bearing fault diagnosis?
2. What datasets are available for benchmarking, and do they represent real-world scenarios?
3. How does CNN performance compare to signal-processing baselines under fair comparison protocols?

### I.5. Contribution

This article provides: (1) a systematic comparison of 5 CNN architectures on 3 public bearing datasets; (2) ablation studies isolating the impact of architecture components; (3) code and trained models for reproducibility.

The rest of this paper is organized as follows...
```

### 5. Run Style-Auditor (Sub-agent)

After drafting, dispatch `style-auditor` agent:

Input contract:
- Draft text (`drafts/<section>.md`)
- Output language (from PROJECT.md: TR or EN)
- Hedging audit: are claims appropriately hedged?
- Tense discipline: are tenses consistent per section?
- Terminology consistency: is "X" always called "X" (not sometimes "Y")?
- Register (academic vs colloquial): is tone appropriate?

```
Example style-auditor return (plain text, NOT JSON — one line-referenced item
per line: file:line · severity · rule-id · current → suggested, plus a 3-line
summary; style-auditor never returns structured JSON, it returns this exact
format so a cheap model can't accidentally produce malformed edits):
drafts/methods.md:12 · fix · article-usage · "the CNN models" → "CNN models" (drop "the")
drafts/methods.md:25 · review · hedging-overstrong · "CNNs are the best..." → "CNNs show promise..." or "CNNs outperform..."
drafts/methods.md:38 · fix · term-inconsistency · "bearing fault" vs "anomaly detection" → standardize to one term
Summary: 3 items (2 fix, 1 review); dominant problem: article usage; terminology drift pairs: bearing fault/anomaly detection.
```

### 6. Apply Safe Fixes

Main session (you, not the model) apply style-auditor's suggestions to `drafts/<section>.md`:
- ✅ Apply: grammar fixes, article fixes, hedging clarifications, term standardization
- ❌ Do NOT apply: rewrites that change meaning, subjective style opinions, contradictions of your intent

Print:
```
✅ Stil denetimi tamamlandı. [N] öneri uygulandı:
  - Makale kullanımı: 3 değişiklik
  - Terim tutarlılığı: 2 değişiklik
  - Eğilim: 1 öneri (gözden geçirin)

Dosya: drafts/introduction.md
```

### 7. Word Count Report

`word_budget.py` scans every file in `drafts/` against PROJECT.md's budget in one
pass — there is no per-section flag. Run it and read the entry matching this
section's filename from the returned `sections` array:
```bash
python scripts/word_budget.py --json
```

Output:
```
Bölüm: introduction
Sözcük sayısı: 1,240 / 1,500 bütçe (82.7%)
[Breakdown by sub-section if available]

Kalan bütçe: 260 sözcük
```

Warn if over budget:
```
⚠️ introduction bütçeden 340 sözcük fazla. Lütfen gözden geçirin veya
/word_budget --trim introduction komutunu çalıştırın.
```

### 8. Final Output

Print:
```
✅ Bölüm taslağı tamamlandı!

Dosya: drafts/introduction.md
Sözcükler: 1,240 / 1,500
Kanıt kartları: 10 bağlantı
[CITATION NEEDED] sayısı: 2 (iddia sağlam, kaynağı henüz bağlanmadı)
[MATERIAL GAP] sayısı: 1 (oturumda bunu karşılayan hiçbir malzeme yok)
[LLM-SUPPLEMENTED] sayısı: 0

Sonraki adımlar:
1. /draft methods — sonraki bölümü taslak yap
2. /verify-citations — alıntı denetimi çalıştır (sonra tüm taslak bitmeli)
3. /status — ilerleme raporu

Not: [CITATION NEEDED] kaynak eksikliğidir — kaynak bulun veya iddiayı kaldırın.
[MATERIAL GAP] ise malzeme eksikliğidir: hafızadan doldurulmadı. Malzeme verin,
ya da doldurmaya açıkça izin verin — o durumda etiket [LLM-SUPPLEMENTED] olur ve
karar kayda geçer. İkisi de bitmiş bir metinde delik sayılır ve kapıyı bloklar.
```

Her `[MATERIAL GAP]` için tek satırla NE eksik olduğunu söyleyin — "hangi
malzeme gerekiyordu" bilgisi olmadan kullanıcı boşluğu kapatamaz:

```
[MATERIAL GAP] §2.3 — örneklem büyüklüğü gerekçesi: güç analizi ya da
benzer çalışmaların N değerleri hiçbir kartta yok.
```

---

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| Outline not approved | Yes | ABORT, ask user to approve outline first |
| Section not found in outline | Yes | ABORT, list available sections |
| No cards for section | Yes | WARN: this section will be synthesis-only; continue if user agrees |
| Methods drafted with most checklist rows (4a) unfilled/unanswerable | Yes | WARN: list which rows are missing and why before finalizing; do not silently ship a thin Methods |

---

## SCRIPT USAGE

```bash
python scripts/evidence_db.py query --tags "rq1,rq2" --min-strength 3
python scripts/word_budget.py --json   # scans all of drafts/; read the matching section entry
```

---

## STABILITY CHECK (optional, diagnostic — not a gate)

Drafting is LLM-mediated, so its accuracy is unmeasured and stays that way: no
gold set exists and the kit refuses to invent one (`eval/MEASUREMENT.md`). Its
**stability** can be measured with no labels at all — draft the same section
2-3× independently, into separate files, then:

```bash
python scripts/draft_stability.py runs/methods-1.md runs/methods-2.md runs/methods-3.md
```

Agreement is reported on the three things that have no honest reason to vary
between renderings of one section from one evidence set: which sources are
cited, which quantities are reported, and how strongly each source is claimed.
Prose is never compared — two honest renderings differ in every sentence.

When to spend the tokens: a section carrying the paper's central numeric claims,
or one where `claim_check.py` already flagged an overclaim. Read the result as
variance only — **a stage that is consistently wrong scores a perfect 1.00**, and
that sentence belongs in any report of the number.

---

## EVIDENCE CARD BINDING FORMAT

Every empirical claim must have a card comment:
```markdown
Claim sentence [@citation_key].
<!-- EV-0045 -->
```

Or if no source:
```markdown
General claim [CITATION NEEDED]
```

**Why:** The comment establishes traceability. Later, `/verify-citations` will cross-check [@citation_key] against sources/registry.jsonl and evidence cards.

---

## ERROR MESSAGES (Turkish)

```
❌ İskelet henüz onaylanmadı. Lütfen /outline çalıştırın.
❌ Bölüm "[section]" iskelet dosyasında bulunamadı.
⚠️ Bu bölüme hiçbir kanıt kartı bağlanmadı. Lütfen /lit-review veya /analyze-data çalıştırın.
⚠️ Bölüm bütçenizi aştı: [N] sözcük fazla.
```

---

## FOLLOWING STEPS

After `/draft <section>`:
- User runs `/draft <next-section>` to draft another section.
- After all drafts: user runs `/verify-citations` to check bibliography.
- After verify passes: user runs `/critique` for peer review.
