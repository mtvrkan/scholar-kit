---
name: present
description: "Turn a finished manuscript into the things it has to become afterwards: a conference talk with its slide plan and timing, an academic poster laid out for the reading distance, a plain-language summary for a lay or funder audience, and a graphical-abstract brief a designer (or you) can execute. Every number and claim is taken from the manuscript's own evidence and run records — a talk that overclaims is the version most people will remember."
disable-model-invocation: true
argument-hint: "[talk|poster|lay|graphical] [--minutes 15]"
---

# /present — What the Paper Becomes Afterwards

A paper is read by a few dozen people. The talk, the poster and the summary reach
more of them, and they are usually made in the last two days before a deadline,
from memory, by someone who has stopped checking numbers.

## Gate

1. `drafts/` holds the manuscript, and `/verify-citations` has passed.
2. **Every number in any of these outputs comes from the manuscript**, and behind
   it from an evidence card or a run record. If a slide wants a figure the paper
   does not report, it does not go on the slide — it goes back to `/analyze-data`
   or `/experiment` first.

## `talk` — a conference presentation

Ask the length first (12, 15, 20 minutes + questions); everything else follows
from it. The plan, not the slides: this produces `exports/talk-plan.md`, which
the author builds in whatever tool their institution uses.

**The shape**, for a 15-minute slot (≈12 minutes of speech, 3 for questions):

| Slides | Minutes | Content |
|---|---|---|
| 1 | 0.5 | Title, authors, affiliation |
| 2-3 | 2 | The problem, and why anyone outside your subfield should care |
| 4 | 1 | The gap — one sentence, the same one as the paper's |
| 5-6 | 2 | What you did (method), at the level a neighbouring field can follow |
| 7-10 | 4 | Results — one claim per slide, each with its uncertainty |
| 11 | 1.5 | Limitations, stated by you before they are asked |
| 12 | 1 | What it means and what is next |
| 13 | — | Backup slides: the ablation, the failed baseline, the parameter table |

Rules that matter more than the design:

- **One claim per slide.** A slide with three findings is a slide with none.
- **Every result slide carries its uncertainty** — the CI or the seed spread from
  `experiment_db.py summary`. A talk is where point estimates go to become facts.
- **Say the limitation out loud.** The question you pre-empt is the question you
  do not have to answer under time pressure.
- **Roughly one minute per slide.** More than 15 slides for 12 minutes means
  cutting content, not talking faster.
- Prepare answers for the three questions the paper invites — `/defense-prep`'s
  question bank works here too, scaled down.

## `poster` — the format nobody is taught

`exports/poster-plan.md`. A poster is read standing up, from about 1.5 metres,
by someone deciding in four seconds whether to stop.

- **Title readable at 3 m** (≈ 85-100 pt), body at 24-28 pt minimum. If it needs
  to be smaller to fit, there is too much on it.
- **One figure carries the poster.** Choose the single figure that shows the
  finding, make it big, and let everything else support it.
- **Text ≤ 800 words in total.** Method as a diagram or a numbered strip, not
  paragraphs. Results as the figure plus three bullets.
- **A conclusion box that stands alone**, because a third of readers read only
  the title, the figure and that box.
- Put the QR code to the paper/preprint and the replication package
  (`/replication-package`) on it — that is what a passing reader actually takes.

## `lay` — the plain-language summary

`exports/lay-summary.md`. Increasingly required by funders (TÜBİTAK, EU) and by
journals; also what a university press office rewrites badly if you do not supply it.

- 150-250 words, no citations, no abbreviations, no method names that need a
  degree.
- Structure: what was the problem → what we did → what we found → what it means
  → what it does **not** mean.
- **That last part is not optional.** A lay summary is where "associated with"
  becomes "causes" in the retelling. Write the boundary yourself, in a sentence,
  and check the claim ladder holds: `python scripts/claim_check.py`.
- If the output language is Turkish, this is one of the few documents where
  everyday register is correct — `tr_style_check.py`'s conversational-token
  warnings do not apply here, and say so when reporting them.

## `graphical` — the graphical-abstract brief

Journals increasingly ask for one; most are bad because they are made last. This
produces a **brief**, not an image: `exports/graphical-abstract-brief.md` —
what it must show (the one relationship the paper establishes), the elements
left to right, the labels with their exact wording, the colour and font
constraints from the venue's guidelines, and the size/format required.

The kit does not draw it. Hand the brief to the author, a designer, or a drawing
tool. **Do not let the image claim more than the paper**: a diagram with an arrow
from A to B asserts a direction, and if the paper reports an association, the
arrow is wrong.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎤 Sunum planı — 15 dakika
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Slaytlar: 12 + 4 yedek · ~12 dk konuşma
Sonuç slaytları: 4 (her biri GA/tohum aralığıyla — RUN kayıtlarından)
Sınırlılık slaytı: var (soru gelmeden söyleniyor)
Beklenen 3 soru + cevap iskeleti: hazır

Uyarı: 7. slayttaki 0.94 için kayıtta koşu yok — experiment_db.py trace boş döndü
```

That last line is the one that matters: a number on a slide with no run behind it
is the same defect as a citation with no source, and it is caught the same way.

## Reference

- **Scripts:** `experiment_db.py summary` / `trace` (numbers and their runs) ·
  `claim_check.py` (the ladder, especially for the lay summary) ·
  `figure_check.py` (the figure you are enlarging exists and is captioned)
- **Related:** `/defense-prep` (thesis defence — the same skills, a harder room),
  `/replication-package` (what the QR code points at), `/submission-pack`
  (highlights, which are the talk's outline in five bullets)

---
*The talk is the version most people will remember. It should not be the version that claims the most.*
