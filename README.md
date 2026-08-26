<p align="center">
  <a href="https://scholar.mtvrkan.com">
    <img src="https://scholar.mtvrkan.com/og-en.png" alt="Scholar-Kit" width="820" />
  </a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-000?style=flat-square" /></a>
  <a href="CITATION.cff"><img alt="v1.0.0" src="https://img.shields.io/badge/version-1.0.0-000?style=flat-square" /></a>
  <a href="CONTRIBUTING.md"><img alt="tests" src="https://img.shields.io/badge/tests-2390%20passing-000?style=flat-square" /></a>
  <a href="https://scholar.mtvrkan.com"><img alt="site" src="https://img.shields.io/badge/site-scholar.mtvrkan.com-000?style=flat-square" /></a>
</p>

# Scholar-Kit

[Türkçe](README.tr.md) · [scholar.mtvrkan.com](https://scholar.mtvrkan.com)

Academic research, writing and thesis production for Claude Code:
10 specialist subagents, 43 commands, 11 knowledge skills, 6 enforcement hooks
and a deterministic Python layer (68 tools). It also covers the work around the
manuscript — grant
proposals and reports, ethics applications, data management plans, referee
reports, promotion dossiers, syllabi and accreditation matrices.

Turkish and English are equal first-class targets, not a base language plus a
translation.

## The problem it solves

An assistant asked for sources will produce them. The reference will be
correctly formatted, the DOI will look right, and the paper will not exist.
Everything here is built around refusing that one failure:

- **A reference never comes from the model's memory.** It is fetched by DOI
  content negotiation or it carries a `verified=false` stamp.
- **Every empirical claim binds to an evidence card** (`EV-####`) that names the
  source it came from. An uncarded claim stays tagged `[CITATION NEEDED]`.
- **Three gates run at the tool-call layer, not in prompt text**: no drafting
  before the outline is approved, no review round before citation verification
  passes, no formatting while a Major finding is open.

The gates hold because they are hooks. A step skipped in conversation does not
skip the gate.

## Install

Two paths, and they give you different things.

**Plugin** — the commands, skills and agents:

```text
/plugin marketplace add mtvrkan/scholar-kit
/plugin install scholar-kit
```

It does **not** give you the script layer or the hooks; those must live inside
your project. So the first command is always `/new-project paper`, which copies
the runtime in and wires the hooks to your Python.

Install the plugin and never run `/new-project` and you get the guidance
**without the guarantees** — the citation gate, the phase gates and the
data-file protection all rest on the script + hook layer. You will not have to
remember that: until it runs, the kit's own hook prints `ENFORCEMENT ABSENT` at
session start, naming each guarantee that is not in force.

**Clone** — `INSTALL.sh` / `INSTALL.ps1`: dependency check, hook interpreter
patching, index datasets, MCP servers. Prefer this to develop the kit itself.

### Requirements

- Python 3.10+, [Claude Code](https://claude.com/claude-code), `pip install -r requirements.txt`
- **bash** — both output builders are shell scripts. Present on macOS/Linux; on
  Windows it comes from Git for Windows (`winget install --id Git.Git`). Without
  it the DOCX/PDF build step fails even with pandoc and TeX installed.
- *Optional:* pandoc (Word), MiKTeX/TeX Live (PDF). Excel and the whole data
  pipeline work without either.
- *Optional:* `requirements-ml.txt` (scikit-learn, pandas, numpy, matplotlib) —
  only if you train models or draw result figures. Deliberately not core: a
  literature review should not pay 200 MB for a stack it never imports.
- *Optional:* MCP servers — semantic-scholar, paper-search, scholar-sidekick.
  Without them the kit falls back to WebSearch plus `doi2bib --verify`.

## Your first paper

```text
$ claude
> /new-project paper          # wizard: topic, RQs, type, venue, style, language, budget
> /lit-review --systematic --lang both    # bilingual search -> your approval -> evidence cards
> /analyze-data data/measurements.csv     # your data; results become cards
> /outline                    # card-bound skeleton -> your approval (the drafting gate)
> /draft methods              # section by section
> /verify-citations           # the fabrication gate; later steps stay locked without PASS
> /critique                   # fresh-context peer review
> /submit-check               # type + reporting standard + budget + build
```

For a thesis: `/new-project thesis` (YÖK front matter, Özet/Abstract
equivalence, `/defense-prep`).

## Commands

| Command | Does | Gate |
|---|---|---|
| `/new-project <type>` | project scaffold + wizard | — |
| `/status` | short status summary, printed each session start | — |
| `/lit-review` | search, screen, cards, synthesis | PROJECT.md |
| `/slr` | full SLR pipeline with qa-auditor double-check; optional meta-analysis | PROJECT.md |
| `/import-library <file>` | .bib/.ris library re-fetched by DOI; no field of the export ships | PROJECT.md |
| `/import-manuscript <file>` | a manuscript written outside the kit, split and re-cited; no sentence edited | PROJECT.md |
| `/journal-check <name>` | venue index profile; `--fit` derives targets from your own references | — |
| `/find-dataset` | finds data, reads each licence, downloads only after it is read | PROJECT.md |
| `/collect-data` | protocol first, then runs it: robots.txt as a gate, every request logged | PROJECT.md |
| `/experiment` | design, run matrix, one record per run, leakage check before any metric | a dataset |
| `/analyze-data <path>` | analysis, figures, tables, own-result cards | PROJECT.md |
| `/preregister` | hypotheses and analysis plan before the data is analysed | PROJECT.md |
| `/outline` | card-bound skeleton + approval | enough cards |
| `/draft <section>` | section draft + style audit | outline approved |
| `/verify-citations` | fabrication, retraction and missing-citation audit | a draft |
| `/critique` | peer-review simulation; `--panel` 4 personas, `--calibrate` stability | verify=PASS |
| `/revise <file>` | work review findings + change log | a critique report |
| `/restyle <style>` | switch citation style in one line | — |
| `/translate` | TR/EN, term table fixed first, then checked for what must not change | a section |
| `/front-matter` | thesis front matter in YÖK order, lists derived from the body | a thesis |
| `/export-excel` | styled multi-sheet Excel | registry populated |
| `/ingest-template <file>` | journal/institute template analysis, template supremacy | — |
| `/disclosures` | AI-use, CRediT and funding statements; nothing invented | — |
| `/submit-check` | full submission check + advisories + AI-disclosure reminder | PASS, Major=0 |
| `/submission-pack` | what the portal asks for, against the venue's own limits | verify=PASS |
| `/respond-review <letter>` | a real decision letter, point by point, coverage checked | a letter |
| `/retarget <venue>` | venue change after rejection | — |
| `/deposit` | preprint or corrigendum, decisions recorded rather than guessed | — |
| `/replication-package` | deposit-ready package; data that must not be shared is not copied | — |
| `/present` | talk, poster, lay summary or graphical-abstract brief | verify=PASS |
| `/merge-coauthor <file>` | what a returned file changed; nothing merged automatically | a draft |
| `/review-paper` | your referee report — the kit never reads the manuscript, you do | — |
| `/ethics-application` | committee form and consent, checked against the collection plan | — |
| `/dmp` | data management plan derived from the registers | — |
| `/defense-prep` | viva question bank + presentation scaffold | a thesis draft |
| `/supervision` | TİK / supervision progress report from the thesis's own records | a thesis |

Outside the manuscript — and all of these rest on one rule: a limit, criterion
or outcome list comes only from a file you filled in. With no authority file the
result is `UNCHECKED`, never `OK`.

| Command | Does |
|---|---|
| `/proposal` | funding proposal: objective/WP/deliverable graph, budget arithmetic, Gantt |
| `/project-report` | progress report against the registers; slippage is stated, not explained |
| `/dossier` | promotion dossier arithmetic; every index claim re-verified |
| `/syllabus` | weights, workload, observable outcome verbs, coverage |
| `/exam` | question/outcome coverage both ways, points, Bloom spread |
| `/rubric` | levels that differ by an observable behaviour, not by an adverb |
| `/accreditation` | programme/course outcome matrix both directions; computes no percentage |

## How it works

Five layers, and every tool call passes through them.

1. **The main session** writes and directs. Drafting and synthesis are never
   delegated: responsibility cannot be.
2. **Subagents** do the read-heavy work in their own contexts and return a short
   report, not hundreds of raw hits.
3. **The script layer** takes everything a rule can settle off the model. Output
   is always one JSON object.
4. **Hooks** run at the tool-call layer, so a skipped step does not skip a gate.
5. **Disk** holds the state. Seven data files can be written only by the script
   that owns them; writing them by hand is blocked.

## Turkish, as a target rather than a translation

YÖK front-matter order, Özet/Abstract equivalence, TR Dizin, DergiPark and YÖK
Thesis Center search, and a deterministic lint over the checkable half of
Turkish academic style. Where the convention is genuinely divided the script
flags the mixture and never the choice.

## Scope and boundaries

The kit is an assistant, not an author. It audits the text and the reported
process — not whether the work was actually done. A study built on fabricated
data passes every gate as long as the fabrication is reported consistently. That
is where tools end, not a gap more checking would close.

Compliance with your institution's and your venue's AI policy is yours;
`/submit-check` issues a disclosure reminder every time. Similarity screening is
your job, and [`POSITIONING.en.md`](POSITIONING.en.md) explains why the kit
refuses to produce a similarity score.

## Documentation

[`POSITIONING.en.md`](POSITIONING.en.md) scope and refusals ·
[`SECURITY.md`](SECURITY.md) what leaves your machine ·
[`CONTRIBUTING.md`](CONTRIBUTING.md) how to work on it ·
[`CHANGELOG.md`](CHANGELOG.md) every change ·
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) why no cost table is published ·
[`docs/RELEASING.md`](docs/RELEASING.md) release and DOI

**Tests:** `python -m pytest` (2390 pass; 8 live-network tests are skipped by
default; add `RUN_LIVE=1` to include them).

**Site:** one page, five sections, built with Astro. No JavaScript file is
downloaded — the whole page is one HTML file with ~4.5 KB of inline script in
it, and not one CSP directive names a host.

## Version and citation

Version **1.0.0**. Cite via [`CITATION.cff`](CITATION.cff). The DOI field is
deliberately empty: a DOI is minted by archiving, and writing one before the
archive exists is a fabricated identifier — the exact defect this kit is built
to prevent, in its own metadata. A test fails the build if it appears early.

## Licence

MIT — see [`LICENSE`](LICENSE). Commercial use, institutional distribution and
derivative work are all permitted.
