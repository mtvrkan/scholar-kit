# Performance and cost — how to measure it, and why no table is printed here

**Türkçe özet aşağıda.**

## Why this page has no numbers

The obvious thing to publish here is a table: `/lit-review ≈ 40k tokens`,
`/draft ≈ 25k`, `a full paper ≈ $12`. Almost every comparable project publishes
one. This kit does not, for the same reason it refuses to print a similarity
score or ship a fabricated reviewer gold label:

**Nobody has measured those numbers, and a table would be believed anyway.**

A per-command figure depends on your paper's length, your corpus size, how many
sources `source-analyst` reads, whether MCP servers are connected, how often you
compact, and how much of the conversation was you thinking out loud. Across two
real projects the same command can differ by an order of magnitude. A single
figure presented as "typical" would be, at best, one anecdote wearing the costume
of a benchmark — and it would age silently as models and prices change.

The kit's own [`eval/MEASUREMENT.md`](../eval/MEASUREMENT.md) sets the standard:
*what did this number measure, and does it say what it did not measure?* An
invented cost table fails that question at the first word.

So this page ships the instrument instead of the answer.

## Measure your own

```bash
python scripts/token_report.py --per-command --per-session
```

It reads Claude Code's own session transcripts for the current project
(`~/.claude/projects/<project-path-slug>/*.jsonl`) and reports the tokens they
actually recorded. Nothing is estimated or modelled.

What you get:

| Field | What it is |
|---|---|
| `total` | input / output / cache-write / cache-read, summed |
| `main_session` vs `subagents` | the architecture claim, made checkable |
| `by_model` | per-model split (a Haiku subagent is not an Opus turn) |
| `by_command` | per slash command, with turns and invocations |
| `cache_read_share` | share of prompt tokens served from cache |
| `excluded_commands` | buckets deliberately NOT attributed, and why |

### Cost

No prices are stored in this repository and none are inferred. To get a cost
column, supply your own rates:

```json
{
  "claude-opus-5":  {"input": 5.0, "output": 25.0, "cache_write": 6.25, "cache_read": 0.5},
  "claude-sonnet-5": {"input": 3.0, "output": 15.0}
}
```

```bash
python scripts/token_report.py --rates my-rates.json
```

Figures are USD per **million** tokens; get them from your own billing page, not
from this document. A model with no entry reports `null`, not `0` — "not priced"
and "free" are different statements.

## How to read the output honestly

**`cache_read_share` is the number that matters most.** The kit's design — state
on disk, subagents that die in their own contexts, read-once delegation — exists
to keep the conversation prefix stable so it stays cached. Cache reads are billed
far below fresh input, so a raw token total systematically **overstates** spend.
Report the share alongside the total or the total means little.

**`by_command` inflates conversational commands.** The attribution rule is stated
in the output itself: a command owns every assistant turn from its invocation
until the next command or the end of the session — your follow-up questions,
corrections and tangents included. That is a choice, not a measurement. Read
`turns` next to `tokens_per_invocation`: 200k tokens over 40 turns was a
conversation you had, not what the command intrinsically costs.

**Claude Code's own commands are excluded, not hidden.** `/compact`, `/clear` and
friends are real spend, but they are not this kit's commands; letting them
inherit the previous command's bucket would charge `/draft` for the cost of
compaction. They appear in `excluded_commands` with their invocation counts, and
their turns land in `(no command — direct conversation)`.

**`/status` is ambiguous and says so.** It is both a Claude Code builtin and a
command this kit defines, and the transcript records only the name. Rather than
guess, the report names the collision.

**Your numbers do not transfer.** A report from your thesis project says nothing
about someone else's clinical review. Do not quote it as a benchmark; if you
publish it, publish the corpus size and paper length beside it.

## What is genuinely NOT measurable here

- **Quality per token.** The whole twin constraint is *quality at low spend*, and
  this tool measures exactly one half of it. Nothing here says the output was
  good.
- **Counterfactual spend.** How many tokens the same paper would have cost
  without the kit is unknown and unknowable from a transcript.
- **Wall-clock time and API latency.** Not recorded per turn in a usable form.
- **Anything before your first session.** The report starts where your
  transcripts start.

---

## Türkçe

Bu sayfa bilerek **rakam içermiyor**. Komut başına token/maliyet tablosu
yayımlamak kolay olurdu ve rakip projelerin çoğu yayımlıyor — ama o sayıları
kimse ölçmedi, buna rağmen okuyan inanır. Bir komutun maliyeti makalenizin
uzunluğuna, korpus büyüklüğüne, kaç kaynağın tam metin okunduğuna, MCP'nin bağlı
olup olmadığına ve konuşmanın ne kadarının sizin düşünmeniz olduğuna bağlıdır;
iki gerçek projede aynı komut on kat farklı çıkabilir. Kitin kendi ölçüm
standardı ([`eval/MEASUREMENT.md`](../eval/MEASUREMENT.md)) şunu soruyor: *bu
sayı neyi ölçtü ve neyi ölçmediğini söylüyor mu?* Uydurma bir tablo bu soruyu
ilk kelimesinde geçemez.

Bu yüzden cevabı değil, **ölçüm aracını** veriyoruz:

```bash
python scripts/token_report.py --per-command --per-session
python scripts/token_report.py --rates kendi-fiyatlarim.json   # maliyet için
```

Araç, Claude Code'un bu proje için tuttuğu oturum transcript'lerini okur ve
**gerçekten kaydedilmiş** token sayılarını raporlar: toplam, ana oturum ↔
subagent ayrımı, model kırılımı, komut kırılımı ve önbellek okuma oranı. Hiçbir
şey tahmin edilmez. Fiyat bu depoda tutulmaz; `--rates` ile kendi fiyatlarınızı
verirsiniz, vermezseniz maliyet sütunu hiç basılmaz.

Okurken üç şeye dikkat: **`cache_read_share`** en önemli sayıdır (önbellekten
gelen istem tokenları çok daha ucuz faturalanır, dolayısıyla ham toplam harcamayı
sistematik olarak **abartır**); **`by_command`** sohbete dönüşen komutları şişirir
(atıf kuralı çıktının içinde yazılıdır — `turns` ile birlikte okuyun); ve
**sizin sayılarınız başkasına transfer olmaz**.

Ölçülemeyen: token başına **kalite**, kit olmasaydı ne kadar harcanacağı, ve
transcript'lerinizden önceki hiçbir şey.
