---
name: collect-data
description: "Collect data yourself when no suitable dataset exists — web/API collection or a survey / human-subject study. Produces the written protocol first (purpose, legal basis, source permission, sampling, fields, minimisation, retention, consent, ethics approval, contact), then RUNS the web collection through collect_run.py under conditions it will not relax: robots.txt gate with no override, the protocol's own field list as the allowlist, an honest User-Agent, a rate limit, a request ceiling, a resumable state file and a log of every request. Scans what came back for personal data without printing it and registers the result in analysis/datasets.jsonl as own-scraped or own-survey. Surveys are still run on an institution's platform, not here."
disable-model-invocation: true
argument-hint: "[scrape|survey] [<what you need to collect>]"
---

# /collect-data — Collect It Yourself, With a Protocol

## What this command is, and is not

It **is**: the protocol, the checks, the paperwork, the collection itself and the
register entry — the things that make collected data usable in a paper and
defensible in front of an ethics board.

It **runs the web/API collection**, through `collect_run.py`, under conditions it
will not relax: a complete protocol, a robots.txt verdict with no override flag, a
field allowlist that is the protocol's own field list, an honest User-Agent
carrying the author's contact address, a rate limit, a request ceiling and a log
of every request. The decision that a collection is permissible is still the
author's — it is made when they write the protocol and answer the robots verdict,
before a single request goes out. What changed is that the collector is no longer
improvised: the parts a reviewer asks about are the parts that used to live in a
script nobody kept.

It is **not** a survey platform, and it does not collect responses from people —
that is an institution's process running on an institution's system (§B). It also
does not log in, does not carry cookies, does not render JavaScript and does not
solve a CAPTCHA. A wall is an answer; the answer is to ask the site owner, use an
API, or find another source.

## Gate: Abort if Failed

1. **Check:** `PROJECT.md` topic and RQs are not TBD.
2. **Check:** has `/find-dataset` been run? Read `analysis/datasets.jsonl`.
   - If no register exists: say "Toplamadan önce var olanı ara — `/find-dataset`.
     Kendi verini toplamak en pahalı seçenek ve çoğu zaman gereksiz." Offer to run
     it. Proceed only if the author says the search was already done or that the
     data cannot exist publicly (their own instrument, their own cohort).

## Route: two very different jobs

| Argument | Path |
|---|---|
| `scrape` | web/API collection — §A below |
| `survey` | people answering questions — §B below |
| neither given | ask which; the difference decides everything downstream |

---

## §A — Web / API collection

### A1. Write the protocol FIRST

Create `analysis/collection-protocol.md` from this skeleton and fill it **with the
author**, not on their behalf. Every heading is a question a reviewer or an ethics
board asks, and `collection_check.py --protocol` checks that each exists:

```markdown
# Veri Toplama Protokolü — <proje>

## Amaç            <!-- hangi RQ, hangi değişken -->
## Hukuki dayanak  <!-- ToS'un ilgili maddesi, KVKK/GDPR dayanağı, lisans -->
## İzin / kaynak   <!-- robots.txt sonucu, API koşulları, hız sınırı, iletişim -->
## Örnekleme       <!-- hangi sayfalar/kayıtlar, hangi aralık, neden bu -->
## Alanlar         <!-- toplanacak her alan, tek tek; veri sözlüğü -->
## Veri minimizasyonu <!-- toplanmayacak alanlar ve neden -->
## Saklama         <!-- nerede, ne kadar, ne zaman silinecek -->
## Onam            <!-- insan verisi yoksa: "uygulanamaz — gerekçe" -->
## Etik kurul      <!-- gerekiyor mu, başvuru no / gerekmiyorsa gerekçe -->
## İletişim        <!-- sorumlu kişi -->
```

Then:

```bash
python scripts/collection_check.py --protocol analysis/collection-protocol.md
```

Exit 2 lists the missing sections. Do not proceed past a missing section by
promising to write it later — the protocol exists to be written before the
collection, because afterwards it is a justification rather than a plan.

### A2. Check what the site itself says

```bash
python scripts/collection_check.py --robots "<the exact URL you will fetch>"
```

Report the verdict **and** the sentence it carries: robots.txt is a request, not
the law. Three outcomes, three different next steps:

- **allowed: false** → stop. Look for an API, ask the site owner in writing, or
  find another source. Do not suggest changing the User-Agent, and do not
  "interpret" the rule away.
- **publishes_rules: false** (no robots.txt) → an absence of a rule is not a
  permission. The ToS and copyright questions are still open and still the
  author's to answer.
- **allowed: true** → proceed, at the declared `crawl_delay` (or 1 request/second
  if none is declared), identifying yourself honestly in the User-Agent.

Record the verdict in the protocol's *İzin / kaynak* section, with the date. That
line is what the methods section will say and what a challenge will be answered
with.

### A3. Write the plan, pilot it, then run it

The plan is the machine-readable half of the protocol — `analysis/collection-plan.json`:

```json
{
  "name": "<short name, becomes the folder under analysis/data/>",
  "mode": "api",
  "protocol": "analysis/collection-protocol.md",
  "contact": "<the address the site owner would write to>",
  "url_template": "https://example.org/api/items?page={n}",
  "range": [1, 40],
  "record_path": "data.items",
  "fields": {"title": "title", "published_at": "published_at"}
}
```

`mode: "api"` extracts by dotted JSON path and is the mode to prefer whenever the
site offers one. `mode: "html"` extracts by regex (`row_pattern` splits the rows,
each field's pattern captures one group) — the kit ships no HTML parser and does
not pretend otherwise: markup changes and yesterday's pattern returns zero rows
today, which is reported as zero rows.

Then, in this order and never out of it:

```bash
python scripts/collect_run.py --plan analysis/collection-plan.json --dry-run
python scripts/collect_run.py --plan analysis/collection-plan.json --limit 5
python scripts/collect_run.py --plan analysis/collection-plan.json
```

The dry run makes every request-free check: protocol completeness, the field
allowlist, and the robots verdict for every host. It refuses — and there is no
override — when the protocol is missing a section, when a field in the plan
appears nowhere in the protocol, or when robots.txt disallows the path. Report the
refusal as it is written; the undeclared-field one in particular is the check that
keeps "we only collected the post text" true six weeks later.

`--limit 5` is the pilot. Look at `rows.csv` before spending the site's bandwidth
on 40 pages: an extractor that returns empty strings is a five-request discovery
or a four-hundred-request one.

The full run stops on its own ceiling (`--max-requests`, default 200;
`--max-minutes`, default 30) and on a 429/503 — the server asking for a lower
rate. Raise `--min-delay` and resume with `--resume`; never retry harder. Every
request is in `request-log.jsonl` with its status and row count, which is what the
methods section describes and what a challenge is answered with.

A long collection belongs in the author's own terminal, not in a session that
will lose its context halfway through — `--resume` exists so it can be picked up.

### A4. Check what came back, then register it

```bash
python scripts/collection_check.py --scan analysis/data/<collected files>
python scripts/dataset_db.py add --payload '{"name":"…","source":"own-scraped", …}'
python scripts/dataset_db.py attach DS-000N analysis/data/<files>
```

The scan reports personal data by count and column, never by value. If it finds
any, the honest options are: remove the column, pseudonymise it with a key held
outside the repository, or aggregate — and then say which one was done, in the
protocol and in the register's `ethics.pii` field. "We did not intend to collect
it" is not one of the options.

---

## §B — Survey / human-subject collection

### B1. Ethics approval comes first, and the kit will not pretend otherwise

Ask, before anything else: **does this study need ethics-board (etik kurul / IRB)
approval, and does it have it?** In Turkey most university studies involving human
participants require approval from the institution's ethics committee before data
collection begins — not after.

- Approval exists → record its reference number; it goes in the protocol, in the
  register's `ethics.irb`, and in the paper's declarations (`/disclosures`).
- Approval is pending → prepare everything else, collect nothing.
- Approval is judged unnecessary → the author writes why, in the protocol. The kit
  does not make that determination and does not endorse it.

### B2. Protocol + instrument + consent text

Same protocol file as §A, plus two artifacts the study cannot run without:

- `analysis/survey-instrument.md` — every item, its response scale, and which RQ
  or construct it serves. Items that serve no RQ are the most common source of
  needless personal data; drop them here, before they are asked.
- `analysis/consent-form.md` — an informed-consent text: purpose, what is
  collected, voluntariness and the right to withdraw, retention and deletion,
  anonymity or pseudonymity, contact, and the ethics reference. Draft it, then
  say plainly that the institution's own template, where one exists, overrides
  this draft.

Measurement-quality questions — construct validity, scale reliability, sample
size and power, pilot testing — are `methodology-advisor`'s, not this command's.
Dispatch it with the instrument before the survey goes out; a survey that has
already been answered cannot be redesigned.

### B3. Collection happens on a platform, not here

The author runs the survey (institutional platform, Google Forms, paper). The kit
does not collect responses from people.

### B4. What comes back is personal data until proven otherwise

```bash
python scripts/collection_check.py --scan analysis/data/responses.csv
```

Then, before any analysis:
- remove or pseudonymise direct identifiers (name, e-mail, phone, national id);
- check indirect re-identification: a small cell (department × age × gender) can
  identify one person as effectively as a name;
- register with `"source": "own-survey"`, `ethics.human_subjects: true`,
  `ethics.irb: "<reference>"`, `ethics.pii: "removed" | "pseudonymised"`.

`dataset_db.py verify` reports human-subject data with no ethics reference as a
problem, every time it runs, until it is declared.

---

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗂  Toplama protokolü hazır
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Protokol:  analysis/collection-protocol.md — 10/10 bölüm ✓
robots.txt: allowed · crawl-delay 5s (kaydedildi, <tarih>)
Etik:      etik kurul onayı 2026/117 · onam metni hazır
Toplama:   38/40 istek · 1.184 satır · 5,0 sn gecikme · durdu: yok
Alanlar:   title, published_at (protokolde tanımlı olanlar — başka alan yazılmadı)
Kayıt:     DS-0003 (own-scraped) · 4 dosya · SHA-256 kayıtlı
PII taraması: 0 bulgu

Açık kalan: <her biri tek satır>
```

Never report a protocol as "complete" when `collection_check.py --protocol` exits
2, and never report a collection as clean when the scan found something. The whole
value of this command is that its report can be handed to a committee.

## Reference

- **Scripts:** `python scripts/collection_check.py` (`--protocol`, `--robots`,
  `--scan`) · `python scripts/collect_run.py` (`--dry-run`, `--limit`, `--resume`
  — runs the collection the protocol describes) · `python scripts/dataset_db.py`
  (registers the result)
- **Subagent:** methodology-advisor (instrument design, sampling, power) —
  dispatch before collection, never after
- **Related:** `/find-dataset` (do this first), `/disclosures` (the ethics and
  data statements the paper must carry), `/analyze-data`
- **Writes:** `analysis/collection-protocol.md`, `analysis/collection-plan.json`,
  `analysis/survey-instrument.md`, `analysis/consent-form.md`,
  `analysis/data/<name>/{rows.csv,request-log.jsonl,collect-state.json}`, and
  `analysis/datasets.jsonl` via dataset_db.py

---
*The protocol is written before the collection. Afterwards it is not a protocol, it is an explanation.*
