# Security

**Türkçe özet en altta.**

This kit handles unpublished manuscripts, unreleased data and pre-submission
peer-review material. The first question a careful researcher should ask is not
"is there a CVE" but **what leaves my machine** — so that is what this document
answers first.

## What leaves your machine

The kit's own scripts make network calls to exactly four hosts of their own, and only these — plus, in one command, a host **you** name:

| Host | Which script | What is sent | Why |
|---|---|---|---|
| `doi.org` | `doi2bib.py` | A DOI string | Content negotiation for BibTeX — the zero-fabrication chain |
| `api.crossref.org` | `doi2bib.py` | A DOI, or a **title** for `--title-search` | Verification; title fallback when a DOI is absent |
| `api.openalex.org` | `venue_check.py`, `citation_triangulate.py` | An ISSN, a **journal title**, or a DOI | Venue index status; second-index corroboration |
| `scimagojr.com`, `doaj.org`, `elsevier.com` | `update_data.py` only | Nothing but the request | One-off download of public index datasets, on explicit `--update-data` |
| **a host you name** | `collection_check.py --robots`, `dataset_fetch.py`, `collect_run.py` | The request itself — a plain GET, no cookies, no credentials, no project data | Reading a site's `/robots.txt`, downloading a dataset you registered, running the collection your protocol describes — see below |

Everything else stays local. Concretely, these are **never** transmitted by the
kit's scripts:

- your drafts, outline, abstract or any manuscript text
- your data in `analysis/`, or any figure, table or model output
- evidence cards, review reports, verification results, the search log
- file paths, project names, or `PROJECT.md`
- any identifier of you: the User-Agent is the fixed literal
  `scholar-kit/1.0 (mailto:scholar-kit@example.org)` — a placeholder, not your
  address. The kit never reads your git config or email into a request.

  **The one exception, and it is deliberate: `collect_run.py`.** Its User-Agent
  carries the contact address **you wrote in your own collection plan**, because
  a research crawler that does not say who is behind it is exactly the thing site
  operators are entitled to block, and the honest identification is the condition
  under which the collection is defensible. It is the address you typed, it goes
  only to the hosts your plan names, and if you do not want it sent, do not run
  that command — there is no mode that scrapes anonymously.

**There is no telemetry.** No usage reporting, no crash reporting, no analytics,
no "anonymous statistics". Nothing phones home, and there is no setting to turn
off because there is nothing to turn off.

Every script that touches the network is listed above. **Eleven** files do, and
they divide into two groups that a single command cannot find together.

Eight open a socket themselves, and a text search finds them:

```bash
grep -ln "requests\.\|urlopen\|http_get_with_retry" scripts/*.py
```

— `doi2bib.py`, `venue_check.py`, `citation_triangulate.py`, `update_data.py`,
`collection_check.py`, `dataset_fetch.py`, `collect_run.py`, and `lib_common.py`
(which holds the shared retry helper the others call).

Three more open none of their own and reach the network by **running
`doi2bib.py` as a subprocess**: `write_verify_status.py`, which re-runs
`doi2bib.py --verify` before writing a PASS; `library_import.py`, which treats
your exported `.bib`/`.ris` as a list of DOIs and re-fetches every one; and
`manuscript_import.py`, which does the same with the reference list of a
manuscript written outside the kit. The requests are doi2bib’s and go to the
hosts already listed for it, but the reader asking "what happens if I run
this?" is owed the answer *it will talk to `doi.org`* — a script that reaches
the network only through a child process still reaches the network.

The grep above cannot follow a subprocess, so it answers with eight of the
eleven. That is a limit of the instrument, stated rather than hidden: this
repository’s own test reads the parsed syntax instead of the source text, which
is what caught two of these three being missing from this document. If the list
ever grows past eleven, this document is wrong — please open an issue.

### The three whose destination you choose

Eight of those eleven talk only to hosts fixed in this repository. Three do not,
and the difference is worth stating plainly rather than burying in a table: their
destination comes from something **you** wrote — a URL you passed, a dataset you
registered, a plan you filled in. None of them can reach a host you did not name.

`collection_check.py --robots <url>` fetches `/robots.txt` from the host in that
URL and nothing else — no page content, no crawling, one request, only when you
run that flag. Its two other modes (`--scan`, `--protocol`) never touch the
network, which matters because those are the ones that read files that may
contain personal data.

`dataset_fetch.py` downloads the files of a dataset that is **already in your
register**, from the URL that record (or your `--url`) names. It sends a plain
GET with no credentials and no cookies; it refuses to fetch at all until the
dataset's licence has been recorded as read; and on a 401/403 it stops and tells
you to use the host's own authenticated path rather than trying anything else.
Nothing about your project goes with the request.

`collect_run.py` is the one that makes many requests. It fetches only the URLs
your plan lists, at the rate `robots.txt` asks for (or one per second), stopping
at a request ceiling, at a time limit, and on a 429. It refuses outright when
`robots.txt` disallows the path, and there is **no flag that overrides that**. It
sends no cookies, no credentials and no JavaScript execution; what it sends is
the request and the User-Agent described above. What comes back is written to
`analysis/data/<name>/` on your machine and goes nowhere else — including the
`request-log.jsonl` that records every URL, which stays local like everything
else in the project.

### Offline use

`venue_check.py --offline` skips OpenAlex and uses local datasets only.
`citation_triangulate.py` is opt-in and never runs unless invoked. The rest of
the pipeline — evidence cards, drafting, every deterministic check, Excel and
document builds — works with no network at all. `doi2bib.py` is the one place
where going offline costs you a guarantee rather than a convenience: without it,
BibTeX cannot be machine-verified, and entries are stamped `verified:false`
rather than silently accepted.

### What is NOT covered by the above

- **MCP servers**, if you enable them (semantic-scholar, paper-search,
  scholar-sidekick). These are third-party services with their own policies, and
  a literature search necessarily sends your **search terms** — which reveal your
  topic. That is inherent to searching, not a defect, but decide deliberately:
  the kit works without MCP, falling back to `doi2bib --verify`.
- **Claude Code itself.** Your conversation and the file contents you open go to
  the model provider under their terms. Nothing in this kit changes that, and no
  kit can. If your manuscript is under an embargo or NDA that forbids third-party
  processing, that constraint applies to the whole tool, not to any one script.
- **Your own `/analyze-data` code.** The `data-scientist` agent writes and runs
  Python on your data. It is hook-scoped to `analysis/`, but a script that
  deliberately uploads something would be a script you asked for.

## Trust boundaries inside the kit

Being precise about enforcement matters more than claiming it:

- **Hooks fail OPEN — but no longer silently.** A PreToolUse hook that crashes,
  times out, or runs under a broken interpreter does not block the operation —
  it allows it. This is deliberate (a broken guard must not brick your session),
  and it means the hook layer is a *safety net*, not a security boundary.
  What changed is the reporting: a gate that cannot evaluate itself now emits a
  `⚠ Scholar-Kit gate degraded` notice naming the gate and stating that the call
  was allowed. Exit 0 with no output is byte-identical to "checked, nothing to
  gate", so a broken gate used to be indistinguishable from a passing one; the
  notice is what separates them (`.claude/hooks/_degrade.py`). The notice
  carries the exception's type and origin only, never its message and never any
  part of the tool input — a hook sees draft prose and shell commands, and
  `str(exc)` built from those is a content-leak channel.
  The one deliberate exception is an EMPTY payload, which stays silent: a probe
  with no stdin is not a broken gate, and warning on every such call would train
  you to ignore the warning that matters.
  `INSTALL.sh` and `/new-project` patch the interpreter path for exactly this
  reason; if you skip both, enforcement is silently absent rather than visibly
  broken — that path is upstream of the hook and no notice can cover it.
  A hook that receives a payload it does not recognise — valid JSON that is not
  an object, or an object with no `tool_name` — is covered by the same notice
  as of D-091. That case is not hypothetical: it is the shape a change in the
  harness's own hook contract would have, and until D-091 every gate answered
  it by exiting 0 with no output, which reads as "checked, nothing to gate".
- **The `allow` list in `settings.json` is prefix-matched, not sandboxed.**
  `Bash(python scripts/*)` approves anything that *starts* that way, so a
  chained command (`python scripts/validate_kit.py && …`) is approved along
  with it. This is a property of how permission rules work, not of these
  particular rules — a narrower pattern would carry the identical hole while
  looking tighter — and it is why the write-protection layers above are hooks
  and OS permissions rather than allow rules. What the allow list buys is fewer
  prompts for the kit's own scripts; what it does not buy is a boundary. If you
  run with `--dangerously-skip-permissions`, it buys nothing at all.
- **Protected data files** (`registry.jsonl`, `cards.jsonl`, `venues.jsonl`,
  `references.bib`, `search-log.jsonl`, `verify-status.json`) are write-blocked
  by `protect_data_files.py` plus deny rules in `settings.json`. They change only
  through `scripts/`. Two layers, both bypassable by a determined user with a
  shell — this prevents accident, not malice.
- **Agent write scope** (`agent_write_scope.py`) confines `format-engineer` to
  `build/`, `exports/`, `templates/ingested/`; `data-scientist` to `analysis/`;
  `source-analyst` to `evidence/extracts/`. The orchestrator session is
  deliberately unrestricted — it is you.
- **Project scope.** Every enforcement hook no-ops unless `PROJECT.md` sits in
  the working directory. Installed as a plugin, the hooks would otherwise fire in
  every unrelated repository you open.

## Reporting a vulnerability

Open a **private security advisory** on GitHub:
**Security → Advisories → Report a vulnerability** at
`github.com/mtvrkan/scholar-kit`. Please do not open a public issue for anything
exploitable.

Include what you did, what happened, and what you expected. A proof-of-concept
repository or a failing test is the fastest possible report.

Expect an acknowledgement within a week. This is a single-maintainer project, so
that is a realistic commitment rather than an SLA.

### In scope

- A path that writes outside the project directory, or reads a protected file
- Command or path injection through a filename, DOI, title, ISSN, or any field
  that reaches a script
- A hook that can be made to *allow* what it exists to deny (fail-open beyond
  the documented crash case)
- Any script transmitting content this document says stays local
- A dependency advisory affecting `requirements.txt`

### Out of scope

- Prompt injection through a *source you chose to ingest*. If you feed the kit a
  PDF containing adversarial instructions, an agent may follow them; the
  mitigations are the phase gates and the fact that you approve each stage. This
  is a known, documented limit of every LLM tool, not a bug in this one.
- The fail-open hook design, which is intentional and documented above.
- A fabricated citation surviving because it was *consistently* fabricated. See
  `POSITIONING.md` § the honest failure shape: the kit audits the text and the
  reported process, not whether the work was done.
- Anything requiring an attacker to already have shell access as you.

## Supported versions

The latest released version. This is a young single-maintainer project; there is
no long-term support branch, and pretending otherwise would be worse than saying
so.

---

## Türkçe

Bu kit yayımlanmamış makaleleri, paylaşılmamış veriyi ve gönderim öncesi hakem
materyalini işler. Sorulacak ilk soru "açık var mı" değil, **makinemden ne
çıkıyor**dur.

**Ağa çıkan tek şey:** `doi.org` ve `api.crossref.org`'a bir **DOI** (ya da
`--title-search` ile bir **başlık**), `api.openalex.org`'a bir **ISSN/dergi
adı/DOI**, ve yalnızca `--update-data` dediğinizde indeks veri setlerinin
indirilmesi. Hepsi bu.

**Asla gönderilmeyen:** taslaklarınız, özetiniz, `analysis/` altındaki veriniz,
şekiller, kanıt kartları, hakem raporları, doğrulama sonuçları, dosya yolları,
proje adı, `PROJECT.md` — ve kimliğiniz. User-Agent sabit bir yer tutucudur
(`scholar-kit@example.org`), sizin adresiniz değil. **Tek istisna, bilinçli
olarak: `collect_run.py`** — kendi toplama planınıza yazdığınız iletişim
adresini User-Agent'ta taşır, çünkü kim olduğunu söylemeyen bir araştırma
kazıyıcısı site sahibinin haklı olarak engellediği şeydir. Yazdığınız adrestir,
yalnızca planınızın adlandırdığı host'lara gider, ve gitmesini istemiyorsanız o
komutu çalıştırmayın: anonim kazıyan bir mod yoktur.

**Telemetri yok.** Kullanım istatistiği, hata raporu, analitik yok. Kapatma
ayarı da yok, çünkü kapatılacak bir şey yok. Doğrulayın:
`grep -ln "requests\.\|urlopen\|http_get_with_retry" scripts/*.py` → sekiz dosya.
Ağa çıkan dosya sayısı ise **on bir**: bu grep bir alt süreci izleyemediği için
kendi soketini açmayan üçünü — `write_verify_status.py`, `library_import.py`,
`manuscript_import.py`, üçü de `doi2bib.py`’ı alt süreç olarak koşturur —
bulamaz. Bu üçünün istekleri doi2bib’in istekleridir ve onun için zaten listelenen
host’lara gider. Ağtan geçen her şey yukarıdaki tabloda.
Bunlardan üçünün hedefi önceden sabit değildir ve üçünde de hedefi **siz**
yazarsınız: `collection_check.py --robots` verdiğiniz URL'in host'undan yalnızca
`/robots.txt` çeker; `dataset_fetch.py` **sicilinizde kayıtlı** bir veri setinin
dosyalarını indirir (lisans okunmadan indirmez, kimlik duvarını aşmaya
çalışmaz); `collect_run.py` yalnızca planınızın listelediği URL'leri, robots'un
istediği hızda, tavanla çeker ve robots yasağını **hiçbir bayrakla** geçemez.
Gelen veri `analysis/data/` altına yazılır, başka hiçbir yere gitmez.
`collection_check.py`'nin `--scan` ve `--protocol` modları ağa hiç çıkmaz;
kişisel veri içerebilecek dosyaları okuyanlar onlar.

**Kapsam dışı olanlar:** açarsanız MCP sunucuları (arama terimleriniz gider —
literatür taramasının doğası gereği), ve Claude Code'un kendisi (konuşmanız ve
açtığınız dosyalar sağlayıcıya gider; bunu hiçbir kit değiştiremez — makaleniz
ambargolu veya gizlilik sözleşmesi altındaysa bu kısıt aracın tamamına işler).

**Hook'lar açık başarısız olur:** çöken veya yanlış yorumlayıcıyla çalışan bir
hook engellemez, **izin verir**. Bilinçli bir tercih (bozuk bir koruma
oturumunuzu kilitlememeli) — ama bu, hook katmanının bir *güvenlik sınırı* değil
*emniyet ağı* olduğu anlamına gelir. Tanımadığı bir yük (payload) alan hook da
artık aynı uyarıyı basar: sessizce geçmek, "kontrol ettim, gateleyecek bir şey
yok" ile aynı sıfır bayttır (D-091).

**`settings.json`'daki `allow` listesi ön-ek eşleşmesidir, kum havuzu değil.**
`Bash(python scripts/*)` o şekilde *başlayan* her komutu onaylar — zincirlenmiş
bir komut (`python scripts/x.py && …`) dahil. Bu, kuralların değil izin
mekanizmasının bir özelliğidir; daha dar bir desen aynı boşluğu daha sıkı
görünerek taşırdı. Koruma katmanının allow kuralları değil hook'lar ve işletim
sistemi izinleri olmasının sebebi budur.

**Açık bildirimi:** GitHub'da **Security → Advisories → Report a vulnerability**.
Sömürülebilir bir şey için lütfen herkese açık issue açmayın.
