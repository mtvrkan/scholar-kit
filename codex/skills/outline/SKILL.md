---
name: outline
description: "Build a structured outline by querying evidence cards, binding each heading to RQs and supporting card IDs, checking RQ coverage, and requesting user approval. Gate: sufficient cards exist (empirical ≥15, review ≥30, thesis ≥40)."
disable-model-invocation: true
argument-hint: ""
---

# Build an Outline

This skill constructs a skeleton outline from your project type, research questions, and evidence cards. Every heading is bound to card IDs and RQ tags for traceability.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim.

## GATE: Sufficient Evidence Cards

**Check:** Read PROJECT.md (get type, RQs). Query evidence database:

```bash
python scripts/evidence_db.py --json stats
```

Parse output: total card count.

**Gate logic** (PROJECT.md's `- **Type:**` holds one of the 15 enum keys — see
its own comment or paper-types/SKILL.md's canonical table; match on the enum
key, never a human-readable label):
```
if type == "empirical-imrad" and cards < 15:
    ABORT with: "❌ Yeterli kanıt kartı yok (minimum 15, şu anda [N]).
                 Lütfen /lit-review tamamlayın veya /analyze-data çalıştırın."

elif type in ["systematic-review", "narrative-review", "scoping-review"] and cards < 30:
    ABORT with: "❌ Derleme için çok az kaynak ([N], minimum 30).
                 /lit-review --systematic çalıştırın."

elif type.startswith("thesis-") and cards < 40:
    ABORT with: "❌ Tez için çok az kanıt kartı ([N], minimum 40).
                 /lit-review bitmemiş gibi görünüyor."
```

If gate passes, print:
```
✅ Kanıt kartları yeterli: [N] kart bulundu.
Kâğıt tipi: [type] — iskelet oluşturuluyor...
```

---

## PROCEDURE

### 1. Load Type Template

Resolve PROJECT.md's `- **Type:**` value via `paper-types/SKILL.md`'s
"Canonical Type → File Resolution" table — do NOT guess a `reference/<type>.md`
path. For `thesis-*` types the table points at the thesis-structure skill
(chapter architecture, not `reference/yok-tr.md` — that file is YÖK-specific
front-matter/Turkish rules, a different concern from heading structure): use
`thesis-structure/SKILL.md` Section 1 (Classic 5-Chapter Structure) instead.

Extract the standard heading hierarchy for that type. Example for IMRaD:
```
1. Introduction
   1.1 Background
   1.2 Existing Work
   1.3 Research Gap
   1.4 Research Questions
   1.5 Contribution

2. Methods
   2.1 Study Design
   2.2 Data Collection
   2.3 Data Analysis

3. Results
   3.1 Descriptive Statistics
   3.2 Primary Findings
   3.3 Secondary Findings

4. Discussion
   4.1 Interpretation of Findings
   4.2 Comparison with Literature
   4.3 Limitations
   4.4 Future Work

5. Conclusion
```

### 2. Tag Headings with RQs

For each heading, infer which RQ(s) it addresses. Example logic:

```
Heading: "3.2 Primary Findings"  → likely RQ1 (main research question)
Heading: "3.3 Secondary Findings" → likely RQ2 or RQ3
Heading: "1.2 Existing Work"    → tag: "background" (no specific RQ)
Heading: "4.2 Comparison with Literature" → tag: "synthesis" (all RQs)

Ask user for each heading:
"Heading '3.2 Primary Findings' — which RQ(s)? (1/2/3/all/none)"
```

Or use heuristic: search evidence cards for RQ tags that naturally cluster, infer from titles. At minimum: annotate in comment.

### 3. Query & Bind Card IDs

For each heading, query evidence cards:

```bash
python scripts/evidence_db.py query --tags "<rq1,rq2>"
```

Retrieve up to 5–10 most relevant cards (by strength score) per heading. Bind them as HTML comments:

```markdown
## 3.2 Primary Findings
<!-- RQ: rq1 | Cards: EV-0023, EV-0025, EV-0031, EV-0045 -->

This section presents the main empirical findings...
```

### 4. Check RQ Coverage

Verify: **Every RQ has at least one supporting heading.**

```python
for rq in RQs:
    if no headings tagged with rq:
        WARN: "❌ Araştırma Sorusu [RQ] hiçbir bölüm tarafından kapsanmıyor.
               Lütfen ilgili kanıt kartlarını sorgulayın veya ek başlık ekleyin."
```

### 5. Write Draft Outline

Generate `outline/outline.md`:

```markdown
# OUTLINE — [Type] on [Topic]

**Project:** [topic from PROJECT.md]
**RQs:** [list]
**Type:** [type]
**Created:** [timestamp]
**Status:** pending-approval

---

## I. Introduction
<!-- RQ: background | Cards: EV-0001, EV-0002, EV-0003 -->

### I.1. Background
[1–2 sentences placeholder]

### I.2. Existing Work
[placeholder: synthesize EV-0001, EV-0002]

### I.3. Research Gap
[placeholder: synthesize gap cards]

### I.4. Research Questions
[placeholder: restate RQs from PROJECT.md]

### I.5. Contribution
[placeholder: summarize what this work will add]

---

## II. Methods
<!-- RQ: rq1, rq2 | Cards: EV-0010, EV-0011, ... -->

### II.1. Study Design
[placeholder]

### II.2. Data Collection
[placeholder]

### II.3. Data Analysis
[placeholder]

---

## III. Results
<!-- RQ: rq1, rq2, rq3 | Cards: EV-0020..EV-0050 -->

### III.1. Descriptive Statistics
[placeholder: own-analysis cards if present]

### III.2. Primary Findings
[placeholder: EV-0023, EV-0025, EV-0031, EV-0045]

### III.3. Secondary Findings
[placeholder: EV-0060, EV-0061]

---

## IV. Discussion
<!-- RQ: synthesis | Cards: all -->

### IV.1. Interpretation
[placeholder: synthesize findings across RQs]

### IV.2. Comparison with Literature
[placeholder: EV-0100..EV-0120 (comparison cards)]

### IV.3. Limitations
[placeholder: gap cards, method limitations]

### IV.4. Future Work
[placeholder: synthesis of gap cards]

---

## V. Conclusion
<!-- RQ: synthesis | Cards: EV-0150..EV-0155 -->

[placeholder: restate contribution, align with RQs]

---

## Card Coverage Summary

| RQ | Headings Covering | Card Count | Status |
|----|-------------------|-----------|--------|
| RQ1 | II.1, III.2, IV.2 | 12 | ✓ |
| RQ2 | II.2, III.3, IV.1 | 8  | ⚠️ sparse |
| RQ3 | III.2, IV.2       | 5  | ⚠️ sparse |
| Background | I.1, I.2  | 6  | ✓ |

**Coverage Check:** All RQs present ✓

---

**APPROVAL REQUIRED** — This outline must be approved by the user before drafting begins.
```

### 6. Display to User & Request Approval

Print to user:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
İSKELET OLUŞTURULDU

Dosya: outline/outline.md

Başlıklar: [N] (her biri RQ ve kanıt kartları ile işaretli)

RQ Kapsamı:
  RQ1 — [M] kart
  RQ2 — [M] kart
  RQ3 — [M] kart

[Outline preview printed to screen]

Onaylıyor musunuz? (evet/hayır/edit)
```

**User input options:**
- `evet` → proceed to step 7
- `hayır` → abort, user edits manually
- `edit <section>` → requery cards for that section

### 7. Record Approval

Add approval line to `outline/outline.md` header:
```markdown
**Status:** approved
**Approved at:** 2024-07-02T14:35:00Z
```

**The field names above are machine-readable and are NOT covered by this skill's
Turkish-output rule — write `Status`, not `Durum`.** `phase_gate.py` matches the
line literally; a localised label used to make it reject an outline the user had
genuinely approved, and report it as "not approved". The gate now also accepts
`**Durum:** approved` so an already-localised project is not stranded, but the
English spelling is the one to write. The rest of the outline — every heading,
every note — stays in the project's output language.

Then record the approval in the provenance chain — **after** the file is written,
never before (the record carries the SHA-256 of the approved bytes, so an
attestation written first attests the wrong content):

```bash
python scripts/provenance.py --record outline-approved --path outline/outline.md \
  --note "approved by user"
```

`phase_gate.py` reads that record and compares its digest against the outline on
disk, so a section edited after approval is caught by content rather than by a
hand-typed timestamp. Skipping this step does not unblock anything and does not
block anything — the gate falls back to the timestamp check — but it does leave
the approval with no record anyone can audit afterwards.

Print:
```
✅ İskelet onaylandı!

Sonraki adımlar:
  1. /draft introduction — İngilizce bölüm taslağı
  2. /draft methods
  3. /draft results
  ... (her bölüm ayrı ayrı taslak yapılır)

Önemli: /draft komutları outline/outline.md'den bölüm kartlarını yükleyecek.
```

---

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| Insufficient cards (empirical <15) | Yes | ABORT, suggest lit-review or data-analysis |
| Insufficient cards (review <30) | Yes | ABORT, expand search |
| Insufficient cards (thesis <40) | Yes | ABORT, expand search |
| RQ uncovered by headings | Yes | WARN, suggest adding heading or expanding outline |

---

## SCRIPT USAGE

```bash
python scripts/evidence_db.py --json stats
python scripts/evidence_db.py query --tags "rq1"
python scripts/word_budget.py --rq-trace  # optional: check RQ trace (no positional args)
```

---

## ERROR MESSAGES (Turkish)

```
❌ Yeterli kanıt kartı yok: [type] için minimum [threshold] gerekli, şu anda [N].
❌ Araştırma Sorusu [RQ] hiçbir bölüm tarafından kapsanmıyor.
⚠️ RQ2 çok az kanıt kartı tarafından destekleniyor ([M] kart).
```

---

## FOLLOWING STEPS

After outline approval:
- User runs `/draft <section>` to write individual sections.
- Each draft command will:
  1. Load outline slice for that section.
  2. Query cards bound to that section's RQs.
  3. Draft in the main session.
  4. Run style-auditor and apply fixes.
