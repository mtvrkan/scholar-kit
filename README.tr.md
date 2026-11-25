<p align="center">
  <a href="https://scholar.mtvrkan.com">
    <img src="https://scholar.mtvrkan.com/og.png" alt="Scholar-Kit" width="820" />
  </a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/lisans-MIT-000?style=flat-square" /></a>
  <a href="CITATION.cff"><img alt="v1.0.0" src="https://img.shields.io/badge/s%C3%BCr%C3%BCm-1.0.0-000?style=flat-square" /></a>
  <a href="CONTRIBUTING.md"><img alt="test" src="https://img.shields.io/badge/test-2509%20ge%C3%A7iyor-000?style=flat-square" /></a>
  <a href="https://scholar.mtvrkan.com"><img alt="site" src="https://img.shields.io/badge/site-scholar.mtvrkan.com-000?style=flat-square" /></a>
</p>

# Scholar-Kit

[English](README.md) · [scholar.mtvrkan.com](https://scholar.mtvrkan.com)

Claude Code için akademik araştırma, makale ve tez üretim kiti:
10 uzman subagent, 54 skill: 43 komut ve 11 bilgi skill'i, araç çağrısı
katmanında çalışan 6 hook ve deterministik bir Python katmanı (69 araç).
Makalenin çevresindeki işleri de kapsar — proje önerisi ve
raporu, etik kurul başvurusu, veri yönetim planı, hakem raporu, atama dosyası,
ders izlencesi ve akreditasyon matrisi.

Türkçe ve İngilizce eşit derecede birinci sınıf hedeftir; biri diğerinin
çevirisi değildir.

## Çözdüğü sorun

Bir asistandan kaynak isterseniz üretir. Künye kusursuz biçimlenmiş olur, DOI
doğru görünür, makale ise yoktur. Buradaki her şey tek bir kusuru reddetmek
üzerine kurulu:

- **Künye hiçbir zaman modelin hafızasından gelmez.** Ya DOI içerik
  müzakeresiyle çekilir ya da `verified=false` damgası taşır.
- **Her ampirik iddia bir kanıt kartına bağlanır** (`EV-####`) ve o kart
  geldiği kaynağı adlandırır. Kartsız iddia `[CITATION NEEDED]` etiketiyle
  kalır.
- **Üç kapı prompt metninde değil, araç çağrısı katmanında çalışır**: iskelet
  onaylanmadan taslak yok, atıf doğrulaması geçmeden hakem turu yok, açık Major
  bulgu varken biçimlendirme yok.

Kapılar hook oldukları için tutar. Konuşmada atlanan bir adım, kapıyı atlatmaz.

## Kurulum

İki yol var ve farklı şeyler verirler.

**Plugin** — komutlar, skiller ve ajanlar:

```text
/plugin marketplace add mtvrkan/scholar-kit
/plugin install scholar-kit
```

Script katmanını ve hookları **vermez**; onlar projenizin içinde yaşamak
zorundadır. Bu yüzden ilk komut daima `/new-project makale`: runtime'ı kopyalar
ve hookları sisteminizdeki Python'a bağlar.

Yalnızca plugin kurup `/new-project` çalıştırmazsanız yönlendirmeleri alırsınız,
**garantileri almazsınız** — atıf kapısı, faz kapıları ve veri dosyası koruması
script + hook katmanına dayanır. Bunu hatırlamak zorunda da değilsiniz: o
çalışana kadar kitin kendi hooku oturum başında `ENFORCEMENT ABSENT` başlığıyla,
o an yürürlükte olmayan garantileri tek tek yazar.

**Klasik kurulum** — `INSTALL.sh` / `INSTALL.ps1`: bağımlılık kontrolü, hook
yorumlayıcı yaması, indeks veri setleri, MCP sunucuları. Kiti geliştirecekseniz
bu yolu seçin.

**OpenAI Codex** — aynı kit, aynı dosyalardan:

```text
codex plugin marketplace add mtvrkan/scholar-kit
codex plugin add scholar-kit@scholar-kit
```

Orada komutlar beceridir: `$new-project makale`, `$draft yöntem`. Aynı uyarı
geçerlidir ve bir ek vardır — Codex bir hooku ancak siz onayladıktan sonra
çalıştırır; projede bir kez `/hooks` ekranını açın. Neyin neye karşılık geldiği
ve Codex altında neyin daha zayıf olduğu: [`docs/CODEX.md`](docs/CODEX.md).

### Gereksinimler

- Python 3.10+, [Claude Code](https://claude.com/claude-code) veya [Codex](https://developers.openai.com/codex), `pip install -r requirements.txt`
- **bash** — her iki çıktı üreticisi de kabuk scripti. macOS/Linux'ta kurulu
  gelir; Windows'ta Git for Windows'tan gelir (`winget install --id Git.Git`).
  Yoksa pandoc ve TeX kurulu olsa bile DOCX/PDF build adımı düşer.
- *İsteğe bağlı:* pandoc (Word), MiKTeX/TeX Live (PDF). Excel ve tüm veri hattı
  bunlarsız da çalışır.
- *İsteğe bağlı:* `requirements-ml.txt` (scikit-learn, pandas, numpy,
  matplotlib) — yalnızca model eğitecek ya da sonuç şekli çizecekseniz. Bilerek
  çekirdek değil: bir literatür taraması hiç import etmeyeceği 200 MB'ı ödememeli.
- *İsteğe bağlı:* MCP sunucuları — semantic-scholar, paper-search,
  scholar-sidekick. Yoksa kit WebSearch + `doi2bib --verify` ile devam eder.

## İlk makaleniz

```text
$ claude
> /new-project makale        # sihirbaz: konu, RQ'lar, tür, dergi, stil, dil, bütçe
> /lit-review --systematic --lang both    # iki dilli tarama -> onayınız -> kanıt kartları
> /analyze-data data/olcum.csv            # kendi veriniz; sonuçlar kartlaşır
> /outline                   # kart-bağlı iskelet -> onayınız (taslak kapısı)
> /draft methods             # bölüm bölüm
> /verify-citations          # uydurma atıf kapısı; PASS olmadan sonrası kilitli
> /critique                  # temiz bağlamda hakem turu
> /submit-check              # tür + raporlama standardı + bütçe + build
```

Tez için: `/new-project tez` (YÖK ön sayfa sırası, Özet/Abstract eşdeğerliği,
`/defense-prep`).

## Komutlar

| Komut | Ne yapar | Kapı |
|---|---|---|
| `/new-project <tür>` | proje iskeleti + sihirbaz | — |
| `/status` | kısa durum özeti, her oturum başında basılır | — |
| `/lit-review` | tarama, eleme, kartlar, sentez | PROJECT.md |
| `/slr` | tam SLR hattı, qa-auditor çift göz; isteğe bağlı meta-analiz | PROJECT.md |
| `/import-library <dosya>` | .bib/.ris kütüphanesi DOI ile yeniden çekilir; ihracın hiçbir alanı gitmez | PROJECT.md |
| `/import-manuscript <dosya>` | kit dışında yazılmış makale; bölünür ve yeniden atıflanır, tek cümlesi düzenlenmez | PROJECT.md |
| `/journal-check <ad>` | dergi indeks profili; `--fit` hedefi kendi kaynakçanızdan türetir | — |
| `/find-dataset` | veri bulur, her lisansı okur, ancak okunduktan sonra indirir | PROJECT.md |
| `/collect-data` | önce protokol, sonra toplama: robots.txt kapı, her istek loglanır | PROJECT.md |
| `/experiment` | tasarım, koşu matrisi, koşu başına tek kayıt, metrikten önce sızıntı kontrolü | kayıtlı veri seti |
| `/analyze-data <yol>` | analiz, şekiller, tablolar, kendi sonuç kartları | PROJECT.md |
| `/preregister` | veri analiz edilmeden önce hipotez ve analiz planı | PROJECT.md |
| `/outline` | kart-bağlı iskelet + onay | yeterli kart |
| `/draft <bölüm>` | bölüm taslağı + üslup denetimi | iskelet onaylı |
| `/verify-citations` | uydurma, geri çekilme ve eksik künye denetimi | bir taslak |
| `/critique` | hakem simülasyonu; `--panel` 4 persona, `--calibrate` kararlılık | verify=PASS |
| `/revise <dosya>` | bulguları tek tek işler + değişiklik günlüğü | bir kritik raporu |
| `/restyle <stil>` | atıf stilini tek satırda değiştirir | — |
| `/translate` | TR/EN; önce terim tablosu sabitlenir, sonra değişmemesi gerekenler denetlenir | bir bölüm |
| `/front-matter` | YÖK sırasıyla tez ön sayfaları, listeler gövdeden türetilir | bir tez |
| `/export-excel` | biçimlendirilmiş çok sayfalı Excel | kayıt dolu |
| `/ingest-template <dosya>` | dergi/enstitü şablonu analizi, şablon üstünlüğü | — |
| `/disclosures` | YZ kullanımı, CRediT ve fon beyanları; hiçbiri uydurulmaz | — |
| `/submit-check` | tam gönderim kontrolü + uyarılar + YZ beyan hatırlatması | PASS, Major=0 |
| `/submission-pack` | portalın istediği her şey, derginin kendi limitlerine karşı | verify=PASS |
| `/respond-review <mektup>` | gerçek karar mektubu, madde madde, kapsam denetlenir | bir mektup |
| `/retarget <dergi>` | ret sonrası dergi değişimi | — |
| `/deposit` | preprint ya da düzeltme; kararlar tahmin edilmez, kaydedilir | — |
| `/replication-package` | depozit paketi; paylaşılmaması gereken veri kopyalanmaz | — |
| `/present` | sunum, poster, sade özet ya da grafik özet brifi | verify=PASS |
| `/merge-coauthor <dosya>` | dönen dosya neyi değiştirmiş; hiçbir şey otomatik birleşmez | bir taslak |
| `/review-paper` | sizin hakem raporunuz — kit makaleyi asla okumaz, siz okursunuz | — |
| `/ethics-application` | kurul formu ve onam, toplama planına karşı denetlenir | — |
| `/dmp` | kayıtlardan türetilen veri yönetim planı | — |
| `/defense-prep` | jüri soru bankası + sunum iskeleti | tez taslağı |
| `/supervision` | TİK / danışmanlık raporu, tezin kendi kayıtlarından | bir tez |

Makalenin dışındakiler — hepsi tek bir kurala dayanır: bir limit, ölçüt ya da
çıktı listesi yalnızca **sizin doldurduğunuz bir dosyadan** gelir. Yetke dosyası
yoksa sonuç `OK` değil, `UNCHECKED`'tir.

| Komut | Ne yapar |
|---|---|
| `/proposal` | proje önerisi: amaç/İP/çıktı grafiği, bütçe aritmetiği, Gantt |
| `/project-report` | kayıtlara karşı ilerleme raporu; sapma açıklanmaz, yazılır |
| `/dossier` | atama dosyası aritmetiği; her indeks iddiası yeniden doğrulanır |
| `/syllabus` | ağırlıklar, iş yükü, gözlenebilir çıktı fiilleri, kapsam |
| `/exam` | soru/çıktı kapsaması iki yönde, puanlar, Bloom dağılımı |
| `/rubric` | seviyeler zarfla değil, gözlenebilir davranışla ayrılmalı |
| `/accreditation` | program/ders çıktı matrisi iki yönde; yüzde hesaplamaz |

## Nasıl çalışır

Beş katman, ve her araç çağrısı bunlardan geçer.

1. **Ana oturum** yazar ve yönetir. Taslak ve sentez asla devredilmez: bir
   metnin sorumluluğu devredilemez.
2. **Subagentlar** ağır okuma işini kendi bağlamlarında bitirir; geriye yüzlerce
   ham sonuç değil, kısa bir rapor döner.
3. **Script katmanı** kurala bağlanabilen her şeyi modelden alır. Çıktı daima
   tek bir JSON nesnesidir.
4. **Hooklar** araç çağrısı katmanında çalışır; atlanan bir adım kapıyı atlatmaz.
5. **Disk** durumu tutar. Yedi veri dosyası yalnızca kendi scriptiyle yazılır;
   elle yazmak engellidir.

## Çeviri değil, hedef olarak Türkçe

YÖK ön sayfa sırası, Özet/Abstract eşdeğerliği, TR Dizin, DergiPark ve YÖK Tez
Merkezi taraması, ve Türkçe akademik yazımın kontrol edilebilir kısmını
deterministik olarak denetleyen bir lint. Konvansiyonun gerçekten bölündüğü
yerlerde script karışımı işaretler, tercihi asla.

## Kapsam ve sınırlar

Kit bir asistandır, yazar değildir. Metni ve **raporlanan süreci** denetler,
işin gerçekten yapılmış olmasını değil. Uydurma veriye dayanan bir çalışma,
uydurma tutarlı biçimde raporlandığı sürece her kapıdan geçer. Bu, daha çok
kontrolle kapanacak bir boşluk değil, araçların bittiği yerdir.

Kurumunuzun ve hedef derginin YZ politikasına uyum sizin sorumluluğunuzdadır;
`/submit-check` her seferinde beyan hatırlatması yapar. Benzerlik taraması sizin
görevinizdir; kitin neden benzerlik skoru üretmeyi reddettiği
[`POSITIONING.md`](POSITIONING.md) içinde.

## Belgeler

[`POSITIONING.md`](POSITIONING.md) kapsam ve retler ·
[`SECURITY.md`](SECURITY.md) makinenizden ne çıkar ·
[`CONTRIBUTING.md`](CONTRIBUTING.md) üzerinde nasıl çalışılır ·
[`CHANGELOG.md`](CHANGELOG.md) her değişiklik ·
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) neden maliyet tablosu yayımlanmıyor ·
[`docs/CODEX.md`](docs/CODEX.md) kit OpenAI Codex altında ·
[`docs/RELEASING.md`](docs/RELEASING.md) sürüm ve DOI

**Testler:** `python -m pytest` (2509 test geçer, 8'i canlı ağ testi olarak
varsayılanda atlanır; dahil etmek için `RUN_LIVE=1`).

**Site:** tek sayfa, beş bölüm, Astro ile derlenir. İndirilecek hiçbir
JavaScript dosyası göndermez — sayfanın tamamı tek bir HTML dosyası ve
içindeki ~4,5 KB satır içi script; CSP'deki hiçbir direktif bir host adlandırmaz.

## Sürüm ve atıf

Sürüm **1.0.0**. Atıf için [`CITATION.cff`](CITATION.cff). DOI alanı bilerek
boş: DOI arşivlemeyle üretilir ve arşiv yokken yazılması uydurma tanımlayıcıdır
— kitin engellemek için var olduğu kusurun ta kendisi, kendi metadatasında. Bir
test erken belirirse build'i kırar.

## Lisans

MIT — bkz. [`LICENSE`](LICENSE). Ticari kullanım, kurumsal dağıtım ve türev
çalışma serbesttir.
