# Contributing

**Türkçe özet en altta.**

Thank you for looking. This document describes what the repository actually
enforces, so you can find out in thirty seconds whether a change will be accepted
instead of after a review round.

## Before anything else: read the boundary

[`POSITIONING.md`](POSITIONING.md) records eight mechanisms this kit **refuses**,
with the reasoning for each. A pull request implementing one of them will not be
merged on its merits — crossing that line is a scope change, and the process for
it is written at the bottom of that document: amend the record with your
reasoning, log a dated entry in [`DECISIONS.md`](DECISIONS.md), *then* write code.

Most rejected contributions to a project like this are rejected for being good
ideas in the wrong project. Five minutes there saves an afternoon here.

## Where to start reading

The repository is large — 69 tools, 54 skills, 10 agents, 2509 tests — and
almost none of it is load-bearing for a first change. These twelve files are.
Read them in this order and you will have the whole design; everything else is
an application of it.

| # | File | Why this one |
|---|---|---|
| 1 | [`CLAUDE.md`](CLAUDE.md) | The ten invariants. Every rule below is one of them, enforced. |
| 2 | [`POSITIONING.md`](POSITIONING.md) | What the kit refuses, and why refusing is the feature. |
| 3 | `scripts/lib_common.py` | Atomic writes, cross-process locking, path sandboxing, the read-only marking of the nine data files. Every script imports it. |
| 4 | `.claude/hooks/_shell_write_sink.py` | Shared write-sink detection, and the densest defect history in the repo. Its header is the best single argument for how this project reviews itself. |
| 5 | `.claude/hooks/phase_gate.py` | Invariant 3 — the three gates that actually block. |
| 6 | `.claude/hooks/protect_data_files.py` | Invariant 6, and how it divides labour with #3's permission bit. |
| 7 | `scripts/registry_db.py` | The canonical script shape: JSON out, `require_within_cwd`, locked read-modify-write. Copy this one. |
| 8 | `scripts/doi2bib.py` | The zero-fabrication chain's root — DOI content negotiation, and the verification that calls fabrication. |
| 9 | `scripts/claim_check.py` | What citation verification structurally cannot check: whether the source says it. |
| 10 | [`eval/MEASUREMENT.md`](eval/MEASUREMENT.md) | How the kit measures itself, and the parts where the honest answer is "not measured". |
| 11 | [`tests/README.md`](tests/README.md) | Which tests protect what, and why some are named after a review round. |
| 12 | [`DECISIONS.md`](DECISIONS.md) | Not front to back — it is long on purpose. Grep it for the file you are about to change; most non-obvious lines have an entry saying which alternative was rejected. |

Two things worth knowing before you change any of them: a docstring here is
often the only surviving record of a shipped bug (which is why there is no
`ruff format` step to reflow them), and `DECISIONS.md` is authoritative for
*why* while the tests are authoritative for *what*.

## Setup

```bash
git clone https://github.com/mtvrkan/scholar-kit && cd scholar-kit
pip install -r requirements-dev.txt      # requirements.txt + pytest, ruff, bandit
pre-commit install                       # optional; runs the fast checks on commit
python scripts/validate_kit.py           # structural integrity
python -m pytest -q                      # the suite CI runs
```

Five commands must pass before you push, because these are exactly what CI runs
on Ubuntu, Windows and macOS across Python 3.10 and 3.13:

```bash
python scripts/validate_kit.py
python -m pytest -q
python scripts/run_evals.py --strict            # gold-set thresholds
python -m ruff check .                          # config + rationale: ruff.toml
python -m bandit -q -ll -r scripts .claude/hooks
```

`pre-commit install` runs the last two (plus a secret scan) on every commit in
under ten seconds, which is why the slow ones are not in it — see
`.pre-commit-config.yaml`.

Plus, if you touched anything under `.claude/`:

```bash
claude plugin validate . --strict
```

## The rules that are actually enforced

Not style preferences — things that fail the build.

**A script's output is JSON.** Every tool in `scripts/` prints one JSON object
and nothing else. A human-readable line printed alongside it breaks the callers
that parse it.

**Advisory checks are WARN-only.** A new check exits 0 even when it finds
something, and offers `--strict` for callers who want it to gate. Three things
already block — the outline gate, `verify=PASS`, and Major=0 — and adding a
fourth is a scope decision, not a feature.

**Paths are sandboxed.** Anything taking a path calls `require_within_cwd()` from
`lib_common.py` before touching it. The two current exceptions are deliberate and
commented: `run_evals.py` guards against the kit root (gold sets are kit-owned),
and `token_report.py` reads transcripts from the home directory (they live
outside every project by design, and it only reads).

**Missing data is reported, never zeroed.** This is the rule most PRs get wrong.
"I found nothing" and "I did not look" are different statements, and collapsing
them is the defect class this kit exists to prevent. A venue with no cached
metadata reports `unknown` with the command that would resolve it, and raises no
concern. A transcript directory with no usage reports `no-usage`, not `0 tokens`.
A skipped failure mode reports `SKIPPED` **with its reason**.

**A number in a document is checkable.** `tests/test_governance_docs.py` pins the
figures in both READMEs to the files that produce them. Bump a count in one place
and the suite tells you the others.

**A lint rule has to be able to find a defect.** `ruff.toml` selects `E,W,F,B`
and disables `E501/E402/E702/E731/E741` — each with its reason written next to
it, and a test that fails if a future entry arrives without one. The criterion
is stated once at the top of that file: enabled if violating it can indicate a
defect, disabled if it can only indicate a taste. That is why there is no
formatter step and no line-length gate. Coverage is wired the same way — a
regression floor in CI, deliberately unpublished, because most of this suite
drives the scripts as subprocesses that the collector cannot see.

**`SKILL.md` bodies stay under 520 lines.** `validate_kit.py` enforces it. Detail
goes into `reference/` files, one level deep — that is the progressive-disclosure
design, not an arbitrary cap. If you are at the limit, something in the body
belongs in a reference file.

**Never hand-write bibliographic data.** BibTeX comes from `doi2bib.py` or is
stamped `verified:false`. This applies to fixtures and test data too.

## Adding things

**A script** → `scripts/<name>.py`, add it to `SCRIPTS` in `validate_kit.py`, add
`tests/test_<name>.py`, and bump the tool count in both READMEs (a test checks
it). Module docstring states what it does **and what it cannot** — every existing
script has that paragraph and it is the most useful part of each.

The rest of that list, in the order the suite will tell you about it — every item
is enforced by a test, so this is a checklist, not advice:

- `tests/conftest.py`'s `AREAS` **and** the table in `tests/README.md` — a test
  file in neither fails the build, and so does an area named in one but not the
  other;
- `web/src/data/tools.ts` (the tool, with its `refuses` line) and the counts in
  `web/src/data/site.ts`, then `npm --prefix web run build`. The built `docs/`
  is compared against `scripts/`, so a tool that exists but is not on the page
  fails;
- `python web/make_og.py` if any count in `site.ts` changed — the share card
  renders those numbers;
- the tool and test counts in **this** file;
- `SECURITY.md` if the script makes a network call: it must be named in the
  document, and every fixed host it contacts must be in the table **and** in
  `test_governance_docs.py`'s `DECLARED_HOSTS`. A script whose destination the
  *user* chooses belongs in the "three whose destination you choose" section
  instead, with what it does and does not send;
- `CLAUDE.md`'s script list — the one the orchestrator actually reads.

**A slash command** additionally needs at least one entry in
`eval/golden-prompts.json` (a prompt a real user would type, ideally one that
discriminates it from the neighbour it is easiest to confuse with) and the
`N prompts / M skills` line in `eval/ROUTING-EVAL.md`. A skill with no golden
prompt is a description nothing measures.

**A DECISIONS.md entry** needs its own line in the collapsed contents list *and*
the `Contents (N entries)` count bumped. All three are checked against each other.

**A check inside an existing script** → extend it, don't add a new script. Wire
it into the skill that should run it and say there how to read the output.

**A skill** → `.claude/skills/<name>/SKILL.md` with frontmatter (`name`,
`description`, `disable-model-invocation` for slash commands, `argument-hint`).
The `description` is what routes work to it, so write it for the router: when to
use it, and when to use something else instead.

**An agent** → `.claude/agents/<name>.md`, and add the file path to the `agents`
array in `.claude-plugin/plugin.json` — that array is hand-listed and a test
compares it against the directory, because a forgotten entry ships a plugin
missing an agent silently.

**A test** → extend the existing file for that unit; don't create a parallel one.
Name it after the behaviour, not the function: `test_zero_events_in_both_arms_is_refused_for_ratio_measures`,
not `test_binary_2`. Comment *why* the case matters when it isn't obvious —
several tests here exist because a specific bug shipped once.

Numeric expectations in tests should be hand-computed from the cited formula, or
exact by construction. `tests/test_lib_stats.py` validates distribution functions
against analytic identities rather than remembered table values, for a reason:
a wrong table value can agree with wrong code; an identity cannot.

## The site

`web/` is the **source**; `docs/` is **generated output that is committed**. That
is deliberate: GitHub Pages serves `docs/` from `main`, so the deploy needs one
setting and one DNS record and no CI workflow at all.

```bash
npm --prefix web install     # once
npm --prefix web run dev     # localhost with hot reload
npm --prefix web run build   # writes ../docs — commit the result
```

Never edit anything in `docs/` — including `docs/PERFORMANCE.md` and
`docs/RELEASING.md`, which look perfectly editable and are copies. Their source is
`web/public/`. Two tests catch that mistake: one compares every `web/public/` file
against its built copy, and one requires the version rendered into the pages to
match `CITATION.cff`. Both fail on a stale build.

Facts about the repository — the tool list, command list, agent list, counts —
live in `web/src/data/`, never inline in a page. A number appears once.

The site is built with Astro because these pages have no interactivity worth a
framework runtime: the only script is a ~20-line language toggle, and the build
ships **0 KB of JavaScript**. Keep it that way; a component that needs client-side
React is a sign the content belongs somewhere else.

Two things the build does that are easy to undo by accident:

- **`postbuild.mjs` injects the Content-Security-Policy**, naming the SHA-256 of
  every inline script on the page. Pages cannot set headers, so the policy has to
  travel in a `<meta>` tag, and hashing after the page exists is the only way the
  hash cannot drift from the script it authorises. Consequences: no inline
  `style` attribute anywhere (`style-src 'self'`), and never hand-edit a built
  page — the browser will simply refuse to run its script.
- **The share card is generated, not drawn.** `python web/make_og.py` writes
  `web/public/og.png` from the same design and reads its counts out of
  `web/src/data/site.ts`. Re-run it whenever those counts or the palette change;
  a test checks the card exists at 1200×630 but cannot read what it says.

## Language

Kit artifacts — agent prompts, `SKILL.md`, scripts, comments, tests — are written
in **English**, for model performance. User-facing strings are **Turkish** by
default and switch with `PROJECT.md`. `README.md` and `POSITIONING.md` are
Turkish with English pairs; a change to one that is checkable in the other has a
test enforcing they agree.

## Commits and pull requests

Prefix with the kind of change: `ADD:` `FIX:` `REMOVE:` `DOCS:` `REFACTOR:`
`RELEASE:`. Say **why** in the body, not just what — `git log` here is a design
record, and several entries are the only surviving explanation for a decision.

Every code change appends to [`CHANGELOG.md`](CHANGELOG.md) under `## Unreleased`
(Keep a Changelog format). One PR, one concern. A PR that fixes a bug and
refactors around it is two PRs.

**Do not bump versions.** `CITATION.cff`, `plugin.json`, `marketplace.json` and
the CHANGELOG heading move together at release time; see
[`docs/RELEASING.md`](docs/RELEASING.md).

## Reporting a bug

Include: what you ran, the JSON the script printed, your OS and Python version,
and whether it reproduces after `python scripts/validate_kit.py`. For anything
security-relevant, use a private advisory instead — see
[`SECURITY.md`](SECURITY.md).

---

## Türkçe

**Önce sınırı okuyun.** [`POSITIONING.md`](POSITIONING.md) kitin **bilerek
reddettiği** sekiz mekanizmayı gerekçeleriyle kaydeder. Bunlardan birini
uygulayan bir PR, kalitesinden bağımsız olarak birleştirilmez — o sınırı aşmak
bir *kapsam değişikliği*dir ve süreci o belgenin sonunda yazılı.

**Nereden okumaya başlamalı:** depo büyük, ama ilk değişiklik için taşıyıcı
olan on iki dosya var — İngilizce bölümdeki *Where to start reading* tablosu
sırayı veriyor. Özeti: `CLAUDE.md` (değişmezler) → `POSITIONING.md` (sınır) →
`scripts/lib_common.py` → `.claude/hooks/_shell_write_sink.py` → `phase_gate.py`
→ `protect_data_files.py` → `registry_db.py` (script şablonu) → `doi2bib.py` →
`claim_check.py` → `eval/MEASUREMENT.md` → `tests/README.md` → `DECISIONS.md`
(baştan sona değil: değiştireceğiniz dosyayı grepleyin).

**Push'tan önce beşi de geçmeli** (CI'ın çalıştırdığı tam olarak bunlar, üç
işletim sisteminde ve iki Python sürümünde):

```bash
python scripts/validate_kit.py
python -m pytest -q
python scripts/run_evals.py --strict
python -m ruff check .
python -m bandit -q -ll -r scripts .claude/hooks
```

`pre-commit install` son ikisini (ve bir sır taraması) her commit'te 10 saniyenin
altında koşturur; yavaş olanlar bilerek dışarıda.

`.claude/` altında bir şeye dokunduysanız ayrıca `claude plugin validate . --strict`.

**Gerçekten zorlanan kurallar:** script çıktısı tek bir JSON nesnesidir · yeni
kontroller WARN-only'dir (`--strict` opsiyoneldir), engelleyen üç kapı vardır ve
dördüncüsü kapsam kararıdır · yola dokunan her şey `require_within_cwd()` çağırır
· **eksik veri sıfırlanmaz, raporlanır** (bulamadım ≠ bakmadım — bu kitin
önlemek için var olduğu kusur sınıfının ta kendisi) · belgedeki her rakam
kontrol edilebilir ve testle bağlıdır · `SKILL.md` gövdesi 520 satırı aşamaz ·
künye elle yazılmaz, `doi2bib.py`'den gelir (fixture'lar dahil) · **bir lint
kuralı kusur gösterebiliyorsa açıktır, yalnızca zevk gösteriyorsa kapalıdır**
(`ruff.toml`: kapatılan her kural gerekçesini yanında taşır, taşımazsa test
kırılır) · kapsam (coverage) CI'da yalnızca gerileme tabanıdır, yayımlanmaz —
testlerin çoğu scriptleri alt süreç olarak koşturur ve ölçer onları göremez.

**Dil:** kit artefaktları (ajan promptları, SKILL.md, script, yorum, test)
**İngilizce** — model performansı için. Kullanıcıya görünen metinler varsayılan
olarak **Türkçe**. İki dilli belgelerde kontrol edilebilir iddialar testle
eşitlenir.

**Commit:** `ADD:` `FIX:` `REMOVE:` `DOCS:` `REFACTOR:` öneki, gövdede **neden**.
Her kod değişikliği `CHANGELOG.md`'ye `## Unreleased` altına işlenir. Sürüm
numarasını siz yükseltmeyin — dört dosya birlikte, yayın anında hareket eder.

Güvenlikle ilgili bir şey için issue değil, özel danışma (private advisory)
kullanın: [`SECURITY.md`](SECURITY.md).
