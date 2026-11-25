---
name: evidence-cards
description: "Create structured evidence cards from research sources for zero-fabrication citation discipline. Use when extracting claims, findings, methods, definitions, statistics, or quotes from academic papers — converts source material into queryable cards bound to specific registry entries. Triggers on: 'extract evidence', 'create evidence card', 'catalog findings', 'record quote', 'evidence from paper', 'from source'."
---

# Evidence Cards — The Kit's Backbone

Evidence cards are the machine-readable unit of academic writing. They bind every empirical claim in your draft to a registered source via a unique card ID (EV-####), enforce plagiarism discipline through verbatim-quote rules, and standardize extraction of ML results (metrics objects) for comparison tables. Cards live in `evidence/cards.jsonl` and are queried via `evidence_db.py` script.

> **Language:** every user-facing string below (gates, aborts, summaries) is
> written in Turkish, the kit's conversational default (CLAUDE.md). If the
> active project's PROJECT.md sets **Conversation language:** `en`, present
> the equivalent content in natural English — translate meaning and
> structure (headings, bullets, ✅/❌ markers), don't reproduce the Turkish
> text verbatim.

## Card Schema (JSONL)

```json
{
  "id": "EV-0042",
  "source": "kaya2023deep",
  "type": "finding|method|definition|statistic|quote|gap|own-result",
  "claim": "one sentence stating the key point",
  "detail": "2-4 sentences of supporting context",
  "page": "12-13",
  "verbatim": false,
  "strength": 4,
  "tags": ["rq1", "transfer-learning"],
  "metrics": {
    "F1": 0.87,
    "dataset": "ImageNet",
    "model": "ResNet50"
  },
  "conflicts_with": ["EV-0017"],
  "lang": "en"
}
```

### Field Rules

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | Auto-generated EV-NNNN; immutable once written |
| `source` | string | Must match a `bib_key` in `sources/registry.jsonl` |
| `type` | enum | `finding`, `method`, `definition`, `statistic`, `quote`, `gap`, or `own-result` |
| `claim` | string | **One sentence only.** The core point: what does this source say? No jargon; newbie-readable. |
| `detail` | string | 2–4 sentences of context, evidence, or qualification. Explains *why* the claim matters. |
| `page` | string | Page number or range: "12" or "12-13". **Mandatory if `verbatim:true`; optional if `verbatim:false`.** |
| `verbatim` | bool | `true` → the detail contains a direct quotation (triggers page requirement). `false` → paraphrase or summary. |
| `strength` | int | 1–5 rubric (see below). Feeds filtering in drafts: `evidence_db.py query --min-strength 3`. |
| `tags` | array | Research question (rq1, rq2, …) + topic tags (e.g., "transfer-learning", "ablation-study"). Enables targeted queries. |
| `metrics` | object | **For ML/quantitative papers only.** Standardized numerical results: `{"F1": 0.87, "AUROC": 0.92, "dataset": "...", "model": "..."}`. Feeds directly into comparison tables. |
| `conflicts_with` | array | Card IDs that contradict or qualify this finding. Seeds Discussion section; marks open questions. |
| `lang` | string | `"en"` or `"tr"` — the source's language. Bilingual papers track language separately. |

## Strength Rubric (1–5)

- **5 — Direct evidence:** empirical result from a rigorous study, peer-reviewed RCT, or systematic review; high methodological quality.
- **4 — Strong support:** well-designed observational study, meta-analysis, or expert consensus; minor methodological caveats.
- **3 — Moderate evidence:** single well-executed study, mixed-method synthesis, or industry standard (e.g., "PyTorch is the dominant framework"); some limits to generalizability.
- **2 — Suggestive:** smaller sample, preliminary results, opinion from recognized authority, or domain consensus without formal evidence.
- **1 — Weak or illustrative:** anecdote, outdated study, weak methodology, or unverified claim useful only as an example.

Draft queries typically filter for `--min-strength 3` (moderate+); Strength 1–2 cards appear in motivation or limitations.

## Writing a High-Quality Card

### One Claim Per Card

A card captures **one discrete, citable unit**. Do not combine multiple findings into a single card.

❌ Bad: claim = "Deep learning outperforms classical ML on large datasets and is computationally expensive"
✅ Good: Two cards —
- EV-0042 / finding / "Deep learning achieves higher accuracy on large image datasets than classical ML" / detail with baseline comparison
- EV-0043 / method / "Deep learning training requires GPU hardware due to backpropagation complexity" / detail on computational demand

### Claim Is One Sentence

The claim must state **what the source says**, not your interpretation or how you'll use it. It must be a complete sentence and should be understandable to someone unfamiliar with the topic.

❌ Bad: claim = "CNN, transfer learning"
✅ Good: claim = "Convolutional neural networks trained on ImageNet can be fine-tuned for domain-specific image classification with fewer labeled samples than training from scratch"

### Detail: 2–4 Sentences

Provide just enough context for the claim to make sense in isolation. Include:
1. **Why the claim is relevant** (e.g., what gap it fills, what problem it solves).
2. **Key methods or evidence** (e.g., study design, dataset size, baseline for comparison).
3. **Any critical caveats** (e.g., "only tested on medical images", "assumes >1000 labeled samples").
4. **Pointer to fuller discussion** if the detail is complex (e.g., "See page 45–47 for ablation details").

Example detail:
"The study trained a ResNet50 on ImageNet (1.2M images, 1000 classes) for 100 epochs with SGD. Transfer to a medical imaging task (chest X-rays, 5000 samples) achieved 94.2% F1 with fine-tuning of final layers, compared to 78.1% from a random-initialization baseline. The gain held across three independent random seeds (std ±1.3%). Limitations: single-task evaluation; results may not transfer to non-imaging domains."

### Metrics Objects for ML Papers

When extracting results from an ML/data-science paper, use a structured metrics object:

```json
{
  "metrics": {
    "task": "image-classification",
    "model": "ResNet50",
    "dataset": "CIFAR-100",
    "train_size": 50000,
    "test_size": 10000,
    "accuracy": 0.961,
    "F1_macro": 0.957,
    "precision": 0.963,
    "recall": 0.959,
    "training_time_hours": 12,
    "num_params_millions": 25.5,
    "num_seeds": 3,
    "std_dev": 0.002,
    "baseline_accuracy": 0.92,
    "improvement_pct": 4.45
  }
}
```

This standardization ensures:
1. Comparison tables can be built directly from card queries.
2. The entry is machine-parseable for Excel export and systematic review matrices.
3. Reproducibility information (seeds, std dev, train size) is explicit.

## Card Types and Usage Patterns

### finding
Empirical result, measured outcome, or observation from the source. Binds to Results sections.
- Example: "ResNet-152 achieved 96.4% top-1 accuracy on ImageNet after training with mixed precision."

### method
A technique, algorithm, dataset, or evaluation protocol described in the source. Binds to Methods sections and comparison tables.
- Example: "The BERT model uses masked language modeling (MLM) and next-sentence prediction (NSP) as joint pretraining objectives."

### definition
A formal or clarifying explanation of a term, concept, or taxonomy from the source.
- Example: "Concept drift in streaming data is defined as a change in the joint distribution P(X, y) over time, often categorized as real, virtual, or seasonal."

### statistic
A numerical summary, benchmark, or prevalence statistic. Useful for motivation and landscape sections.
- Example: "As of 2023, 87% of Fortune 500 companies had deployed at least one machine learning model in production."

### quote
A verbatim extract from the source, word-for-word. **Mandatory:** set `verbatim: true` and include `page` number. Quotes >30 words should live in card detail, not pulled into text directly (paraphrase instead).
- Example: detail = "\"The reproducibility crisis in machine learning stems from a combination of dataset bias, hyperparameter tuning on test sets, and lack of code availability.\" (p. 14)"

### gap
A stated research gap, open question, or limitation the source identifies. Binds to introduction and discussion.
- Example: "No prior work has combined transfer learning with continual learning to achieve zero-shot domain adaptation on streaming data."

### own-result
A result from the user's own analysis or experiments (produced by the data-scientist agent). These are registered in evidence/ just like sourced cards, with `source` pointing to a synthetic registry entry like `own-experiment-001`.
- Example: claim = "Our CNN architecture trained on 500 augmented X-ray images achieved 91.7% F1 on a held-out test set of 100 images."

## Registry Binding (bib_key)

Every card's `source` field must exactly match a `bib_key` entry in `sources/registry.jsonl`. The registry is the single source of truth for:
- DOI and full citation metadata
- Venue index status (SCI-E, Scopus, TR Dizin, etc.)
- Download/access status (PDF, URL, or unavailable)

When source-analyst extracts a card, it:
1. Reads the PDF/fulltext identified by registry ID
2. Extracts the claim and detail
3. Adds the card to `evidence/cards.jsonl` with `source: registry_entry.bib_key`

The main session then queries cards via tags/strength and drafts cite them as `[@bib_key]` using pandoc syntax — the citation verifier cross-checks every key against references.bib before finalization.

## Querying Cards in Drafts

The `evidence_db.py` script retrieves relevant cards for a drafting session:

```bash
# Get all cards for RQ1 with strength ≥3
python scripts/evidence_db.py query --tags rq1 --min-strength 3

# Get all metrics objects (ML results)
python scripts/evidence_db.py query --type finding --tags dataset

# Get quotes only (for verbatim sections)
python scripts/evidence_db.py query --type quote

# Conflict view (cards that contradict each other)
python scripts/evidence_db.py conflicts
```

Output is JSONL; a typical drafting flow is:
1. Load cards for current section via query
2. Synthesize them into prose, binding each claim to [@key]
3. Run `cite_audit.py --quick` to verify keys exist in bib/references.bib

## Conflicts and Discussion Discipline

The `conflicts_with` field seeds the Discussion section. If EV-0042 contradicts EV-0017, mark it:
```json
{
  "id": "EV-0042",
  ...
  "conflicts_with": ["EV-0017"]
}
```

The `conflicts` subcommand surfaces all such pairs, allowing the Discussion to:
1. Acknowledge both findings explicitly
2. Propose reasons for divergence (methodology, context, sample, publication bias)
3. Argue which finding applies to your research question

This transforms a potential weakness (conflicting literature) into a strength (nuanced, honest synthesis).

## Verbatim Quote Discipline (Zero Plagiarism)

- **If `verbatim: true`**, the detail must be a direct quotation from the source and **must include the page number** in the `page` field.
- **If `verbatim: false`**, a paraphrase or summary is acceptable without page number (though recording page is still good practice for verification).
- Quotes >30 words should not appear verbatim in the final text; instead, paraphrase the card's claim and cite it.
- Short, pithy quotations (<30 words) can move into text under the rule: quote + page number in parenthetical citation ([@key, p. XX]).

This rule prevents plagiarism and ensures that even if the model drafts a sentence that matches the source word-for-word, the citation-verifier will catch it and report it as an anomaly for review.

## See Also

- **[card-writing-checklist.md](reference/card-writing-checklist.md)** — quality checklist before saving a card.
- **evidence_db.py** — execute `python scripts/evidence_db.py add --stdin < cards.jsonl` to bulk-load cards; execute `python scripts/evidence_db.py query --help` to see all query modes.
- **registry_db.py** — cards point to registry entries; understand registry structure and status fields.
