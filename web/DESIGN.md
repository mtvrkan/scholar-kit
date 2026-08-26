# Site design — direction, references, constraints

Working notes for `scholar.mtvrkan.com`. The site source is `web/`; the built
output is committed to `docs/`, which GitHub Pages serves.

This file exists because the design has now been reworked several times and the
reasoning kept living in chat. What a reference *is* and what it is *for* are
different questions, and only the second one survives being written down.

---

## Current direction — "TUTANAK" (the record)

The site is typeset as a critical edition of a verification record.

- **Warm paper ground** (`--paper #f6f2e9`), not grey and not black. The full
  token set is at the top of `global.css`; nothing below that block writes a
  literal colour, which is what makes the dark remap fifteen lines instead of a
  second stylesheet.
- **Archival ink-teal** (`--arc #14454f`) as the *structural* accent: section
  numbers, record chrome, links, the mark, the rule under a group heading.
- **Verdict colour, rationed to three** — `--pass` green, `--fail` vermilion,
  `--flag` amber. These are the only hues allowed to carry meaning, and they
  appear wherever the kit itself would render a judgement.
- **The apparatus margin.** `.ed` is a two-column grid; `.ann` marks an
  annotated passage and `.note` lifts out of it into the margin beside the
  sentence it qualifies. Below 64rem the margin folds and the note becomes a
  footnote where it was written.
- **Inter** throughout, **IBM Plex Mono** for anything that is a record: field
  names, figures, ledger rows, commands, section numbers.
- **The signature moment:** the landing hero is `Pipeline.astro` — the six
  stages of a run with the three gates drawn *between* them, in the places where
  a stage cannot start. Not a screenshot of a product: the sequence itself, with
  the locks where the kit actually puts them.

### Why the hero is the pipeline and not a picture of a product

A landing page's hero is the one thing a visitor cannot skip, and this kit's
entire claim is about what it refuses to do rather than what it produces. The
panel that stood here before typeset a real `03-verify-status.json` imported at
build time — the artifact rather than a mockup — and it went when the showcase
runs did: two of the three never reached a result their author would stand
behind, and evidence that has been withdrawn cannot go on being cited. What
replaces it is a claim the repository can still keep, because the gates it draws
are enforced in `.claude/hooks/` and covered by the suite.

### What was replaced, and why this time it was not taste

Three directions preceded this one. The first two are worth remembering as
evidence about what this page needs; the third is worth remembering as a
warning.

- **"HAT / The Line"** — achromatic on principle: ink, steel, paper, colour
  reserved for a verdict, plus a scroll rail and an instrument readout. Its own
  entry recorded the risk ("whether the no-colour rule reads as a thesis or as
  *drab*"), and the verdict came back: drab. **TUTANAK is not a return to it:**
  the ground is warm rather than grey and the teal is structural rather than
  held back for verdicts, so colour is on every screen. What is rationed is
  which colours are allowed to *mean* something.
- **"KÂĞIT"** — a light critical edition, warm paper and vermilion, with a
  margin apparatus. The apparatus survived into every direction since, because
  it is the kit's own argument — a claim with its evidence beside it — rendered
  as a layout. TUTANAK is the closest descendant of this one.
- **"AURA"** — ported from a supplied brief for a premium, AI-native product
  page: `#0c0c0c` ground, a swept gradient headline, liquid-glass cards, a
  macOS menu-bar strip, a fullscreen video backdrop. It was replaced for four
  reasons, and only the last is aesthetic:

  1. **The backdrop was a third-party request for an asset this project does
     not own** — a CloudFront URL under someone else's user path. It forced
     `media-src` to name a remote host, which cost the site's "no outbound
     request" line its unqualified form and put the marketing site at odds with
     `SECURITY.md`, whose first section is *what leaves your machine*.
  2. **Nobody had ever seen it render.** The previous version of this file
     recorded that the CDN was unreachable from the build machine — and then
     shipped the hero anyway. A hero that has never been verified, on the site
     of a kit that exists to refuse unverified things, is the whole problem in
     one element. (Re-checked when this direction was written: still
     unreachable, request timed out.)
  3. **The menu-bar strip's leading glyph was the Apple corporate logo.**
  4. It read as every other AI product page of its year, worn by the one
     project whose differentiator is refusing to claim what it has not
     measured. Form and thesis were arguing with each other.

  Removed with it: 172 KB of Archivo `woff2` in `public/fonts/` and `docs/fonts/`
  that no stylesheet had declared since "KÂĞIT" and that shipped to every
  visitor regardless.

### Dark mode

The edition prints on dark stock when the reader's system asks for it. Only the
tokens move — `@media (prefers-color-scheme: dark)` remaps the same names, the
warmth is kept (a warm near-black, not `#000`), and the verdict hues are lifted
for contrast. Every rule outside that block is written once.

---

## Hard constraints (these are not preferences)

| Constraint | Enforced by | What it rules out |
|---|---|---|
| One stylesheet, shared by all five pages | `test_every_site_page_exists_and_shares_the_stylesheet` | Per-page CSS files. `inlineStylesheets: 'never'` is what holds it. |
| **No inline `style` attribute, anywhere** | `test_no_built_page_carries_an_inline_style_attribute` | Per-element colours passed as attributes. Under `style-src 'self'` the browser drops the attribute and the element renders unstyled rather than erroring. |
| No bundled or external `.js` | `postbuild.mjs` CSP (`script-src` = inline hashes) | React, Framer Motion, any library. |
| **No CSP directive names a host** | `test_site_is_self_contained` + `test_the_policy_names_no_remote_host` | A font CDN, a remote stylesheet, an embed, a hosted video. This is the constraint AURA broke. |
| No root-absolute asset paths in pages | `test_no_built_page_uses_a_root_absolute_asset_path` | `/assets/…`; `postbuild.mjs` relativises pages and the emitted CSS. |
| Every published number derived from the repo | `test_governance_docs.py` | Invented stats. Change `web/src/data/site.ts`, rebuild, or the tests fail. |
| **The landing description states no hand-written count** | `test_the_landing_description_states_no_stale_counts` | The meta description drifting from the catalogue — it shipped "9 subagent, 17 komut" against a real 10 / 43, which is what a search result showed. |
| **The page claims no run it cannot show** | `test_the_site_claims_no_run_it_cannot_show` | A showcase band coming back as prose after its artifacts were withdrawn. |
| Bilingual, both languages in the HTML | `test_every_page_is_bilingual` | Copy that only exists in one language. Turkish is the pre-toggle default. |
| Two `<h1>` per page, one per language | `test_every_page_has_exactly_one_h1` | A single `<h1>` wrapping two language spans — the test counts `<h1>` elements *by language class*. |
| Every tool name inside `<b>` on the tools page | `test_the_tools_page_lists_every_tool_in_the_repository` | Restyling that drops the `<b>`; the test reads the built page with a regex. |
| Opens from disk (`file://`) | `postbuild.mjs` | Absolute paths, server-only APIs. |

## Things worth knowing before editing

- **The record's leader dots are a border, not characters.** `.rec-row > s` is a
  flexible spacer with `border-bottom: 1px dotted`, so the dots run exactly from
  the label to the figure at any width. A row of literal dots would also be
  collapsed by `compressHTML`, which is the same reason the old specimen aligned
  on a grid rather than on runs of spaces.
- **`.ann` is the annotated passage; `.note` lifts into the margin from inside
  it.** Markup order stays reading order, which is what keeps it correct for a
  screen reader and on a narrow screen, where the note stays put as a footnote.
- **The share card is generated, not drawn.** `python web/make_og.py` reads its
  counts out of `site.ts` and its palette from the constants at the top of that
  file. It has now been dark, light, dark and light again without a line of its
  drawing code moving — which is the argument for keeping a card that plain.
