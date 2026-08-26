# Evidence Card Writing Checklist

Before saving a card to `evidence/cards.jsonl`, verify:

## Card Content

- [ ] **Claim is exactly one sentence.** No compound claims, no "and also"; if you want to add a second claim, split into a second card.
- [ ] **Claim is understandable to a domain newcomer.** Minimize jargon; use "convolutional neural network" on first mention, not "CNN" alone.
- [ ] **Claim is what the source says, not my interpretation.** Avoid "This suggests that…" or "I infer that…" — record what the source explicitly states.
- [ ] **Detail is 2–4 sentences.** If detail is >4 sentences, split into two cards or move some context to a separate card.
- [ ] **Detail includes context for why this claim matters.** What problem does it solve? What gap does it fill?
- [ ] **Detail includes key numbers/methods (if relevant).** Sample size, study design, dataset, baseline for comparison — enough for reproducibility.
- [ ] **If `verbatim: true`, then `page` is filled and detail contains the exact quote.** Page is mandatory for verbatim claims.
- [ ] **If `verbatim: false`, the detail is a paraphrase in my own words.** Page is optional but recommended for traceability.

## Metadata

- [ ] **`source` exactly matches a `bib_key` in `sources/registry.jsonl`.** Run `python scripts/registry_db.py list` to see all registered sources.
- [ ] **`type` is one of:** `finding`, `method`, `definition`, `statistic`, `quote`, `gap`, or `own-result`.
- [ ] **`strength` is 1–5 per the rubric.** Strength 5 = peer-reviewed RCT or meta-analysis; Strength 1 = anecdote or preliminary.
- [ ] **`tags` include at least one research question** (e.g., `rq1`, `rq2`) **and at least one topic tag** (e.g., `transfer-learning`, `attention-mechanism`). This enables targeted queries.
- [ ] **If the card is from an ML/quantitative paper, `metrics` is a structured object** with keys like `model`, `dataset`, `accuracy`, `F1`, `num_seeds`, etc. — not a free-form string.
- [ ] **`lang` is `"en"` or `"tr"`** matching the source language.

## Conflicts

- [ ] **If this card contradicts or qualifies another card, `conflicts_with` lists those card IDs** (e.g., `["EV-0017", "EV-0023"]`). This seeds the Discussion.
- [ ] **Conversely, if you know another card conflicts with this one, add this card's ID to that card's `conflicts_with` field.** Bidirectional linking is optional but cleaner.

## Script Validation (Execute, Don't Read)

After writing a batch of cards, run:

```bash
python scripts/evidence_db.py stats                 # confirms all cards added, shows tag/strength distribution
python scripts/evidence_db.py query --tags rq1     # spot-check that your RQ1 cards are queryable
python scripts/evidence_db.py conflicts             # verify conflicts are recorded bidirectionally
```

Exit code 0 = all cards valid; exit code 1 = schema error (missing required field, invalid type, etc.).

## Example Card (Passing Checklist)

```json
{
  "id": "EV-0087",
  "source": "krizhevsky2012imagenet",
  "type": "finding",
  "claim": "AlexNet reduced ImageNet top-5 error from 26.2% to 15.3% using convolutional neural networks with ReLU activations.",
  "detail": "The 2012 study trained an 8-layer CNN on 1.2 million ImageNet images across 1000 object classes using SGD with momentum. The architecture featured ReLU activations and local response normalization (LRN) layers, which accelerated training compared to tanh units. The model achieved 15.3% top-5 classification error on the test set—a significant 40% relative improvement over the previous best result. Training required five GPUs and took six days. This work catalyzed the deep learning revolution in computer vision.",
  "page": "4-5",
  "verbatim": false,
  "strength": 5,
  "tags": ["rq1", "deep-learning", "image-classification", "convolutional-neural-networks"],
  "metrics": {
    "task": "image-classification",
    "dataset": "ImageNet",
    "train_size": 1200000,
    "test_size": 50000,
    "num_classes": 1000,
    "top5_error": 0.153,
    "top5_error_previous_best": 0.262,
    "architecture": "AlexNet",
    "num_params_millions": 60,
    "training_time_hours": 144,
    "num_gpus": 5
  },
  "conflicts_with": [],
  "lang": "en"
}
```

Checklist:
- ✓ Claim is one sentence, specific, and citable.
- ✓ Detail explains methodology, context, and significance (4 sentences).
- ✓ Page range included for traceability.
- ✓ verbatim: false (paraphrase, not direct quote).
- ✓ Strength 5 (landmark peer-reviewed study, extremely influential).
- ✓ Tags include RQ (rq1) and topics (deep-learning, image-classification, CNN).
- ✓ Metrics object is structured: task, dataset, dataset size, error rates, architecture, compute.
- ✓ No conflicts (this is a canonical positive result).
- ✓ Source "krizhevsky2012imagenet" matches a bib_key in registry.jsonl.
