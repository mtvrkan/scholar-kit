# Claim-Strength Ladder — TR + EN

Epistemic claims sit on an ordered strength scale. The defect this reference
governs is **saying more than your source does**: a citation that is real,
resolvable and correctly formatted, attached to a sentence the cited work does
not actually support.

Citation verification (`/verify-citations`, `doi2bib.py --verify`) answers *"does
this reference exist?"* It cannot answer *"does it say that?"* — that is this
document's job, and `scripts/claim_check.py` is its deterministic half.

---

## The ladder

```
0  is consistent with · may suggest · appears to          ← hedged
1    is associated with · correlates with · is related to
2      predicts · is a predictor of
3        contributes to · plays a role in
4          affects · influences · leads to · increases · reduces
5            causes · determines · proves · demonstrates that
```

Turkish, same rungs:

```
0  ile tutarlıdır · olabilir · düşündürmektedir · gibi görünmektedir
1    ilişkilidir · bağlantılıdır · korelasyon göstermektedir
2      öngörmektedir · yordamaktadır · tahmin etmektedir
3        katkıda bulunmaktadır · rol oynamaktadır
4          etkilemektedir · artırmaktadır · azaltmaktadır · yol açmaktadır
5            neden olmaktadır · kanıtlamaktadır · belirlemektedir
```

The exact ordering is **field-relative** — a clinical "predicts" and an
econometric "predicts" are not the same object. When unsure whether two
phrasings occupy the same rung, treat them as different rungs and keep the
source's wording.

---

## The rule: one direction is a defect

| Move | Verdict |
|---|---|
| Source says rung 1, you write rung 4 | ✗ **Overclaim** — misrepresents the source |
| Source says rung 4, you write rung 1 | ✓ Safe — writing more cautiously than your evidence is never wrong |
| Same rung, different wording | ✓ Fine |

This asymmetry is deliberate and is where the kit differs from revision-diff
tools. Those compare a draft against *the author's own previous draft*, so
silent movement in **either** direction misrepresents the author. Here the
baseline is **the source**, and under-claiming a source is a rhetorical choice,
not a misrepresentation.

> A separate rule does apply downward: never *silently* delete a caveat the
> source stated (design limitation, scope hedge, null result). That is not a
> ladder move — it is dropping evidence, and it belongs to the same defect
> family as an unsupported claim.

---

## What counts as a move

**Is a move** — needs the source to actually support it:

- `associated with` → `leads to` / `reduces` / `drives` / `causes`
- `may improve` → `improves` (dropping a modal hedge is an upward move)
- `ilişkilidir` → `neden olmaktadır`
- `etkileyebilir` → `etkilemektedir` (dropping `-ebil-` is an upward move)
- re-attaching a **background** citation's claim to **your own** finding
- turning a single-study result into a general statement ("studies show…")

**Is not a move** — no source support needed beyond what you already have:

- reordering a sentence while keeping the verb and hedges
- emphasis that does not touch the verb ("importantly, X is associated with Y")
- same-rung synonym swap (`narrows` ↔ `reduces the range`)
- condensing prose while preserving every hedge

---

## The attributive-participle trap

The single most common false reading — by humans and by matchers alike:

| Phrase | Reading |
|---|---|
| "associated with **reduced** lung capacity" | rung 1 — `reduced` is an adjective naming an outcome |
| "capacity **was reduced** by the intervention" | rung 4 — passive verb, a directional claim |
| "**azaltılmış** kapasite ile ilişkilidir" | rung 1 — `azaltılmış` is a participle-adjective |
| "kapasiteyi **azaltmaktadır**" | rung 4 — finite verb |

Naming an outcome is not claiming to have moved it. When you paraphrase, check
whether you converted an adjective into a verb — that is an invisible rung jump.

---

## Hedging matched to evidence

| Evidence you have | Highest defensible rung |
|---|---|
| One study, small n, no replication | 0–1 |
| Multiple observational studies, consistent direction | 1–2 |
| Observational + plausible mechanism | 2–3 |
| Experimental design with controls, single context | 3–4 |
| Replicated experiments / RCT / meta-analysis | 4–5 |

Observational data cannot reach rung 5 no matter how large. If the design
cannot establish causation, no amount of significance can promote the verb.

---

## Running the check

```bash
python scripts/claim_check.py                  # WARN-only, both checks
python scripts/claim_check.py --check overclaim
python scripts/claim_check.py --strict         # exit 2 on any warning
```

`overclaim` compares each cited sentence's rung against the strongest rung
found in the evidence cards for the sources it cites. It reports the card ID so
you can read the card's own claim text and adjudicate.

Coverage limits, stated plainly:

- A cited source with **no evidence card**, or cards with no ladder verb, is
  skipped — there is no basis for comparison, so nothing is guessed. Uncarded
  sources therefore weaken this check silently; `evidence_funnel.py` is what
  surfaces them.
- A sentence citing several sources is compared against the **strongest** of
  them, so synthesis is not punished for exceeding the weakest source.
- The matcher sees verbs, not meaning. It cannot detect a claim whose
  overreach lives in scope ("in all populations"), in negation, or in a
  swapped subject. Those stay a human read — and a `reviewer-critic` read.

Every finding is advisory. A rung difference can be entirely legitimate when a
second uncarded source, your own data, or an established mechanism licenses the
stronger verb. The check's job is to make you say so on purpose.

---

## Related

- [paraphrase.md](paraphrase.md) — source fidelity when rewording
- `evidence-cards` skill — what belongs in a card's `claim` field (the ladder's
  comparison basis is only as good as the card)
- `comparative-analysis` skill — causal vs correlational claims in Discussion
