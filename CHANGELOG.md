# Changelog

## Unreleased

### Added — kit artık OpenAI Codex altında da çalışıyor (D-099)

- Kit tek bir gövde, iki harness: beceriler, ajanlar, hooklar ve anayasa bir kez,
  Claude Code biçimlerinde `.claude/` altında yazılıyor; Codex'in okuduğu her şey
  `scripts/codex_sync.py` tarafından onlardan ÜRETİLİYOR ve tek bir klasörde,
  `codex/` altında duruyor. `--check` bayat bir dosyada testi düşürüyor; `codex/`
  içinde elle yazılmış tek satır yok. [2026-11-25]
- `.codex-plugin/plugin.json` + `.agents/plugins/marketplace.json`: aynı depo
  artık bir Codex plugini de (Codex'in kökte istediği iki sabit yol; geri kalanı
  `codex/` içinde). `codex/skills/`, `.claude/skills/`'in bayt bayt kopyası;
  `disable-model-invocation: true` taşıyan 43 komutun yanına üretilen
  `agents/openai.yaml` aynı sözü Codex'e veriyor (komut adıyla çağrılınca
  çalışır, kendiliğinden değil). 11 bilgi becerisi iki tarafta da örtük yüklenir.
- `templates/codex/codex_adapter.py`: Codex dosyaları tek bir araçla,
  `apply_patch` ile düzenler ve yükünde `file_path` yoktur — yalnızca yama metni.
  Uyarlanmamış bir kapı bu çağrıya sıfır baytla cevap verir; "denetlendi,
  kapılanacak bir şey yok" ile ayırt edilemez. Adaptör yamanın dokunduğu her yol
  için aynı kapıya bir kez sorar; tek ret tüm yamayı reddeder. Kapılar
  değiştirilmedi ve kopyalanmadı: tek yaptırım katmanı `.claude/hooks/`.
- Codex'te alt ajanların araç listesi yoktur. Adaptör, frontmatter'ında yazma
  aracı bulunmayan her ajanı `agent_write_scope` için boş kapsamla (salt-okunur)
  tutar — liste ajan dosyalarından türetilir, elle yazılmaz.
- `codex/agents/` (10 ajan, rol metni harfi harfine), `codex/hooks/hooks.json`
  (aynı altı kapı), `codex/rules/scholar-kit.rules` (Bash ret listesi →
  `forbidden`), `codex/AGENTS.md` (kısa bir okuma kılavuzunun altında
  `CLAUDE.md` aynen). Model adı YAZILMAZ: `opus/sonnet/haiku` → akıl yürütme
  çabası `high/medium/low`.
- `/new-project`, `codex_sync.py --project` ile aynı dosyaları Codex'in bir
  PROJEDE aradığı sabit yollara üretiyor; `INSTALL.sh` / `INSTALL.ps1` `codex/`
  klasörünü aynı yorumlayıcıya üretiyor ve MCP sunucularını kurulu olan her iki
  CLI'ye ekliyor. `enforcement_notice.py` `--harness codex` ile, Claude için
  kapılı ama Codex için kablosuz bir projeyi de adıyla söylüyor.
- Codex altında neyin daha ZAYIF olduğu `docs/CODEX.md`'de açıkça yazılı:
  kapılar ancak kullanıcı `/hooks` ekranında onaylayınca çalışır; salt-okunur
  ajan araç setiyle değil sözleşme + hook ile salt-okunurdur; `Read(./.env)`
  retleri ve `permissions.allow` bilerek aktarılmadı.
- 2390 -> **2509** test (README.md, README.tr.md, CONTRIBUTING.md,
  web/src/data/site.ts); 68 -> **69** araç.

## 1.0.0 — 2026-08-26

> **Sürüm numaraları yeniden düzenlendi.** Bu, kitin ilk KAMUYA duyurulan
> sürümü; ondan öncesi yayın öncesi geliştirme döngüsüydü ve artık 0.1.0–0.4.0
> olarak numaralanıyor. Tek bir satırı, tarihi ya da kaydı silinmedi — yalnızca
> başlıklarındaki numara değişti. Eski `v1.0.0`–`v1.3.0` etiketleri bu yüzden
> geçersizdi ve silindi: aşağıdaki numaralarla artık aynı şeyi göstermiyorlardı.
>
> **Git geçmişi de bu sürümde tek commit'e indirildi.** Sebebi kozmetik değil:
> yayın öncesi geçmiş, bir hocanın özel çalışma dosyalarını barındırıyordu
> (`DECISIONS.md`, D-038) ve depoyu public yapmanın belgelenmiş ön koşulu o
> geçmişin yeniden yazılmasıydı.

### Fixed — üç bölümün kartları kalıcı olarak kaymış duruyordu

- Giriş animasyonunun ön-durumu hiç serbest bırakılmıyordu. `.js #gates .cards
  > *` gibi kurallar bir ID taşıdığı için (1,2,0) puanlıyor; onları geri alması
  gereken `.js .is-in > *` ise (0,2,0) ve her seferinde kaybediyordu. Sonuç
  kalıcıydı: kapı kartları 24px aşağıda, kurulum adımları 26px aşağıda, beş
  katman kartı ise kendi grid hücresinin **14px solunda** — telefonda grid tek
  tam genişlikte sütun olduğu için bu, bölümün tamamı ortalanmamış gibi
  görünüyordu. Opacity doğru serbest bırakıldığından tek belirti "biraz yamuk"
  bir sayfaydı. Kurallar artık `:not(.is-in)` ile yazılıyor: `is-in` gelince
  bildirim eşleşmeyi bırakıyor, yani geride üstünlük kurulacak bir şey kalmıyor.
  Ölçülen kayma 0. [2026-08-26]

### Removed — telefonda menü yok

- Burger düğmesi, açtığı tam ekran sayfa, arkaplanı, kaydırma kilidi, Escape
  işleyicisi ve yeniden boyutlandırma koruması kaldırıldı. Hepsi, tek bir
  kesintisiz kaydırmadan ibaret bir sayfada beş çapa arasında atlamak içindi;
  bölümler zaten savın yürüdüğü sırada geliyor, telefonda kaydırmanın kendisi
  gezinme. Satır içi JavaScript 5,5 → 4,5 KB. [2026-08-26]
- Bunun bir yan etkisi olarak sayfadaki yatay kayma da gitti: silinen bloktaki
  `.nav { width: 100vw }` kaydırma çubuğunu da sayıyordu, yani sabit öğe görünür
  alandan bir çubuk genişliği fazlaydı ve belgeye yatay kaydırma açıyordu.
  [2026-08-26]

### Changed — TR/EN kontrolü sayfanın geri kalanıyla aynı dilde

- Dil düğmesi 999px'lik tam yuvarlak hap olmaktan çıkıp 10px köşeye geçti —
  nav öğesi 9px, menü düğmesi 10px; aradaki tek kontrol masthead'in tek yuvarlak
  nesnesiydi. Kayan işaretçi 7px ile eşmerkezli. Menü düğmesi de camın eksik iki
  parçasını (üst kenar ve blur) kazandı; onsuz, on bir piksel yanındaki panenin
  yanında sadece renkli bir kutuydu. [2026-08-26]

### Fixed — paylaşım kartı: yarım kesilen metin, görünmeyen logo

- `og:description` iki dilin birleştirilmesiyle **343 karakter** oluyordu;
  önizleme gösteren her mesajlaşma uygulaması 160-200 arasında kesiyor, yani
  kart cümlenin ortasında biten bir Türkçe parça olarak varıyor ve İngilizce
  yarısına hiçbir okur ulaşmıyordu. Kart artık tek dil konuşuyor — `og:locale`
  zaten tr_TR, `og:locale:alternate` da İngilizcenin var olduğunu söyleyen
  protokol parçası. Yeni açıklama 151 karakter ve ne yaptığını söylüyor.
  [2026-08-26]
- `og:title` de aynı şekilde iki dili orta noktayla birleştiriyordu
  ("sıfır uydurma atıf · zero fabricated citations"). Tek satır, 48 karakter.
  [2026-08-26]
- `og:image:secure_url` eklendi: spec'te var, sayfada yoktu, ve bazı
  scraper'lar HTTPS sayfalarda `og:image` yerine onu okuyup yoksa kart
  göstermiyor. [2026-08-26]
- Karttaki logo büyütüldü (marka 30→40, mark 31→44 piksel); küçük önizleme
  boyutunda mark seçilmiyordu. Mark artık kelime markasının MÜREKKEBİNE göre
  ortalanıyor: konum yüzün nominal ascent/cap değerlerinden tahmin ediliyordu ve
  bu tahmin markı 6,5 piksel yukarı koyuyordu — harfler cap-tepesinden taban
  çizgisine uzanırken markın mürekkebi kendi karesini tamamen dolduruyor, yani
  iki merkez `brand_y`'ye aynı uzaklıkta değil ve tek bir sayıyla
  yerleştirilemez. Ölçülen sapma artık 0,0 piksel. [2026-08-26]

### Removed — kiti inşa eden dosyalar kitin kendisi değil

- `SCHOLAR-KIT-PLAN.md` (575 satır) ve `web/probe.html` depodan çıktı. İlki
  kite ait değil, kiti üretmek için yazılmış bir talimat — ilk satırı
  "Execute this plan top-down" diyor; ikincisi bir CSS genişlik yoklaması.
  CHANGELOG'daki üç anımları da yolu adlandırmadan yeniden yazıldı, çünkü tek
  commit'e indirilmiş bir geçmiş, kaydı olmayan bir yolu doğrulayamaz — bunu
  denetleyen test aynı hatayı bir kez zaten yakalamıştı. [2026-08-26]

### Changed — README'ler: İngilizce öne, ve yarı yarıya kısaldı

- `README.md` artık İngilizce, Türkçe `README.tr.md`'ye taşındı. Özel geliştirme
  boyunca varsayılan README Türkçeydi; public bir depo için bu ters: `README.md`
  GitHub'ın herkese açtığı dosyadır ve onu okuyamayan kişi, diğerini bulması en
  zor olan kişidir. Türkçe ikincil olmadı — aynı testlerin tamamına tabi.
  [2026-08-26]
- İkisi de 485/492 satırdan **209/210 satıra** indi. Mimari makalesi, sorun
  giderme, dizin ağacı, maliyet bölümü ve site tasarım denemesi çıktı; komut
  tabloları kaldı ama satır başına 3-6 satırlık paragraflardan tek satıra
  sıkıştı — bir referans tablosu taranabilir olmalı. Site "43 komutun tamamı
  READMEde" diye link verdiği için tabloların taşınması o iddiayı bozardı.
  [2026-08-26]
- Emoji kaldırıldı (`🎓`, `✨`). Sitedeki README bağlantısı da tek yerine iki
  ankraja bölündü: Türkçe okuru İngilizce dosyaya göndermek, teknik olarak
  çözülen ama takip edeni yarı yolda bırakan bir bağlantıdır. [2026-08-26]

### Removed — vitrin, artefaktlarıyla birlikte

- `examples/showcase`, `examples/showcase-slr` ve `examples/showcase-slr-en`
  depodan kaldırıldı (39 dosya). Üç koşudan ikisi yazarının arkasında duracağı
  bir sonuca ulaşmadı; tamamlanmamış işi bitmiş iş gibi sergilemek kitin
  engellemek için var olduğu kusurun kendisi. [2026-08-26]
- Siteden `#vitrin` bölümü, üç koşu kartı ve masthead'deki Vitrin bağlantısı;
  READMEler ve `README.en.md`den vitrin bölümleri ve üç koşu tablosu; bu
  artefaktlara bağlı 28 test. Yayımlanan test sayısı 2415 → 2387. [2026-08-26]

### Security — Astro 7, ve sıfır zafiyet

- `astro` 5.18 → 7.2.7, `esbuild` 0.27 → 0.28, `sharp` bağımlılık ağacından
  çıktı. `npm audit` üç uyarıdan (2 high) **sıfıra** indi. Kullanılmayan
  `@astrojs/sitemap` bağımlılığı da kaldırıldı: `astro.config.mjs` zaten
  "sitemap entegrasyonu yok" diyordu, paket yalnızca duruyordu. [2026-08-26]

### Fixed — yükseltmenin sessizce söndürdüğü cam

- Astro 7 varsayılan CSS minifier'ını Lightning CSS'e çevirdi ve o, sıkıştırmakla
  kalmayıp bildirimleri hedef tarayıcılara göre YENİDEN YAZIYOR: her
  `backdrop-filter`'ı `-webkit-backdrop-filter` ile değiştirip standart özelliği
  düşürdü. Güncel Chrome artık o takma adı tanımıyor
  (`CSS.supports('-webkit-backdrop-filter', 'blur(2px)')` → false), yani bildirim
  hiçbir şeye çözülüyordu: masthead paneli, yanan gezinme öğesi, rakam şeridi —
  sayfadaki her cam yüzey blur'unu aynı anda kaybetti. Build yeşil, suite yeşil,
  hiçbir yerde hata yok; tek belirti tasarımın camdan olmayı bırakmasıydı.
  `vite.build.cssMinify: 'esbuild'` düzeltiyor,
  `test_the_built_stylesheet_keeps_the_standard_property_beside_every_prefixed_one`
  bir daha olmasını engelliyor — kural `backdrop-filter`'a özel değil: derlenen
  stil dosyası bir `-webkit-` özelliği bildiriyorsa öneksizini de bildirmeli.
  [2026-08-26]
- Açık temanın gezinme kuralları dosyada cam kuralından ÖNCE duruyordu. Media
  query özgüllük kazandırmaz, yani aynı seçicinin sonraki hâli iki temada da
  kazanıyordu: açık temanın kendi nav düzenlemesi, tam da "açık tema neyi farklı
  yapar" demek için var olan bloğun içinde ölü koddu. Kurallar cam kuralının
  arkasına taşındı ve artık yalnızca kenarlığı sertleştiriyor. [2026-08-26]

### Added — WCAG 3.1.2 ve sürümü söyleyen her yüzey teste bağlandı

- Her iki dildeki 148 bölüm artık kendi `lang` özniteliğini taşıyor. İki dil
  aynı anda DOM'da duruyor ve yalnızca `<html lang>` değişiyordu, yani belge
  yarısı için yanlış bir dil ilan ediyordu. Etkisi küçük (gizli yarı
  `display: none` ve ekran okuyucu onu seslendirmiyor) — ama bu, tek öznitelik
  ile çözülen bir sorunu düzeltmenin gerekçesi, tutmanın değil. [2026-08-26]

- Paylaşım kartının `og:image:alt`'ı iki tasarım önceki kartı tarif ediyordu:
  "üzerinde FABRICATED çıkan bir doğrulama kaydı". Kart artık bir kelime markası,
  iki satırlık başlık ve tek cümle. Alt metni tam da kontrol edemeyecek olanlar
  okur. [2026-08-26]
- `test_every_surface_that_states_a_version_states_the_citable_one`. Sürüm
  testleri makine tarafından okunan yüzeyleri (`CITATION.cff`, `plugin.json`,
  `marketplace.json`, `site.ts`, CHANGELOG başlığı) birbirine bağlıyor, insanın
  gerçekten okuduğu iki yeri hiçbir şeye bağlamıyordu — ve tam da denetimsizliğin
  izin verdiği kadar kaymışlardı: iki README de 1.0.0 rozetinin altına 1.1.0
  yazan bir cümle basıyordu, `web/package.json` da 1.1.0 diyordu. Rozet alt
  metniyle değil shields.io URL'siyle eşleşiyor; alt metin `v1.0.0` derken
  arkasındaki görsel 1.1.0 diyordu, yani etikete bakan bir test yanlış resmin
  önünden geçerdi. [2026-08-26]

### Added — SSS masthead'e

- Gezinme SSS/FAQ bağlantısını kazandı ve `#vitrin`in boşalttığı yeri aldı.
  Sayfada kendisine ulaşmanın tek yolu kaydırmak olan tek bölümdü, oysa henüz
  ikna olmamış okurun gitmek istediği yer orası. [2026-08-26]

### Fixed — var olmak ile çalışmak aynı şey değil (12 sahte hata)

- `_find_git_bash()`'in beş kopyası da adayın **var olmasına** bakıyor,
  **çalışabilmesine** bakmıyordu. Kısmi bir Git for Windows kurulumunda
  `bin\bash.exe` yerinde durur ama exec ettiği `usr\bin\` boştur; helper o ölü
  stub'ı memnuniyetle döndürüyor, hemen altındaki atlama koruması hiç
  devreye girmiyordu. Sonuç: kabuğa çıkan 12 test, bozuk bir kabuğu, test
  ettikleri scriptlerin hatası gibi raporluyordu — yani katkı verenin makinesinde
  kendi değişikliğiyle ilgisiz bir kırmızı suite. Aday artık `bash -c "exit 0"`
  ile yoklanıyor; testler geçemedikleri yerde dürüstçe atlanıyor.
  `test_pipeline_end_to_end.py`'deki altıncı, gömülü kopya da düzeltildi.
  [2026-08-26]

### Fixed — READMElerin site hakkında tutamadığı iki iddia

- "**0 KB JavaScript** (sayfanın tek script'i ~18 satırlık dil değiştirici)"
  cümlesi iki yönden birden yanlıştı. "0 KB" ölçtüğü şey için doğruydu — hiçbir
  JavaScript DOSYASI çekilmiyor, `script-src` yalnızca hash taşıyor — ama okurun
  anladığı şey için yanlıştı: HTML'in içinde 5,5 KB script gidiyor. "Tek script
  ~18 satırlık dil değiştirici" ise düpedüz yanlıştı; değiştirici küçük yarısı,
  yanında bir görünürlük gözlemcisi, bölüm takipçisi, telefon menüsü ve başa dön
  kontrolü var. İddia ayrı ayrı denetlenebilir iki parçaya bölündü ve
  `test_the_readmes_state_the_javascript_the_page_actually_ships` ikisini de
  derlenen sayfaya bağladı. [2026-08-26]
- Aynı cümle siteyi "dört bölüm" diye sayıyordu; SSS eklendiğinden beri beş.
  [2026-08-26]

### Fixed — 1.0.0 hazırlığı: sapan üç sürüm numarası

- `README.md`, `README.en.md` ve `web/package.json` 1.1.0 diyordu; hepsi
  `CITATION.cff`'in ilan ettiği 1.0.0'a çekildi. Diğer beş yüzey zaten
  1.0.0'daydı. Yayımlanan test sayısı 2388. [2026-08-26]

### Changed — gönderilen baytlarda yorum yok, ve çapalar İngilizce

- `postbuild.mjs` artık sayfaların `<!-- -->` bloklarını ve inline scriptlerin
  yorumlarını çıktıdan siliyor. Kaynaklar gerekçesiyle birlikte yazılıyor ve bu
  bilinçli; bilinçli olmayan, o gerekçenin View Source'a düşüp hiç muhatabı
  olmayan bir okura ulaşması — sayfa on sekiz paragraf tasarım notu taşıyordu.
  Kaynağı boşaltmak yerine burada yapılması kuralın kalıcı olmasını sağlıyor:
  tek seferlik silme, kendini açıklayan bir sonraki düzenlemeyle geri gelir.
  Ayıklama esbuild ile, regex ile değil — `//` her mutlak URL'de, `/* */` en az
  bir string literalinde geçiyor ve dizeyi yorumdan ayıramayan bir kalıp
  scripti sessizce bozar; CSP hash'i de bozuğunu sadakatle yetkilendirirdi.
  [2026-08-26]
- Bölüm çapaları İngilizceye çevrildi: `#genel-bakis` → `#overview`,
  `#kapilar` → `#gates`, `#nasil` → `#how-it-works`, `#kurulum` → `#install`,
  `#sss` → `#faq`. Bir fragment metin değil, tanımlayıcıdır: issue'lara,
  sohbetlere ve başkalarının belgelerine yapıştırılır. Görünen etiketler iki
  dilde kalmaya devam ediyor. [2026-08-26]

### Changed — camın hepsi, ve karta bir sayı listesi değil bir cümle

- Masthead'de seçili gezinme öğesi artık sayfanın kendi cam reçetesini
  kullanıyor (`--glass-bg` + `--glass-border` + `--glass-edge` + blur), kendi
  alfalarını karan bir kopyasını değil. [2026-08-26]
- Rakam şeridindeki filigran ikonlar geri geldi. Kaldırılma sebepleri fikir
  değil tek satır CSS'ti: dördüncü ikon `--pass` rengiyle ve yüzde dokuzda
  duruyordu, yani şeritteki tek okunabilir işaretti. Dördü de aynı mürekkep,
  aynı alfa. [2026-08-26]
- Paylaşım kartından dört sayaç kaldırıldı; kart artık tek bir iddia taşıyor.
  [2026-08-26]
- Gezinme artık gövde yüzüyle (Inter) diziliyor. Masthead'de iki şey var ve
  ikisi iki ayrı aileyle yazılmıştı; mono bu tasarımın KAYIT sesi — alan adı,
  komut, defter satırı — ve bir gezinme bunların hiçbiri değil. [2026-08-26]
- Rakam hücrelerinin dolgusu simetriğe döndü. Asimetri iki turdur yanlış
  ölçümden savunuluyordu: kutular değil MÜREKKEP ölçülünce 24/32 bloğu 3,5px
  yukarı, 40/32 ise 3,9px aşağı koyuyor; eşit dolgu yarım pikselin altında
  kalıyor. [2026-08-26]

### Fixed — ilk ekran gerçekten ilk ekran kadar

- Kahraman bölümü artık `calc(100svh - var(--head-h))`. Kuralın kendi yorumu
  "masthead sayfayı itmez, çıkarma gerekmez" diyordu; bu `fixed` için doğru,
  `sticky` için yanlış ve masthead sticky. Bölüm 4.5rem aşağıdan başlayıp tam
  bir ekran boyu istiyordu, yani katlanmanın 72px altına taşıyordu; ortalanmış
  içerik de bunun yarısı kadar aşağı kalıyordu. Üstüne, zaten açık olan bir
  masthead'i geçmek için yazılmış 7rem/4rem dolgu 24px daha ekliyordu. Pane
  çıkarılıp dolgu dengelenince ilk ekran tam katlanmada bitiyor ve kopya 60px
  yukarı geliyor. `--head-h` tek sayı olarak `.head-in`in kendi min-height'ını
  da besliyor, böylece pane boy değiştirirse ilk ekran peşinden geliyor.
  [2026-08-26]

### Fixed — logonun kendi geometrisi

- `make_og.py`'nin logosu artık dolgu alanı olarak çiziliyor (`pieslice` çifti,
  dört kat büyütülüp yeniden örneklenerek), çizgi kalınlığı olarak değil.
  Pillow `arc` ve `ellipse`'i kenar yumuşatmıyor ve kalınlığı yarıçapı
  adımlayarak üretiyordu; kartın 31px'lik markası bu yüzden dört kırık virgül
  olarak basılıyordu. [2026-08-26]

### Changed — baslik kitin kapsamina buyudu, ve paylasim karti temaya dondu

- Dorduncu baslik. Bir oncekiler belirsizdi; bu kucuktu. "Makale ve tezinizi
  Claude Code ile yazın" acikti ve yazmanin etrafina bir kutu ciziyordu —
  oysa kit proje onerisi ve ilerleme raporu, etik basvurusu ve onam formu, veri
  yonetim plani, hakem raporu, atama dosyasi, ders izlencesi ve akreditasyon
  matrisi de uretiyor. Derdi bir TUBITAK onerisi olan ziyaretci o basligi okuyup
  gider. Baslik artik kapsami, altindaki cumle araligi soyluyor. [2026-08-25]
- `make_og.py` bastan yazildi. Onceki kart sicak kagit zeminde murekkep-teal
  bir belge ciziyordu; site uc yeniden tasarimdir siyah camdi — dosyanin kendi
  docstring'inin uyardigi kayma, tam olarak o dosyanin basina gelmisti. Yeni
  kart sayfanin temasi: siyah zemin, cizgili kagit, Turkce baslik buyuk,
  Ingilizcesi altinda, uretim hatti paneli ve dort sayac. [2026-08-25]
- Zemin cizgileri daha soluk; her bolumun girisi birbirinden daha ayirt
  edilebilir, ve bolum basliklari odaktan cikip netlesiyor. [2026-08-25]

### Fixed — bir gecis, acmak istedigi seyi bozmamali

- Bolum girisleri geri alindi, ama sadelestirilerek degil duzeltilerek. Bir
  onceki turda eklenen `rotateX` her kapi kartini yamuk ciziyordu ve metnini
  egiyordu: saniyenin buyuk kismi boyunca ilk kartin basligi okunakli sekilde
  italikti ve panesi gozle gorulur bicimde dikdortgen degildi. Kosu kartlarinin
  uzerindeki blur ayni seyi cumlelerine yapiyordu. **Kendi icerigini deforme
  eden bir gecis, uzerinde zamanlayici olan bir kusurdur** — normal hizda
  kaydiran okur o gecisin tamamina bakiyor. [2026-08-26]
- Sayilar seridi: dort rakam, kendisi de yukselen bir panelin ICINDE 28px
  asagi kayiyordu, yani giris boyunca kendi kutularinin altinda, ustlerinde bos
  bir bant ile duruyorlardi — hareket degil, bozuk hizalama olarak okunuyordu ve
  dogru okunuyordu. Panel tek parca olarak yerlesiyor; icindeki figurler yalnizca
  soluyor, kendi hucrelerinin ortasindan hic ayrilmiyor. [2026-08-26]
- Bes katmanin 52 pikselllik yatay yolculugu "bunlar soldan geliyor" diye
  okunmuyordu; "bu satir ortali degil" diye okunuyordu. 14 piksele indi. Bir
  dizinin sirasini okunur yapan sey mesafe degil, KADEME. [2026-08-26]
- Sayilar seridindeki filigran isaretler kaldirildi. Yuzde dortte, dordunden
  ucu bir sekil olarak degil bir leke olarak cozunuyordu; serideki tek renkli
  isaret olan dorduncusu ise net cikiyordu — yani dort hucre, biri icinde bir
  sey varmis gibi. Bu boyda bir rakamin isarete ihtiyaci yok. Hucre dolgusu da
  optik olarak ortalandi: rakamin satir kutusu tepe yuksekliginin ustunde ~10px
  bosluk tasiyor, etiket ise taban cizgisinin altinda ~4px. [2026-08-26]
- Ikincil buton artik kenari olan bir nesne. Ikisi de 44px olcuyordu ve
  olcmuyor gibi duruyordu: acik olan siyah uzerinde neredeyse beyaz bir sekil,
  kendi dolgusu kendi konturunu ciziyor, ve karanlik zeminde parlak bir sekil
  oldugundan buyuk gorunuyor. Hayaletin dolgusu sayfanin renginden birkac puan
  farkli oldugundan ust ve alt kenarlari zemine karisiyordu. Ikisi de 44px.
  Yalnizca biri bunu soyluyordu. [2026-08-26]

### Changed — paylasim karti bastan: sade, iki dilde, ve logosu dogru

- `og.png` artik iki kart: Turkce icin `og.png`, Ingilizce icin `og-en.png`.
  Onceki surum "tek URL tek kart alir" diye akil yurutmustu ve haklıydi — ama
  sonucu, 1200x630'un icinde bir Turkce baslik, bir Ingilizce baslik, dort
  sayac, dokuz satirlik uretim hatti paneli ve iki alt satirin yaristigi bir
  kucuk resimdi. Bir paylasim karti bir saniyede okunur. Site Turkce karti
  bildiriyor (`og:locale` tek bir dil soyleyebilir); Ingilizce kart
  `README.en.md`'nin acilisi — yani kullanilmayan bir alternatif degil, kendi
  okuru olan bir belge. [2026-08-25]
- Kartin tamami 3x cizilip kucultuluyor. Pillow'un `arc`'inda kenar yumusatma
  yok ve isaret otuz piksellik dort ceyrek halka: 1x'te dort kirik lekeydi, yani
  kucuk boyutta egri cizemeyen bir kutuphanenin cizdigi bir logo. [2026-08-25]
- Menudeki secili ve hover hali saydam cam: alfalar dil kontrolununkinin yarisi
  ve arkasinda blur var. Ayni sozluk, ayni sayilar degil — cunku ikisi ayni
  zeminde durmuyor: toggle'in isareti blurlu bir panenin ICINDE, menu ogesi
  dogrudan mastheadin uzerinde. Ayni sayilar orada isik, burada boya
  okunuyordu. [2026-08-25]
- Bolum girisleri artik fark edilir: kapilar okura donerek (`rotateX`, ve
  perspektif EBEVEYNDE — yoksa donme ortografik olur ve ezilme gibi okunur),
  koseler soldan, kurulum adimlari sirayla asagidan, kosular bulaniktan
  netlesip yukselerek, sorular ust cizgiden asagi acilarak, kapanis bandi
  buyuyerek. Fark edilmeyen bir gecis, byte harcayip hicbir sey satin
  almiyor. [2026-08-25]

### Fixed — gorulmemis bolum kalmiyor, ve 404 rozet takmiyor

- Reveal artik yalnizca IntersectionObserver'a bagli degil. Tarayici programatik
  bir siçramada (bir capa tiklamasi, End, geri yuklenen kaydirma konumu) kesisme
  cagrilarini birlestirir ya da atlar, arka plan sekmesinde ise tamamen kisar —
  ve o sirada gecilen her bolum `opacity: 0`'da kalir. Kaydirma isleyicisi artik
  ayni isi geometriyle de yapiyor: ustu bir bucuk ekran icinde olan hedef
  aciliyor, gozlemci ne yaptiysa yapsin. Bittiginde sup kendini emekli ediyor.
  Kullanicinin "bazi bolumler animasyonlu gelmiyor" raporu bu kusurun disaridan
  gorunusuydu. [2026-08-25]
- Ayni degisiklikte bir golgeleme tehlikesi de kapandi: `var targets` dosyada
  iki kez tanimliydi (reveal hedefleri ve menu capalari) ve `var` fonksiyon
  kapsamli — ikinci satirdan sonra `targets` okuyan her sey capalari alirdi.
  Hicbir sey okumuyordu; sup okumak zorunda kaldi. [2026-08-25]
- 404'un durum satiri rozet olmaktan cikti. Nokta + uc rakam + yuvarlak kenar,
  bu tasarimin CANLI BUILD damgasi icin kullandigi sekildi; bir durum degil bir
  baslik olan bir sayi icin odunc alinmisti. Artik dizilmis: rakam buyuk, altinda
  yukaridaki bolumlerin kullandigi ayni kicker, ve blogu kapatan bir cizgi.
  Butonlarina da ikon geldi. [2026-08-25]

### Fixed — ayni is yapan iki buton ayni boyda, ayni satirda

- Kapanis bandindaki "Kiti indir" GitHub markasini tasimiyordu; herodaki
  tasiyordu. Ayni eylem, bir ekran arayla iki farkli sekilde cizilmisti — ve
  ikincisini goren okur hero'yu coktan gecmis olan okur, yani markanin en cok
  gerektigi kisi. Marka `GitHubMark.astro`'ya tasindi (tek cizim), ve
  `test_every_button_to_the_repository_is_drawn_the_same` bunu artik tutuyor:
  guvendigi sey `<svg>` degil, bilesenin kendi path verisi — her butonun sonunda
  zaten bir chevron var, o da bir svg. [2026-08-25]
- Bir buton satirindaki iki buton artik tek genislikte. Kapanis bandinda 110px
  ve 174px'lerdi: alternatif olarak sunulan iki secenek, biri onemliymis gibi
  cizilmis. `grid-auto-columns: 1fr` ile `width: fit-content` birlikte okunur —
  daralan bir kutu icinde `1fr` en genis sutunun max-content olcusune coker. 32
  rem altinda satir doner; esik, sitedeki en genis cift olan Ingilizce kapanis
  bandindan olculdu. Ayni kural 404'un buton satirinda da. [2026-08-25]
- Yan yana okunan her kart grubunda aciklama satir sayilari esitlendi — kurulum
  adimlari 1/3/2 satirdi, kapilarin ilki tek satir, bes katmanin ikisi Ingilizce'de
  bir satir fazla, ve kapanis kartlarinin ortanca basligi Ingilizce'de iki satira
  sarkip cumlesini komsularindan 23px asagi itiyordu. Metinler esitlendi, ve
  esitligi koruyan yer tutma (`min-height: 2lh`) yazildi: uc kart yan yana
  okunuyorsa, okundugu satirin var olmasi gerekiyor. [2026-08-25]
- Hero'nun ilk cumlesi ucuncu satirda tek bir sozcukle bitiyordu; iki dengeli
  satira indi. [2026-08-25]

### Changed — menudeki isik dil kontroluyle ayni

- Menu ogesinin hover ve secili hali, TR/EN kontrolunun isikli yarisini
  kullaniyor: ayni gradyan, ayni kenar, ayni ic parlaklik. Ayni seridin icinde
  on bir piksel arayla duran iki kontrol "acik" halini iki farkli sozlukle
  soyluyordu. [2026-08-25]

### Added — 404'un karti ve yayin denetimi

- 404 sayfasi artik paylasim karti tasiyor. Indekslenmiyor ve yine de
  paylasiliyor: birisi kirik bir baglantiyi sohbete yapistirdiginda onizleme,
  projeden gorulen ilk sey oluyor. `og:url` basarisiz adresi degil sitenin
  kokunu gosteriyor — okuru var olan bir yere goturmeli. [2026-08-25]
- `test_the_site_is_ready_to_publish`: `docs/og.png` ile `web/public/og.png`
  ayni mi (yeniden uretilip derlenmemis bir kart, canli onizlemede eskisidir),
  404 noindex ve kartli mi, robots.txt'nin gosterdigi sitemap gercekten
  yayinlaniyor mu. Ucu de yabanci birinin, zaten gonderilmis bir baglanti
  uzerinde fark ettigi seyler. [2026-08-25]

### Fixed — mobilde ortalanmayan isaret

- Footer'daki isaret telefonda 380px'te tam **77 piksel** solda kaliyordu.
  `justify-items` kapsayicida, `justify-self` ogede: ikincisi kazanir ve
  `.brand` masthead'den `justify-self: start` tasiyor. Ogeye soylemek gerek,
  kapsayiciya degil. [2026-08-25]
- OG kartinin basligi panelin altina girip sag kenardan tasiyordu. Artik
  sigacak boya kuculuyor ve kuculdugunu yaziyor — baglanti zaten paylasildiktan
  sonra fark edilen turden bir kusur, cunku yazar kaynaga bakar, okur kucuk
  resme. [2026-08-25]
- Kartin isareti kendi negatifi olarak ciziliyordu: `Base.astro`'daki yol dort
  ceyrek HALKA, dort ceyrek disk degil. [2026-08-25]

### Fixed — canli sitede gorunmeyen uc kart, ve pilin icinde asagi kaymis yazi

- Kapanis bandinin uc karti **hic gorunmuyordu**: yerlerini kapliyor, hicbir sey
  boyamiyorlardi. Sebep, animasyonun iki kuralinin farkli derinlige ulasmasi.
  Baslangic durumu `.js .cards > *` diyor, birakma `.js .is-in > *` diyordu; her
  kademeli kapsayicinin KENDISI reveal hedefi oldugu surece ikisi ayni sey. O
  kapsayicilardan biri bir reveal'in ICINDE durunca cocuklarini `opacity: 0`
  yapan kural onlari esliyor, birakan kural eslemiyordu. Birakma artik ic ice
  kapsayicilara da uzaniyor. [2026-08-25]
- READMEye giden pilin etiketi kapsulun ustunden 11, altindan 2 piksel
  uzaktaydi. Bu bir hizalama tercihi degildi: pil bir `<p>` icinde duruyor ve
  duzyazi-link kurali (`.band p a:not(.pill)`) ona da ulasip kayan alt cizgiyi
  bir butonun uzerine ciziyor, `padding-bottom: .06em` ile pilin kendi 9,6
  pikselini eziyordu. Kural artik `p:not(.more)`: duzyazi linkleri icin bir
  bicim, duzyazi linkleri icin oldugunu soylemek zorunda. [2026-08-25]

### Changed — cizgiler sayfanin tamamina yayildi

- Cizgili zemin `.hero::before` uzerindeydi, yani sayfa bir goruntu boyunca
  cizgili kagit, sonraki dortte duz siyahti — bu bir karar gibi degil,
  yuklenmemis bir doku gibi okunuyor. Artik `main` uzerinde: tek katman, belgenin
  boyunda, sag ve sol kenarda soldurulmus. Ilk ekran biraz daha fazlasini
  tutuyor, cunku cizgi sayfanin en bos oldugu yerde en gorunur olmali ve gosterecek
  yeri olan tek ekran orasi. [2026-08-25]

### Changed — baslik, vitrin rakamlari ve zemin

- Baslik ucuncu kez degisti ve her seferinde ayni testi baska turlu gecemedi.
  "Doğrulanmamış bir atıf / nihai çıktıya giremez" tanistirilmamis bir mekanizma
  hakkinda kesindi; "Makale ve tez yazımı, uçtan uca" ise hicbir sey soylemiyor
  — "uçtan uca" her aracin kullandigi kalip ve okurun yapacagi bir eylemi
  adlandirmiyor. Simdi eylem ve yer: **"Makale ve tezinizi Claude Code ile
  yazın."** [2026-08-25]
- Vitrindeki uc kart artik ayni uc olcuyu gosteriyor. Onceden her kosunun kendi
  raporunun en ilginc buldugu sey yazıyordu — "1.572 kayıttan 100", "6
  havuzlanabilir", "4 → 0 Major". Hepsi dogru ve hicbiri, ciktigi derlemeyi
  okumamis birine bir sey ifade etmiyor; dahasi uc farkli sey olcen uc kart
  karsilastirilamaz, ve uc karti yan yana koymanin tek sebebi odur. Ilk iki
  deger her kosunun kendi dogrulama kaydindan okunuyor. [2026-08-25]
- Zemin kareli izgaradan **cizgili kagida** dondu: kare izgara her gelistirici
  aracinin arka plani, bu ise makale yazmak icin bir kit — zemin de bir makalenin
  uzerine yazildigi sey. [2026-08-25]
- Rakam seridinde isaret sayinin ustunde rozet degil, arkasinda filigran: dort
  ikon dort sayinin ustunde seridi iki satirlik icerik yapiyordu, oysa soyleyecek
  tek seyi var. [2026-08-25]
- Kapanistaki uc soz kart oldu; isaretler halka icinde. [2026-08-25]
- Footer kunyesi daktilo yuzunden cikip govde yuzune dondu — bir kunye sayfadaki
  tek satirdir ki ne veri ne referanstir, daktiloda bir log kaydi gibi okunur.
  Kalp de bir ton koyulastirildi; #ef4444 bu zeminde 14px'te titriyordu.
  [2026-08-25]
- Surum satiri footer'dan kaldirildi. Sayfa surumunu hala bildiriyor — head'deki
  SoftwareApplication grafiginde, ki bir tarayici ve bir atif araci zaten oraya
  bakar — ve testin sordugu sey de o: bayat bir `docs/` guncel numarayi hicbir
  bicimde icermez. [2026-08-25]

### Added — her bolume kendi girisi

- Her bandin animasyonu artik icerigine gore: rakam seridi yerine oturur,
  katmanlar numaralandiklari yonde soldan gelir, kosular yukselir, kapanis
  buyuyerek gelir. Yalnizca BASLANGIC donusumu farkli — birakma kurali hepsinde
  ayni, yani bir reveal yanlis davrandiginda dusunulecek tek bir sey var.
  [2026-08-25]
- Kaydirma cubuklari sayfanin kendi tokenlarina gecti. Varsayilan cubuk, her
  kenarina ve yuzeyine kendisi karar vermis bir sayfanin ustunde duran isletim
  sistemi kromu; kod bloklarinin ICINDE ise bolumun en gurultulu nesnesiydi.
  [2026-08-25]

### Fixed — hizalanmayan kartlar, kayan bosluk ve telefonda kenarsiz baslik

- Uc kapi kartinin basliklari ayni satirdaydi, paragraflari degildi: biri tek
  satirlik, ikisi iki satirlik cumle tasiyordu. Baslik satiri artik sabit
  yukseklikte. [2026-08-25]
- READMEye giden satirin ustunde 40, altinda 96 piksel vardi — kendi alt marji
  kabuktan disari cokup altinda bolumun dolgusu kaliyordu. Ikisi de 48.
  [2026-08-25]
- Telefonda masthead panosu ekranin iki kenarina yapisikti: kabugun oluğu, pano-
  nun kendi dolgusuyla ayni 1rem. Bandin kendi ici bosluğu eklendi. [2026-08-25]
- Telefonda footer ortalanmiyordu. Kural footer'in kendi kurallarindan ONCE
  yaziliydi: bir media query, esit ozgullukte ve daha sonra gelen bir bildirimi
  yenmez. Sira, duzeltmenin tamami. [2026-08-25]
- Yukari-cik butonu sayfanin en altinda gizleniyor: orada footer'in son satirinin
  uzerine biniyordu, ve sayfanin sonuna varmis bir okura basa donebilecegi
  soylenmesine gerek yok. [2026-08-25]

### Changed — ilk ekran artik kitin ne oldugunu soyluyor

- Hero panelindeki dogrulama kaydinin yerini kitin kendi uretim hatti aldi: alti
  komut, bir makalenin onlardan gectigi sirayla, ve aralarindaki uc kapi.
  Onceki panel gercek bir artefakti (`03-verify-status.json`) diziyordu — sitenin
  kaniti — ama ilk ekranda bir JSON dokumuydu ve ziyaretciden, bu seyin ne
  oldugu soylenmeden once bir dogrulama kaydini okumasini istiyordu. Kanit
  sayfadan gitmedi: ait oldugu kosunun anlatildigi vitrine tasindi.
  [2026-08-25]
- Vitrindeki "19/19 · 122/122 · 49/49" rakamlari artik uc kosunun kendi
  `03-verify-status.json` dosyalarindan derleme aninda okunuyor, sayfaya elle
  yazilmiyor. Kaydin testi de onlarla birlikte tasindi. [2026-08-25]
- Baslik: "Doğrulanmamış bir atıf / nihai çıktıya giremez" bir mekanizma
  hakkinda kesindi ve ilk kez gelen okurun elindeki soruya — bu sey nedir —
  hicbir cevap vermiyordu. Yerine "Makale ve tez yazımı, uçtan uca"; garanti
  altindaki cumlede duruyor. [2026-08-25]
- Basligin ustundeki damga kaldirildi: footer'in soyledigi bir olguyu ve henuz
  kimsenin fikri olmadigi bir surum numarasini, sayfanin en gorunur bos
  alaninda tasiyordu. Surum footer'in sol koşesinde tek satir olarak duruyor —
  iki test built sayfanin kaynaginin ilan ettigi surumu tasidigini kontrol
  ediyor, ve bayat bir derlemeden yayina cikildigini fark eden sey o.
  [2026-08-25]
- Rakam seridi cam bir bant oldu: her hucrede bir isaret, aralarinda sac teli.
  Dort sayi zeminde yuzerken dort ilgisiz olgu gibi okunuyordu; tek seritte bir
  ozet gibi okunuyorlar — olduklari sey de o. [2026-08-25]
- Katman ikonlarinin cercevesi kalkti. Kutu icinde kutuydu — bes panonun
  ustunde bes kucuk cerceve — ve sira zaten sabit yukseklikte bir izgara
  satirinda hizalaniyor. [2026-08-25]
- Kapanis bandinda uc soz alt alta degil yan yana; band bir ekranin cogunu
  altmis kelime icin kaplamayi birakti. [2026-08-25]
- Footer'da kunye saga yaslandi ve aracin yuz tipine gecti — sayfadaki tum kucuk
  yazi gibi. Govde yuzunde kalan tek satirdi, o yuzden bitirilmemis bir cumle
  gibi okunuyordu. [2026-08-25]

### Added — hero'daki komutlarin gercek oldugunun testi

- `test_the_hero_pipeline_names_real_commands`: panelin bastigi her slash
  komutu `.claude/skills/<ad>/SKILL.md` karsisinda dogrulanir. Komut uyduran bir
  tanitim sayfasi, tam olarak bu kitin reddetmek icin var oldugu hatanin kendi
  pazarlamasinda islenmis halidir — ve makul gorunen bir ad, gercek bir ad gibi
  okundugu icin incelemeden gecer. [2026-08-25]

### Added — vitrindeki makalelerin kendisi

- Uc kosudan ikisinin derlenmis makalesi artik siteden dogrudan aciliyor.
  Ikinci kosunun PDF'i zaten vitrindeydi; ucuncununki koşunun kendi exports
  dizininde durup vitrine hic girmemisti, `14-manuscript.pdf` olarak eklendi ve
  dizin tablosuna yazildi. Birinci kosunun artefaktlarinin tamami burada ama
  belgesi depoda yok, o yuzden o kart tek eylem gosteriyor: olmayan bir dosyaya
  baglanti, baglanti olmamasindan kotudur. [2026-08-25]

### Changed — footer, kapanis ve katmanlar

- Footer'da yalnizca isaret, tek cumle ve "Developed with ♥ by mtvrkan" kaldi,
  hepsi solda. Yedi linklik satir tek sayfalik bir site icin site haritasiydi ve
  her hedefi okurun zaten acacagi deponun bir tik otesinde; altindaki colophon
  ise sayfanin tepesindeki damganin tasidigi surum numarasini basiyordu.
  [2026-08-25]
- Kapanis bandi tek basliktan ve dort host, bir DOI, bir ISSN ve bir dergi
  adindan olusan tek bir cumleden ibaretti — uc ayri soz, her biri bir yan
  cumleye katlanmis. Simdi satir basina bir soz, soz basina bir isaret.
  [2026-08-25]
- Bes katman cam panolara donustu; ikonlar kendi karolarinin icinde, cunku bes
  farkli siluet dogrudan yuzeyin uzerinde hicbir zaman tek bir sira gibi
  durmaz. [2026-08-25]
- Kanit panosu heronun sagina dondu, yazi solda. Bir tur altinda durdu; temiz
  okunuyordu ve sayfaya argumanini kaybettiriyordu: iddia ile onu kanitlayan
  artefakt bir kaydirma uzaktaydi, yani ilk ekran yaninda hicbir sey olmayan bir
  iddiaydi. [2026-08-25]
- Bant metinleri kisaltildi. [2026-08-25]

### Fixed — hover'da okunamayan buton ve link gibi gorunen span

- Ghost butonu hover'da bembeyaz oluyor, uzerindeki beyaz yazi kayboluyordu.
  Sebep: `.pill:hover` acik butonun beyaz zeminini boyuyor, `.pill-ghost` kendi
  dolgusunu KENDI kuralinda ezip hover durumu hakkinda hicbir sey soylemiyordu —
  cascade de ghost'a acik butonun yuzunu veriyordu. Bir dolguyu ezen bir durum,
  o durumda da ezmek zorundadir. [2026-08-25]
- Vitrin kartinin tamami tek bir baglantiydi ve altindaki iki eylem birer
  `<span>`di: "Makale (PDF)" ikinci bir hedef gibi gorunup birincisine
  gidiyordu. Ic ice `<a>` da gecerli degil, o yuzden kart baglanti olmaktan
  cikti ve eylemler numarayla yaptiklari sey oldular. [2026-08-25]
- Kurulum adimlarinda komut kutusunun altinda bos pano seridi kaliyordu. Kartlar
  artik esnek sutun: paragraf boslugu soguruyor, komutlar uc kartta da alt
  kenara oturuyor. [2026-08-25]
- README satiri izgaranin son sutununun hizasina degil sayfanin ortasina
  oturuyor: `text-align` satir ici icerigi ortalar, ve inline-flex bir hap
  satir ici icerktir. [2026-08-25]

### Changed — site bir tanitim sayfasi oldu

- Dort referans bolumu kaldirildi: her komut kapisiyla, altmis sekiz aracin her
  biri reddiyle, hook tablosu, subagent tablosu, tasdik numunesi, uc kosu dosya
  indeksleriyle. Yirmi bin piksel, ve hepsi zaten READMEde — o detayi isteyen
  okur oraya gidiyor. READMEyi tekrarlayan bir site, ayni anda guncel tutulmasi
  gereken iki belgedir ve biri kayar. Sayfa **26.800 pikselden 5.700'e** indi.
  [2026-08-25]
- Kalan: hero, kanit panosu ve dort rakam, uc kapi, bes katman, kurulum, uc
  kosu, SSS, kapanis. Her biri hala dogru olan en kucuk halinde ve her biri
  detayi tasiyan belgeye baglanti veriyor. [2026-08-25]
- Ilk ekranda yalnizca hero var: `min-height: 100svh` (vh degil — telefonda vh
  goruntu alaninin ULASTIGI en buyuk degerdir, yani ona gore olculen bir bolum
  her zaman gorunenden uzundur ve altindaki blok folddan tasar). Bes genislikte
  olculdu: 380 · 760 · 1000 · 1100 · 1440, hicbirinde tasma yok. [2026-08-25]
- Duzen ortalandi. On ikinci sutunlu "edition" izgarasi, bolum numaralarini ve
  kenar notlarini tasiyan aparat rayi ve olcuye kilitli sol ucte duran metin
  gitti — bir belge icin dogru sekildi, bir tanitim icin degil: her bolumun
  kenarina bir §01 koyuyor ve genis ekranin sag iki uctunu bos birakiyordu.
  [2026-08-25]
- Menu masthead'in ortasinda. `1fr auto 1fr`, `auto 1fr auto` degil: ikincisi
  orta izi disardaki ikisinin biraktigi bosluga ortalar, yani menu isaretle
  kontrollerin genislik farkinin yarisi kadar kayar. [2026-08-25]
- Rakam seridi paneli birakti. Dort sayi dort ince cizgiyle bir panelin icinde,
  bir baslik taklidi yapan kucuk bir tabloydu; sayfanin en sessiz icerigine en
  gurultulu cerceveyi veriyordu. [2026-08-25]
- Yukari-cik butonunun etrafinda ilerleme halkasi var. Sayfanin ustunden ayri
  bir cubuk yerine, olguyu ve onu geri alacak kontrolu ayni nesne yapmak.
  [2026-08-25]

### Fixed — animasyonsuz gelen bloklar, kayan katman ve halka geometrisi

- Reveal `.sec, .record, .figs` diye UC sinif adi sayiyordu; sayfa baska
  bloklar kazandi ve onlar hic hareket etmedi. Bes blok animasyonla gelip
  altincisi birden belirince okur altinciyi bozuk sanar. Artik `.reveal` sinifi
  tasiyan her sey. [2026-08-25]
- Bes katmandan biri komsularindan bes piksel daha uzun cikiyor, ikonu ve
  basligi digerlerinin hizasindan kayiyordu. Satir yukseklikleri artik
  bildirilmis; icerigin tartisabilecegi bir sey kalmadi. [2026-08-25]
- Halka: `pathLength="100"`. Tarayici bir cemberi dort bezier ile cizer ve yol
  118,61 uzunlugunda cikar — 2πr'nin soyledigi 119,38 degil — yani yaricaptan
  hesap, sayfanin sonunda halkayi kapanmis gostermez. Ve `transform-origin`
  bildirildi: SVG ogesinde HTML kutusundaki gibi merkeze varsayilmaz, yani
  cıplak bir `rotate(-90deg)` halkayi sol ust kosesinden dondurur — tam cember
  olan raydan bu gorunmez, altindaki yayin bastan bambaska bir yeri
  gosterdigi anlasilmaz. [2026-08-25]
- Gizli sekmede rAF durur, yani kaydirma isleyicisinin boyadigi her sey (yapisik
  masthead, buton, halka) sekmeye en son bakildigi andaki haliyle kalir. Sekme
  gorunur olunca isleyici bir kez daha calisiyor. [2026-08-25]
- Olcek 5 ve 10 basamaklarini kazandi. Uc ayri duzenleme turu `--s5`/`--s10`e
  uzandi; bu, merdivende bosluk oldugunun isareti. 20 ve 40 piksel, ayni 4px
  izgarada. [2026-08-25]

### Removed — sitenin tasidigini iddia etmedigi seyin testi

- `test_the_tools_page_lists_every_tool_in_the_repository` konusuyla birlikte
  silindi. Her aracin adini sayfada arayan iyi bir kapiydi — sayfa her araci
  LISTELEDIGINI iddia ettigi surece. Artik tek bir arac adi gecmiyor, README'ye
  baglaniyor; ortada kontrol edilecek iddia yok ve bosuna gecen bir test,
  testsizlikten kotudur cunku kapsam gibi okunur. [2026-08-25]

### Changed — baslıklar iddia degil icerik soyluyor

- Hero: "Yapay zeka kaynak uydurur / Bu kit uyduramaz" reklam metniydi — once
  bir yazilim kategorisi hakkinda iddia, sonra ovunme. Yerine kitin gercekten
  ZORLADIGI sey, kodda yazildigi haliyle: yetkili kayda karsi cozulemeyen bir
  kunye `verified: false` damgasi alir ve nihai ciktidan bloklanir. Eskisinden
  dar, ve kontrol edilebilir. [2026-08-25]
- Bolum basliklari aforizma olmaktan cikip bolumun icerigini soyluyor ve
  sayilar SITE'den geliyor — yani test paketinin depodan yeniden turettigi
  degerler: "43 komut, 11 bilgi skilli" · "68 deterministik arac" · "Bes katman,
  6 hook" · "Uc kosu, acilabilir dosyalariyla". Baslik artik birinin
  guncellemeyi hatirlamasi gereken bir iddia degil, build'in dogru tuttugu bir
  olgu. [2026-08-25]
- "On dakikada baslangic" → "Kurulum". Bir bolum basligi saat hakkinda soz
  vermez. [2026-08-25]
- Butonlarin altindaki dort kucuk olgu satiri kaldirildi. [2026-08-25]

### Changed — surum 1.0.0

- Yayimlanan her yerde 1.0.0: `CITATION.cff`, `plugin.json`,
  `marketplace.json`, `web/src/data/site.ts`, iki README rozeti ve
  `RELEASING.md`. Yayin oncesi dort dongu 0.1.0–0.4.0 olarak yeniden
  numaralandi; tek satir, tarih veya kayit silinmedi. [2026-08-25]
- Bunun bir sonucu var ve `RELEASING.md`'de yazili: mevcut `v1.0.0`–`v1.3.0`
  etiketleri artik yanlis, cunku `v1.0.0` 1.0.0 OLMAYAN bir commit'i
  gosteriyor. Etiketlemeden once silinmeleri gerekiyor. [2026-08-25]


### Changed — hero'da tek bir paragraf kaldi

- Ilk ekranda dort ayri metin blogu vardi: lede, uzmanlik gerekmedigini soyleyen
  ikinci paragraf, DOI icerik muzakeresini anlatan kenar notu, ve butonlarin
  altinda uc tam cumlelik guvence listesi. Dordu de dogruydu ve dordu de "once
  beni oku" diyordu; okur nereden baslayacagina karar vermek zorunda kaliyordu.
  Kalan: baslik, iki satirlik tek paragraf, iki buton, tek satirda dort kucuk
  olgu. Mekanizma zaten kendi bolumunde. [2026-08-25]
- Guvence satiri artik dipnot boyutunda saran bir sira; onceki hali govde
  boyutunda uc satirdi, yani ilk ekrandaki dorduncu paragraf. [2026-08-25]

### Fixed — hero'da ust uste binen isaretler ve telefonda kesilen komut

- Isaretli kelimenin altina cizilen pass renkli cizgi kaldirildi. Span'in
  icerik kutusunun dibinde duruyordu — italik bir serifin ALT UZANTILARININ da
  oldugu yer: Turkce'de kelime "uyduramaz" ve cizgi y'nin kuyrugundan geciyordu.
  Ingilizce'de ("This kit cannot") o kelimede alt uzanti yok, yani carpisma
  kontrol edildigi dilde gorunmez, sitenin onde tuttugu dilde apacikti.
  Yukari almak harflerin icine, asagi almak paragrafin icine sokardi.
  [2026-08-25]
- Kenar notunun 2px isareti, notun degil butun ek bloklarinin boyunca — 61px
  yerine 257px — lede paragrafinin ustunden basliyor ve hicbir seyin yaninda
  duruyordu. Sebep: iki sutunlu hero'da nota `position: static` verilmisti ve
  bir konumu kaldirmak, icindeki mutlak konumlu her seyin de konumunu kaldirir;
  kapsayan blok `.ann` oluyordu. Iki tur once dugme parlamasinda olan sey, ayni
  sekilde. `test_the_stylesheet_never_unpositions_an_element` artik bunu
  kirmizi yapiyor. [2026-08-25]
- Ayni duzeltmenin actigi ikinci hata: 64rem'deki rail kurali `inset-inline-start:
  calc(100% + gutter)` de yaziyordu. Konumsuzken etkisizdi, `relative` olur olmaz
  notu 756px saga — kayit panosunun altina — itti. Bir konumu geri almak
  ofsetlerini de geri almaktir. [2026-08-25]
- Telefonda kurulum komutu kesiliyordu. Grid ogesinin otomatik minimum boyutu
  MIN-CONTENT genisligidir ve `.cmd` `white-space: nowrap` — yani her adim
  komutun tamamindan dar olmayi reddediyordu. 380px'de oge 440px kaliyor,
  `.cta`'nin `overflow: hidden`'i kesiyordu: sayfada okurun birebir kopyalamasi
  gereken tek dize, ortasindan bitiyordu. `min-width: 0` eklendi; `.rows` de
  `1fr` yerine `minmax(0, 1fr)`. [2026-08-25]

### Added — genislik probu (yayimlanmaz)

- Bir genislik yoklama sayfasi: ayni sayfayi bes sabit CSS genisliginde yan yana gosteren
  bir gelistirme araci. `public/` altinda DEGIL, cunku oradaki her sey docs/'a
  kopyalanir. Bu turdaki uc hatanin ucu de pencerenin o an bulundugu tek
  genislikte gorunmuyordu. [2026-08-25]

### Added — ikon seti ve katlanan referans bolumleri

- `Icon.astro`: tek bilesende 21 ikon, hepsi 24x24 izgarada tek kalinlikta.
  Geometri Lucide'in (ISC); lisans metni bilesenin kendi basliginda duruyor.
  Paketlenmedi, kurulmadi, CDN'den cekilmedi — sayfanin CSP'si `default-src
  'none'` ve bir ikon fontu sitenin tek dis istegi olurdu. [2026-08-25]
- Arac gruplari, dosya listeleri ve SSS artik `<details>`. Script yok, CSP
  istisnasi yok, klavye ve ekran okuyucu bedava; ve 68 aracin tamami HTML'de
  duruyor — testin ve tarayicinin okudugu yer orasi. Sayfa 26.800 pikselden
  20.400'e indi. [2026-08-25]

### Changed — hero, hedef okura gore yeniden yazildi

- Baslik "Atiflariniz / Dogrulanmis" idi ve ilk paragrafta "DOI icerik
  muzakeresi" geciyordu. Hepsi dogru, hicbiri okurun aradigi sey degil: okur,
  bu araclarin kaynak uydurdugunu duymus, bunun uydurup uydurmadigini merak
  eden bir akademisyen — ve Claude Code'da akici olmak zorunda degil. Baslik
  artik onun zaten sahip oldugu problem, ilk paragraf cevabi, ve hemen altinda
  uzmanlik gerekmedigi acikca yaziyor. Mekanizma sayfada duruyor; kenar
  notunda. [2026-08-25]
- Hero'nun alt satiri "Windows · macOS · Linux · MIT" idi. Yerine bir
  akademisyenin devam etmeden once karar verdigi uc sey: sure, dil, maliyet.
  [2026-08-25]
- Uc kapi kartinin her biri ayni uc maddeyi kelimesi kelimesine tasiyordu —
  dokuz satirda uc sey, ustelik kartlara degil MEKANIZMAYA ait uc sey. Bir kez,
  ucunun altinda. [2026-08-25]

### Fixed — panelin altinda hic bosluk yoktu, ve olmayan bir olcek basamagi

- `.ed` yalnizca sutun boslugu tanimliyor; dikey bosluk her ogenin kendi
  marjindan geliyor. Panellerde marj yoktu, dolayisiyla kurulum kartinin
  hemen bitiminde — sifir piksel — bir paragraf basliyordu. Bosluk panele
  verildi: `.full + p` yalnizca iki dil varyantindan BIRINCISINI eslestirirdi,
  yani duzeltme Turkce'de calisip Ingilizce'de sessizce calismazdi.
  [2026-08-25]
- Olcek 1 2 3 4 6 8 12 16 24 32; 5 ve 10 yok. Bir tur duzenleme alti yerde
  `var(--s5)` ve `var(--s10)` yazdi — panelin altina bosluk koyan kural dahil.
  Tarayici boyle bir bildirimi sessizce dusurur: kural derlendi, gonderildi ve
  hicbir sey yapmadi. `test_every_custom_property_the_stylesheet_uses_is_one_it_defines`
  artik bunu kirmizi yapiyor. [2026-08-25]
- `.group-h span` — `T` bilesenini dil varyantlarini `<span>` olarak bastigi
  ve o span'lar `<h3>`'un icinde oldugu icin — dokuz grup BASLIGINI sayac
  cipinin monospace'i, harf araligi ve cercevesiyle diziyordu. `>` eklendi.
  [2026-08-25]
- Kapali bir grubun altindaki 2px murekkep cizgi, altinda hicbir sey olmayan
  bir basligin alti cizgisiydi — bolumun en kalin cizgisi, dokuz kez. Kapaliyken
  saç teli. [2026-08-25]

### Changed — masthead, kayit panosu, footer ve hero

- Header'daki GitHub butonu kaldirildi. Ayni depoya giden ucuncu yoldu (hero'nun
  birincil cagrisi ve footer'in kaynak satiri digerleri) ve gezinmeyle yarisan
  tek nesneydi. Indirme, indirme gerekcesinin yeni sunuldugu yerde durur.
  [2026-08-25]
- Dil anahtari tek butondan iki durumlu segmentli kontrole cevrildi. "English"
  yazan tek buton, bir dil anahtarinin asla tasiyamayacagi belirsizligi
  tasiyordu: "Ingilizce okuyorsunuz" da okunur, "Ingilizce icin basin" da.
  Yanan yarim `data-lang`'dan secilir, `aria-pressed` ayni seyi ekran okuyucuya
  soyler. 404 de ayni kontrolu aldi. [2026-08-25]
- Kayit panosunun alt yarisi (PASS damgasi, `retracted: 0` kutusu, dosya
  satiri) bu tasarimin kendi dilinde yeniden dizildi: iki satirlik cumlenin
  ortasinda asili duran cerceveli cip yerine ilk satira oturan dolu damga,
  her dokumantasyon ureticisinin gonderdigi bordo "admonition" bloku yerine
  yukaridan asagi sonen bir vurgu, ve middot'la ayrilmis gri mono satir yerine
  kenari olan uc dosya cipi. [2026-08-25]
- Footer sadelesti: dort basliklı link sutunu bir satira indi. On ikinin besi
  zaten masthead'in tasidigi gezinmeydi. [2026-08-25]
- Hero: maskesi kenara varmadan sifirlanan cizgili zemin, "Dogrulanmis /
  Verified" kelimesinin altina gec cizilen pass renginde bir kural, ve damganin
  noktasinda tek yavas nefes. [2026-08-25]
- Surum numarasi bes yerine iki yerde: bolum damgalarindan kaldirildi, hero ve
  colophon'da kaldi. Bes ayri belge tek sayfaya birlestirilirken kalan dikisti.
  [2026-08-25]

### Fixed — yatay kaydirma, ters cevrilen durum noktasi, yerinde olmayan anahtar

- Hero'nun cizgili zemini kutusunun %25 disina tasiyordu: her sayfanin sagina
  125px kaydirilabilir hiclik ekliyordu. `mask-image` BOYANANI soldurur,
  olculeni asla. [2026-08-25]
- Acik temada `.eyebrow::before` hala `invert(1)` ile ters cevriliyordu — kural,
  o isaret beyaz bir SVG parilti oldugu donemden kalmaydi. Simdi pass renginde
  bir durum noktasi, yani her acik ekranda yesil isik macentaya donuyordu:
  isi gecti demek olan tek bilesende alarm rengi. [2026-08-25]
- 404'un dil anahtari "isaretle birlikte durur" diyordu ve durmuyordu: ortalanmis
  bir sutunun sag ustune cakiliydi, sayfadaki tek diger nesnenin dort yuz piksel
  uzerinde ve hicbir seyin yaninda. [2026-08-25]
- Acik temada gorunmez kalan iki yeni isaret (hero zemini, dil anahtarinin
  isaretcisi) murekkeplendi. [2026-08-25]

### Changed — site ayri dala TASINMADI, arsivden cikarildi

- Karar ve gerekcesi: site testlerinin **26'si kitin olgularindan** turetiyor
  (`scripts/` altinda kac arac var, kac hook kayitli, `CITATION.cff` hangi surumu
  ilan ediyor). Yani bir `site` dali kiti de tasimak zorunda — ayirmaz,
  KOPYALAR, ve her kit degisikliginden sonra birlestirip yeniden derleme
  zorunlulugu ekler, yoksa oradaki testler kirmizi olur. Bedeli surekli; kazanci
  bir checkout'un %17'si.
- `.gitattributes`: `web/` ve `docs/` artik `export-ignore`. `git archive` —
  yani "Download ZIP" ve her release tarball'i — bu 1,3 MB'i tasimiyor. Depoda
  zaten `DECISIONS.md` icin kullanilan mekanizmanin aynisi. `git clone`'u
  kucultmez; bunu yapacak tek sey dal ayrimiydi ve reddedilen takas o.
  [2026-08-25]

### Fixed — 404 iki dili ust uste gosteriyordu

- Sayfa bilerek `Base` uzerine kurulmadi, dolayisiyla dil mekanizmasini da
  DEVRALMIYORDU: Turkce ve Ingilizce alt alta basiliyordu. Kayip bir okurun
  dustugu tek sayfa, sectigi dili yok sayan tek sayfaydi. Ayni `sk-lang`
  anahtari, ayni degistirici. [2026-08-25]
- Paylasim karti iki dili birden tasiyor. Tek URL tek kart demek — dil secimi
  istemci tarafinda, yani tarayici, Slack onizlemesi ve WhatsApp karti markupta
  ne varsa onu gorur, okurun secimini asla. Iki kart iki URL ister, iki URL iki
  belge ister: sitenin az once biraktigi sey. `og:locale` tr_TR, ilan edilen
  alternatif en_US. [2026-08-25]

### Fixed — dugmenin parlamasi hala sayfada geziniyormus

- Onceki turda `overflow: hidden` eklenmisti ama `position: relative` degil, ve
  tasiyici olan yari oydu. Parlama `position: absolute`; kapsayan blogu en yakin
  KONUMLU atadir — dugme konumsuz oldugu icin o ata, o an hangi bolum `relative`
  ise oydu, ve `inset: 0` dugmeyi degil BOLUMU kapliyordu. -%130 otelenince
  sayfanin uzerine bir metre genisliginde diyagonal bir bant boyuyordu; dugmenin
  `overflow: hidden`'i onu kirpamiyordu, cunku dugme hicbir zaman onun kapsayan
  blogu olmadi. Kirpmak ve kapsamak iki ayri is; ilk duzeltme yalnizca birini
  yapmisti. 404'te ciplak zeminde gorununce yakalandi. [2026-08-25]

### Changed — site testleri kendi dosyasina ayrildi

- `tests/test_site.py`: `docs/` okuyan yirmi alti test `test_governance_docs.py`'den
  cikarildi. Sebep hazirlik: site kendi dalina tasinacak ve bu testler onunla
  gitmeli — yoksa `main`'de, `docs/` orada olmadigi anda kirilan yirmi alti test
  kalir. Ne kontrol ettikleri degismedi; turetmeleri KOPYALAMAK yerine ithal
  ediyorlar, cunku "kac hook kayitli" sorusunun iki kopyasi tam da bu dosyanin
  yakalamak icin var oldugu suruklenmedir. [2026-08-25]
- `tests/conftest.py`: alan haritasindaki giris KOSULLU. Sabit bir giris, dosyayi
  tasiyan dalda "her dosya haritada" testini gecirir ve tasimayan dalda "haritadaki
  her dosya var" testini kirar — iki indeks testi, yoklugu bir yeniden adlandirma
  degil DOGRU olan bir dosya icin zit yonlere ceker. [2026-08-25]

### Added — 404 sayfasi, tek sitemap ve README kapisi

- `web/src/pages/404.astro`: Pages'in `/` disindaki her sey icin sundugu sayfa
  vardi ama BIZIM degildi — GitHub'in varsayilani cikiyordu. Bilerek `Base`
  uzerine kurulmadi: Base tam gezinmeyi tasiyor ve o gezinme bes SAYFA-ICI capa;
  404'te `#komutlar` diye bir yer yok, yani her ogesi sessizce hicbir sey yapan
  bir baglanti olurdu. Yanlis bir hedef, hedefsizlikten kotudur. [2026-08-25]
- Sitemap `sitemap-index.xml` + `sitemap-0.xml` ikilisiydi: sayfalamaya ihtiyac
  duyacak kadar URL'i olan bir site icin dogru sekil, tek sayfalik bir site icin
  gereksiz dolayli. Artik `public/sitemap.xml` — tek URL, `lastmod` yok: her
  derlemede yeniden yazilan bir tarih diff gurultusu, yazilmayan bir tarih yalan.
  `robots.txt` onu adlandiriyor. [2026-08-25]
- Favicon iki yon eski paletle duruyordu (sicak kagit + arsiv teali) ve genel bir
  belge ikonuydu. Artik markanin kendi glifi, sitenin kullandigi renklerde — 16px
  oldugu icin kimsenin gormedigi, tarayici sekmesinde butun gun durdugu icin
  herkesin gordugu parca. [2026-08-25]
- `meta name="author"` eklendi. [2026-08-25]

### Fixed — her iki README de UC kosuyu IKI diye sayiyordu

- Ucuncu vitrin eklendi, site uc kosuya guncellendi, README'ler birkac surum
  boyunca "iki gercek makale" demeye devam etti — hem de okurun gordugu ilk
  cumlede. Sebep: sayi duzyazida, kanit bir dizin listesinde, ve ikisini
  birlestiren hicbir test yoktu. Ikisi de duzeltildi ve `examples/showcase*`'a
  BAGLANDI; mutasyonla sinandi. [2026-08-25]
- `README.en.md`'de "gercek makalelerde kanitlandi" bolumu **hic yoktu** — TR
  tarafinda vardi. Kitin merkezi iddiasi TR/EN esitligi oldugu icin bu, esitligin
  kendi vitrininde bozulmasiydi. Ucu de yazildi. [2026-08-25]
- Iki README'ye paylasim karti ve rozetler geldi. Kart mutlak URL ile referans
  veriliyor — derlenmis site her zaman bu dosyayla ayni dalda olmayacak — ve bir
  test her ikisinin de sitenin ilan ettigi alan adini gosterdigini dogruluyor.
  [2026-08-25]

### Changed — altbilgi kredisi ev cizgisine dondu

- `Gelistiren — Mehmet Turkan` tahminle yazilmisti. CookieExport ve Followlens'in
  kullandigi bicim bulunup birebir alindi: **Developed with (kalp) by mtvrkan**,
  `mtvrkan.com`'a. Ayni sozcukler, ayni sekil, ayni kalp atisi — bir ev cizgisi,
  yani ayni cumlenin ucuncu bir soylenisi haline gelmemesi gerekiyor. Ceviri de
  bu yuzden yok. [2026-08-25]
- Kalbin rengi tek degisen sey: `#ef4444` o sitelerin zeminine gore secilmisti,
  saf siyah uzerinde bu boyutta titriyor. Biraz koyusu ayni tonu koruyup
  titremeyi kesiyor. [2026-08-25]
- Atis sonsuz dongude, yani `prefers-reduced-motion`'in tam da durdurmak icin
  var oldugu turden bir hareket. Genel kural yineleme sayisini 1'e cekiyordu —
  bir kez atardi; artik hic baslamiyor. [2026-08-25]

### Changed — tablolar, SEO, guvenlik, mobil, yukari-cik ve sade altbilgi

**Tablolar.** Sitenin tasidigi asil sey bunlar — altmis sekiz arac, kirk uc
komut, hooklar, ret listeleri — ve uzerinde en az calisilmis parca onlardi: yan
yana iki metin sutunu ve her ciftin altinda bir kil cizgi. Dort degisiklik ayni
isaretlemeyi liste degil TABLO gibi okutuyor:

- **Sutunlar arasina dikey cizgi.** Dikey bir kenar olmadan ad ile aciklamasi
  yalnizca yan yana duran iki paragraf; cizgiyle birlikte goz ad sutunundan
  asagi, her satirda yeniden bulmak zorunda kalmadan inebiliyor. [2026-08-25]
- **Gorunur bir imlec durumu.** `--paper-2` idi, cam uzerinde neredeyse camin
  kendisi: imlecin uzerinde durdugu satir digerleriyle ayni gorunuyordu.
  [2026-08-25]
- **Zebra**, hissedilecek ama gorulmeyecek kadar dusuk alfada — bu uzunluktaki
  satirlarda gozun yanlis aciklamaya kaymasini durduran sey bu. [2026-08-25]
- **Kapi/ret satiri bir cip oldu.** "Kapi: PROJECT.md" kalin metin + metindi,
  yani etiket ve degeri ustundeki cumleyle ayni bicimdeydi ve goz, metaveri
  oldugunu anlamak icin satiri okumak zorundaydi. [2026-08-25]

**SEO.** `theme-color` palet degisiminden iki kez geri kalmisti, duzeltildi.
Vurgu yuzu (`Instrument Serif`) artik onden yukleniyor: sayfa basliginin iki
sozcugunu diziyor, yani ust katlanmanin ustundeki en buyuk metin ve cogu ekranda
LCP ogesi — stylesheet'ten kesfedilmeye birakilinca ilk boyamadan SONRA geliyor
ve baslik gorunur bicimde Times'tan yeniden diziliyordu. Tek belge oldugu icin
tek ogeli BreadcrumbList kaldirildi, yerine bes bolumu bildiren
`SiteNavigationElement` geldi: tek URL goren bir tarayicinin sayfanin bir yapisi
oldugunu bilmesinin baska yolu yok. [2026-08-25]

**Guvenlik.** CSP'ye `frame-ancestors 'none'`. Buradaki hicbir sey cerceve
icinde gosterilmek uzere degil, ve savi kaynak-gosterilebilirlik olan bir sitede
sayfanin baskasinin cercevesi icinde onun gibi sunulmasi bedeli olan tek gomme.
`X-Frame-Options` bir baslik, Pages ozel baslik gondermiyor — CSP bicimi hem tek
secenek hem zaten daha guclusu. [2026-08-25]

**Yukari-cik.** Sayfa artik tek belge ve yirmi alti bin piksel. Son bolumden
cikisin tek yolu en uzun yoldu, cunku gezinme ust menude. Bir ekran asagidan
sonra beliriyor: daha erken belirse okur zaten tepedeyken gorunur. Telefonun
home cizgisinden kaciniyor ve menu acikken gizleniyor. [2026-08-25]

**Altbilgi sadelesti.** Pano icinde panoydu — zaten kartlardan olusan bir sayfada
dort bag sutunu tutan bir kart. Okurun gordugu son seyin en cok kurgulanmis sey
olmasi gerekmiyor: ustte tek bir aydinlik cizgi, acik zeminde sutunlar, altta tek
satir — ve o satirda **Gelistiren**. [2026-08-25]

**Mobil.** Satirlar yiginlandiginda dikey cizginin ayiracagi bir sey kalmiyor;
ad, altindaki blogun basligi oluyor. 390px'te yatay tasma yok. [2026-08-25]

### Changed — site tek sayfa oldu

- Bes belge, bir sayfanin bes bolumu. Site aralarinda ust menuyu, altbilgiyi ve
  dil dugmesini tekrar eden bes ayri dokumandi; ikisi arasindaki her gecis, ayni
  savin dort bolumunu daha okumak icin tam bir sayfa yuklemesine mal oluyordu.
  `web/src/sections/` altinda dort bolum bileseni, `index.astro` hepsini
  birlestiriyor, gezinme capalara donuyor. [2026-08-25]
- Baslik hiyerarsisi duzeldi: tek sayfada bes `h1` olmaz. Bolum acilislari `h2`,
  onlarin ic basliklari `h3`; bicimlendirme etikete degil ROLE bagli oldugu icin
  `.sec h2`'deki kural `.sec h3`'e de tasindi — ve kart icindeki, bolum basligi
  OLMAYAN h3'ler ayri tutuldu, yoksa hepsi birden cizgi buyuturdu. [2026-08-25]
- Gezinme artik okurun sayfadaki yerini isaretliyor. Bes dokumanda bu cevap
  URL'den bedava geliyordu; tek sayfada bunu bilen hicbir sey yok, ve bu
  uzunlukta bir sayfada konumu hic isaretlemeyen bir gezinme harita degil
  baglanti listesidir. [2026-08-25]
- Sayfa artik `Pager`'a ihtiyac duymuyor; bilesen silindi. [2026-08-25]

### Changed — rozet: susten etikete

- Soldan saga gri gradyan ve uzerinde parlayan bir kivilcim vardi: tanitim
  amacli bir sus, ve sayfadaki tek nesne olarak tasarimin geri kalaninin
  kullanmadigi bir gorsel fikri odunc aliyordu. Soyledigi sey ise bir bolum adi
  ve bir surum numarasi — yani basvuru bilgisi. Artik aracin yuzunde, buyuk
  harfle, yarismayan bir boyutta, geri kalaniyla ayni panonun icinde. Tek
  isareti, bir olgu tasidigi icin yerini hak eden durum noktasi. [2026-08-25]

### Fixed — kendi CHANGELOG kapimin onermesi fazla katiymis

- `tests/test_changelog_scope.py`: bir girdinin andigi yol artik diskte VEYA
  deponun gecmisinde aranıyor. Ilk surum yalnizca calisma agacina bakiyordu ve
  bu, korudugu belge icin yanlis bir onerme: changelog olan biteni kaydeder,
  yani sonradan silinmis ya da yeniden adlandirilmis bir dosya uzerindeki isi
  dogru anlatan bir girdi hala dogrudur — ve testi gecirmek icin yazari kaydi
  TAHRIF etmeye iterdi. Avlanan asil kusur, burada hic var olmamis bir yol; git
  bunu, girdiden bugunu anlatmasini istemeden cevapliyor. Mutasyonla sinandi:
  hic var olmamis bir yol hala kirmizi veriyor. [2026-08-25]
- Testler tek sayfaya yeniden yonlendirildi. Arac listesi denetimi artik
  `#araclar` bolumuyle SINIRLI: mimari bolumu alti hooku ayni `<b>ad.py</b>`
  biciminde yaziyor ve sayfa butun olarak okununca depoda olmayan alti arac
  gibi geliyorlardi. [2026-08-25]

### Changed — kabuk, ust menu, dugmeler, altbilgi ve kahraman

- **Kabuk 1920'den 1536'ya.** "Tam genislik", "monitor kadar genis" demek degil:
  bu noktadan sonra sutunlar bir sey kazanmiyor, sayfa KAYBETMEYE basliyor —
  kelime isareti ust menunun bir ucunda yalniz kaliyor, bir baslik ile kendi
  tablosu bir karis birbirinden ayri dusuyor. Bantlar hala uctan uca; duran sey
  okuma izgarasi. [2026-08-25]
- **Ust menu bir pano oldu**, bant degil: ustten iceri kacik, kendi yuvarlatilmis
  cami, ve sayfa gorunur bicimde ALTINDAN geciyor. Marka ve gezinme birlikte
  solda; yalnizca eylemler saga sabit. Gezinmeyi ortalamak soyutta dogru,
  sayfada yanlisti — kelime isaretini yaninda yuzlerce piksel hiclikle birakiyor
  ve bu, bosluk degil eksik oge gibi okunuyordu. [2026-08-25]
- **Dugmeler tek aileye alindi.** Birincil, beyaz kenarlikli saf beyaz bir
  levhaydi; siyah bir sayfada bu mumkun olan en parlak nesnedir ve altinda
  durmasi gereken basligin sesini bastiriyordu. Simdi hala acik olan — bu zeminde
  acik olan birincildir — ama yuzunden koyu bir cerceveyle: sayfada acilmis bir
  delik degil, kenari olan aydinlik bir yuzey. Ikincil ise sayfanin geri kalaniyla
  AYNI pano, dugme boyunda; oncekiler iki ayri siteden gelmis gibi duruyordu.
  Gezinme haplari da opak metal levhalardan panolara dondu. [2026-08-25]
- **Kahraman iki sutun.** Metin sayfanin ucte birine kadar uzaniyordu ve kalan
  iki ucu siyahti — bu agirbaslilik degil, bitmemis kompozisyon. Dogrulama kaydi
  yanina tasindi: sayfanin asil iddiasi o, ve kanitiyla yan yana duran bir iddia
  bosluga bakan bir iddiadan degerlidir. [2026-08-25]
- **Altbilgi pano oldu** ve ust kenari boyunca aydinlatildi; sayfa artik bir arka
  plan rengi degisimiyle degil bir yuzeyle bitiyor. [2026-08-25]

### Fixed — telefonda gezinme diye bir sey yokmus

- 56rem altinda nav `display: none` idi ve yerine hicbir sey konmamisti: bes
  sayfanin dordu digerlerinden ERISILEMEZDI. Bu bir bicimlendirme eksigi degil
  cikmaz sokak, ve sevk ediliyordu. Yerine tam ekran bir sayfa: bes hedef,
  basparmagin isabet ettirecegi boyutta, sayfayi karartmak yerine bulaniklastiran
  bir zemin uzerinde. Escape, baglantiya tiklama ve 56rem ustune yeniden
  boyutlandirma kapatiyor. [2026-08-25]
- **`backdrop-filter` bir icerme blogu yaratir.** Menu basligin cocugu ve
  `position: fixed`; `.head-in` uzerindeki bulaniklik onu ust cubugun icine
  hapsediyordu — 226x144 piksellik bulanik bir hiclik, icinde bes tane 2px
  yuksekliginde baglanti. Dolgu ve bulaniklik bir sozde-ogeye alindi: ayni cam,
  icerme blogu yok. `position: relative` guvenli, cunku o `absolute` icin
  icerme blogudur, `fixed` icin asla. [2026-08-25]
- `left:0; right:0` verilmis menu 226px cikiyordu: nav bir izgara kabinin cocugu
  ve temel kuraldaki `justify-self: start`i koruyor, bu da kullanilan genisligi
  iki ofset arasina yayilmak yerine icerige gore buzuyordu. Genislik acikca
  yazildi. [2026-08-25]
- `nav` ogesinde `id="site-nav"` yoktu — hamburger'in `aria-controls`'u ve script
  ikisi de onu adiyla ariyordu, yani menuyu acan kosula hic girilmiyordu.
  [2026-08-25]
- Kahramanin iki sutunu ilk denemede tutmadi: `.ed > .ann` iki sinif, `.hero > *`
  bir sinif ve bir evrensel — genel kural kazaniyor ve metin iki izli bir
  sablondan `span 7`/`span 8` istiyordu, tarayici alti tane sifir genislikli
  ortuk sutun uretiyor, baslik hepsini kapsiyor ve panel yanina oturacagi metnin
  ustunde kendi satirina itiliyordu. Sablonu ezmek yerine yerlesim on iki sutunun
  UZERINDE verildi. [2026-08-25]

### Changed — site bastan tasarlandi: tam genislik on iki sutun, sivi cam

**Faz 1 — izgara.** Govde 912px'ti, 1920 ekranda **%47,5**. Simdi kabuk ekrani
dolduruyor ve icerik 12 sutunlu bir izgarada. Kritik ayrim: tam genislik
DUZENIN ozelligi, cumlelerin degil — 1800px'lik bir satir 260 karakterdir ve
kimse iki kez okumaz. Genislikten kazanan her sey (tablolar, kart izgaralari,
kayit) 12 sutunu aliyor; soldan saga okunan her sey 7 sutun aliyor ve olcude
duruyor. [2026-08-25]

- `.rows` 1440px ustunde **iki sutuna** aciliyor. Ad/aciklama ciftlerinden olusan
  bir listeyi 1900px'te tek sutun gostermek eldeki genisligin en kotu
  kullanimiydi: 240px ad, 1500px aciklama, ve her seferinde bastan basa donen
  bir goz. [2026-08-25]
- Kenar notlari izgaranin ICINE, duzyazinin biraktigi sutunlara tasindi ve
  artik pasajin SAGINDA. Kabugun disina asmak yalnizca kabuk bir bosluk
  birakacak kadar darken isliyordu; ekrani dolduran bir kabugun disi yok. Sol
  ray 1900px'lik bir sayfada notu kendi cumlesinden bir ekran ayirir. [2026-08-25]

**Faz 2 — zemin.** Tek merkezi wash bir vinyetti; cam, arkasinda YAPISI olan bir
sey ister, cunku duz bir alanin bulanigi yine ayni duz alandir ve panel gri bir
dikdortgen olarak okunur. Uc kaynak, her buyuk panelin arkasinda bir aydinlik
ve bir karanlik bolge olacak sekilde yerlestirildi. [2026-08-25]

**Faz 3 — cam.** Tek tarif, sekiz bilesen. Bir yuzeyin cam okunmasi icin dort
sey gerekiyor ve biri eksik olunca renkli kutu oluyor: yari saydamlik, arkasini
bulaniklastirip hafifce doyurmasi (gercek cam sacilirken rengi yogunlastirir),
parlak UST KENAR — isigin pahi yakaladigi cizgi, buradaki en guclu derinlik
ipucu — ve yumusak bir golge. Onceden dokuz farkli arka plan ve alti farkli
kenarlik vardi, her yon bir tane biriktirmisti. [2026-08-25]

**Faz 4 — kurumsal yapi.** Ust menu uc parcali izgara oldu: 960px'te esdegerdi
ama 1900'de degil — satir, kelime isaretini bir ucta yalniz birakip gerisini
obur uca yigiyor ve gezinme gozun aradigi yerde olmuyordu. Kunye seridi
`space-between`ten dort esit sutuna gecti; dort figuru 1800px'e yaymak onlari
etiket uzunluklarinin tesadufune gore diziyordu. Bolum basliklarinin altina
izgara genisliginde cizgi geldi. [2026-08-25]

**Faz 5 — hareket.** Cam panel bir paragraftan daha fazla oturuyor: 1500px'lik
bir panelde ayni 12px seyirme gibi okunuyor. Imlec altinda yalnizca iki panel
kalkiyor — okurun fiilen isaret ettikleri; farenin gectigi her tablonun
parlamasi susleme olur. [2026-08-25]

### Fixed — dugmenin parlamasi sayfada geziniyordu

- `.pill`'e `overflow: hidden` konmamisti. Parlama sozde-ogesi imlece kadar
  `translateX(-130%)`te park ediyor, yani dugmenin bir bucuk boyu SOLUNDA; kirpma
  olmayinca orada boyaniyor ve ust menunun ortasinda hicbir seye bagli olmayan
  metalik bir serit birakiyordu. `isolation` isin z-index yarisini yapiyordu,
  kutu hakkinda hicbir sey. [2026-08-25]

### Changed — site yeniden tasarlandi: siyah zemin, Inter, tek serif vurgu

- Yon degisti ve gonderdigin sartnamenin dili uygulandi. Zemin **saf siyah**
  (#000, tonlu bir yakin-siyah degil): sayfadaki her yuzey o zemin uzerinde
  dusuk alfali beyaz, yani zemindeki herhangi bir ton hepsi tarafindan tasinir
  ve griler notr okunmayi birakirdi. [2026-08-25]
- Yazi: sayfayi **Inter** tasiyor. Serif TEK bir role dustu — sayfa basligindaki
  vurgulanan sozcukler — ve orada iki degisikligi birden yapiyor: yuz degisimi
  (grotesk'e karsi yuksek kontrastli serif) ve **griye dusme**. Beyaza degil:
  vurgulanan sozcukler satirdan GERI cekiliyor, ki bu vurgunun normalde yaptiginin
  tersi ve dusunulmus bir eslesme gibi okunmasinin sebebi. [2026-08-25]
- `Instrument Serif` italik **kendi barindiriliyor**, iki alt kume: Turkce
  basliklar g ve s tasiyor, onlar latin disinda. Google Fonts <link> kullanilamaz
  — sayfanin kendi politikasi `font-src 'self'`, tarayici istegi reddeder ve
  baslik sessizce Times'a duserdi. [2026-08-25]
- Bilesenler: gezinme **sivi metal haplar** (capraz gradyan + imlecte uzerinden
  gecen isik bandi), birincil dugme dikey gradyanli aci yuzey, ikincil dugme
  buzlu cam (`backdrop-filter`), ust satir gradyan dolgulu **rozet** + kivilcim.
  Kivilcim bir alt oge degil arka plan: rozet markup'ta tek dugum kaliyor ve dort
  sayfa birer ikon tasimak zorunda kalmiyor. [2026-08-25]
- Kunye seridi kutulu izgaradan araliklandirilmis bir satira dondu. Hucrelerin
  her birinde kenarlik, dolgu ve yaricap vardi; dort sayidan dort kucuk kart
  yapiyor ve sayfanin en sessiz icerigine en gurultulu kabi veriyordu.
  [2026-08-25]
- Giris koreografisi sartnamenin merdivenine tasindi ve ust menu de merdivene
  katildi: daha once birinci karede oradaydi, bu da sayfayi iki kez yuklenmis
  gibi gosteriyordu — cerceve hazir, icerik sonradan geliyor. [2026-08-25]
- Acik tema aynadan gecirildi, kopyalanmadi. Beyaz uzerinde koyu bir hap, koyu
  sayfadaki isik yakalayan seridin ayni nesnesi degildir; siyah bir dikdortgendir.
  Gradyanlar ters cevrildi, kivilcim murekkeplendi. [2026-08-25]

### Added — yuzey ve hareket katmani

- `web/src/styles/global.css`: zemin artik duz bir dolgu degil. Sayfada bir isik
  kaynagi var (`--glow`, `body`'ye sabitlenmis) ve kagit lifi var (`--grain`,
  dosyanin icinde uretilen dort satirlik SVG — bir goruntu istegi, hicbir istek
  yapmayacagini soyleyen sayfada olmaz). Yukseltilen her yuzey ustunden bir
  cizgi isik yakaliyor (`--edge`); numara bu, ve her turlu golgeden ucuz.
  [2026-08-25]
- **Kenar cizgisi.** Prova sayfasinin bir kenar cizgisi vardir. Olmadigi icin
  aygit sutunu bir *bosluk* gibi okunuyordu — sol ucte bos duran bir seridin
  duzen hatasi degil isaretlerin yeri oldugunu soyleyen sey bu cizgi. Iki ucunda
  soner, cunku basili bir cizgi tam guclu bir uctan baslamaz. [2026-08-25]
- **Uc hareket, ucu de sayfanin kendi iddiasindan.** Bir pasaj OTURUR: son
  birkac pikseli yukselip durur. Bir isaret CIZILIR: elin baslayacagi uctan
  buyur — grup basligindaki cizgi, notun kirmizi rayi, baglantinin alt cizgisi.
  Bir kayit BASILIR: satirlar birbiri ardina gelir, ki bu sitede hareketin
  DOGRU bir sey anlattigi tek yer — o satirlari bir program tek tek, bu sirayla
  yazdi. Hicbiri ekran disindan kaymiyor, buyumuyor, ziplamiyor. [2026-08-25]
- Baslik sayfaya BASILIYOR: yukselirken satir kutusu onu ustten asagi aciyor
  (`clip-path`). Sarmalayici span yerine clip-path, cunku alternatif bes sayfada
  iki dilde her basligin etrafina bir `.headline-line` ogesi koymakti — gorsel
  bir etki icerigin tasimasi gereken bir seye donusmemeli. Isaretlenen sozcuk
  bir tempo sonra keskinlesiyor, boylece duzeltme satira YAPILMIS gibi okunuyor.
  [2026-08-25]
- Ust satir bir damgaya dondu (kenarlik + yuzey), birincil dugmenin uzerinden
  imlecte tek bir isik gecisi geciyor. Gecis, sayfanin isiginin zaten geldigi
  acida ve dusuk alfada: yuzey donuyor gibi okunuyor, metal gibi degil.
  [2026-08-25]

### Fixed — hareket katmaninin kendi tuzaklari

- `web/src/layouts/Base.astro`: **olu adam anahtari.** `.js` sinifi icerigi
  gizler ve onu birinin gosterecegi vaadine dayanir; o vaadi tutan script hic
  kosmazsa — ileride bir sozdizimi hatasi, engellenmis bir inline script, once
  hata atan bir eklenti — sayfada bunu fark edecek baska hicbir sey yok, ve
  sonuc eksik animasyon degil BOS SAYFA. Artik acilis kendini isaretliyor;
  DOMContentLoaded'da o isaret yoksa `.js` geri aliniyor. Sinandi: isaret
  silindiginde gizli kalan oge sayisi sifir. [2026-08-25]
- `rootMargin` negatif verilmisti, yani acilis GEC tetikleniyordu ve hizli
  kaydiran okur baslamamis bir bolume varip bos sutun goruyordu. Sezgisel
  gorunen hata bu; kok asagi dogru BUYUTULMELI. Artik ceyrek ekran onden
  tetikleniyor ve oturma .45sn. [2026-08-25]
- `threshold` bir kesirdi. Kesir, bir blogun belli bir ORANDA gorunmesini
  ister; kisa bir sayfanin dibine yaslanmis uzun bir bolumun kisaltilmis kok
  icinde ulasabilecegi oran sinirlidir, yani metni `opacity: 0`'da kalabilir ve
  kaydirilacak yer kalmaz. Artik `0`: aclikla olmeyen tek kosul. [2026-08-25]
- Kahraman parlitisi kaldirildi. Bir radyal, sonumu kutunun ICINDE bittigi
  surece isik gibi durur; bu blogu %12 asacak sekilde gerilmisti, yani wash
  hala gucteyken oge bitiyordu ve sayfada aygit sutunu boyunca dikey kenari
  gorunen aydinlik bir panel olusuyordu. Tek lamba `body`'de. [2026-08-25]
- Ust satir damgasi `inline-flex` idi ama bir izgara ogesi aksi soylenmedikce
  hucresine yayilir: damga butun blok genisligindeydi, yani sayfaya vurulmus
  bir isaret degil etrafi cerceveli bir alt yazi. [2026-08-25]
- `prefers-reduced-motion` "ayni sey, daha hizli" degil: butun baslangic
  durumlari kosulsuz serbest birakiliyor. En kotu durumda sinandi — acilis hic
  kosmamis gibi `.is-in` sokulup blok uygulandiginda gizli kalan oge sifir.
  [2026-08-25]

### Changed — sitenin gorsel sistemi: duzeltilmis prova sayfasina donus

- `web/src/styles/global.css`: tipografi ciftlemesi geri geldi ve tersine —
  DISPLAY yuzu monospace (arac, kayit, damga), GOVDE yuzu serif (elyazmasi).
  Site bastan asagi tek grotesk ile diziliyordu ve o dizgi ikisini de
  soylemiyordu. Serif yigini web fontu getirmiyor: hicbir istek yapmayacagini
  soyleyen bir sayfada dis istek, ustune yavas baglantida sessiz geri dusus.
  [2026-08-25]
- Palet sicak kagittan **soguk arduvaza** dondu, teal vurgu yerine **oksit
  kirmizisi**. Sebep kavramsal: kirmizi, bir duzeltmenin yapildigi anlamina
  gelir; teal ise duzeltmeden SAG CIKAN muredir. Eski palette her ton
  notrun ayni tarafindaydi, o yuzden sayfadaki hicbir sey baska bir seyin
  uzerine uygulanmis gibi durmuyordu. [2026-08-25]
- Vurgulanan sozcuk artik serifin kendi italigiyle ve kirmiziyla diziliyor —
  ayni roman yuzunde ikinci bir renk degil. Bir duzeltme gibi okunmasini
  saglayan sey KESIM degisikligi. [2026-08-25]
- Bolum baslikari kucultuldu ve monoya alindi: sayfada buyuk olan tek sey
  baslik. Eski olcek her basligi ayni ses tonunda bagiriyordu, yani hiyerarsi
  is yapmiyordu. [2026-08-25]
- Kenardaki notun cizgisi ve anahtari kehribardan kirmiziya: bir kenar notu
  tanimi geregi bir isarettir, ve bu sayfanin butun savi kenardaki isaretin
  oksit kirmizisiyla yazildigi. Grup basligindaki 900px'lik cizgi ise tersine
  murekkebe alindi — bir el 900px'lik cizgi cizmez, ve isaretleme rengini
  bolumun en genis ogesine harcamak sayfadaki gercek isaretlerin hepsini
  sessizlestiriyordu. Birincil dugme de ayni gerekcyle murekkep. [2026-08-25]

### Fixed — canlandirilan paletin olculmemis murekkepleri

- Geri getirilen `--ink-2`/`--ink-3` degerleri geldikleri tasarimda BUYUK HARF
  mono etiketler icin secilmisti; burada not duzyazisini ve tablo alt metnini
  tasiyorlar, yani normal govde metni ve 4.5:1 borclular. Oldugu gibi 4.0 ve
  **2.9** veriyordu. Olculup duzeltildi: acik temada 6.3 ve 4.9, koyuda 6.9 ve
  4.9. Ayrica acik temadaki `--flag` 4.17'den 4.7'ye — ret etiketleri kalin
  12px, yani buyuk metin sayilmiyor. [2026-08-25]
- `web/src/layouts/Base.astro`: `theme-color` metalari yeni zemine baglandi;
  eski sicak degerleri tasiyorlardi ve tarayici cubugu sayfayla uyusmuyordu.
  [2026-08-25]

### Fixed — sitenin sayfa duzeni: uc sol kenar yerine bir tane

- `web/src/styles/global.css`: duzenleme izgarasi tek sutuna indi. Sayfa uc ayri
  sol kenar tasiyordu ve bunlar asagi dogru donusumlu geliyordu: duzyazi olcu
  sutununda bir kenarda, her tablo/kart `.full` ile 240px soldaki baska bir
  kenarda, ve bir bolumun KENDI basligi adlandirdigi tablonun sagina girintili.
  Goz blogu hicbir yerde bulamiyordu. Artik her sey tek kenardan basliyor,
  duzyazi o kenardan baslayip olcude bitiyor. [2026-08-25]
- Kabuk (`--wrap`) 76rem'di, icerik 57rem'e geliyordu — ve izgara sutunlari
  kapsayicinin BASINA yaslanir. Artan 19rem her sayfanin saginda olu bosluk
  oluyordu; blok merkezden 135px solda duruyordu ve kabugu dolduran ust menu,
  altindaki her seyden 256px daha sagda bitiyordu. Kabuk artik blogun kendisi
  kadar: bastan asaga iki dikey cizgi, baskasi yok. [2026-08-25]
- Kenar aygiti (§ isaretleri ve numarali notlar) artik blogun DISINA, gercek
  kenar boslugua asiliyor. Notlar zaten `position:absolute` ile akistan
  cikariliyordu; sutun yalnizca § isaretleri ve her paragrafin yanindaki
  bosluk icin yer ayiriyordu. [2026-08-25]
- Asilmanin kac piksel yer istedigi aritmetik, begeni degil: `--margin + --s6`.
  1440px ustunde kabuk ortalanir ve aygit kullanmadigi bosluga asilir; 1216 ile
  1440 arasinda ortalanan sey BLOK degil BILESIM olur, cunku o bandin tamami
  dizustu ekranidir ve alternatif, cetvelsiz gorulemeyen bir ortalama ugruna
  notlari kaybetmekti. Altinda notlar yazildiklari yere geri katlanir.
  [2026-08-25]
- Baslikta `max-width: 20ch` kaldirildi: izgaranin kendi genisligine 50px kala
  bitiyordu — bir karardan cok bir hata gibi okunan ucuncu sag kenar. [2026-08-25]

### Fixed — ag tespiti metni degil sozdizimini okuyor

- `tests/test_governance_docs.py`: SECURITY.md'nin dayandigi "hangi betikler aga
  cikiyor" listesi artik `ast` ile turetiliyor. Metin taramasi bir islev adinin
  ANILMASI ile CAGRILMASI'ni ayirt edemiyordu — iki yonde birden yaniliyor:
  nazik bir docstring dosyayi listeye sokuyor, `getattr(requests, "get")` yazan
  bir betik listeden cikiyor ve suite yesil kaliyor. [2026-08-25]
- `SECURITY.md`: liste **dokuz degil on bir** dosyaymis. `library_import.py` ve
  `manuscript_import.py` kendi soketini acmiyor ama `doi2bib.py`'i alt surec
  olarak kosturarak DOI'lerin tamamini yeniden cekiyor — hicbir surumde
  yazmiyordu, ve o grep onlari hicbir zaman bulamazdi. Belge artik ikiye
  ayiriyor: grep'in bulabildigi sekiz, alt surec uzerinden cikan uc. [2026-08-25]
- `SECURITY.md`: Ingilizce yari "nine", Turkce yari "sekiz" diyordu. Iki sayi da
  artik testten geciyor; sozle yazilan bir sayinin uzerinde hicbir kapi yoktu ve
  iki yari birer duzenlemede birbirinden ayrilmisti. [2026-08-25]

### Fixed — yanlis atesleyen uc denetim

- `scripts/consistency_check.py`: bir aralikin ust ucu, bir yuzde ve bir isme
  yapisan rakam artik sayilmiyor. `61.5-76.2 records` icindeki **76.2**
  ornek sayisi sanilip manifestteki **76** ile catisiyordu; `COVID-19 records`
  ondokuz seyin sayisi degildir. Bu anahtarlarin hepsi tam sayidir, kesirli bir
  eslesme bir okuma hatasidir. [2026-08-25]
- `scripts/tr_style_check.py` + `templates/tr-terminology.json`: cok-anlamli
  sozcukler artik sozlukte `tr_ambiguous` alaninda ilan ediliyor ve hic
  sayilmiyor. Bastirma daha once sozcugun YALNIZCA BIR KEZ gectigi durumda
  calisiyordu; bu tersineydi, cunku cok-anlamlilik sozcugun ozelligidir, kac kez
  gectiginin degil — ve kosul, bastirmayi tam da metnin yaslandigi sozcukte ise
  yaramaz hale getiriyordu. Kural artik projenin duzenleyebildigi dosyada.
  [2026-08-25]
- `scripts/consistency_check.py` · `failure_scan.py` · `cite_audit.py`: HTML
  yorumlari artik metin sayilmiyor. Dort kardesinde duzeltilmis, bu ucunde hic
  sinanmamisti; ucunde de kusur gercekti. En agiri `cite_audit`'inki: yoruma
  alinmis bir anahtar atif sayiliyor, boylece kaynakcadaki oksuz bir kunye
  atifli gorunuyordu. PRISMA baglantisi (`<!-- PRISMA: ... -->`) ham metinden
  once okundugu icin etkilenmiyor, ve bunun kendi testi var. [2026-08-25]

### Changed — TECH-DEBT defteri gercege getirildi

- `.claude/TECH-DEBT.md`: on acik satirin besi zaten duzeltilmis ama silinmemisti
  (`decimal_separator` binlik ayiraci, Ingilizce Abstract blogu, `temporal_check`
  20xx nicelikleri, `phase_gate` cevrilmis onay isareti). Dogrulanip silindiler.
  Defterin kendi kurali "kosul gercekten kalktiginda satiri sil" idi ve satirlar
  kalmisti — bir bayrak listesi, tekrar okundugunda dogru degilse bir bayrak
  listesi degildir. [2026-08-25]
- Geriye iki acik satir kaliyor, ikisi de gitignore'daki `runs/` altinda yalnizca
  bu makinede yaniltan yerel tuzaklar; sevk edilen hicbir seyi etkilemiyorlar.
  [2026-08-25]

### Added — vitrin sayfasi ucuncu kosuyu taniyor

- O gunun vitrin sayfasi ve arac tablosu: ucuncu kosu icin
  `ARTIFACTS_SLR_EN` tablosu (13 artefakt, TR+EN) ve kendi bolumu. Sayfa
  bastan asagi guncellendi, cunku bir tanesini atlamak sayfayi kendisiyle
  celiskiye dusuruyordu: hero sayaclari (2 -> 3 kosu, 22 -> 23 hakem turu),
  sayfa aciklamasi, OG basligi, "Bunlar ne degildir" listesindeki "Iki kosu,
  iki konu" satiri ve nihai belgenin neden yalnizca bir kosuda oldugunu
  anlatan kapanis paragrafi — artik iki kosuda. Bolum numaralari 03/04'ten
  04/05'e kaydi. [2026-08-25]
- "Kiti kusurlu gosteren dosyalar" bolumune ucuncu kosunun en sert dosyasi
  eklendi: sitasyon kapisinin bes denetci temiz raporlarken FAIL vermesi, ve
  sebebi — besi de bir kaydin KENDI DOI'siyle eslesmesine bakiyor, hicbiri
  DOI'nin hala guncel olup olmadigina. [2026-08-25]
- "Bunlar ne degildir" listesine besinci madde: makalenin hicbir dergiye
  gonderilmedigi. Icindeki 26 calisma ve sayilar gercek; makalenin statusu
  degil. [2026-08-25]

### Added — CHANGELOG kapisinin gormedigi yarisi

- `tests/test_changelog_scope.py`: bir girdinin adini andigi YOLUN checkout'ta
  cozulmesi artik sinaniyor. Kardes kontrol bir dosya adinin CIPLAK bicimini
  yakaliyordu ama bir girdinin fiilen yazildigi bicimi — dizinle nitelenmis
  hali — hic gormuyordu, cunku desende bolu isareti yoktu. Bes girdi tam bu delikten gecti: iki
  script ve `pdf2md.py`'nin uc sayacli surumu, hepsi yalnizca `runs/` altinda
  yasarken burada yayimlanmis, ve suitenin tamami yesil kalmisti. Ilk
  segmenti bu depoda bulunmayan yollar (`analysis/`, `drafts/`, `src/`)
  kapsam disi: onlar kitin degil, kitin uzerinde kostugu projenin yollari.
  [2026-08-25]
- Sinirini kendisi soyluyor: yalnizca KONUM denetlenebilir. O yoldaki dosyanin
  girdinin anlattigi seyi yapip yapmadigini hicbir test okuyamaz; o yari,
  girdiyi niyetten sonra degil diff'ten sonra yazmakla kaliyor. [2026-08-25]

### Added — ucuncu vitrinin butunluk testleri

- `tests/test_governance_docs.py`: `examples/showcase-slr-en/` icin on bir test.
  Ilk iki vitrinin sahip oldugu koruma seti (listelenen her dosya var mi,
  indeksin andigi sayilar onlari ureten artefaktlardan geri geliyor mu,
  kaynakca tumuyle makine-dogrulanmis mi, iletisim bilgisi var mi) artik
  ucuncusunde de kosuyor. Vitrin bir commit once, testleri olmadan girmisti;
  o gun elle dogruydu, ama elle tutulan durum tam olarak sessizce kayan
  durumdur. Ucu bu kosuya ozgu: `.docx` icindeki `word/media` sayisi ile
  `<w:drawing>` sayisinin esitligi — yani "derleme OK dedi ama belge figursuz
  cikti" kusurunun tam kendisi; defterin `--verify` zincir hukmu; ve
  "korumalarin yakaladiklari" bolumundeki her okun gercek bir artefakta
  dusmesi. Bir de ters yon: indekste yazmayan bir dosyanin dizine sizmasi.
  [2026-08-24]
- Testlerin kirmizi olabildigi alti mutasyonla dogrulandi (dosya silme, kacak
  dosya, kaynakca-kapi sayi uyusmazligi, ekilmis e-posta, figurleri soyulmus
  bir `.docx`, sonradan yeniden yazilmis bir defter kaydi); hicbiri gercek
  dosyalara dokunmadan, kopya uzerinde. [2026-08-24]

### Added — kitin ucuncu vitrini: korumalarin yakaladiklari

- `examples/showcase-slr-en/`: bir sistematik derleme kosusunun 13 artefakti ve
  onlari cerceveleyen README. Diger iki vitrin kitin iyi bir cikti uretebildigini
  gosteriyor; bu kosunun gosterdigi sey farkli — kitin yazarini kac kez
  yakaladigi. Sitasyon kapisi bes denetci PASS demisken FAIL verdi (hepsi bir
  kaydin KENDI DOI'siyle eslesmesine bakiyor, hicbiri DOI'nin hala guncel olup
  olmadigina); bir baslik korumasi kazara yeniden adlandirilmis bir kamera-hazir
  surumu buldu; insan tarama referansi hicbir protokolde yazmayan bir tarih
  penceresini ortaya cikardi; faz kapisi, outline attestation'i ile eslesmedigi
  icin yazmayi durdurdu; ve ilk derleme "OK" yazip figursuz, tablosuz bir belge
  uretti. Makale hicbir dergiye gonderilmedi ve bu, kendi baslik sayfasinda
  yazili. [2026-08-24]

### Fixed — bozuk bir font haritasi tum donusumu cokertiyordu

- `scripts/pdf2md.py`: font-to-unicode haritasi bozuk bir PDF, dusuk yarisi
  dusmus bir astral karakteri TEK BASINA vekil (lone surrogate) olarak geri
  veriyor. utf-8 yazimi bunda hata firlatiyor ve 16 sayfalik makalenin tamami
  donusmeden dusuyordu — dosyadan zaten kurtarilamayan 29 karakter yuzunden.
  PyMuPDF'in kendi duz metin cikarimi ayni karakteri coktan U+FFFD'ye
  dusuruyordu; artik pdf2md de ayni sekilde dusuruyor ve sayiyi
  `meta.json`'daki yeni `lossy_chars` alanina yaziyor, boylece kayip sessiz
  degil raporlanmis oluyor. [2026-08-24]

### Added — uctan uca boru hatti testleri: birimler dogruydu, dikisler degil

- 2026-08-23'te bitmis bir elyazmasi ilk kez kitin kendi boru hattindan gecirildi
  ve **on iki kusur** dokuldu. Hepsi mevcut test suitesinden GECMISTI, cunku suite
  fonksiyonlari sinaviyordu ve boru hatti dikislerden ibaret: birimler kendilerine
  verilen girdiler hakkinda haklıydi ve gercek bir elyazmasinin girdileri
  hakkinda yanlisti.
- `tests/test_pipeline_end_to_end.py`: TEK bir gercekci projeyi kuruyor —
  Turkce ondalik sayilar, madde numaralari KALIN yazilmis bir hakem raporu,
  satir kayan kalin bir anahtar kelime satiri, sonunda karar yorumu tasiyan bir
  baslik, bir STATUS gunlugu, bir ek, iki ozet — ve gercek betikleri ve gercek
  kancayi ona karsi alt surec olarak kosturuyor.
- En onemlisi son test: kitin manset garantisini SIRAYLA sinar — once atif
  kapisi, sonra Major = 0, sonra derleme. Iki yari ayri ayri test edilmisti ve
  BILESIMI test edilmemisti; iki Major tasiyan bir raporun acik bir kapiya
  ulasmasi tam olarak boyle oldu. 9 test. [2026-08-23]

### Fixed — anahtar kelime denetimi iki dilli bir elyazmasinda yanlis listeye bakiyordu

- Yeni boru hatti testinin ILK kosusunda cikti: `check_keywords` yalnizca
  `drafts/abstract.md`'yi okuyor, yani **Turkce bir makalenin INGILIZCE listesini**
  denetliyor ve `ozet.md`'yi hic acmiyordu. Dergiler ikisini birden ister.
- Ikisi de okunuyor ve **birbirleriyle karsilastiriliyor**: uzunluklari farkli
  iki liste, tek dosyaya bakan hicbir denetimin goremeyecegi bir kusurdur, cunku
  her biri tek basina kurallara uygundur. Cikti dosya basina sayiyi veriyor ve
  sorun mesaji hangi dosyanin ihlal ettigini adiyla soyluyor. 2 test.
  [2026-08-23]

### Added — env_capture: ureten modeli de kaydediyor, adlandirmiyor SAYIYOR

- Bir yapay zeka beyani yazilimin adini VE surumunu ister; `compliance_gen.py`
  `--tool` ile `--uses`'u zorunlu kilar — ama kit surumu uretecek hicbir sey
  KAYDETMIYORDU. Beyanin en denetlenebilir olmasi gereken alani, kosunun
  ureteemedigi tek alandi; gercek bir elyazmasinda kitin DISINDAKI oturum
  gunluklerinden dolduruldu ve depoyu klonlayan biri onu dogrulayamaz.
- `--model`: bu projenin Claude Code transkriptlerindeki her yardimci turunun
  `model` alanini sayar ve farkli kimlikleri TUR SAYILARIYLA birlikte raporlar.
  Transkript yoksa ya da hicbiri model kimligi tasimiyorsa `unavailable` yazar,
  nereye baktigini soyler ve makul bir model adi UYDURMAZ — bulunamamis bir model
  yok demek degildir.
- `<synthetic>` turleri sayilmaz (kancanin urettigi turlerdir, model ciktisi
  degil), ve blok ortam hash'inin DISINDA durur: hash iki KOSUYU karsilastirmak
  icindir, sonraki bir oturumun transkripte tur eklemesi kimildamamis bir ortamin
  parmak izini degistirmemelidir. 5 test. [2026-08-23]

### Fixed — submission_pack iki dilli bir elyazmasinda tek ozet goruyordu

- `check_abstract` yalnizca `drafts/abstract.md`'yi okuyor ve tek bir
  `abstract_max_words` sayisiyla karsilastiriyordu. Kitin kendi kurulusu iki
  dillidir — `ozet.md` + `abstract.md`, ve `tr_style_check` ikisinin
  esdegerligini zaten denetler — ama gonderim denetiminin ikinci ozet diye bir
  kavrami yoktu.
- Sonuc: elyazmasinin KENDI DILINDEKI sinir, CEVIRIYE uygulaniyordu. Kitin
  ornek Turkce derlemesinde Turkce ozet 250 sinirinin tam icindeydi ve
  Ingilizce ozet, DERGININ KENDI CUMLESIYLE Turkcesinin en cok %15 fazlasi
  olabilirdi (287); denetim yine de "sinir asildi" diyordu. Yanlis alarm da bir
  yanlis sayidir.
- `abstract_max_words_by_file` eklendi (`{"ozet.md": 250, "abstract.md": 287}`);
  tablosu olmayan her ozet dosyasi eskisi gibi `abstract_max_words`'e duser, yani
  varsayilan davranis degismedi. Cikti artik dosya basina sayiyi ve sinirini
  ayri ayri veriyor, sorun mesaji da hangi dosyanin astigini adiyla soyluyor.
  3 test. [2026-08-23]

### Fixed — dogruluk beyani ureten betik sabit bir yanlis cumle basiyordu

- `compliance_gen.py ai-disclosure` her ciktisina KOSULSUZ olarak *"No results,
  data, or findings were AI-generated"* cumlesini basiyordu. `--uses "data
  analysis"` verildiginde beyan ayni anda hem analizi yapay zekanin yaptigini
  hem hicbir verinin yapay zeka uretimi olmadigini soyluyordu — tek bir cumle
  ciftinin icinde kendi kendini yalanlayan bir beyan.
- Bu bir bicim kusuru degildir. Beyanin butun amaci dogruluktur; dergiler
  yapay zeka kaynakli yanlis sunumu giderek bir bicim hatasi degil SUISTIMAL
  olarak degerlendiriyor (ornegin kitin ornek kosusunun hedef dergisi bunu
  kendi politika sayfasinda acikca yaziyor).
- Cumle artik OPT-IN (`--no-ai-results`), cunku o bir kalip degil ISIN
  KENDISI HAKKINDA BIR IDDIADIR ve yalnizca yazar yapabilir. Bayrak `--uses`
  analiz/veri/sonuc/bulgu adlarindan birini iceriyorsa betik REDDEDER ve hangi
  kelimenin catistigini soyler. Bayraksiz cikti, iddianin yapilmadigini ve bazi
  dergilerin bu noktanin iki yonden de acikca ele alinmasini istedigini bir
  notta bildirir. 3 test. [2026-08-23]

### Fixed — sozcuk sayaci her ondalik sayiyi iki sozcuk sayiyordu

- `word_budget.count_words` kalibi `\b[\w'-]+\b` idi ve ondalik ayraci `\w`
  degildir: **"0,940" iki sozcuk, "1.572" iki sozcuk.** Word'un, gonderim
  portalinin ve editorun tek sozcuk saydigi her sayi burada iki sayiliyordu.
  Sayi yogun bir ozette bu onlarca sozcuk eder ve dogrudan bir dergi sinirina
  karsi olculur — kitin ornek derlemesinin ozeti 288 gorundu, kusur giderilince
  278 cikti.
- Kalip artik ic ayracli sayiyi tek jeton olarak esliyor. `submission_pack` de
  ayni fonksiyonu kullandigi icin gonderim denetimi de duzeldi. [2026-08-23]

### Fixed — submission_pack: uc sayi da makuldu, ucu de yanlisti

Ilk kez gercek bir elyazmasi ve gercek bir derginin sinir dosyasiyla kosuldu.
Uc alan da bir sayi dondurdu, uc sayi da yanlisti — ve hicbiri hata gibi
gorunmuyordu.

- **Baslik, PROJECT.md'nin karar yorumlarini iceriye aliyordu.** `title_of()`
  `**Title (working):**` sonrasini oldugu gibi aliyor; PROJECT.md ise kararlarin
  gerekcesini satir sonundaki HTML yorumlarinda tasiyor. 118 karakterlik bir
  baslik **788** karakter olarak raporlandi — hem derginin baslik sinirina karsi
  karsilastirilan sayi, hem de bir insanin portala YAPISTIRACAGI dize. Kapali
  yorumlar once, satir sonunda acik kalan yorum sonra temizleniyor (`.` satir
  sonunu gecmedigi icin cok satirli bir yorum buraya zaten kirpilmis geliyor ve
  `<!--.*?-->` onu bulamiyordu).
- **Anahtar kelime satiri iki ayri sebeple yanlis okunuyordu.** Gercek markdown
  iki nokta ustusteyi KALININ ICINE yazar (`**Keywords:** a; b`), dolayisiyla
  kapanis yildizlari ilk kelimenin icine dusuyordu (`"** diabetic retinopathy"`);
  ayrica liste satir kaydiginda `(.+)` ilk satirda duruyor ve geri kalan her
  kelime SESSIZCE dusuyordu. Alti kelimelik bir liste dort okundu — derginin
  asgari sayisina karsi eksik sayan bir hata.
- **Govde sayimi STATUS.md'yi ve ekleri govdeye katiyordu.** STATUS.md yazim
  gunlugudur, makale metni degildir — kitin kendi verify-citations becerisi onu
  ayni sebeple disliyor. Ekler ise makaledir ama derginin kelime siniri ANA
  METIN icindir; uzun bir eki govdeye katmak gonderilebilir bir makaleyi
  gonderilemez gosterir (ya da yazar govdeyi, govdede olmayan kelimeler icin
  kesmeye kalkar). 36.830 sozcukluk bir govde **70.982** olarak raporlandi.
  Ekler artik ayri, STATUS.md sayimin disinda ve hangisinin dislandigi
  ciktida yaziyor. 3 test. [2026-08-23]

### Fixed — latex_build.sh fontspec'li hicbir belgeyi derleyemiyordu

- Betik `latexmk -pdf` cagiriyordu, yani pdflatex. Pandoc on bilgisinde
  `mainfont:` tanimlayan bir belge — Latin-1 disindaki her elyazmasi kendi
  yazisini almak icin bunu tanimlamak zorundadir — pdflatex altinda
  "LaTeX Error: Unicode character X" verir ve **hic PDF uretmez**. Bu bir belge
  hatasi degil, yanlis motordur; kitin ornek Turkce derlemesi bu yuzden
  hicbir zaman derlenmemisti.
- Motor artik .tex'in KENDISINDEN saptaniyor (`fontspec` / `setmainfont` /
  `setsansfont` / `setmonofont` -> xelatex, aksi halde pdflatex), boylece bir
  proje kendi yazitipi tercihinin hangi motoru gerektirdigini bilmek zorunda
  degil. `LATEX_ENGINE` (pdf | xelatex | lualatex) elle ezer ve gecersiz bir
  deger latexmk'nin varligindan ONCE reddedilir — yanlis bir deger, ilgisiz bir
  kontrolun arkasina saklanmamalidir. 4 test. [2026-08-23]

### Fixed — dizgi kapisinin Major sayaci dokuz turun sekizinde yanilmisti

- `phase_gate.py`, raporda acik bir `Major issues: N` satiri yoksa
  `## MAJOR ISSUES` bolumundeki maddeleri sayiyordu; kalip yalnizca `^\d+\.`
  idi. Hakem madde numarasini kalinlastirdiginda (`**1. ...`) ya da baslik
  yaptiginda (`### 1. ...`) satir rakamla baslamaz, madde GORUNMEZ olur ve
  sayac **sifir** doner. Kitin kendi ornek derlemesinin dokuz ardisik hakem
  raporu eski sayactan gecirildi: **sekizinde yanlis**. Dordu tehlikeli yonde
  — 4, 3, 2 ve 2 cozulmemis Major tasiyan raporlar kapiya temiz gorundu.
- Ters yon de olculdu: hukmunu "yok" verip *neyi arayip bulamadigini*
  numaralayan bir rapor **8 Major** okundu. Kusur boylece iyi yazilmis raporu
  cezalandiriyor, kotu bicimlendirilmis olani odullendiriyordu.
- Fazla sayma gurultuludur ve kendini duyurur; eksik sayma sessizdir — sifir
  donen bir kapi ile gecen bir kapi ayirt edilemez. Kalip artik uc
  numaralandirma bicimini de taniyor, ve dolu bir bolumden hic madde
  cikaramadiginda sifir TAHMIN ETMIYOR: bilinmiyor deyip kapiyi kapatiyor.
  Yeni sayac ayni dokuz turun sekizinde dogru.
- Kalan tek hata bilerek birakildi: tek bir Major'in "ne duzeltir" listesi
  sutun-0'da numaralandiginda bes ayri kalem gibi sayiliyor. Hicbir kalip
  "sorun maddesi" ile "cozum adimi"ni bicimden ayiramaz — ve bu, sayimin
  onarilacak degil TERK EDILECEK bir yontem oldugunun kanitidir. Yonu bloke
  edendir, dolayisiyla guvenlidir; bir test kabulun kendisini kayda geciriyor
  ki sonraki bir okur onu tehlikeli yone "duzeltmesin". 6 test. [2026-08-23]

### Changed — Major sayisi tahmin edilecek bir sey degil, yazilacak bir sey

- `/critique` artik `## MAJOR ISSUES` bolumunun ILK satirina `Major issues: N`
  yazmakla yukumlu (`Major issues: 0` dahil), ve `reviewer-critic` bunu kendi
  cikti sozlesmesinde tasiyor. Kancanin sertlestirilmesi bir sezgiselin
  onarimidir; asil cozum sayinin yazilmasidir.
- SKILL.md'nin gerekce notu olculmus tabloyla birlikte duruyor, cunku bu
  kusurun ilk teshisi ("sayac yalnizca fazla sayar, yani guvenli yonde
  yanilir") olculmeden yazilmisti ve olculdugunde yanlis cikti. [2026-08-23]

### Added — prisma_flow: sema, elyazmasinin dilini konusur

- `--labels`: akis semasinin kutu etiketleri bir JSON dosyasindan okunur.
  PRISMA'nin kendi semasi Ingilizcedir ve baska bir dilde yazilmis bir derleme,
  kendi dilindeki dislama gerekcelerinin etrafina Ingilizce kutu adlari
  basiyordu — kitin ornek elyazmasi "Records identified" basliginin altinda
  "indeks test derin ogrenme degil" yaziyordu. Sekil elyazmasinin parcasidir.
- Varsayilan Ingilizcedir ve kismi bir dosya gecerlidir: adlandirilmayan
  anahtarlar Ingilizce kalir. BILINMEYEN BIR ANAHTAR HATA VERIR — bir yazim
  hatasi sessizce Ingilizce varsayilani birakir, ve bayragin butun amaci okurun
  tek bir kacak etikete rastlamamasidir.
- `--verify` de ayni etiketlerle yeniden uretir; yoksa yerellestirilmis her
  proje "bayat" okunurdu. 5 test. [2026-08-22]

### Fixed — failure_scan: M3 hicbir sayi hakkinda yanilmiyordu, yanilabilme yetisini kaybetmisti

- `backed()` bir artefakt sayisinin prose degeriyle BASLAMASINI kabul eder,
  cunku 0,8712 tutan bir tablo metinde mesru olarak "0,87" olur. Kural bir avuc
  artefakt icin saglam, binlercesi icin bostur: kitin kendi ornek derlemesinin
  havuzu 19.513 sayi tasiyor ve iki ondalikli degerlerin YUZDE YUZUNU
  "destekliyor". M3, hicbir betigin uretmedigi bir korelasyon, iki ortanca ve
  iki p degeri tasiyan bir Tartisma paragrafina CLEAR verdi.
- `backing_saturation()` bunu olcer: havuzun, siradan iki ondalikli degerlerin
  ne kadarini destekledigini. Esigin (%50) ustundeyse M3 ve M6'nin statusu
  CLEAR yerine INSUFFICIENT EVIDENCE olur — kritik beceri referansinin kendi
  ucuncu yargisi, ve o yargi acikca bir gecis DEGILDIR. Doygun bir havuz bir
  CLEAR'i dusurur, bir FLAGGED'i asla.
- Bu gerilemeyi sinamak yeni bir dogrulama kanali gerektirdi: hicbir bulgu
  eklenmez ya da kaldirilmaz, BOS BIR BULGU LISTESININ ANLAMI degisir.
  `run_evals.py` artik `expect_status` (mod -> beklenen statu) destekliyor ve
  entrypoint'ler istege bagli olarak (findings, meta) donebiliyor. 6 test,
  5 altin vaka, 1 mutasyon. Ayrica onceden hayatta kalan
  `m1-citation-exemption-removed` mutasyonu icin ikinci bir negatif vaka:
  failure_modes'un alti mutasyonunun altisi da yakalaniyor. [2026-08-22]

### Added — prisma_flow: basilan sema, sayaclarin urettigi sema mi?

- `--verify` yeni: hicbir sey yazmaz, sayaclardan yeniden uretir ve DISKTEKI
  `prisma.tex` / `prisma.mmd` dosyalarinin sayilarini onunla karsilastirir.
  `check()` "sayaclar tutuyor mu" sorusunu yanitliyordu; bu "dizgicinin
  okudugu dosya bu sayaclarin urettigi dosya mi" sorusunu yanitlar. Ikisi, bir
  sema bir dizinden otekine kopyalandigi anda ayrisir — ve kitin kendi ornek
  elyazmasinda ayrismisti: bir derleme adimi terk edilmis bir akisi
  (170/4/166/19/147/36/111/11/100) dogru uretilmis semanin uzerine yaziyordu,
  her sayac ozdesligi tutuyordu ve hicbir kapi ateslenmedi. Eksik artefakt
  "uyusmazlik bulunamadi" diye okunmaz, ayrica bildirilir.
- `--counts-file` yeni: sayac nesnesini UTF-8 bir dosyadan okur ve ust duzey
  bir `counts` anahtarini acar. Sebebi olculmustur: ayni nesne argv uzerinden
  gecirildiginde Turkce gerekce dizesi konsol kod sayfasinda bozuldu
  ("tasimayan" -> "tapymayan") ve bozuk dize hicbir hata uretmeden semaya
  dizildi. 7 test. [2026-08-22]

### Fixed — phase_gate: `sed -n` ile OKUMAK yazma sayiliyordu

- `_shell_write_sink`'in yerinde-duzenleme kalibi (`-[A-Za-z]*i`) bir jeton
  basina BAGLI DEGILDI, dolayisiyla tirenin YOL ICINDE gectigi her yerde
  esliyordu: `sed -n '34p' drafts/ek-e-cihaz-eslemesi.md` `-ci` uzerinden
  eslesti. `src/api-client.ts`, `notes/pre-training.md`, `docs/multi-arm.md` ayni
  sinifta. Hepsi duz OKUMA; faz kapisi hepsini kapali bir dizine yazma
  girisimi diye reddediyordu — kitin kendi elyazmasinda bes ek dosyasindan
  dordu. Bayrak artik bir jeton baslatmak zorunda. `sed -i`, `sed -i.bak`,
  `sed -ni`, `perl -pi -e`, `gawk -i inplace` aynen yakalaniyor.
  [2026-08-21]

### Fixed — phase_gate: `python - <<'PY'` faz kapisini tamamen atliyordu

- `strip_heredocs` her heredoc GOVDESINI atiyordu, cunku bir gövde VERIdir:
  `cat <<'EOF' > file` icinde gecen bir yonlendirme gercek bir cagri degildir.
  Ama gövde bir YORUMLAYICININ girdisiyse gövde veri degil PROGRAMDIR, ve o
  program dosya yaziyorsa yazdigi hicbir yerde gorunmuyordu. `python - <<'PY'`
  ile `drafts/methods.md` yazmak sifir hedef bildiriyor ve kapidan geciyordu;
  ayni islemin `python -c "..."` yazimi dogru sekilde reddediliyordu. Modulun
  kendi belgesi zaten "python tek satirlari da kapili" diyordu — heredoc
  yazimi degildi. Istisna dar: gövde yalniz stdin'den program okuyan bir
  yorumlayiciya (`python -`, `bash -s`, `cat <<PY | python`) gidiyorsa
  taranir; `python script.py <<EOF` eskisi gibi atilir, orada gövde gercekten
  veridir. 13 test + 2 mutasyon. [2026-08-21]

### Fixed — consistency_check: bir DERLEMEDE "records" akisin sozcugudur

- `n_samples` kalibi `records?` tasiyordu ve iki kollu bir derleme ayni dosyada
  iki dogru cumle kurar: bir kol 1.572 kayit tanimlar, defter otekinden 68
  kayit tutar. Surukleme denetimi ikisini TEK bir nicelik okuyup elyazmasini
  iki dogru seyi soyledigi icin tutarsiz ilan ediyordu. Akisin kendisi
  denetleniyorsa (defter ya da sayac dosyasi cozuldu, baglantilar asama asama
  karsilastirildi) o sozcugun sahibi bellidir ve `n_samples` onu birakir;
  denetlenecek akis yoksa sozcuk yine ornek buyuklugu demektir. [2026-08-21]
- Uyusmazlik mesaji da artik gercekten karsilastirdigi kaynagi adlandiriyor.
  `--prisma-counts` kullanildiginda bile "the register-derived flow" diyordu —
  o bayragin var olma sebebi ise defterin bazen akis OLMAMASIDIR. 4 test +
  2 mutasyon. [2026-08-21]

### Fixed — claim_check: beyanlar bolumu tanim geregi kendi isidir

- Fon, cikar catismasi, CRediT, veri erisilebilirligi, kayit — PRISMA 2020
  md. 25-27 ve dergilerin "Statements and Declarations" blogu. Her cumlesi BU
  elyazmasi HAKKINDA bir beyandir: neyin fonlandigi, neyin yatirildigi,
  kurallarin ne zaman yazildigi. Atacak kaynak yoktur cunku kaynak yazarin
  kendisidir — ve gercek bir tanesi, kendi PRISMA sayaclarinin neden kayit
  defterinden turemedigini acikladigi icin "atifsiz ampirik iddia" olarak
  raporlandi. Yontem ve ekler zaten ayni listedeydi. 5 test + 1 mutasyon.
  [2026-08-21]

### Fixed — tr_style_check: uc yeni yanlis pozitif sinifi

- **Urun surumu ondalik degildir.** Arac degerlendiren bir derleme surum
  numarasi ile doludur: "IDx-DR 2.0", "EyeArt system v2.0", "RetCAD v.2.2.0".
  Her biri, hangi ayracin egemen oldugunu belirleyen sayimin NOKTA tarafina
  yaziliyordu; elyazmasi bunu duzeltemezdi de, cunku o dizeler kaynaktan
  birebir alintidir ve bir urun adini "2,0" yapmak daha kotu olurdu. Iki kalip:
  `v`/`v.`/`ver.` isaretcisi, ya da onunde bir MODEL ADI (0'inci konumdan sonra
  buyuk harf) ve surum bicimli bir sayi. Ikincisi bilerek IGNORECASE DEGIL —
  oyle olunca "buyuk harf" sinifi kucugu de esliyor ve kalip her ondalik
  sayiyi yutuyor. [2026-08-21]
- **Uretilmis dosya yazarin uslubu degildir.** Banner tasiyan bir tablo
  hucrelerinde kaynagin Ingilizce dizelerini tasir; bunlar Turkce govde
  hakkindaki kulliyat capinda bir oylamanin azinlik tarafina yaziliyordu ve
  uyari YAPISI GEREGI uygulanamazdi: "duzeltilecek" tek yer, banner'in elle
  duzenlemeyi yasakladigi dosyadir. Bir lint, okuyucusunun degistirebilecegi
  metni gostermelidir. Banner bir HTML yorumudur ve `strip_noise` yorumlari her
  denetimden ONCE siler — bu yuzden tespit islenmis metni degil DOSYAYI okur;
  ilk surumu hicbir dosyada banner bulamiyor ve sessizce hicbir seyi
  dislamiyordu, ham dize uzerindeki birim testleri ise geciyordu. [2026-08-21]
- **"hâliyle" ve "malum" yalniz SOYLEM BELIRTECI olarak gayriresmidir.** "ham
  hâliyle" = "ham durumuyla" ve bu duzgun akademik Turkcedir; Turkce ona baska
  bir yazim vermez. Belirtec anlami bir tumce sinirinda durur, ad anlami
  onundeki niteleyiciyle gelir — sinir sinavi ikisini bir cozumleyici olmadan
  ayirir. [2026-08-21]
- 9 test + 3 mutasyon + 6 gold vaka (uçu negatif, uçu esli pozitif: her
  muafiyetin denetimin kendisini silahsizlandirmadigini sinayan). [2026-08-21]

### Changed — gold set ve yayimlanan sayilar

- Gold set: 234 -> **240 vaka** (111 pozitif / 129 negatif), 63 -> **66
  mutasyon**; hepsi yakalaniyor. `tr_style` 34 -> 40 vaka, 10 -> 13 mutasyon.
  `english-abstract-exemption-removed` mutasyonunun capasi kodla birlikte
  guncellendi — harness "kod tasindi, bu mutasyon artik hicbir seyi sinamiyor"
  diyerek kendi capasinin bayatladigini bildirdi. eval/MEASUREMENT.md
  guncellendi. [2026-08-21]
- Yayimlanan test sayisi 2254 -> **2292**; docs/ yeniden derlendi. [2026-08-21]


- Gold set: 229 -> **234 vaka** (108 pozitif / 126 negatif), 61 -> **63
  mutasyon**; hepsi yakalaniyor. `failure_modes` 30 -> 35 vaka, 3 -> 5 mutasyon.
  eval/MEASUREMENT.md guncellendi. [2026-08-21]
- Yayimlanan test sayisi 2235 -> **2247**; docs/ yeniden derlendi. [2026-08-21]
- Gold set: 226 -> **229 vaka** (106 pozitif / 123 negatif), 59 -> **61
  mutasyon**; hepsi yakalaniyor, hicbiri hayatta kalmiyor. `temporal` 14 -> 17
  vaka, 3 -> 5 mutasyon. eval/MEASUREMENT.md guncellendi. [2026-08-21]
- Yayimlanan test sayisi 2204 -> **2235**; docs/ yeniden derlendi. [2026-08-21]
- Gold set bu turlarda 210 -> **226 vaka** (105 pozitif / 121 negatif) ve
  54 -> **59 mutasyon**; hepsi yakalaniyor, hicbiri hayatta kalmiyor. Ara
  adimlar: `tr_style` 25 -> 34 vaka ve 7 -> 10 mutasyon (DOI oneki, Ingilizce
  Abstract, katlama carpismasi, kaydirilmis anahtar sozcuk listesi),
  `claim_strength` 71 -> 75 vaka ve 10 -> 11 mutasyon (romen rakamli bolum
  gondermesi), `consistency` 14 -> 17 vaka ve 5 -> 6 mutasyon (binlik ayraci).
  eval/MEASUREMENT.md tablosu, toplam satiri ve set-basi araligi guncellendi.
  [2026-08-21]
- Yayimlanan test sayisi 2157 -> **2204** (README.md, README.en.md,
  CONTRIBUTING.md, web/src/data/site.ts; docs/ her seferinde yeniden
  derlendi). Sayiyi her defasinda
  `test_published_test_count_matches_the_suite` yakaladi, ben degil.
  [2026-08-21]
### Fixed — failure_scan da BINLIK AYRACINI ondalik saniyordu

- Ucuncu betikte ayni sinif. `_norm`, "1.572" ve "1,572"yi ondalik okuyordu ve
  bunun IKI sonucu vardi: sayi, kodun kendi "tam sayilar sayim ve yildir,
  olcum degildir" atlamasini gecip bir OLCUM sayiliyor; ve uretildigi
  artefaktla (`1572` tutan bir JSON) eslesemiyordu. Kitin kendi ornek
  derlemesinde bu, PRISMA tanimlama sayisini **uc bolumde birden** "arkasinda
  artefakt olmayan kendi sonucu" diye raporladi — oysa artefakt
  `analysis/data/prisma-counts.json` icinde tam olarak o sayiyi tutuyordu.
  [2026-08-21]
- Ayrica atlama kararinin HAM belirtec yerine NORMALLESTIRILMIS bicim uzerinde
  verilmesi gerekiyordu: "1.572" nokta tasir ama tam sayidir, ve bir sayim bir
  olcum degildir. 13 test + 1 mutasyon + 3 gold vaka (ikisi negatif, biri
  pozitif — gercek bir desteksiz olcumun hala yakalandigini sinayan).
  [2026-08-21]

### Fixed — failure_scan M1: atif tasiyan bir metrik LITERATUR sayisidir

- M1, "tam olarak 1,0" bildiren her cumleyi bir sabit sizintisi adayi sayiyordu.
  Bir DERLEMENIN isi ise tam da bunu iceriyor: baskasinin yayimladigi
  inandirici olmayan bir 1,0'i RAPORLAMAK. Kitin ornek derlemesi iki boyle
  calismayi adiyla aniyor ve sizintiyi bir sonraki cumlecikte teshis ediyor —
  ve bunu yaptigi icin isaretlendi. `scan_m3` ayni muafiyeti ("bir literatur
  sayisi") ZATEN yapiyordu; M1 artik ayni kurali uyguluyor. Kendi sonuclar atif
  anahtari tasimadigi icin asimetri guvenlidir. 2 test + 1 mutasyon + 2 gold
  vaka. [2026-08-21]

### Notes — ayni kusur sinifi UC betikte birden cikti

- Binlik ayraci korlugu bu turlarda `consistency_check`, `tr_style_check`
  (DOI oneki) ve `failure_scan`'de ayri ayri bulundu. Ucu de sayiyi kendi
  basina ayristiriyor ve ucu de ayni varsayimi yapiyordu. Bunun kaydi burada
  duruyor cunku dorduncu bir betik ayni seyi yapiyorsa, onu bulmanin yolu
  "sayiyi kim ayristiriyor" diye sormaktir. [2026-08-21]

### Fixed — citation_triangulate: ayni yazari iki turlu indeksleyen kaynaklar

- Ilk-yazar karsilastirmasi, OpenAlex'in gorunen adindaki SON BOSLUK BELIRTECINI
  yerel BibTeX yazar alanindaki virgul-oncesi TAM BILESIGE karsi ariyordu. Gercek
  bir 121 kunyelik kaynakcada bu **12 uyusmazlik** uretti ve hicbiri yanlis bir
  makaleye isaret etmiyordu: parcacikli soyadlar (`van der Heijden` vs `Heijden`),
  bilesikler (`Abreu-González` vs `González`, `dos Reis` vs `Reis`), OpenAlex'in
  servis ettigi U+2010 tire (`Baget‐Bernaldiz`), diyakritik farki (`Özçelik` vs
  `Ozcelik`), ve bir aile-adi-once Cince gorunen ad (`Lu Li`, ki orada son
  belirtec SOYADI DEGIL). **%9 gurultu orani olan bir dogrulama kapisi,
  okunmayan bir kapidir.** [2026-08-21]
- Artik iki taraf da normallestirilmis BELIRTEC KUMESI olarak karsilastiriliyor:
  NFKD + birlestirici isaret soyma, her Unicode tire cesidinin ASCII'ye
  esitlenmesi, harf-disi her seyden bolme (BibTeX'in "Soyad, Ad" virgulu dahil),
  ve tek harflik belirteclerin atilmasi — bir harf bir ad degil, bir bas
  harftir. Turkce noktasiz `ı` ile `ğ` NFKD ile ayrismadigi icin ayrica
  esleniyor. [2026-08-21]
- **`doi2bib._local_family_names` BILEREK DEGISTIRILMEDI.** Orada ayni
  karsilastirma, yanlis bir DOI baglanmasini guvenli bir ustveri duzeltmesinden
  ayiran telafi denetimidir; gevsetmek uydurma bir atifi "FIX" diye geciririrdi.
  Burada denetim WARN-only ve zaten yetkili bir Crossref dogrulamasinin
  ARKASINDA duruyor, dolayisiyla kacirilan bir durtmenin bedeli kucuk, gurultunun
  bedeli buyuktur. Iki farkli esik, iki farkli gerekce. [2026-08-21]
- 12 test + 2 mutasyon. **Ilk yazdigim testlerin ikisi de mutasyonlari
  KACIRDI** ve ikisi de ayni sebepten: yardimciyi dogrudan cagiriyor, KANCALANDIGINI
  sinamiyorlardi. Uctan uca bir test eklendi ve yerel taraf `van der Heijden`
  bicimine cevrildi — cunku zaten cıplak bir soyadla yazilmis bir vaka eski
  karsilastirmayi da geciyordu. [2026-08-21]

### Fixed — temporal_check: dort haneli bir sayi ancak BAGLAMI soyluyorsa yildir

- Dosyanin basindaki "21xx bir yil degildir" istisnasi, genel bir sinifin tek bir
  ornegi icin yazilmis bir aralik hilesiydi. Iki baglam "bu bir yil degil" der ve
  ikisi de kitin hedefledigi yazinda surekli gecer:
  (1) **Nicelik ve tensor boyutu.** "2048 features" ResNet-50'nin Global Average
  Pooling genisligidir — 20xx araliginda kalan TEK ikinin kuvveti ve bilgisayarli
  gorude en yaygin oznitelik boyutu. Bir DL derlemesi onunla neredeyse her
  cikarim kartinda karsilasir. "2016 images", "1998 patients" ayni sinif.
  (2) **Yazar-yil atfi.** Bir kart mesru olarak BASKA bir calismayi anabilir;
  2021 kaynakli bir kartin icindeki "Polater & Isik 2024" bir capraz gondermedir,
  o makalenin 2024 hakkinda bir iddiasi degil. [2026-08-21]
- **Ilk yazdigim yazar-yil muafiyeti FAZLA GENISTI ve SHIPPED BIR GOLD VAKAYI
  BOZDU.** "The 2022 recalibration protocol" cumlesinde "The" buyuk harfli oldugu
  icin soyadi sanildi ve gercek bir anakronizm bastirildi. Gold set bunu ayni
  kosuda yakaladi. Bir islev-sozcugu blok listesi eklendi: gercek pozitifleri
  yutan bir muafiyet, kaldirdigi yanlis pozitifle ayni kusurdur, ters yonden.
  [2026-08-21]
- 14 test + 2 mutasyon. Ilk mutasyon (`_is_a_year_here` cagrisinin kaldirilmasi)
  yine KACIRILDI cunku testler yalnizca yardimciyi cagiriyordu; uctan uca bir
  kart testi eklendi. Hicbir seyin cagirmadigi bir yardimci bir duzeltme
  degildir. [2026-08-21]

### Notes — FWD: geri cekilme tespiti icin bir betik yok

- `write_verify_status.py` bir `--retracted` alani ister ve citation-verifier
  ajaninin tanimi geri cekilmis makaleleri saptadigini soyler, ama KITTE bunu
  yapan bir betik yoktur — `bib_doctor --retract` kaldirma yoludur, tespit
  degil. Deterministik yolu izleyen (ajan cagirmayan) bir kullanici o alani
  arkasinda hicbir denetim olmadan doldurabilir. Ornek kosuda alan elle
  yazilmadi, Crossref'in `update-to`/`updated-by` iliskileri 121 DOI icin
  gercekten sorgulandi (0 geri cekilme), ama bu bir betigin yerini tutmaz.
  Kapatilmasi gereken bir bosluk olarak isaretlendi. [2026-08-21]

### Fixed — consistency_check BINLIK AYRACINI hic tanimiyordu

- `_NUM` gruplanmis binlikleri kapsamiyordu, dolayisiyla desen gruplanmis bir
  sayinin YALNIZCA SON GRUBUNU esliyordu: `1,572 records` -> **572**,
  `12,345 records` -> **345**, ve en kotusu, bu denetimin ilk dili Turkce oldugu
  halde, `1.572 kayit` -> **ondalik 1.572**. Bu bir yanlis uyari degil, YANLIS
  SAYIDIR: bir manifesto karsilastirmasi hic yazilmamis bir degere karsi kosar,
  ya da yanlis bir sayiyla sessizce anlasir. Bir metnin bir sayiyi iki turlu
  soyledigini yakalamak icin var olan bir denetim, sayinin kendisini yanlis
  okuyamaz. [2026-08-21]
- Her iki konvansiyon da destekleniyor (`1,572` ve `1.572`), ondalik kuyruklariyla
  birlikte (`12,345.67` ve `12.345,67`). Ayirt etme kurali `tr_style_check`'in
  ayni sekil icin zaten kullandigi kuraldir: **UCLU gruplar halinde tekrarlayan
  ayrac binlik ayracidir**, digeri ondalik. Bas grubun 1-9 ile baslamasi `0.809`u
  ondalik tutar; `1.5`in uc haneli grubu olmadigi icin o da ondalik kalir.
  11 test (7'si parametreli) + 3 gold vaka + 1 mutasyon. [2026-08-21]

### Fixed — tr_style_check: Ingilizce Abstract Turkce yazim kuraliyla yargilaniyordu

- Bir Turkce makalenin Ingilizce Abstract'i neredeyse her Turkce dergi ve YOK tez
  yonergesi tarafindan ZORUNLU tutulur ve INGILIZCE yazimla yazilir: ondalik
  nokta, yuzde isareti sayidan SONRA. Turkce kurala gore denetlenmesi dogru isi
  yanlis diye raporluyordu — ve daha kotusu: `decimal_separator` ile `term_unity`
  BASKIN BICIMI belirleyen kulliyat capinda sayimlardir, yani Ingilizce ozetin
  sayilari ve terimleri, TURKCE GOVDE hakkindaki bir oylamada azinlik tarafina
  yaziliyordu. Bu kosuda dogru bir Turkce govde + dogru bir Ingilizce ozet, "iki
  ondalik ayrac birden kullanilmis" ve bes yuzde-yerlesimi hatasi olarak
  raporlandi; besinin besi de dogru Ingilizceydi. `ozet_abstract` istisnadir ve
  tam listeyi okumaya devam eder — ikisini karsilastirmak onun butun isi.
  6 test + 4 gold vaka + 1 mutasyon; Ozet'in Turkce kalmasi ayrica sinandi.
  [2026-08-21]

### Fixed — tr_style_check: EKLI bir Turkce sozcuk Ingilizce terime KATLANIYORDU

- `term_unity` hem Turkce hem Ingilizce degiskenleri KATLANMIS kulliyata karsi
  esliyordu. Katlama Turkce diyakritiklerini soyar; eklemeli bir dilde bu, dogru
  cekimlenmis bir Turkce sozcugu bir Ingilizce terime birebir esitleyebilir:
  **"literatüre" (yonelme hali) katlaninca tam olarak "literature" olur.** Hicbir
  Ingilizce sozcuk yazmamis bir metne "Ingilizce adi iki kez kullandin"
  deniyordu. Ingilizce degiskenler artik KATLANMAMIS metne karsi esleniyor —
  Ingilizce'nin Turkce diyakritigi yok, dolayisiyla katlamadan bir sey
  kaybetmiyor. Carpisma sinifi sistematikti: Ingilizce bicimi, ekli bir Turkce
  bicimden yalnizca diyakritikle ayrilan her sozluk kaydi. 2 test + 1 mutasyon.
  [2026-08-21]

### Fixed — tr_style_check: kaydirilmis anahtar sozcuk listesi kesiliyordu

- `_keywords` yalnizca eslesen SATIRI okuyordu, oysa markdown'da kaydirilmis bir
  anahtar sozcuk listesi olagandir. Ayni alti terimi tasiyan iki liste, farkli
  yerlerde kaydiklari icin **3'e karsi 4** diye raporlandi — var olmayan bir
  uyusmazlik; ve ayni kusur, kaydirmanin otesinde saklanan GERCEK bir
  uyusmazliktan da haberdar olmazdi. Devam satirlari bos satirda ya da yeni bir
  blok baslangicinda (baslik, kalin etiket, liste ogesi, alinti) durur.
  6 test + 2 gold vaka + 1 mutasyon; gercek bir sayi uyusmazliginin hala
  yakalandigi ayrica sinandi. [2026-08-21]

### Fixed — claim_check: ROMEN RAKAMLI bolum capraz-gondermesini gormuyordu

- `ARTEFACT_RE`, kendi metnine yapilan gondermeyi own-work isareti sayar ama
  yalnizca "Section 3" / "Bolum 3" / "Tablo 5" gibi ANAHTAR SOZCUK + ARAP
  RAKAMI bicimlerini taniyordu. Bolumlerini I./II./III./IV. diye numaralayan
  bir metin — bir Turkce tezin ya da makalenin EN SIK kullandigi duzen — bu
  yuzden hicbir calisan own-work isaretine sahip degildi: "(III.4)" hicbir
  seye uymuyordu. Sonuc, Tartisma bolumunde kendi Bulgular'ini tekrarlayan her
  cumlenin "atifsiz ampirik iddia" olarak geri gelmesiydi — tek bir dosyada
  ON YEDI tane, hicbiri gercek bir bulgu degil. Bu, bir denetimin en zararli
  basarisizlik bicimidir: gurultu, kullaniciyi denetimi gormezden gelmeye
  egitir. [2026-08-21]
- Desen dar tutuldu: **romen rakami + nokta + en az bir rakam** (III.4, IV.2,
  III.5.1, III.6a). Cumle basi "I" ya da baresel bir "V" eslesmiyor — her
  buyuk romen harfine acilan bir muafiyet Ingilizce nesrin cogunu sessizce
  muaf tutardi ve bu, duzeltilen hatanin aynisi olurdu. Ingilizce ve Turkce
  metinde ayni sekilde calisiyor. [2026-08-21]
- 9 birim testi (5'i parametreli negatif, 3'u parametreli pozitif) + 4 gold
  vaka + 1 mutasyon. Iki mutasyon da yakalaniyor: klozu kaldirmak da, her
  romen harfine acmak da. [2026-08-21]

### Fixed — tr_style_check: DOI onekini ondalik sayi sanmasi

- `check_decimal_separator`, bir DOI'nin kayitci onekini (`10.17780/...`)
  ondalik nokta sayiyordu. Zarar kozmetik degil: bu sayim, virgul mu nokta mi
  BASKIN oldugunu belirleyen oydur, dolayisiyla cok sayida DOI anan bir
  derleme — ki bir sistematik derleme tanimi geregi oyledir — tutarli bicimde
  virgul kullandigi halde "karisik" diye raporlanabilir ve yanlis baskin form
  bildirilebilirdi. Zaten var olan binlik-ayraci atlamasiyla ayni bicimde,
  DOI aciklikları da atlaniyor. [2026-08-21]
- Atlamanin fazla genis olmamasi ayrica sinandi: DOI'nin YANINDAKI gercek bir
  kacak nokta hala yakalaniyor — bir muafiyetin sessizce butun satiri
  susturmasi, duzeltilen hatanin aynisi olurdu. 3 birim testi + 3 gold vaka
  (ikisi negatif, biri pozitif) + 1 mutasyon. [2026-08-21]

### Added — doi2bib: kanonik olmayan kaynakcaya yazarken uyari

- `doi2bib.py --append`, hedef `bib/references.bib` DEGILSE artik ciktisinda
  `off_canon_bib` uyarisi tasiyor. Sebep gercek bir vakadir: bir projede
  `--append references.bib` (kok dizin) calistirilmis, 93 yetkili kayit
  kitteki hicbir okuyucunun acmadigi bir dosyaya inmisti. cite_audit,
  bib_doctor, citation_triangulate, evidence_funnel, run_evals ve iki derleme
  betiginin hepsi `bib/references.bib` varsayar; sonuc, 121 kaynak anan bir
  makalenin 28 kaynakla derlenmesi ve ayni atiflarin cite_audit tarafindan
  "eksik" diye raporlanmasiydi — tek sebep, birbiriyle ilgisiz gorunen iki
  belirti. **Engel degil uyaridir:** bolum basina ayri bir .bib ya da bir
  replication-pack kopyasi mesru hedeflerdir. Hata, basarinin sessiz
  olmasiydi. [2026-08-21]
- Kanonik duzeni kullanmayan bir proje uyarilmaz (`bib/` yoksa susar) ve ayni
  dosyanin farkli yazilislari (mutlak yol, `..` iceren yol) `resolve()` ile
  karsilastirildigi icin yanlis uyari vermez. 8 test, 3 mutasyonun ucu de
  yakalaniyor — bunlardan biri ILK yazdigim testin yakalayamadigi mutasyondu:
  `Path("./bib/references.bib")` zaten yapicida sadelesiyor, dolayisiyla o
  yazilis duz metin karsilastirmasini da geciyordu ve `resolve()`'u hic
  sinamiyordu. Test, sadelesmeyen iki yazilisla degistirildi. [2026-08-21]

### Changed — yayimlanan test sayisi

- 2390 -> **2391** (README.md, README.en.md, CONTRIBUTING.md, web/src/data/site.ts,
  docs/ yeniden derlendi). CHANGELOG yol kontrolu eklenince. [2026-08-25]
- 2379 -> **2390** (README.md, README.en.md, CONTRIBUTING.md, web/src/data/site.ts,
  docs/ yeniden derlendi). Ucuncu vitrinin on bir butunluk testi eklenince.
  [2026-08-24]
- 2157 -> **2166** (README.md, README.en.md, CONTRIBUTING.md, web/src/data/site.ts,
  docs/ yeniden derlendi). Sayiyi ben degil, `test_published_test_count_matches_the_suite`
  yakaladi. [2026-08-21]

### Added — the coverage question, asked in the other direction

- **`evidence_funnel.py` now reports extraction records the register never heard
  of.** The forward check added earlier this session catches an included study
  that reached no analysis; this is its mirror, and it caught a real one on the
  first run. A study had been retrieved, read, judged eligible, extracted, and
  deliberately kept out of the pooled estimate for a recorded reason — while its
  registration never ran. It was counted in no PRISMA box at all, neither
  included nor excluded at full text, and the flow printed one fewer included
  study than the review had actually assessed. The eligibility reading said 97,
  the registration log held 96, and nothing compared the two directories, so
  nothing said so. `orphan_extractions` does. Matching is by every identifier a
  project might use — filename stem, or an id/doi/pmid/bib_key field inside the
  record — because the kit does not own that directory's naming. Two gold cases
  (one negative: a DOI-named record that IS registered) and a mutation.
  [2026-08-21]

### Fixed — a claim that outlived the set it was true for, and a changelog that was two changelogs

- **`eval/ROUTING-EVAL.md` asserted routing accuracy it had never measured.**
  The page said "Every prompt in the shipped set has now been scored live" on the
  strength of run 5, which scored 48 prompts over 28 skills. The set then grew
  through 50/29, 54/31, 56/32 and 65/39 to 95/54 and the sentence did not move:
  47 prompts and 26 skills — the whole grant, ethics, DMP, referee, dossier,
  teaching and empirical-chain half of the catalog — had never faced a router
  while the document said they had. What makes it worth recording is that the
  page had *already* built a gate against this exact drift, and the gate held:
  `--require-full-coverage` and a test wired to the "N prompts / M skills" line
  kept that line derived and correct at 95/54 throughout. A gate on the
  denominator does not gate the sentence that uses it. Run 6 has now scored the
  complete set blind — 95/95, six prompts at `medium` confidence and all six
  correct — and `tests/test_routing_eval_currency.py` parses the "Live-scored: N
  of M" line, requires M to equal the shipped set, and refuses full-coverage
  wording while N is below M. Blockquotes are exempt so the page can quote the
  retired sentence without the check firing on its own history. [2026-08-21]
- **The kit's CHANGELOG was carrying a research project's log.** Six sections of
  `[Unreleased]` recorded a manuscript getting 13% shorter, PRISMA box counts,
  and eight scripts under `runs/dr-tarama/analysis/` — a path `.gitignore`
  excludes, so a clone read release notes for files it could not contain. The
  line is not "no project may be mentioned": `consistency_check.py` gained its
  table-totals check because one manuscript's table summed to 67 while its prose
  said 68, and that sentence belongs here. The line is the SUBJECT — if the thing
  that changed is not in this repository, its record is not in this repository's
  changelog. Those sections now live in `runs/dr-tarama/CHANGELOG.md`, and
  `tests/test_changelog_scope.py` rejects any entry naming a path under `runs/`
  or a `.py`/`.sh` file `scripts/` does not ship. [2026-08-21]
- **Two entries were recorded twice, at two lengths.** The `replication_pack.py`
  read-only-bit fix and the secondary-review deposit addition each appeared in
  two sections four apart, because a section restated from memory does not read
  as a duplicate to the person restating it. Merged into the fuller version; the
  same test fails on a repeated descriptive `###` heading within one release.
  [2026-08-21]
- **`eval/MEASUREMENT.md`'s per-set range was hand-typed.** The case total and
  the negative/positive split were already bound to the harness; "across nine
  checkers — 10 to 71 per set" beside them was not, and neither half moves when
  a tenth gold set lands. Now derived, lower bound included — that is the
  load-bearing number, since the paragraph exists to say the sets are small.
  [2026-08-21]

### Notes — what the new table-totals check caught, and what no check can

- **The table-totals check earned its place within a day.** Added to fix a
  disposition table that summed to 67 while its prose said 68, it immediately
  caught a *different* error in the repaired table: a subset row ("of these, 24
  abstracts were read") that is not an addend, silently inflating two column
  totals. That row is now prose, and the table contains only rows that sum. [2026-08-17]
- **The error the same round's reviewer found was NOT catchable by a checker,
  and this is worth recording.** The PRISMA flow had been re-derived with 14
  never-retrieved reports counted as "assessed for eligibility" — the exact
  distortion the manuscript's own Methods section forbids in writing.
  `prisma_flow.py` already validates all four flow identities and they held
  before and after: the flow was arithmetically perfect and semantically wrong,
  because the records were misclassified in the register itself. Catching it
  would require the checker to know which records had a full text in hand, which
  the register does not encode and which no amount of arithmetic recovers. A
  heuristic on the Turkish reason text was considered and rejected: a lint that
  fires on correct prose is a lint nobody reads, and this file's own
  `check_prisma_narration` docstring records why that lesson was learned the
  hard way. This class of defect is caught by a reader, not a guard. [2026-08-17]

### Fixed — a table that nothing checked

- **`consistency_check.py` now checks a table against itself.** Rows and columns
  labelled "Toplam"/"Total" must actually sum. The reference manuscript's
  disposition table summed to 67 while its own prose said 68, in a table whose
  caption claimed the numbers were register-derived rather than typed — and five
  rounds of review missed it, because every numeric guard in the kit checked
  prose against data and none checked a table against itself. Cells holding
  ranges, percentages or QUADAS marks are skipped rather than guessed at. [2026-08-17]

### Fixed — the replication package could be built exactly once

- **`replication_pack.py` copied protected registers with their read-only bits,
  then died on its own previous output.** `shutil.copy2` carries the source's
  mode, so the second `--build` hit EACCES on `references.bib` — and on Windows
  could not even delete the stale copy, since a read-only file refuses deletion.
  Destinations are now unprotected before the unlink and after the copy. [2026-08-17]
- **The package README shipped the paper's revision history as part of its
  title.** A `PROJECT.md` title line carries trailing `<!-- ... -->` notes
  explaining why the title changed; they were being pasted into the deposit's
  `# Replication package — …` heading verbatim. [2026-08-17]

### Added — a deposit package that fits a review rather than an experiment

- **`replication_pack.py` recognises secondary reviews and carries their
  registers.** For `systematic-review`, `narrative-review`, `scoping-review` and
  `theoretical`, an empty run register and no dataset are the normal state, not
  gaps — reporting them as gaps trains the reader to skip the gap list, which is
  where the review's real gaps (a missing search log, unrecorded exclusion
  reasons) would then go unread. In their place the package now carries and
  checksums `sources/registry.jsonl`, `search-log.jsonl`, `venues.jsonl`,
  `evidence/cards.jsonl`, the protocol, every search-round narrative under
  `sources/`, and the Invariant 9 authority files — globbed, not listed, so a
  later round's file is not silently dropped. The Environment and Runs sections
  are suppressed for these types instead of printing two failures a review has
  no obligation to avoid. [2026-08-17]

### Fixed — an appendix arrived as a page of uncited assertions

- **`claim_check.py`'s own-work skip list did not know about appendices.**
  Methods, Results and the abstract are on it because they are own-work by
  construction; an appendix is the same kind of document one level further out.
  A reporting-checklist appendix says which section answers which item, and an
  own-analysis appendix reports a computation the review performed — neither
  cites a source because neither has one. Two such appendices arrived as eight
  "uncited empirical assertions", which is exactly the noise the list exists to
  prevent. `ek-`, `ekler`, `appendix`, `appendices` and `supplementary` now skip
  the uncited check; overclaiming inside an appendix is still in scope. The
  first attempt anchored the whole alternation with `\b`, which silently missed
  `ek_a.md` — `\b` does not hold between an underscore and a letter. [2026-08-16]

### Added — the PRISMA flow's prose is now checked against the register that derives it

An external reader reviewing the reference manuscript found what four rounds of
peer review had not: the Methods section said *"34 could not be retrieved … 19
assessed … 12 excluded"* while the diagram, the abstract and the results all
said 35/18/11. A register correction had moved the derived flow and left the
prose behind — in a manuscript whose own Methods claims its numbers "cannot go
stale silently". Nothing in the kit compared the two.

- **`consistency_check.py` gained a PRISMA check.** Counts are derived from
  `sources/registry.jsonl` and compared with what the drafts state, by
  **binding** rather than by guessing: the author writes
  `<!-- PRISMA: not_retrieved=35 -->` beside the sentence, exactly as every
  empirical claim already binds its evidence card, and the comparison is then
  exact. A first attempt located stage phrases and compared whatever number sat
  nearest; Turkish syntax beat it — *"35'i elde edilemedi (34'ü YÖK tezi)"* puts
  the subset closest to the phrase — and it reported ten mismatches on a
  manuscript whose one real error was already fixed. A lint that fires on
  correct prose is a lint nobody reads. Stages with no binding are reported as
  `unbound` rather than passed over, so silence cannot read as agreement.
  [2026-08-16]

- **`prisma_flow.py` learned `reason_category`.** PRISMA asks for exclusion
  reasons grouped with counts; a register holds one free-text reason per record,
  and a conscientious screener writes a distinct sentence for each. The figure
  therefore listed eleven categories for eleven exclusions — a register dump.
  A record may now carry a short category alongside its full reason: the figure
  groups on the category, the register keeps the audit trail, and a record
  without one falls back to the free text so no existing diagram changes.
  [2026-08-16]

### Fixed — publishers register HTML, and it printed that way in the reference list

- **`&amp;` reached the finished bibliography.** doi.org's BibTeX is generated
  from what the publisher deposited, and publishers deposit HTML: a journal
  called *Diabetes Technology & Therapeutics* arrived as
  `Diabetes Technology &amp; Therapeutics` and nothing between the fetch and
  the printed page decoded it. Ampersands in journal names are common enough
  (*Science & Justice*, *Health & Place*, *Cell & Bioscience*) that this is a
  defect every manuscript citing such a source inherits — and one that only
  becomes visible when the PDF is finally built and read.
  `doi2bib.py` now decodes at fetch time, and `bib_doctor.py --fix` repairs
  entries fetched before it did. Decoding runs **once**, not to a fixed point:
  `&amp;amp;` is a publisher's double-encoding mistake to report, not one to
  silently repair into a value nobody deposited. The entity pattern
  deliberately does not match a bare `&`, so a correctly-decoded field is not
  re-flagged forever. [2026-08-16]

### Fixed — the PRISMA figure contradicted its own caption, then became unreadable

Building the reference manuscript to PDF for the first time put the flow diagram
in front of a reader instead of in a `.tex` file nobody opened. Three defects,
none of which any check could have caught, because each produced a *valid* file.

- **The full-text exclusion box listed reasons for every exclusion, screening
  included.** It announced `Excluded (n = 11)` and then itemised reasons
  covering 30 records. PRISMA 2020 asks for reasons at the full-text stage;
  title/abstract screening is reported as a bare count, which is exactly why the
  diagram has one reason box and not two. Reasons are now derived from
  full-text-stage exclusions only, so the list and the box's own number agree.
  [2026-08-16]

- **One 400-character exclusion reason flattened the whole diagram.**
  `registry_db.py` accepts whatever `--reason` string the screener typed, and a
  conscientious screener writes a paragraph; the TikZ node is fixed at 4.6cm
  wide, so that paragraph became a column tall enough to squeeze every other box
  into an illegible ribbon. LaTeX reported the float overrunning the page by
  ~3500pt **and emitted it anyway** — the failure arrived as a silently
  unreadable figure, not as an error. Reasons are now cut at a word boundary
  with a visible ellipsis, at most three are named, and the remainder is
  reported as `+N further reason(s), M record(s) — see register` so the
  arithmetic still closes for a reader adding up the box. [2026-08-16]

- **The box was centred on its parent, so it grew upward into its neighbours.**
  It is the only node whose height depends on free text; centred, it overlapped
  the screening-exclusion and not-retrieved boxes above it. It is now anchored
  by its top-left corner and grows downward, which holds whatever the reasons
  say. [2026-08-16]

### Fixed — claim_check graded a reporting-checklist appendix as a page of uncited claims

- **An appendix says "bu ek", not "bu derleme".** The own-work marker had
  already been widened once, because a review calls itself *bu derleme* and not
  *bu çalışma*; the same blind spot sat one layer further down. A PRISMA-style
  checklist appendix is nothing BUT self-reference about the manuscript's own
  apparatus — which row covers what, why a column is blank — so every such
  sentence was reported as an empirical assertion missing its citation.
  `bu ek` / `bu tablo` / `bu şekil` / `bu protokol` / `bu kontrol listesi` now
  count as self-reference. (The first attempt at this anchored the group with a
  trailing `\b`, which silently dropped every inflected form — *bu çalışmanın*,
  *bu ekte* — and two existing tests caught it.) [2026-08-16]

- **Markdown table rows were graded as prose.** The sentence splitter breaks on
  sentence punctuation, which no table respects: a cell that does not end in a
  period is glued to the following row, so a single flagged fragment could span
  two unrelated rows and quote a phrase from neither. A cell has nowhere to put
  a citation either — its source is the row's own study column, or the section
  the row points at — so the uncited-assertion lint, whose entire premise is
  "this should have carried a key", cannot be satisfied inside one however true
  the cell is. Table rows are now skipped for that check only; overclaiming
  inside a cell is still entirely possible and stays in scope. [2026-08-16]

### Fixed — the citation gate reported "not corroborated" when corroboration had actually succeeded

- **`write_verify_status.py` gave its live `doi2bib --verify` recheck 120
  seconds, and a real bibliography needs longer.** Measured on the reference
  manuscript: 20 entries take over 300 seconds of Crossref content
  negotiation, so the recheck always expired and `verify-status.json` recorded
  `doi2bib_confirmed: false`. That field is the gate's own statement about
  whether its PASS was independently confirmed — and `false` there is
  indistinguishable from *the recheck disagreed*. Running the identical
  command by hand returned PASS on all 20 entries — in **1229 seconds**, timed.
  The budget now scales with the bibliography, taking the larger of doi2bib's
  own retry arithmetic (which tracks retuning of `RETRIES`/`TIMEOUT` instead of
  going stale the way a hard-coded literal did) and a measured per-entry cost.
  Floored at 120 s so a small bibliography still gets a fair network window,
  capped at 1800 s so a pathological run cannot hang the gate; the budget used,
  and whether the cap bound it, are both written into `verify-status.json`.

  Worth recording because the obvious reasoning is wrong: `requests`' `timeout=`
  bounds each socket **read**, not the total duration of a request, so
  `RETRIES × TIMEOUT + backoff` is a floor and not an upper bound. The measured
  run cost ~61 s per entry against an arithmetic 41.5 s. **No budget guarantees
  completion**, which is exactly why the honest-reporting half above is the part
  that matters: an expired budget now says `timeout` and points at the standalone
  command, instead of silently reading as a failed verification. [2026-08-16]

- **`SECURITY.md` now names `write_verify_status.py` among the networked
  scripts.** It opens no socket of its own — it runs `doi2bib.py --verify` as a
  subprocess — but a reader asking "what happens if I run this?" is owed the
  answer *it will talk to `doi.org`*. The kit's own governance test caught the
  omission the moment the file started naming the retry helper. [2026-08-16]

- **The WARN blamed the one cause that was not the cause.** `_live_reverify`
  collapsed "file absent", "wrong path", "network down", "checker crashed" and
  "ran out of time" into a single `None`, so the warning could only guess —
  and it guessed paths: *"If the real project files live elsewhere … check the
  paths."* The paths were correct; `cite_audit_confirmed` was `true` against
  the same ones. Each check now carries its own reason
  (`confirmed`/`absent`/`timeout`/`error`/`unparseable`), persisted in
  `live_recheck` and named in the warning, so a reader is sent at the clock
  rather than at a path bug that does not exist. [2026-08-16]

### Fixed — four tools read the kit's own evidence-binding syntax as prose

- **`word_budget.py` charged the author for HTML comments.** The worst of the
  four, because the other three emit advisory warnings while this one produces a
  number the author acts on: it is checked against a venue's word limit, and
  against it the author cuts real sentences. On the reference manuscript the
  reported body was 9,937 words; the honest figure is **9,730**. The Özet lost 28
  words and the Abstract 40 — an abstract that looked 536 words long against a
  300-word ceiling was 496. Comments are now dropped before counting, ahead of
  the heading strip so a commented-out heading is not counted either. [2026-08-16]

- **HTML comments were scanned as manuscript text by `claim_check.py`,
  `figure_check.py` and `tr_style_check.py`.** The `/draft` skill *requires*
  binding every empirical claim to its card in an HTML comment
  (`<!-- EV-0045 -->`), so a compliant draft is dense with them — and all three
  checkers then graded that markup as though a reader would see it. The failures
  ran in both directions: a comment carrying a card id and a percentage became an
  "uncited assertion with a statistic"; `<!-- bkz. Şekil 9 -->` invented a missing
  figure; a note written with English decimals made the decimal-separator check
  report a convention *mixture* the published text did not contain, which is the
  one thing that check exists to flag. Conversely `<!-- Şekil 3 -->` would have
  exempted the sentence beside it from a check it should have faced, and a
  commented-out figure still counted as embedded. Comments are now stripped
  before analysis in all three, replaced with whitespace so neither the words on
  either side of an inline comment fuse nor the line numbers after a multi-line
  one shift. [2026-08-16]

- **`claim_check.py`'s own-work marker did not know what a review calls
  itself.** A systematic review says *"bu derleme"*, never *"bu çalışma"*, so
  every sentence in which the review described its own scope was reported as an
  uncited empirical assertion — on the paper type the kit is built around. The
  same blind spot had already been fixed one layer over (`DEFAULT_SKIP` carries
  `sentez` because a review's results section cannot be named `results`) and was
  missed here. *derleme*, *inceleme* and English *this review* now count as
  self-reference. On the reference manuscript the two fixes together took the
  check from 6 warnings to 3, and all three survivors are known stem-matching
  false positives the script already documents. [2026-08-16]

### Fixed — a gate that called an approved outline unapproved

- **`/outline`'s approval marker was localisable, and localising it broke the
  phase gate.** The skill tells the session to write every user-facing string in
  Turkish and then shows an English `**Status:** approved` template; a session
  obeying both writes `**Durum:** approved`, and `phase_gate.py` — which matches
  the line literally — refuses the draft with *"outline not approved"*. That
  message is false: the outline was approved, the label was unreadable. It also
  sends the reader to re-run `/outline`, regenerating a file whose content was
  already right.

  The gate now accepts either label, and separates two failures it used to merge:
  an outline still saying `pending-approval` (never approved — go approve it) and
  one with no marker at all (possibly approved and since mangled — restore the
  line). The skill now states that the field name is machine-readable and is not
  covered by its own Turkish rule. Found by hitting it while drafting.
  [2026-08-15]

### Fixed — three Turkish lint checks that fired on correct Turkish

- **`tr_style_check.py` read Turkish thousands separators as decimal points.**
  "7.651 hasta" is seven thousand six hundred and fifty-one; the checker counted
  it as a `0.95`-style decimal and reported a mixed-separator defect on every
  draft that mentions a sample size. Thousands groups are now recognised, with
  the leading group anchored `[1-9]` so a real decimal like `0.809` is still a
  decimal.

- **`term_unity` reported drift in documents whose terminology never drifted.**
  Several glossary variants are ordinary Turkish words with a life outside the
  technical sense — *nitelik* also means quality, *sonuç* also means consequence
  — so a single incidental use was counted as a competing spelling. Those
  specific words now need two occurrences; unambiguous pairs like *veri
  seti*/*veri kümesi* still flag at one each, because the fix is a property of
  the word rather than a global threshold.

- **`voice_mixing` counted every borrowed *-ic* adjective as a first-person verb.**
  *diyabetik*, *sistematik*, *otomatik*, *pratik*, *kritik*, *analitik* all end
  in `-tik`, and a Turkish medical or ML manuscript is saturated with them. Two
  compounding causes: the module's fold maps `ı → i`, and **`re.IGNORECASE`
  treats `ı` and `i` as the same letter** because both uppercase to U+0049 — so
  the check destroyed the exact distinction its morphology depends on before
  matching. It now lowercases Turkish-correctly (`I → ı`) and separates the two
  senses by morphology rather than a word list: a first-person `-tik` has a
  consonant before the suffix (*eğit-tik*, *seç-tik*) and obeys vowel harmony,
  while a loan adjective has a vowel there (*diyabe-tik*) or violates harmony
  (*sistematik*). 35 hand-checked forms pin the behaviour.

  All three surfaced while drafting a real section: the first two buried the
  third, which was a genuine finding about the draft.
  [2026-08-15]

- **`term_unity` masked matches per concept, so a compound term was read as the
  bare one inside it.** "evrişimli sinir ağı" is a convolutional network — a
  different concept, not a second spelling of "yapay sinir ağı" — but while
  counting the `neural network` entry in isolation, the bare "sinir ağı" still
  matched inside the compound and the checker reported drift in a manuscript
  that had used both terms correctly. Masking now runs longest-first across the
  whole glossary in one pass, because nesting crosses concept boundaries too.
  `templates/tr-terminology.json` gains `convolutional neural network` and `deep
  neural network` as concepts in their own right, and loses `sonuç` as a variant
  of `finding` — in Turkish academic prose it means result/consequence and names
  a standard section heading, so listing it made every ordinary use read as
  terminology drift. [2026-08-15]

- **`tr_style_check.py` read a Roman-numeral heading as the abbreviation "v.s."**
  `# V. Sonuç` matched, because the pattern allowed whitespace across the period
  and `re.IGNORECASE` let a capital V start it. Every Turkish manuscript with
  numbered sections has a "V." heading, so the check fired on correct prose in
  the one place a Turkish author cannot avoid. The letters must now be lowercase,
  and a match inside a Roman-numeral heading is skipped — a genuine `v.b.` in the
  body under that heading is still caught. [2026-08-15]

- **`figure_check.py` could not see a Turkish figure or table.** It matched only
  "Figure N" / "Table N", so a Turkish manuscript writing "Şekil 2" and "Tablo 1"
  came back with zero figures, zero tables and zero warnings — the worst output a
  linter can produce, because silence reads as "checked and fine". `Şekil`,
  `Tablo` and `Çizelge` (plus their ASCII-folded forms) are now accepted
  everywhere, and the mention pattern tolerates the case suffix Turkish attaches
  to the number ("Şekil 2'de"). On the draft that exposed it, the fixed check
  immediately found three real defects: two figures mentioned but never embedded,
  one table embedded but never mentioned, and a numbering gap.

  This is the fourth place where the kit's Turkish path was weaker than its
  English one (after the outline approval marker and two `tr_style_check`
  defects). `.claude/TECH-DEBT.md` records the pattern rather than just the
  instance. [2026-08-15]

- **`claim_check.py` scanned a review's Results section for missing citations.**
  Its own-work skip list covered `results|bulgular|findings` but not `synthesis`
  — and a review's results file has to be named `synthesis`, because that is the
  key `word_budget.py`'s review proportions use. Two kit scripts disagreeing
  about one filename left a systematic review's central section as the only
  own-work file still scanned, and it duly reported the review's own synthesis
  sentences as uncited assertions. `synthesis`/`sentez` now skip like every other
  results section. [2026-08-15]

- **`temporal_check.py` read four-digit quantities in the 2100s as years.** A
  card reporting "2111 fundus images" was flagged as an anachronistic claim
  about the year 2111. No bibliography carries a 22nd-century date and no
  plausible typo produces one, so the `21xx` branch bought nothing; dropping it
  cut this project's card warnings from 9 to 3. The remaining three are the same
  class inside `20xx` — a 2048-dimensional feature vector, and a year belonging
  to a source the card cites rather than to the card's own source — and are
  recorded in `.claude/TECH-DEBT.md` rather than papered over, because
  separating them needs context, not a narrower range. [2026-08-15]

### Added — background citations that stay out of the PRISMA flow

- **A systematic review has to cite things its search never returned**, and the
  register had nowhere to put them. Invariant 1 forbids citing anything absent
  from `sources/registry.jsonl`; `prisma_flow.py` counted every record in that
  file as "records identified". Both rules are right on their own and they cut
  across each other: adding the epidemiological background, a reporting
  guideline, or a prior review cited for contrast inflated the flow with sources
  the search never found, and every box downstream with it.

  Records may now carry `scope: "background"`, which takes them out of the flow.
  The default is in-flow, so no existing project's numbers move, and the number
  taken out is reported as `background_excluded_from_flow` rather than silently
  dropped — a reader comparing the flow against the register must be able to see
  why the two totals differ. Found while closing four `[MATERIAL GAP]` markers in
  a real review: eight background sources would have turned a 76-record flow into
  an 84-record one. [2026-08-15]

### Added — the PRISMA box for reports you never obtained

- **`unretrieved` is now a registry status, and the flow diagram has the box that
  goes with it.** PRISMA 2020 separates *reports sought for retrieval* from
  *reports assessed for eligibility*; the gap between them is *reports not
  retrieved*. The kit could not express that gap. A paywalled article or an
  access-restricted thesis had two homes, and both lied: `excluded` asserts an
  eligibility judgement nobody made, and `candidate` let `prisma_flow.py` compute
  `fulltext = screened - excluded_screening` and count it as assessed.

  Found while running the kit on a real review, where 34 of 54 sought reports could
  not be obtained. The old flow reported 54 reports assessed for eligibility. Twenty
  had been opened.

  `derive_counts` now emits `sought` and `not_retrieved`, and `check()` enforces
  `sought - not_retrieved == fulltext`. Both keys are optional in a hand-written
  `--counts` object, so every flow written before today still validates — with
  `not_retrieved` at 0 the new box collapses onto the old arithmetic exactly.
  [2026-08-15]

### Fixed — a retrieval gap silently inflating screening precision

- **`screening_score.py` scored an unobtainable report as "undecided" and dropped it
  from the denominator.** A record sought for retrieval passed title/abstract
  screening — that is a screening *include*, and the failure that followed was
  access, not judgement. Since the reports you cannot reach are by definition ones
  you screened in, discarding them removes only true positives and inflates
  precision. They now score as includes, counted under
  `stage.unretrieved_scored_as_include` so the basis is visible rather than assumed.
  [2026-08-15]

### Fixed — an agent that was never loading, and nothing said so

- **`methodology-advisor` was absent from every session for as long as its
  description has had its current wording.** Its YAML frontmatter used an
  unquoted multi-line `description:` whose continuation line read
  `...before a meta-analysis: may these studies be`. A plain YAML scalar cannot
  contain `: ` — the parser reads that line as a new mapping key, the frontmatter
  fails, and the harness drops the agent silently. `validate_kit.py` reported
  `agents: 10, problems: 0` throughout, because it counts files and never parses
  what it counts.

  Found by dispatching to the agent and being told it does not exist — during the
  one task it exists for, ruling on whether a set of studies may be pooled.
  Quoting the description fixes it; the agent loads again.

  `test_every_agent_frontmatter_survives_a_yaml_parse` now holds the whole class:
  for every agent, a continuation line inside an unquoted frontmatter scalar may
  not contain `: `. Verified the way this repo verifies things — the test fails
  when the fix is reverted, not just when nothing is wrong. Parsed as text rather
  than with PyYAML, for the reason `test_lint_and_ci_config.py` already gives.
  [2026-08-15]

### Changed — the site is a record now ("TUTANAK")

The design direction was replaced, and three defects found while auditing it
were fixed with it. The direction it replaces, "AURA", was — in its own
`web/DESIGN.md`'s words — *"ported from a supplied brief for a premium,
AI-native product page"*: it read as every other AI product page of its year,
worn by the project whose one differentiator is refusing to claim what it has
not measured. [2026-08-15]

- **The hero is the artifact, not a picture of one.** `Record.astro` *imports*
  `examples/showcase/03-verify-status.json` and typesets it, so the figures on
  the landing page are read from the real gate output of the real paper run at
  build time — there is no second copy for them to drift from. It replaces a
  fabricated workspace mockup (invented inbox, invented senders) that sat on the
  landing page of a kit whose thesis is that a record you cannot open is not
  evidence. Beside it, the line that makes `retracted: 0` mean something: the
  retraction was caught one stage earlier, at PRISMA full-text screening, so the
  citation gate had nothing left to count.
  `test_the_landing_record_matches_the_showcase_artifact` fails the build if the
  page and the JSON disagree. [2026-08-15]

- **The site's only outbound request is gone, so the claim is unqualified
  again.** The backdrop was a `<video>` on a third-party CloudFront
  distribution, under a user path this project does not own, which forced
  `media-src` in the CSP to name a remote host — on the marketing site of a kit
  whose `SECURITY.md` opens with *what leaves your machine*. `DESIGN.md` had
  already recorded that the CDN was unreachable from the build machine, i.e.
  **the hero had never once been seen rendering**, and shipped it anyway
  (re-checked: still unreachable, request times out). Not one CSP directive
  names a host now, and `test_the_policy_names_no_remote_host` reads the policy
  rather than the markup, because the tag-based self-containment test could
  never have seen this. [2026-08-15]

- **The landing page's meta description was stale, in the one place that is not
  on the page.** It hard-coded "9 subagent, 17 komut" against a real 10 and 43
  while the other four pages all interpolated from `site.ts` — so a search
  result and every shared link advertised roughly half the kit.
  `test_the_landing_description_states_no_stale_counts` now requires every
  integer in it to be a count the repository actually reports. [2026-08-15]

- **172 KB of fonts nobody had declared since two directions ago.** Four
  Archivo `woff2` files in `web/public/fonts/` and `docs/fonts/`, referenced by
  no stylesheet and no built page, served to every visitor. Removed with the
  Apple corporate logo that led the retired macOS menu-bar strip. The built site
  is 188 KB lighter overall and the landing page 9 KB lighter on its own.
  [2026-08-15]

- **Dark mode, from the same tokens.** Every colour resolves to a custom
  property, so `prefers-color-scheme: dark` remaps names rather than restating
  rules; the warmth is kept and the verdict hues are lifted for contrast. The
  share card was regenerated in the new palette without a line of its drawing
  code moving — the fourth time that has held. [2026-08-15]

### Fixed — a red gate recorded as green, and two stale counts

An external review pass over 0.4.0 (tagged 1.3.0 at the time) ran the gates instead of reading about them.
Three findings, one of which was a live break. [2026-08-15]

- **The `lint` job was red on a clean tree, and a test docstring said it was
  not.** `bandit -q -ll` reports MEDIUM **and above**; the two HIGH B202
  `extractall` findings in `dataset_fetch.py` were therefore reported, bandit
  exited 1, and `.pre-commit-config.yaml` was rejecting every commit that
  touched `scripts/`. The note in `test_remediation_2026_08_15_axes_review.py`
  recording "CI's `-ll` threshold already passes" had been written without
  running the command — which is the same defect as the six findings that file
  exists to hold: *a check reported OK for having checked nothing*. The
  extraction guards were never in question (path-escape rejection,
  symlink/hardlink refusal, member and size ceilings, `filter="data"` on 3.12+),
  so both call sites now carry a justified `# nosec B202` stating the argument
  next to the code it defends. `test_lint_and_ci_config.py` now **runs** the
  bandit line out of `ci.yml` and asserts exit 0, rather than asserting that
  `ci.yml` mentions bandit. [2026-08-15]

- **`.claude-plugin/marketplace.json` advertised "17 workflow commands + 11
  knowledge skills + 9 subagents"** against a real 43 / 11 / 10 — stale by more
  than half, in the first sentence anyone reads before installing. Every
  existing manifest test checked structure (paths resolve, versions agree, the
  agent list matches the directory) and structure was fine.
  `test_plugin_manifest.py` now binds the storefront counts to the catalogue the
  way `test_governance_docs.py` already binds both READMEs and `site.ts`.
  [2026-08-15]

- **README.md contradicted itself on the agent count**, two hundred lines apart:
  "10 subagent" in the opening paragraph, "(9 subagent)" in the directory-
  structure section a reader consults to find out what is installed. The
  governance test pinned one sentence per language and could not see the second
  mention; it now checks **every** agent count each README states. [2026-08-15]

## 0.4.0 — 2026-08-15

### Added — the other three axes of an academic's job

Thirteen commands and nine tools. The manuscript axis was finished; a gap scan
run against the **job** rather than the artefact found that what remained was not
inside that chain at all. The same person who writes the paper also writes the
grant proposal, files the ethics application, referees for journals, assembles a
promotion dossier, and teaches — and each of those has an **authority document**
the kit must not remember plus an **arithmetic** to run against it. That shape
already existed in `submission_pack.py`'s `limits.json`; this release generalises
it and names it (CLAUDE.md invariant 9). See DECISIONS.md D-098. [2026-08-15]

- **`/review-paper` + `scripts/referee_report.py` — refereeing, built as a
  refusal.** A paper sent to you for review arrives under a confidentiality
  undertaking that Elsevier, Springer and NIH state explicitly, so the kit
  **never reads it** — pointed at a `.pdf`/`.docx`/`.tex` it stops and says why,
  and there is no override flag. You read it; your notes become a structured
  report, and the report's own defects are audited: an unanchored Major, broken
  numbering, a recommendation outside the journal's own option set, and the
  phrases ("as we showed in our previous work", "kendi çalışmamızda") with which
  an anonymous referee signs it. [2026-08-15]

- **`/dossier` + `scripts/dossier_score.py` — a promotion file that keeps no
  record.** This looked like the feature that would finally have to move
  `POSITIONING.md`'s cross-paper-memory line. It did not: the publication export
  and the criteria table are handed over per run, nothing is stored, and a test
  asserts nothing is written outside the project directory. The value was never
  in remembering — it is the arithmetic, and re-verifying every publication's
  index claim against the venue cache, because an ESCI paper counted as SCI-E is
  a dossier's most frequent error. `--cv` renders a CV from the same list.
  [2026-08-15]

- **`/proposal` + `/project-report` + `scripts/proposal_check.py` — the half of a
  proposal that is arithmetic.** Every objective bound to a work package and back,
  every deliverable inside the project's own duration, budget lines summing to the
  declared total, and the personnel figure following from the person-months —
  the four things reviewers find every round with a calculator. Renders the Gantt
  (markdown and pgfgantt). `--report` turns the same plan into the progress or
  final report, with the actual side derived from the run, dataset and source
  registers and **no reason written for a gap**. [2026-08-15]

- **`/ethics-application` + `scripts/ethics_pack.py` — the protocol's second
  writing.** The ethics board asks for the collection protocol's material again on
  its own form, weeks later, by which time the field list has moved. The
  collection plan's own `fields` map is the authority here: a column the plan
  writes and the consent text does not name is the finding. Ten consent elements,
  a vague-retention check, and a refusal to write any approval number.
  [2026-08-15]

- **`/dmp` + `scripts/dmp_gen.py` — the data management plan, derived.** FAIR is
  reported one letter at a time with the record that evidences it, and a dataset
  whose licence or citation DOI is unrecorded gets **no sentence at all** — the
  gap is listed under its own heading. The document never contains "this project
  follows FAIR principles", a sentence available to anyone regardless of what they
  did. [2026-08-15]

- **`/merge-coauthor` + `scripts/coauthor_diff.py` — the returned file.** Track
  changes answers "which words moved", the one question whose answer is obvious.
  This extracts the three that survive a read-through: a citation key deleted while
  its sentence stayed, a number no recorded run produced, a claim that moved up
  the strength ladder — plus the Word comments pandoc drops. Merges nothing and
  compares no prose. [2026-08-15]

- **`/deposit` + `scripts/deposit_pack.py` — either side of publication.**
  `--preprint` checks the server's own limits and **records** the five decisions
  (journal policy, licence, category, version, co-author consent) rather than
  printing them: an undecided one is a finding, because a posted licence cannot be
  taken back. `--corrigendum` produces the part of a correction that is actually
  hard — everywhere the wrong value went, across drafts, the figures named beside
  it, run records and evidence cards, matched across both decimal conventions.
  [2026-08-15]

- **`/syllabus`, `/exam`, `/rubric`, `/accreditation` +
  `scripts/syllabus_check.py`, `scripts/outcome_matrix.py` — the teaching axis.**
  Assessment weights, workload against the ECTS (as the Bologna 25–30 *range*
  unless the institution fixes a figure), learning outcomes carrying a verb an
  examiner can observe, coverage in every direction, and the rubric check that
  earns its place: strip the intensity adverbs and report the levels that then say
  the same thing. The accreditation matrix runs both ways and computes **no**
  achievement percentage. No MÜDEK or ABET outcome list ships — it comes from your
  programme's own document. [2026-08-15]

- **`/supervision` — the TİK report, with no tool of its own.** Chapter word
  counts, RQ↔chapter traceability, card and run statistics, and what changed since
  the last report, assembled from tools that already exist. Keeps no student
  records. [2026-08-15]

### Fixed — the self-review of the axes above, and the failure it kept finding

Every gate was green before this review: `validate_kit`, `ruff`, the full suite,
both eval harnesses, the rebuilt site. Ten defects followed, six of them the same
one — **a check reporting `OK` for having checked nothing**. That mode survives a
green suite by construction: a test written for a populated fixture never visits
the empty one, and the empty one is what a first-time user has. [2026-08-15]

- **Six "nothing checked" paths now report a finding instead of `OK`:** a DMP over
  an empty dataset register (`UNCHECKED`), a proposal whose call file carries a
  `source_url` but no `fields` (refused outright — every other authority file in
  the kit already required its list), a syllabus with no learning outcomes, a
  workload table with no ECTS beside it, an empty publication export, and a
  progress report with no work-package plan behind it. [2026-08-15]
- **`ethics_pack` matched collected field names as substrings**, so a column called
  `id` or `e` read as disclosed by any sentence containing those letters — a false
  negative on the one check that script exists for. Now word-boundary matched, in
  both the `post_text` and `post metni` spellings. [2026-08-15]
- **`dossier_score` dropped publications past a criterion cap without naming
  them**, silently deciding which of your papers count, in export order. It now
  lists them and says the order it used was no order at all. It also no longer
  writes the looked-up quartile back into the caller's export. [2026-08-15]
- **Bloom verbs were prefix-matched in English too**, so "useful" read as *apply*,
  "namely" as *remember* and "statement" as *remember* — an unmeasurable outcome
  passing as measurable. English now takes inflections only (including the y→ies
  form), Turkish keeps its open suffix because the language is agglutinative, and
  `bloom_of` returns the **highest** level present rather than the first: an
  outcome names the level of its most demanding verb. [2026-08-15]
- **The three new project directories were missing from the write allowlist** in
  `.claude/settings.json`, so every funding, career and teaching command would
  have hit a permission prompt on its first write. [2026-08-15]
- `/dmp`'s SKILL.md documented `dataset_db.py verify DS-0002`; the flag is `--id`.
  The CLI contract test checks flags that are written, not positionals written
  where a flag belongs. [2026-08-15]

### Changed

- `POSITIONING.md` and `POSITIONING.en.md` gain a refused mechanism (processing a
  manuscript you are refereeing), a clarification that `/dossier` does not move the
  cross-paper-memory line, the scope widening to the teaching axis, and a new
  **authority-file rule** section. `CLAUDE.md` gains invariants 9 and 10.
  [2026-08-15]
- `templates/proposal/proposal.md` replaced: the 14-line stub nothing drove is now
  a real generic skeleton wired to `proposal_check.py`, `dmp_gen.py` and
  `ethics_pack.py`. `project-template/` gains `proposal/`, `teaching/` and
  `dossier/`. [2026-08-15]

- `/find-dataset`, `/collect-data` and `/experiment` now wire in the scripts
  above; `SECURITY.md` documents the three scripts whose destination **you**
  choose and states plainly that `collect_run.py` deliberately transmits the
  contact address you wrote in your own collection plan — the one exception to
  the "no identifier of yours leaves the machine" promise. [2026-08-14]
- `results_table.py` reports groups in register order (first appearance in
  `runs.jsonl`) rather than the alphabetical order `experiment_db.summarise`
  returns, so a model named `a-net` cannot appear above the baseline it is
  compared against. [2026-08-14]

- **`eval/MEASUREMENT.md`'s "not measured" row is one line shorter again.**
  Synthesis moved out of it: `draft_stability.py` reads any evidence-bound
  markdown, and a synthesis matrix rendered N times is exactly that, so the row
  now says "stability measurable, accuracy not" rather than nothing. What
  remains unmeasured is the style audit, which returns an edit list and has no
  evidence-bound prose to compare. `/lit-review` offers the check at the
  synthesis step and does not run it by default — it costs N synthesis passes.
  [2026-08-14]

- **The site now wears the "AURA" design language.** `#0c0c0c` ground, a fixed
  fullscreen backdrop, guide lines at the container edges, a shiny gradient
  headline swept across a 200%-wide ramp under SVG grain, a macOS menu-bar strip
  carrying the kit's own phases, liquid-glass cards, a workspace mockup, and the
  three gates as 44px-radius glass cards under a 9rem watermark. Ported from a
  React + Framer Motion + Tailwind brief **without** React, Framer Motion or
  Tailwind: every entrance in it is a fade and a translate on a fixed delay, so
  they are CSS keyframes with the same delays and easing, and the page still
  ships 0 KB of JavaScript. Inter is now self-hosted alongside IBM Plex Mono, so
  there is still no font request. The workspace mockup shows the kit's real
  artefacts — the registry, the retracted source held back at full text, one
  verification record — rather than invented content. Direction, what was
  deliberately not ported, and the constraint table: [`web/DESIGN.md`](web/DESIGN.md).
  [2026-08-14]

- **The site makes one outbound request now: the backdrop video.** It is served
  from CloudFront, so `media-src` in the injected CSP names a host and the
  READMEs' "zero outbound requests" line became "one, and here is what it is".
  Everything else stayed same-origin and `connect-src 'none'` still forbids the
  page from talking to anything. The CDN was unreachable from the machine this
  was built on, which is why the layer beneath the video is a composed CSS wash
  rather than bare black: it is a designed state, not an empty one. Emptying
  `BACKDROP` in `Base.astro` removes the request and the directive with it.
  [2026-08-14]

- **The site was redesigned from scratch: "KÂĞIT", a critical edition.** The
  previous direction was achromatic on principle, and its own `web/DESIGN.md`
  recorded the risk in advance — whether the no-colour rule would read as a
  thesis or as drab. It read as drab. The replacement sets the site as a
  scholarly edition: a main column for reading and a **margin column of numbered
  notes keyed to markers in the text**, which is the kit's own argument — a claim
  with its evidence beside it — in typographic form. Warm paper ground, one
  vermilion for marking and striking, one green for a PASS verdict; a system
  serif for the argument, Archivo for the apparatus, Plex Mono for anything that
  is a record. Light-only on purpose. Three IntersectionObservers went with the
  old design, so the page's entire JavaScript is the language toggle again —
  which is what both READMEs always claimed. Eleven components were replaced by
  four. Every site governance test still passes unchanged, including the CSP
  hashes, the single shared stylesheet and the no-inline-style rule. Direction,
  costs and the constraint table: [`web/DESIGN.md`](web/DESIGN.md). [2026-08-14]

- **The bootstrap CI and Cohen's κ now live in `lib_stats.py`**, shared by
  `calibration_score.py` and `screening_score.py`. A confidence interval
  computed two slightly different ways in two places is two different claims
  wearing one name; the second caller was the moment to move it rather than
  copy it. [2026-08-14]
- **All nine gold sets are now held to P ≥ 0.95, R ≥ 0.95**, not just
  `claim_strength`. Leaving the other eight at 0.90 was recorded as a deliberate
  choice whose argument would apply "the moment any of them grows". Measuring
  them showed it already had: `tr_style:percent-detector-disabled` was dying at
  0.8889 against a 0.90 line — a margin of 0.011, one added positive case from
  surviving, which is exactly how `first-person-exception-list-emptied` was lost
  once before. Waiting for the symptom means waiting for a mutation to go quiet,
  and a mutation going quiet is the one event this harness cannot report. All 49
  mutations still die at the stricter line, every checker still scores 1.00, and
  a test now asserts the floor so a gold set copied from an old manifest cannot
  inherit 0.90. [2026-08-14]
- **The claim-strength gold set is held to 0.95 instead of 0.90**, and grew from
  38 cases to 71. Adding cases to a pooled set quietly weakens every mutation
  scored against it — three that had been failing the build for months started
  surviving once the set grew — so the threshold moves with it. The checker
  already scores 1.00; this is a stricter bar, not a looser one. [2026-08-13]
- **MEASUREMENT.md's prose totals and DECISIONS.md's contents index are now
  bound by tests.** Both stated counts that nothing checked, and the first had
  already drifted away from the table printed above it. [2026-08-13]

- **Site: the architecture page's fail-open passage was out of date** the moment
  the notice landed — it described the failure as silent. Rewritten in both
  languages to state that the layer fails open *and says so*. [2026-08-13]
- Test count 1182 → 1207. [2026-08-13]

- **Site redesigned from scratch — "Cilt" (the bound volume), plus a new mark.**
  The page is laid out as a bound library volume: sections alternate
  between a navy buckram *case* and a paper *leaf* with hard edges, and a brass
  foil rule runs the full height of every band as one unbroken spine, filling in
  as each section is read. The palette is library binding cloth and foil stamping
  (`#111C28` / `#B58F4B`) rather than a product accent, and the display face is
  the Palatino/Iowan humanist line — chosen, not fallen back to, because the site
  ships **zero external requests** and a font CDN would quietly make that claim
  false. The logo is now the spine of a bound volume with a check stamped in its
  title panel. Motion is CSS-only: one page-load sequence, and scroll-linked
  effects behind `@supports (animation-timeline: view())` that degrade to a
  static page rather than a broken one. [2026-08-12]
- **Security: every built page ships a Content-Security-Policy.** GitHub Pages
  cannot set response headers, so the policy travels in a `<meta>` tag injected
  by `postbuild.mjs`, which hashes every inline script on the page after it
  exists — the only way the hash cannot drift from the script it authorises.
  `default-src 'none'` with explicit exceptions; no `'unsafe-inline'` anywhere,
  which is why the site now carries a small closed set of spacing utilities
  instead of `style` attributes. Two limits are written down rather than papered
  over: a meta policy cannot express `frame-ancestors`, and a policy delivered in
  the document defends against injected content, not a compromised host.
  [2026-08-12]
- **SEO: a generated share card and a fuller structured-data graph.**
  `web/make_og.py` renders `og.png` (1200×630) from the same design and reads its
  counts out of `web/src/data/site.ts`, so the card cannot advertise last
  release's figures. Pages now emit a `WebSite` + `Person` +
  `SoftwareApplication` + `BreadcrumbList` graph, the overview adds a six-question
  `FAQPage`, and every page declares `og:image`, `og:image:alt` and a
  `theme-color`. [2026-08-12]
- **Accessibility: skip link and a named main landmark on every page**, a visible
  foil focus ring, ≥44px controls, and a full `prefers-reduced-motion` stop.
  [2026-08-12]
- **Eight new site tests.** The CSP must be present and start from
  `default-src 'none'`; its hashes must match the page's inline scripts exactly
  (a mismatch silently disables the language toggle and nothing else notices); no
  page may carry an inline `style` attribute; the share card must exist at
  1200×630 on the site's own domain; exactly one `<h1>` per language per page;
  a skip link that resolves to a `<main>`; and the structured FAQ must ask only
  questions the page visibly answers. [2026-08-12]

- **The site is now an Astro build, and the built output is committed.**
  `web/` holds the source; `npm --prefix web run build` writes `../docs`, which
  GitHub Pages serves from `main`. Committing generated output is a deliberate
  trade: it keeps the deploy to one Pages setting and one DNS record, with **no CI
  workflow** in a repository whose CI currently only runs tests.
  Astro rather than a React meta-framework because these pages have no
  interactivity worth a runtime — the only script is a ~20-line language toggle,
  and the build ships **0 KB of JavaScript**. Five pages, one design system,
  content-hashed CSS, JSON-LD, per-page canonicals, sitemap and robots.
  Two build decisions are documented in the config because both look like
  oversights otherwise: `format: 'file'` (so URLs are `komutlar.html`, not
  `komutlar/`) and a post-build pass that rewrites Astro's root-absolute asset
  paths to relative. Both exist so that **opening `docs/index.html` from disk is
  the site** — being able to check the thing without a server is worth more than a
  marginally cleaner URL. The same pass deletes the content-layer artefacts Astro
  emits for a project that declares no content collections; in a normal `dist/`
  they would be throwaway, here they would be committed and served.
  Everything factual — the tool list, commands, agents, counts — moved into
  `web/src/data/`, so a number is written once.
  **Three new tests guard the committed-build failure mode**, which is staleness:
  every file in `web/public/` must byte-match its copy in `docs/` (and
  `docs/PERFORMANCE.md` is exactly the file someone would edit in the wrong
  place, since both READMEs link to it), the version rendered into the pages must
  match `CITATION.cff`, and no page may carry a root-absolute asset path.

- **`SECURITY.md`** — leads with the question a researcher holding an unpublished
  manuscript actually has: *what leaves my machine.* A table of the four hosts
  the scripts contact and the only things ever sent (a DOI, an ISSN, a journal
  title); an explicit list of what never is — drafts, `analysis/` data, evidence
  cards, review reports, file paths, `PROJECT.md`, and any identifier of you, the
  User-Agent being a fixed placeholder rather than your address. No telemetry, and
  no setting to disable because there is nothing to disable. It also names what is
  NOT covered — MCP servers necessarily receive your search terms, and Claude Code
  itself receives the conversation, which no kit can change — and states plainly
  that the hooks **fail open**, making them a safety net rather than a security
  boundary. Scope for reports includes path escapes and injection; it excludes
  prompt injection through a source you chose to ingest, which is a documented
  limit of every LLM tool.
  **Six tests keep the document honest**, and one of them is the point: it greps
  `scripts/` for network calls and fails the build if a script contacts an
  undeclared host or is absent from the policy. Another asserts the User-Agent
  still carries the placeholder — interpolating the user's git email is the
  *polite* thing to do for Crossref, and would quietly start transmitting an
  identifier the policy promises never leaves.
- **`CONTRIBUTING.md`** — what the repository actually enforces, so a change can
  be judged in thirty seconds instead of a review round: JSON-only output, new
  checks WARN-only (three gates block, a fourth is a scope decision), sandboxed
  paths with the two commented exceptions, the 520-line skill cap, and the rule
  most PRs get wrong — **missing data is reported, never zeroed**. Opens by
  pointing at `POSITIONING.md`, because most contributions a project like this
  rejects are good ideas in the wrong project.
- **Issue templates.** Blank issues off; security routed to a private advisory
  instead of a public issue. The bug form requires the full JSON output rather
  than an excerpt (these tools deliberately report what they did *not* determine,
  and that is exactly the part people trim) and makes the reporter confirm
  `PROJECT.md` exists — without it every enforcement hook is silently a no-op,
  which is the likeliest cause of "the gate didn't fire".

- **The site has an address: `scholar.mtvrkan.com`.** Moved to `docs/index.html`
  with a `docs/CNAME`, because GitHub Pages serves a branch folder only from the
  repo root or `/docs` — this way the deploy needs no workflow file at all, just
  one DNS record and a settings toggle. Added a canonical link, Open Graph and
  Twitter card metadata (the share preview repeats the page's own thesis — what
  the kit refuses — rather than a growth claim), an inline SVG favicon, and the
  version in the footer. `docs/RELEASING.md` gains the DNS/Pages procedure,
  including the two things that look like failures and are not: the site answers
  on `mtvrkan.github.io` until the certificate is issued, and a Cloudflare-proxied
  record must stay grey-clouded until then. `CITATION.cff` now carries `url:`.
  Five tests hold it together — the domain must agree across CNAME, canonical and
  `og:url` (any two disagreeing de-indexes the live site), both READMEs must link
  it, the page must stay self-contained, and it must show the current version.

- **The showcase manuscript was added and then withdrawn before release.** The
  PDF was clean — placeholder author, all 26 pages scanned, no name, affiliation,
  address or ORCID — so this is a *timing* decision, not a redaction one: the
  paper is in a journal's review process and this repository is headed for a
  permanent Zenodo archive. A file can be removed from GitHub; a released archive
  cannot, and a permanently citable version differing from what reviewers saw is
  a problem to inherit rather than create. It goes in once the paper is published.
  The identity guard added alongside it stays, dormant, for that day.
  The showcase loses nothing that carries its argument: the final document is the
  kit's *output*, while the evidence is how that output was reached — which is
  what the ten process artifacts are.

## 0.2.0 — 2026-08-12

- **`requirements.txt`** pinned with tested-baseline floors + major-version caps;
  CI now installs via `-r requirements-dev.txt` (single source of truth, no drift).
- **Release archives** (`git archive`) exclude dev-provenance docs
  (`DECISIONS.md` ve o gunun yapim plani) via `.gitattributes export-ignore`.
- Test suite: 663 cases (661 passed + 2 live-network smokes skipped by default).

## 0.1.0 — 2026-07-05

First official release. Built per the v2.0 build plan and hardened
through extensive internal review before this cut — full round-by-round
rationale for every fix lives in DECISIONS.md (D-001…D-083); this entry
describes what ships, not how it got here.

### Added — the empirical chain, closed; and the paper that already exists

- **`scripts/dataset_fetch.py` — the download that was never part of the chain.**
  `/find-dataset` ended at a register row and the author opened a browser; from
  that moment nothing tied the file on disk to the record. The fetch now starts
  from the register: it refuses while the licence is unread (`license_verified:
  false` blocks it and names the fix), hashes the bytes **as they arrive**, keeps
  a fetch log of URL/date/status/digest beside the data, exits BLOCKED on a
  credential wall with that host's own documented path, and unpacks archives with
  path-escape and size guards. `--attach` hands the files to `dataset_db.py`,
  which stays the register's only writer. [2026-08-14]

- **`scripts/collect_run.py` — the collector nobody kept.** `/collect-data`
  produced a protocol and then a hand-written scraper, different every session:
  the rate limit, the field list, the robots verdict and the request log lived in
  a file nobody kept. The kit now runs the collection under conditions it will not
  relax — an incomplete protocol refuses, a field absent from the protocol is
  never collected, a robots disallow has **no override flag**, the User-Agent
  carries the author's own contact address, there is a request ceiling and a rate
  limit, a 429 stops the run rather than triggering a retry, and every request is
  logged. Resumable via `--resume`; `--limit` runs a pilot first. This moves a
  boundary `POSITIONING.md` had drawn; the reasoning is recorded there and in
  DECISIONS.md D-097. [2026-08-14]

- **`scripts/train_runner.py` — the script that produced the numbers, written
  fresh every time.** Runs the matrix from `analysis/experiment.json`. Its point
  is one guarantee no instruction ever reliably produced: preprocessing is a
  `Pipeline` step, so `preprocessing_fitted: "within-fold"` is true **by
  construction** rather than by declaration — the one leak `leakage_check.py`
  could only take the author's word for. Writes the split manifest as it splits,
  saves per-fold predictions, records every run including the losers, adds a
  trivial baseline to any matrix without one, and refuses unregistered or drifted
  data, a seedless config, and a `--best` flag that does not exist. Needs
  `requirements-ml.txt`. [2026-08-14]

- **`scripts/results_table.py` + `scripts/results_figure.py` — the two artefacts
  that were still transcribed.** The results table is generated from the register
  in markdown/LaTeX/CSV, with the seed count in its own column and the difference
  against a reference model as a **paired bootstrap interval** computed from the
  predictions; the figure draws one point per seed rather than a bar of means.
  Neither sorts by score and nothing is bold. The table is stdlib-only, because
  the machine that writes the paper is not always the machine that trained the
  model. [2026-08-14]

- **`/import-manuscript` + `scripts/manuscript_import.py` — the paper that
  already exists.** Every command assumed the manuscript started here; the most
  common request does not. A `.docx`/`.tex`/`.pdf`/`.md` is converted through the
  tool that owns that format, split on the headings the document actually has, and
  its reference list is read as **a list of DOIs, not as bibliographic truth**.
  Not one sentence of the text is edited and not one citation is rewritten — the
  numeric→bib-key mapping is written to `drafts/citation-map.json` as a proposal.
  From there `/verify-citations`, `/critique` and `/submit-check` apply to it like
  any other draft. [2026-08-14]

- **`/translate` + `scripts/translation_check.py` — what a translation must not
  change.** Section-by-section TR↔EN translation with the terminology fixed first,
  then a deterministic check of the three things that must survive: citation keys,
  quantities (normalised across both decimal conventions, so `1.250,75` and
  `1,250.8` are recognised as one quantity at two precisions and reported as a
  *rounding* difference, kept separate from a digit that moved), and
  cross-reference numbers. Prose is never compared. [2026-08-14]

- **`requirements-ml.txt` — the ML stack, kept out of the core.** scikit-learn,
  pandas, numpy and matplotlib are optional and imported on first use; the two
  scripts that need them exit `BLOCKED` naming this file, the same contract pandoc
  and latexmk already have. Every existing gate, check and build still runs on the
  five core dependencies. [2026-08-14]

### Fixed

- `python -m ruff check .` had nine standing violations (five test modules
  importing a script purely to prove it imports, three genuinely unused imports,
  one unstrict `zip` over CSV rows that are legitimately ragged). A linter with
  standing violations is not a gate. [2026-08-14]

- **`"İçindekiler".lower()` is not `"içindekiler"`, twice.** Python decomposes the
  dotted capital I into i + COMBINING DOT ABOVE, so every Turkish heading a
  keyword check looked for silently failed to match — first in the collection
  protocol check, then again in the thesis front-matter check. Both now fold
  through `lib_common.transliterate`, which already existed for bib keys: one
  implementation, in the place a third caller will find it. [2026-08-14]

- **`bash` was a prerequisite nothing declared and nothing checked.** Both
  final-output builders are shell scripts and every skill invokes them as
  `bash scripts/…`, but the requirement lists named only Python, the Claude CLI,
  pandoc and MiKTeX, and neither installer probed for it. On Windows that
  interpreter comes with Git for Windows and nowhere else, so a machine with
  pandoc and MiKTeX installed still failed at `/submit-check`'s build step after
  every dependency check had printed `[ok]`. `INSTALL.ps1` and `INSTALL.sh` now
  probe for it, both READMEs list it (with where Windows gets it) and carry a
  troubleshooting entry, and three tests bind the claim to the installers and to
  the builders still being shell scripts. See DECISIONS.md D-092a. [2026-08-14]

- **The scope guard trusted a marker anyone can carry.** `PROJECT.md` decided,
  alone, whether the enforcement hooks were in jurisdiction — and that name is
  not this kit's property, so an unrelated repository holding a file by it
  re-armed the drafts/build/exports/`references.bib` gates. It is now two-stage:
  a positive kit signal (a signature line now in the template, enough of the
  template's own field labels to be it, or any file only a kit project holds)
  settles it outright, and only in the absence of any signal does a package
  manifest veto. A directory matching neither stays gated, deliberately:
  over-gating announces itself in a deny message, under-gating is silent. See
  DECISIONS.md D-092b. [2026-08-14]

- **Doc drift the "every number is checkable" rule never reached.**
  `CONTRIBUTING.md`'s opening line still read "35 tools … ~1370 tests" — the
  first number a new contributor sees was the one number nothing checked. Fixed,
  and now bound to `scripts/`, `.claude/skills/`, `.claude/agents/` and the
  published test count. [2026-08-14]

- **Every hook crashed on valid JSON that was not an object, and took a payload
  with no `tool_name` in total silence.** `json.loads("[]")` succeeds and the
  next line — `payload.get(...)` — raises outside the `try` written to contain
  it, so `[]`, `"str"` or `123` on stdin produced a traceback and a non-zero
  exit from all five hooks, contradicting the "never a crash" each one's own
  docstring promises. The quieter half was worse: an object with no `tool_name`
  matched no branch and exited 0 with no output, which is byte-identical to
  "checked, nothing to gate" — and that is exactly the shape a change in the
  harness's hook contract would have, i.e. every gate in the kit switching off
  at once while still looking like a gate that passed. Both now route through
  `_degrade.read_payload()` / `missing_tool_name()` and produce the standing
  `⚠ Scholar-Kit gate degraded` notice, which names the gate and states that
  the call was allowed. Empty stdin and an empty object stay silent, unchanged:
  a harness probe is not a broken gate. The notice carries a type name or a key
  name and nothing else, under the same leak rule as the rest of the module.
  It fires only inside a kit project, so a plugin install stays quiet in
  repositories that were never this kit's to gate. `SECURITY.md` § Trust
  boundaries also now states, rather than implies, that `settings.json`'s
  `allow` list is prefix-matched and is not a boundary. See DECISIONS.md D-091.
  [2026-08-14]

- **Two skill descriptions collided in ways the router could not resolve, and
  one of them was the collision this repository had predicted in writing.** The
  48-prompt golden set was scored live for the first time, blind — the agent got
  the extracted catalog and the prompts with their `expect` labels stripped —
  and returned 45/48. `slr`'s description opened on the word *systematic* while
  `lit-review`'s never used it, so "run a systematic literature review" routed to
  the heavy pipeline; and "APA'dan IEEE stiline nasıl geçerim, referanslarımı
  yeniden mi yazmam lazım?" routed to `restyle`, the command that performs a
  switch, rather than to `citation-styles`, which answers what switching
  involves. `ROUTING-EVAL.md` had named that exact pair as the one to watch.
  Four descriptions now state the criterion rather than more keywords —
  artefacts vs. the word "systematic", instruction vs. question — and a second
  fresh agent scored **48/48**, with the 45 previously-correct prompts unmoved.
  [2026-08-14]
- **The routing eval's own reproduction instructions leaked the answers.** They
  said to hand the agent `eval/golden-prompts.json`, which carries `expect`
  beside every prompt; following them measures reading comprehension. The
  procedure now requires stripping the labels and forbidding the agent to open
  the repository, where this document would tell it the answers anyway — the
  same refusal `calibration_score.py` already makes about contaminated verdicts.
  [2026-08-14]
- **The site's own data files were never in the repository, and a fresh clone
  could neither build the site nor pass its own governance tests.**
  `.gitignore`'s first line was a bare `data/`, which matches a directory of
  that name at *any* depth and so swallowed `web/src/data/site.ts` — the single
  source of truth for every count the site publishes, and the file
  `test_governance_docs.py` reads to check them. Nothing local said so, because
  the maintainer's working copy had it; a clean clone failed six tests with
  `FileNotFoundError`. Anchored to `/data/`, and `/evidence/` with it before it
  cost the same. [2026-08-13]
- **A clone's `/new-project` produced a project with no `build/` directory.**
  The same unanchored-rule class, second instance: `build/` matched
  `project-template/build/`, which is not output but the shipped skeleton
  `/new-project` copies verbatim. `test_first_run.py` already asserted the
  directory exists and passed anyway, because the untracked directory was
  sitting in the working copy the whole time. The marker now ships; its contents
  stay ignored. Two new tests ask the question the rest of the suite never did —
  not "is the file on disk" but "is it in the repository" — since only the
  second is what a user's clone gets. [2026-08-13]
- **`norm_ppf` raised `OverflowError` in the far tail.** The Halley refinement
  step divides by the density, spelled `exp(x²/2)`, which overflows a double
  past |x| ≈ 37.7 — so a *refinement* step failed loudly on inputs Acklam's
  approximation handles perfectly well, and p below ~1e-308 returned no answer
  at all rather than a slightly less refined one. The guard is derived from
  `log(DBL_MAX)` rather than rounded to a tidy 37, which would have silently
  dropped p = 1e-300 to the unrefined path. [2026-08-13]
- **`/verify-citations` no longer instructs an edit the kit blocks.** Its
  fabricated- and retracted-entry branches now route through
  `doi2bib.py --append` and `bib_doctor.py --retract`, name the order (prose
  first, bib second), and say where to record the removed entry. The hook's own
  refusal message names all three verbs, since that message is the only thing a
  blocked user reads. The same skill issued the `write_verify_status.py` command
  twice, in two steps, which is two chances for the spellings to drift.
  [2026-08-13]
- **Turkish and Greek characters were being corrupted on the way into the source
  register.** `registry_db.py add --stdin` decoded through the console codepage,
  so on a default Turkish Windows every title `literature-scout` ingests — that
  agent holds no Write tool, so this is the only path in — was written to
  `sources/registry.jsonl` as mojibake and stayed there, in a file the kit
  deliberately makes read-only. `evidence_db.py` had fixed this for evidence
  cards; both now share one reader, which also accepts the byte-order mark
  PowerShell's `$json | python …` idiom emits. [2026-08-13]
- **Claims written as noun phrases now count as claims.** The claim-strength
  ladder was built from verbs only, so "the effect of X on Y" — the same
  assertion as "X affects Y", and the more common register in formal academic
  prose — was exempt from the overclaim check rather than merely weak. The gap
  was worse in Turkish, where `etkisi`, `nedeni`, `sebebiyle` and
  `kaynaklanmaktadır` carried no strength at all. Meta-analysis vocabulary
  ("effect size", "etki büyüklüğü") and the Turkish privative `etkisiz`, which
  asserts the opposite, are held clear by their own cases. [2026-08-13]

- **Two skills had never been put in front of a router, and the page reporting
  routing accuracy said otherwise.** `disclosures` and `restyle` had no golden
  prompt — 26 of 28 skills covered — while ROUTING-EVAL.md read "full coverage".
  The static check reported uncovered skills without counting them as problems,
  so adding a skill without a prompt broke nothing. Four prompts added (TR + EN
  for each), `--require-full-coverage` makes an uncovered skill exit 2, and two
  tests bind both the flag and the set size stated in the document. The live
  figure is stated as 44 measured of 48, not 48/48: the four new prompts are in
  the set but no fresh agent has scored them yet. [2026-08-13]
- **MEASUREMENT.md's results table said "do not hand-edit this table" and
  nothing enforced it.** In a document whose argument is that every claim should
  be bound to something that fails, the table a reader quotes was maintained by
  hand. Case counts and the positive/negative split are now derived from the
  harness by a test. [2026-08-13]
- **Adding a true positive silently disarmed a mutation.** A new `tr_style` case
  lifted the set's tp from 8 to 9, which raised the precision produced by
  `first-person-exception-list-emptied` from 8/9 = 0.89 to exactly the 0.90
  threshold — the mutation started surviving while nothing was reported and the
  set had only grown. Mutation catching is threshold-based, so a set can lose a
  mutation by gaining a case; a second negative that also dies under it restores
  the margin (9/11 = 0.82). The property is now written down where the next
  person adding a case will read it. [2026-08-13]
- **`pytest` and `pytest-cov` were the only unpinned dev dependencies.** The
  argument for capping tools by major version — a tool that judges this repo
  must not change its judgement without a commit saying so — was written for
  ruff and bandit and applied only to them, leaving the runner the whole suite's
  meaning rests on free to major-bump underneath it. [2026-08-13]
- **Two stray backticks in ordinary prose silently deleted every citation
  between them — a false negative in the check that blocks.** The inline-code
  pattern `` `[^`]*` `` does not exclude newlines, so a threshold written ``5` ``
  and a quoted keystroke three paragraphs later paired up and stripped
  everything in between, including each `[@key]`. Those keys never reached
  `cited`, so `cite_audit.py` never reported them as missing from the
  bibliography and `/verify-citations` passed a manuscript it exists to stop.
  `tr_style_check.py` already used the correct single-line form; `cite_audit`,
  `claim_check`, `consistency_check`, `failure_scan` and `figure_check` did not,
  and now all do. Found by a *surviving mutation* in the new `cite_audit` gold
  set — the precision column was 1.00 before the fix and 1.00 after, which is
  precisely why the mutation column exists. [2026-08-13]
- **The published test count was stale, and nothing checked it.** Both READMEs
  and `web/src/data/site.ts` stated 1213 passing tests; the suite passes 1329.
  Every other number those files publish is re-derived from the repository by
  `tests/test_governance_docs.py` — the test count was the one hand-written
  exception, in the number describing that very suite. It is now derived from a
  real collection run (~3s, collection executes nothing), the published skip
  count is checked against the items collected under `-m live`, and a third test
  fails when `site.ts` changes without a site rebuild, which is how the built
  `docs/` pages quietly served the old figure. Counting collected *items* rather
  than `@pytest.mark.live` occurrences in the source matters: the first version
  grepped and reported 4 where the truth is 8. [2026-08-13]
- **`requirements.txt` broke its own stated pinning policy.** The header says
  major-version caps guard against breaking API bumps, but `pymupdf4llm` shipped
  uncapped while the other five dependencies were capped — and the whole PDF→
  Markdown stage depends on it. Now `>=1.0,<2`. [2026-08-13]
- **`eval/MEASUREMENT.md`'s "Adding a gold set" list numbered two steps `5`.**
  [2026-08-13]
- **`claim_check.py` produced a false uncited-assertion on any sentence citing
  an equation.** `Eq.` was absent from the sentence-splitter protection list
  even though `ARTEFACT_RE` recognises it, so "the threshold is derived in
  Eq. 4 and equals 0.63" split at the abbreviation and the fragment carrying the
  statistic lost the artefact pointer that exempts it. Found by writing a gold
  case for an allowance the mutation harness had flagged as unheld. `Sec.`,
  `Alg.` and `Tbl.` had the same gap. [2026-08-13]
- **The own-work allowance was weaker in Turkish than in English.**
  `ARTEFACT_RE` accepted the English abbreviation `Fig.` but none of the Turkish
  ones a Turkish author actually writes — `Şek.`, `Denk.`, `Böl.`, `Tbl.` — so
  "Şek. 2 uyarınca eşik 0,63'tür" was reported as an uncited assertion while its
  English equivalent was not. In a kit whose central claim is that the two
  languages are equal targets, that is the asymmetry that matters most.
  [2026-08-13]
- **Two shipped gold sets were holding less than their perfect scores suggested.**
  `claim_strength` covered the artefact-pointer allowance with one case, so
  deleting the allowance outright dropped precision only to 0.90 — exactly the
  threshold — and the suite still passed. `failure_modes` covered zero-variance
  with one case, leaving recall at 0.92 with the detector gone. Both now carry
  the cases that hold them. [2026-08-13]

- **The hook count was wrong in three places: 7 claimed, 6 real.** Both READMEs
  and the live site said "7 hooks"; `settings.json` registers six. The number
  counted *files* in `.claude/hooks/`, which also holds the underscore-prefixed
  shared libraries (`_shell_write_sink`, `_project_scope`, and now `_degrade`)
  that no event ever invokes. Corrected in `README.md`, `README.en.md`,
  `web/src/data/site.ts` and the rebuilt site, and pinned by test so it cannot
  drift again. [2026-08-13]
- **`protect_data_files.py` evaluated its check unguarded**, so an unexpected
  error there exited on a traceback rather than through the same reported
  fail-open path the other three gates use. Same contract as theirs now.
  [2026-08-13]

- **`turkish-academic.md` taught a TDK violation.** Its units row gave `"95 %"`
  as correct and `"95%"` as wrong; TDK places the percent sign **before** the
  number with no space (`%95`). Split into separate percent and unit rows —
  the reference and the new checker now agree. [2026-08-12]

- **`/journal-check` stated acceptance rates from nowhere** ("Q1 ~10–15%, Q2
  ~20–30%, Q3–Q4 ~40%+"). Those numbers had no source, and quartile measures
  citation impact, not selectivity — so the inference was wrong on top of being
  unsourced. Replaced with an instruction to read the journal's own published
  figures and to say plainly when it publishes none. [2026-08-12]

- **`pdf2md.py --key` drive-letter check was POSIX-inert.** The existing
  containment check resolved `out_dir / key` and compared it against `out_dir`
  — correct on Windows, where WindowsPath's `/` operator drops everything left
  of a drive-rooted right operand (`out_dir / "C:evil"` → `"C:\evil"`, escaping
  `sources/md/`). On POSIX, `/` has no such special case (a colon is an
  ordinary filename character), so the same key resolves harmlessly inside
  `out_dir` and the check correctly let it through — but a bib key is project
  data that can be committed and reopened on a different OS than the one that
  created it, so a key inert on macOS/Linux today must not become a live
  escape the day the project is opened on Windows. Added an explicit,
  OS-independent regex rejection of any `^[A-Za-z]:` key prefix, checked
  before the resolve-based containment check.
- **`test_latex_build_windows_backslash_outdir_not_mangled` was Windows-only
  by construction, not by CI configuration.** It derived a "Windows absolute
  path" by replacing `/` with `\` in the host's own `tmp_path` — a no-op on
  Windows (WindowsPath already prints backslash-separated, so the result is a
  genuine `C:\...` string) but on POSIX `tmp_path` starts with `/` and has no
  drive letter, so the same replacement produces a bare-backslash string
  (`\tmp\...`) that isn't drive-absolute at all. `latex_build.sh`'s own
  case-pattern logic was correctly falling through to the relative branch for
  that non-absolute-looking string; the test's premise, not the script, was
  wrong on non-Windows hosts. Skipped on `os.name != "nt"` — the
  forward-slash variant already covers the cross-platform-safe form of this
  regression.
- **Write-sink deletion bypass (hook layer).** `_shell_write_sink.py` now models
  `find … -delete` / `-exec rm|unlink|shred {}`, `… | xargs rm`, and
  `gio trash`/`trash-put` — three standard deletion idioms (not obfuscation) that
  previously deleted a script-owned file (`registry.jsonl`, `cards.jsonl`, …) with
  every gate active, because `-exec rm {}` binds the literal `{}` rather than the
  file and no `find`/`xargs`/`gio` verb was modeled. A read-only `find … -name
  '*.md'` and a path-less `echo hello | xargs rm` stay allowed. Regression tests
  added.
- **Unquoted Windows backslash paths, `install`, and .NET file APIs** now caught by
  the same write-sink matcher (`del sources\registry.jsonl`, `install -m644 evil
  sources/registry.jsonl`, `[IO.File]::Create/OpenWrite`, `[IO.StreamWriter]::new`).
- **`venue_check.py`** no longer raises an uncaught `TypeError` on a corrupt cache
  row with `"checked_at": null`.
- **`doi2bib.py --append`** dedup now normalizes DOIs via `clean_doi()` so a
  URL-prefixed and a bare form of the same DOI are recognized as duplicates.
- **`xlsx_export.py`** dropped redundant in-function re-imports of `json`/`Path`.
- **`skill_routing_eval.py`** subprocess call gained a 60s timeout;
  **`extract_skill_descriptions.py`** now guards each SKILL.md read so one
  malformed file can't abort the catalog dump.
- **`validate_kit.py`** now asserts the full enforcement/UX hook set is actually
  wired to its event in `settings.json` (`protect_data_files`, `phase_gate`,
  `agent_write_scope`, `template_supremacy_gate` → PreToolUse; `cite_warn` →
  PostToolUse; `session_status` → SessionStart). Previously it only checked that
  a *referenced* hook file existed, so silently dropping or misrouting a hook
  entry disabled data-file protection / phase gating with no other signal — the
  "enforcement depends on hooks being wired" gap flagged by the audit. Regression
  tests added.

- **Phase gate hard-blocked `/export-excel`, `/slr`'s Excel stage, and
  `/ingest-template` at the moment they run (C1).** `phase_gate.py` classified
  `xlsx_export.py` (the literature/screening/synthesis matrix) and
  `make_reference_docx.py` (the reference-doc STYLE template, built once at
  ingest-template setup) as build scripts, so both were denied unless
  `verify-status.json` = PASS **and** the latest review had 0 Major issues — but
  all three commands legitimately run in the literature/setup phase, before any
  draft, citation verification, or critique exists. `BUILD_SCRIPTS` now holds
  only the manuscript builders (`latex_build.sh`, `docx_build.sh`); the
  `exports/` path gate carves out the literature spreadsheet types (`.xlsx`/
  `.xls`/`.csv`) while still gating manuscript renders (`.docx`/`.pdf`/…). Tests
  that had enshrined the wrong behavior were corrected.
- **`pip install <pkg>` mis-read as a file write (M1).** `install` was folded
  into the write-sink's cp/mv verb list under a whitespace-permissive anchor, so
  it also fired on the second word of `pip/npm/apt install <pkg>`, capturing the
  package name as a bogus write target — a live false-positive DENY of ordinary
  package installs by scoped agents. A dedicated command-position-anchored
  pattern leaves package managers alone while still catching real coreutils
  `install … sources/registry.jsonl`.
- **Redirect/`open()` detection is now quote-aware.** A write-sink whose
  operator/verb anchor sits INSIDE a quoted argument (`git commit -m "note >
  drafts/x.md"`) is data, not an executed sink, and no longer gates. Quoted
  TARGETS after a genuine operator (`> "drafts/my draft.md"`) and real sinks
  inside nested-shell wrappers (re-scanned by `_unwrap`) still detect;
  unbalanced quotes fail closed (no filtering).
- **Read-only agents could smuggle a write via a script's `--out` flag.**
  `agent_write_scope.py` saw only shell write-sink syntax, never a sanctioned
  script's internal write; an empty-scope agent (`citation-verifier`,
  `literature-scout`, `qa-auditor`) could therefore run `xlsx_export.py --out
  <path>`. The `--out`/`--output`/`--out-dir` destination of a `scripts/…`
  invocation is now scope-checked for those agents. Writer agents keep their
  documented in-scope `--out` flows.
- **`write_verify_status.py`** now rejects negative counts on the FAIL path too
  (only the PASS path validated signs before). **`skill_routing_eval.py`** guards
  the path it actually reads (`ROOT/--prompts`) instead of a cwd-resolved one, so
  the validated and read targets can't diverge. **`validate_kit.py`** matches the
  whole interpreter token (`python3.11`, not a truncated `python3`). **`lib_common`**
  atomic-write temp files are now keyed on thread id as well as pid.

### Added — the half of an academic's job that starts when the manuscript ends

- **`/submission-pack` + `scripts/submission_pack.py` — the second document
  nobody talks about.** Title length, abstract words, keyword count, highlights
  (3-5 bullets, ≤85 characters each), five declarations, a cover letter,
  suggested reviewers: every one has a limit the venue publishes and an editorial
  assistant checks before a reviewer ever sees the paper. All of it is arithmetic
  and none of it existed here. The limits come from a file the author fills from
  the venue's **own** author guidelines with the URL they read them at — the kit
  will not recall "Elsevier abstracts are 250 words", because a remembered limit
  is the same error class as a remembered DOI and causes exactly the desk
  rejection this prevents. With no limits file the result is `UNCHECKED`, not
  `OK`: "nothing was checked" and "no problems" must not read the same.
  Suggested reviewers are derived from the project's own reference list, and no
  e-mail address is ever invented. [2026-08-14]

- **`/respond-review` + `scripts/review_letter.py` — the letter a journal
  actually sent.** `/critique` simulated a review and `/revise` worked through
  its findings; the document an author receives — an editor's decision with three
  reviewers and forty numbered comments — had no entry point at all. The letter is
  parsed into structured comments (numbering restarts per reviewer, so the ids are
  `Reviewer 2.3`), each is classified as do / do differently / cannot / disagree
  **before** any edit, and the response letter's coverage is then checked
  mechanically: every comment answered, and none answered that the letter never
  made. Matching is on numbers, never on wording — a paragraph that echoes a
  reviewer's phrasing is not an answer from the editor's side either. A letter
  with no numbering is reported as one comment rather than split into invented
  ones, and whether an answer is *adequate* is explicitly not judged. [2026-08-14]

- **`/replication-package` + `scripts/replication_pack.py`, and a derived
  availability statement.** The package is assembled from the two registers: code,
  figures, tables, `runs.jsonl`, `datasets.jsonl`, an environment file, a SHA-256
  manifest, and a README generated from the records — including a "what this
  package does not establish" section when there are gaps. Data whose record says
  human subjects, personal data or a restrictive licence is **never copied**; it
  is named with its access route, because a package is public the moment it is
  deposited and a DOI makes a data-protection incident permanent.
  `compliance_gen.py availability` writes the data/code statement from the same
  registers and writes **no sentence** for a dataset with no citation DOI or no
  recorded licence — "available from the corresponding author on reasonable
  request" is the sentence most often found to be untrue after publication.
  [2026-08-14]

- **`/preregister` — the plan, before the results.** Directional hypotheses, the
  design, the sampling and stopping rule, the analysis plan, what would falsify
  it, and which analyses are exploratory — attested through the hash-chained
  ledger. If runs already exist, the command says so and refuses to call the
  document a preregistration. The limit is stated every time: the chain shows the
  file was not rewritten, not that it was written before the data; for that, OSF
  or AsPredicted, where the timestamp is a third party's. [2026-08-14]

- **`/front-matter` + `scripts/frontmatter_check.py` — the pages the institute
  checks first.** A thesis is turned back at the formal check far more often than
  at the defence, and almost never for its science: a missing ethics declaration,
  an approval page in the wrong position, a contents entry for a renamed chapter,
  a list of figures that stops at 11 while the body has 14. The kit knew the YÖK
  order; nothing checked a document against it. Presence, order, Özet↔Abstract
  keyword parity, contents against the body's real headings, and the lists against
  its real figures — with `--order` so an institute's own guideline wins over the
  kit's default. [2026-08-14]

- **`/retarget` — the same work, a different venue.** After a rejection: the new
  venue's index profile and predatory flag (checked precisely when an author is
  most willing to overlook it), the word budget, the citation style, the template,
  the regenerated cover letter, and the previous reviewers' comments carried
  forward and classified — the cheapest peer review the paper will ever get.
  [2026-08-14]

- **`/present` — what the paper becomes afterwards.** A conference talk with its
  slide plan and timing, a poster laid out for reading distance, a plain-language
  summary, and a graphical-abstract brief. Every number comes from the
  manuscript's own evidence and run records, and the report names any figure on a
  slide that `experiment_db.py trace` cannot find a run behind. [2026-08-14]

- **`scripts/overlap_check.py` — text recycling against your own earlier work.**
  Offline, only against files the author names, reporting **locations and never a
  percentage**: POSITIONING.md refuses a similarity score and this does not
  smuggle one in. A test asserts no field in the payload is a ratio, and the
  payload itself says it is not a plagiarism check and does not replace the
  institution's tool. Wired into `/submit-check`'s advisories, where "no earlier
  work named" is reported as SKIPPED rather than as "no overlap". [2026-08-14]

### Added — the empirical half, phase A: where the data comes from

- **`/find-dataset` + `dataset-scout` + `scripts/dataset_db.py` — the data an
  analysis ran on is now part of the chain.** Every claim from the literature
  bound to a fetched record and every claim from an analysis to an evidence card;
  the data underneath had no binding at all. A file appeared under `analysis/` and
  "we used the CWRU bearing dataset" rested on nothing — no version, no licence,
  no citation, and no way to tell later whether the bytes that produced the
  numbers are the bytes still on disk. The register answers the four questions a
  methods section has to answer anyway: where it came from, whether you may use
  it, how to cite it (DOI → `doi2bib.py`, the same authoritative path as any
  paper), and what exactly ran (per-file SHA-256, so `verify` separates changed
  bytes from a missing file from an incomplete record). It refuses to guess a
  licence — one that was not read is `unknown`, which is not permission — to state
  a row count it did not measure, or to judge whether an ethics arrangement is
  sound. `dataset-scout` searches the hosts, Turkish open data, and the datasets
  the project's own registry already cites, reading each candidate's own licence
  page rather than recalling it. [2026-08-14]

- **`/collect-data` + `scripts/collection_check.py` — collecting it yourself,
  with a protocol.** When no suitable dataset exists, the failure mode stops being
  a wrong number and becomes a wrong act: data taken from a site that forbids it,
  personal data carried into a repository, human subjects with no ethics approval.
  Three of those questions have deterministic answers and the script answers
  exactly those: does the site's own robots.txt allow that path for that agent,
  does the collected file contain personal data and in which column, and which
  sections the written protocol does not state (ten of them, EN+TR). It rules on
  none of them — robots.txt is a request, not the law and not the Terms of
  Service; a complete protocol is not an approved protocol. The PII scan reports
  counts and column names and **never the matched values**, because a scanner that
  echoes what it found has copied that data into a terminal, a log and a
  transcript. The kit runs no scraper and collects no survey responses: a tool
  that scrapes on request has made the decision that the scrape is permissible,
  and that decision is the author's, is site-specific, and for human subjects is
  an institution's. [2026-08-14]

### Added — phases B and C: which run produced the number, and whether the split was honest

- **`/experiment` + `scripts/experiment_db.py` + `scripts/env_capture.py` — a run
  record, so a results table stops being a transcription.** "The model reached
  0.94" is the sentence an empirical paper is built on, and nothing here could
  answer the three questions a reviewer asks about it: which run, which seed,
  which data. There is now one line per run carrying the dataset id (checked
  against the dataset register, not merely stated), the seed, the configuration
  and its hash, the metrics, and a fingerprint of the environment — Python,
  platform and package versions, captured rather than recalled, because "we used
  scikit-learn 1.5" written three months later is wrong about as often as it is
  right. `summary` derives the results table with mean, std, min, max and the
  seeds behind each group; `trace 0.809` answers where a number in the manuscript
  came from, and exits 2 when the answer is nowhere. It refuses a run with no seed
  (not defaulted — refused), a run pointing at unregistered data, and any `--best`
  flag: which mean is larger is not the question a paper answers, and the paired
  test that answers the real one already runs by default. Losing runs are recorded
  too, so a search over 40 settings cannot quietly become "we used lr=0.01".
  [2026-08-14]

- **`scripts/leakage_check.py` — the four leaks that are arithmetic.** A leak does
  not look like an error; it looks like a good result. Over the split manifest the
  analysis writes while it splits: the same id in train and test, the same
  subject/patient/session on both sides, byte-identical rows under different ids,
  and a column that maps one-to-one onto the target. Wired into `/experiment`
  **before** any metric is presented and into `/submit-check`'s advisories. Its
  limit is in its own output and in a test named after it: preprocessing fitted
  outside the fold — the second most common leak in applied ML — leaves no trace
  in a split, so it is reported from the manifest's *declaration* and never
  detected. A CLEAN result is a statement about four leaks, not about the
  experiment's validity. [2026-08-14]

- **`analysis/runs.jsonl` is the ninth script-owned, read-only data file** (config
  hashes are a tamper check, and a tamper check anyone can rewrite checks nothing),
  and `data-scientist`'s contract now requires both the run records and the split
  manifest rather than a prose RUNLOG alone. [2026-08-14]

- **`analysis/datasets.jsonl` is the eighth script-owned, read-only data file**,
  with `dataset_db.py` as its only sanctioned writer — a recorded checksum that is
  as easy to edit as the file it describes reports nothing. `PROJECT.md` gains
  *Data origin* and *Ethics approval* fields, and `project-template/analysis/data/`
  ships so a new project has somewhere to put the data. `SECURITY.md` now states
  the one script whose destination is not fixed in advance: `--robots` fetches
  `/robots.txt` from the host **you** name and nothing else. [2026-08-14]

## 0.3.0 — 2026-08-14

### Added

- **`/import-library` — the library you already have, without the claims it
  carries.** Every prospective user arrives with a Zotero collection, a Mendeley
  folder or the `.bib` an earlier paper was written from, and the only way in was
  `registry_db.py add`, one record at a time: a researcher with 200 references met
  the kit as a data-entry task. `library_import.py` reads BibTeX and RIS and
  treats the export as exactly two things — a list of DOIs, each re-fetched from
  the authoritative record by `doi2bib.py`, and a screening worksheet whose
  unverified metadata lands in the register, where nothing cites it. Not one
  field of the file reaches `references.bib`; an entry with no DOI is registered
  as a candidate and reported, never written to the bib. The script writes
  neither data file itself — both go through their sanctioned writers, so
  Invariant 6 does not acquire a third exception, and a test asserts that by
  name. `--plan` looks without writing (a 400-record import is tedious to undo),
  and `--resolve` finishes an offline import from the register instead of
  re-running it, which would have marked the whole library `duplicate`. Turkish
  names survive: BibTeX escapes are decoded by Unicode composition, because a
  name nobody can search for is a record nobody finds. [2026-08-14]

- **`review_stability.py` — the reviewer's stability, computed rather than
  narrated.** `/critique --calibrate` already ran `reviewer-critic` three times;
  the comparison was then performed by the orchestrating model reading its own
  three reports, which is not a measurement of that model. The script parses the
  report format `/critique` already writes and reports decision agreement, the
  Major-issue count range and which sections the runs disagree about — sharing
  `draft_stability.py`'s intersection-over-union rule rather than reimplementing
  it. Same limit, stated in the payload: a consistently wrong reviewer scores
  1.00. [2026-08-14]

- **A blinded screening worksheet (`screening_score.py --sample`).**
  `eval/screening/README.md` asked the labeller not to look at the kit's decision
  first — the one instruction a document cannot enforce, protecting against a
  large and well-documented effect in dual screening. `--sample N` now draws a
  random worksheet carrying id, title, year and venue and *not* the decision, its
  reason or its stage; `--from-worksheet` turns the filled sheet back into the
  gold JSONL. Blank rows are skipped and reported rather than read as exclusions,
  an unreadable label is refused rather than guessed, an existing worksheet is
  never overwritten without `--force`, and the seed is printed so the same sample
  can be regenerated instead of quietly redrawn. The CSV carries a BOM, so
  Turkish titles survive Excel. [2026-08-14]

- **`provenance.py` — an append-only, hash-chained record of what was attested,
  when.** All three gates are file-based: the session that must pass a gate can
  write the file the gate reads, and no secret exists that it cannot also read,
  so prevention is architecturally out of reach. Evidence is not. Every
  attestation is now a line carrying the SHA-256 of the artifact and the hash of
  the record before it, so rewriting history breaks the chain (`--verify` names
  the record), while an artifact edited after attestation is reported separately
  as drift — tampering and ordinary revision are different findings. The ledger
  is the seventh script-owned, read-only data file. The outline gate now binds
  approval to the approved bytes instead of to a hand-typed timestamp, which was
  wrong in both directions. Stated in the header, on the tools page and in two
  tests named after it: the chain proves a record was **not rewritten**, never
  that it was **earned**. See DECISIONS.md D-093a. [2026-08-14]

- **`draft_stability.py` — the drafting stage, measured without a gold set.**
  Accuracy needs labels and the kit still refuses to invent them; stability does
  not. Across N independent renderings of one section from one evidence set, it
  scores agreement on the three things that have no honest reason to vary —
  cited sources, reported quantities, claim strength per source — reusing the
  existing extractors. Prose is never compared; years and decimal separators are
  deliberately excluded from the numeric comparison. `eval/MEASUREMENT.md`'s
  "not measured" row now covers synthesis and the style audit only. The limit
  travels with the number: a stage that is consistently wrong scores 1.00. See
  DECISIONS.md D-093b. [2026-08-14]

- **The format gate now says when the PASS it is opening on was never
  corroborated.** `verify_passed()` could only ever ask whether
  `verify-status.json` is internally self-consistent, which a hand-authored file
  satisfies trivially — while `write_verify_status.py`, the sanctioned writer,
  had already re-run `doi2bib.py --verify` and `cite_audit.py` against the files
  on disk and recorded the outcome in a `live_recheck` block the gate never
  read. At the moment a build or export is authorised, a missing or unconfirmed
  block is now reported. Advisory, not blocking (three things gate; a fourth is
  a scope decision) — an offline run and a fresh project both degrade here
  legitimately, which is why the writer only warns about the same condition. What
  changed is where it lands: on the artifact, instead of once at write time
  hundreds of turns earlier. Silent for a corroborated PASS, outside the format
  gate, and whenever the gate is already denying. See DECISIONS.md D-092c.
  [2026-08-14]

- **`screening_score.py` — the first measurement of an LLM-mediated decision
  other than the reviewer's.** Screening was chosen ahead of drafting and
  synthesis for a reason that is not convenience: a study wrongly excluded at
  title/abstract never reaches full text, never becomes an evidence card, and
  never appears in any downstream report, so `cite_audit`, `evidence_funnel` and
  `qa-auditor` — all of which examine what survived — are structurally blind to
  it. The script scores the kit's include/exclude calls against labels **you**
  produce, and reports recall, precision and Cohen's κ. It never reports
  accuracy: at a realistic 5–10% inclusion rate, excluding everything scores
  90–95% while finding nothing. It reports no rates at all below 20 scored
  records, reports an undefined κ as `null` rather than 0, lists the missed
  includes by name, and refuses a decisions file that carries the labels. No
  gold set ships — one written by the model whose decisions it scores measures
  agreement with itself. See `eval/screening/README.md`. [2026-08-14]
- **`.zenodo.json`, so the archived release is credited to a person.** Zenodo's
  GitHub integration reads it when a release is archived and what it says
  becomes the citation other people copy; without it the record carries a
  GitHub username and the repository blurb. Title, licence, author and keywords
  are held equal to `CITATION.cff` by a test. It deliberately declares no
  `version` (the git tag is the source of truth) and no `doi` (minted, not
  written) — the DOI field in `CITATION.cff` stays empty until an archive
  actually exists, and the test that enforces that is unchanged. [2026-08-14]
- **`template_compliance.py` — the half of TEMPLATE SUPREMACY that was never
  mechanical.** `template-profile.md` is written in prose, so no build could be
  compared against it: the PreToolUse gate only caught a build that ignored the
  registered template outright, and `docx_style_check.py` compares a build
  against the reference doc it was rendered with, which can itself be wrong.
  `/ingest-template` now appends a machine-readable ```json template-rules block
  (margins, page size, body and heading font/size, line spacing, caption style,
  LaTeX class and required packages), and both build scripts check the built
  document against it as a non-fatal WARN. Three outcomes, and the third is the
  point: a rule that is `null` in the profile, or that the document never states,
  is reported **unchecked** and never folded into the pass count — a profile with
  no block at all reports **unbound**. `null` is mandatory for anything the
  analyzer could not determine; a fabricated rule would be checked against the
  build and reported as compliance with something the venue never required.
  [2026-08-14]

- **`bib_doctor.py --retract <key>` — the sanctioned way to remove a
  bibliography entry, which the kit did not have.** `references.bib` is
  script-owned and both of its writers could only ever grow it, so the one
  workflow that most needs removal — a citation `/verify-citations` has just
  identified as fabricated or retracted — dead-ended: the skill told the user to
  "update manually in `bib/references.bib`", `protect_data_files.py` refused the
  edit, and the refusal message named two commands that cannot delete anything.
  `--retract` refuses while the key is still cited in `drafts/` (removing only
  the bib half turns a *wrong* citation into a *missing* one, which
  `cite_audit.py` then blocks a stage later, further from the decision that
  caused it), `--force` allows the reverse order and records that it was used,
  and the deleted entry comes back in the JSON as `removed_bibtex` — the bib
  file keeps no history, so that field is the only surviving record of what the
  entry said. [2026-08-13]

- **Coverage now measures the subprocesses the suite actually runs — 59% → 92%,
  and it was 92% all along.** Most tests drive the scripts as CLIs, and coverage
  started in the pytest process cannot see into a child, so the collector was
  reporting what the tests imported rather than what they exercised
  (`skill_routing_eval.py` read 0% while a dozen tests ran it end to end). CI's
  comment explained that gap at length instead of closing it. `.coveragerc` plus
  `COVERAGE_PROCESS_START` closes it: every child starts its own collector,
  writes its own data file, and the parent combines them — including the
  first-run suite's copy of the kit, remapped onto the real files rather than
  reported as a second set. The floor moves 55 → 85, still well below the
  reading, because a floor set at the current number is a target in disguise.
  [2026-08-13]
- **Four adversarial gold cases became seventeen, and one of them argued with
  the checker.** Cases written to *break* `claim_check` and `tr_style_check`
  rather than demonstrate them. A doubly hedged Turkish sentence
  ("azaltabileceğini düşündürmektedir") over an associative card was labelled
  clean and fired anyway — the checker was right and the label was wrong, since
  attributing a direction to a source that reported a correlation is an
  overclaim however softly it is put. It ships as a positive with its English
  twin and three negatives pinning the boundary from below. The bilingual probes
  passed: a thesis page holding Turkish decimals beside English ones, and a
  Turkish impersonal body beside a first-person English abstract, are both
  correct and neither fired. [2026-08-13]
- **A plugin install now says when it has no enforcement layer.** Installing the
  plugin and skipping `/new-project` gives the guidance without the guarantees;
  that was documented in three places and signalled in none.
  `.claude/hooks/enforcement_notice.py`, wired through the plugin's own
  `.claude-plugin/hooks.json`, prints **ENFORCEMENT ABSENT** at session start
  when a directory has a `PROJECT.md` but no `scripts/` or `.claude/hooks/`,
  and names the specific guarantees not in force (citation gate, phase gates,
  script-ownership of the registry). Silent everywhere else — a notice that also
  fired in unrelated repositories would be trained away within a day. It warns
  rather than blocks: an author mid-paper may proceed, as long as nobody is
  telling them their citations are gated when they are not. [2026-08-13]
- **`ruff.toml`, with the criterion for what a linter is allowed to say.**
  Enabled if violating it can indicate a defect, disabled if it can only
  indicate a taste — so `E501` (872 standing violations), `E402`, `E702`,
  `E731` and `E741` are off, each with its reason written beside it and a test
  that fails if a future entry arrives without one. There is deliberately no
  formatter step: reflowing these docstrings would bury the review history they
  carry. [2026-08-13]
- **A twelve-file reading order at the top of `CONTRIBUTING.md`.** The set that
  actually carries the design, so a second contributor does not have to infer it
  from 333 files. [2026-08-13]
- **Coverage as a CI regression floor — measured, deliberately unpublished.** It
  reads 59%, and that number is mostly an artifact of the suite driving the
  scripts as subprocesses the collector cannot see (`registry_db.py` reads 17%
  while being among the most exercised modules here). Publishing it beside the
  test count would be publishing a measurement of the instrument, so a test
  fails the build if a README ever states a coverage percentage — the same
  refusal `docs/PERFORMANCE.md` makes about per-command cost. [2026-08-13]

- **`.gitignore` fix: `*.lock` swallowed dependency lockfiles.** The pattern
  exists for `file_lock()`'s `<path>.lock` sidecars; it also silently ignored
  `uv.lock`, `poetry.lock` and `Cargo.lock`, which a repository is supposed to
  commit. Narrowed to the three extensions the kit actually locks. [2026-08-13]

- **Gold-set coverage extended to the zero-fabrication spine: three new sets,
  nine total.** `cite_audit` (13 cases) measures the in-text/bibliography
  cross-diff the citation gate is built on; `bib_doctor` (13) measures
  bibliography hygiene — DOI syntax, duplicate detection, required fields per
  entry type, the `verified={true}` stamp; `evidence_funnel` (10) measures the
  judgement that actually matters there, orphan card versus expected-uncited
  (own-result cards and cards from an excluded source are uncited *by design*).
  The measured surface is now 152 cases, 68 positive / 84 negative, 43 declared
  mutations, all caught. `cite_audit.py` grew a `check()` function so the harness
  can call it the way it calls the others — main() keeps every argument and
  exit-code decision. `word_budget.py` stays uncovered (it reports arithmetic,
  not judgements) and `citation_triangulate.py` deliberately so: it queries a
  live index, and a gold set scored against a network response measures the
  network. [2026-08-13]
- **`tests/README.md` — a subject index for the test suite, bound to the suite
  it describes.** Most test files are named after the module they exercise, but
  the regression suites are named after the review round that produced them, and
  each round genuinely spans several subsystems — so "which tests protect the
  phase gate?" was a grep, not a lookup. `tests/conftest.py::AREAS` now declares
  the mapping once (`hooks`, `citation`, `build`, `export`, `lint`, `kitmeta`,
  `corelib`, `pipeline`) and turns it into real pytest markers, so
  `python -m pytest -m hooks` selects all 504 enforcement-layer tests across
  every file that holds them. Renaming or splitting those files was considered
  and rejected: `DECISIONS.md` cites them by name from the entry explaining why
  each test exists, and a subject name on a multi-subject file would misdescribe
  it. `tests/test_tests_index.py` fails the build if a test file joins the suite
  without joining the map, if the map names a file that no longer exists, if an
  area is undocumented, or if a date-named file appears outside the review-round
  convention. [2026-08-13]
- **Every hook module's docstring now anchors its own change history.** The hook
  layer carries long "an earlier version of this hook…" narratives, and they stay
  at the point of use deliberately — each names a bypass that actually shipped.
  The defect was that they were unanchored: the same history also lives in
  `DECISIONS.md` and `CHANGELOG.md`, with nothing tying the copies together, so a
  reader could not tell which was authoritative. Each of the nine hook modules
  now carries a `Change record:` section naming its `D-0xx` entries (or stating
  that it postdates the log) and the tests that lock the behaviour.
  `tests/test_hook_change_records.py` enforces the section's presence, that it
  cites a real authority, that the test files it names exist, and that no cited
  `D-` entry is invented. [2026-08-13]

- **Mutation checking — the gold sets are now measured too.** Precision and
  recall answer "does the checker do what its author meant?" They cannot answer
  "would these cases notice if it stopped?", and a negative case that stays
  silent however the code is broken scores exactly like one that measures
  something. Every manifest now declares named, source-level `mutations` of its
  own checker; `run_evals.py --mutate` applies each and confirms the set drops
  below threshold. Substitution against the real source rather than
  monkeypatching, so a mutation whose anchor was refactored away dies loudly
  instead of silently testing nothing. `tests/test_run_evals.py` requires every
  gold set to declare mutations, requires each to state in prose what it breaks,
  and fails the build if any survives — so it rides into CI on the ordinary
  pytest run. 27 mutations, all caught. [2026-08-13]
- **Two more gold sets: `consistency` (12 cases) and `figures` (14).** Both are
  WARN-only lints wired into `/submit-check` and both were unmeasured.
  Deterministic-checker coverage is now six checkers, 116 cases, 49 positive /
  67 negative. [2026-08-13]

- **Two new gold sets, doubling the measured surface of the checker layer.**
  `eval/gold/temporal/` (14 cases, 5 positive / 9 negative) covers
  `temporal_check.py`: future-dated bibliography years, `fetched_at` timestamps
  that predate their own publication year, and evidence cards attributing a
  later year's development to an earlier source. Every case pins `today`, so the
  set measures the checker rather than the calendar. `eval/gold/tr_style/` (20
  cases, 8 / 12) covers `tr_style_check.py`, the kit's most involved
  deterministic checker and previously the largest unmeasured one — including
  the near-misses that matter: the section number that looks like a decimal, the
  first-mention English parenthetical, the noun ending in -tık. Both run under
  `run_evals.py` and gate CI like the existing two. [2026-08-13]
- **Gold sets are now mutation-checked before acceptance.** A negative case that
  would stay silent however the checker were broken measures nothing while
  looking like it does. Nine deliberate mutations were run against the two new
  sets; the one that went unnoticed exposed a real hole in case `107`, which
  used a single `artık` and sat under the voice-mixing floor either way. Method
  and the finding are recorded in `eval/MEASUREMENT.md`. [2026-08-13]
- **`.claude/hooks/_degrade.py` — the hook layer's fail-open is now visible.**
  Every gate still fails OPEN, unchanged and deliberate. What changed is that it
  no longer fails *silently*: exit 0 with no output was byte-identical to
  "checked, nothing to gate", so a broken gate could not be told apart from a
  passing one. A gate that cannot evaluate itself now emits a
  `⚠ Scholar-Kit gate degraded` notice naming the gate and stating the call was
  allowed. The notice carries the exception's type and origin only — never
  `str(exc)`, never any part of the tool input, because a hook sees draft prose
  and shell commands. Wired into all four gates (`phase_gate`,
  `protect_data_files`, `agent_write_scope`, `template_supremacy_gate`); an
  empty stdin payload stays silent by design. [2026-08-13]
- **Documentation inventory claims are bound to the artifacts they describe.**
  `test_governance_docs.py` now derives the hook count from `settings.json`, the
  agent count from `.claude/agents/` (cross-checked against `plugin.json`'s
  hand-maintained list), and the skill split from `.claude/skills/` — the same
  treatment the tool count already had. Also asserts every registered hook file
  exists and is not an underscore-prefixed library. [2026-08-13]

- **`meta_analysis.py` — quantitative synthesis for `/slr`.** Fixed- and
  random-effects pooling (DerSimonian–Laird), per-study effects with CIs and both
  weightings, Q / I² / tau² / H², a prediction interval (Higgins et al. 2009),
  Egger's test, and an ASCII forest plot — for six measures (log OR, log RR, RD,
  MD, Hedges' g, precomputed inverse-variance). Formula provenance is stated in
  the docstring for every quantity where published variants differ, because a
  silent choice between them is not reproducible.
  The honesty layer is the point, not an afterthought: the script **refuses to
  judge whether pooling is appropriate** and says so — that is a design question
  for `methodology-advisor`, answered *before* running it, and I² explicitly does
  not answer it. Both models are always reported, with a caveat forbidding the
  choice from being made after seeing the p-values. Egger is **not run** below 10
  studies (Sterne et al. 2011) and names the reason rather than returning a
  meaningless null. Continuity corrections for zero cells are applied
  transparently and reported per study, since they bias toward the null. Studies
  with zero events in both arms are refused for ratio measures — no information
  about a ratio exists in them — rather than silently corrected into a number.
- **`lib_stats.py`** — the normal / chi-square / Student's t functions, in pure
  Python. SciPy would be a ~90 MB compiled dependency added so one script can
  call three CDFs, and would break installation wherever a wheel is missing.
  26 tests validate these against **analytic identities** (chi²(2) = exp(−x/2),
  t(1) = Cauchy, chi²(1) = 2·Φ̄(√x), inverse-CDF round trips) rather than
  remembered table values — a wrong table value can agree with wrong code; an
  identity cannot.
- **`/slr` stage 6b** wires it in, gated on a methodology judgement rather than a
  statistic, with the interpretation limits written out for the manuscript.
  53 tests in `tests/test_meta_analysis.py`, every numeric expectation either
  hand-computed from the cited formula or exact by construction (a planted
  funnel asymmetry `yi = θ + b·se` must return intercept exactly `b`).
- **`venue_fit.py` — target-venue shortlist derived from the project's own
  reference list.** Where the literature you cite gets published is the most
  defensible venue signal a project already owns: measured from the registry,
  needing no external ranking, impossible to fabricate. The script groups
  `included` sources by venue (conference-proceedings prefixes folded, so
  "Proceedings of the X" and "X" are one venue), enriches each group from
  `venue_meta` or the `venue_check.py` cache without fetching anything, and
  ranks by a plain **count** — never a composite score, whose weights would be
  hidden exactly where `POSITIONING.md` refuses them. The output states in both
  directions what it measures (topical proximity) and what it does not
  (acceptance probability, journal quality, a submission recommendation).
  Venues with no cached metadata are reported `unknown` with the resolving
  command, never as "nothing found" — and never raise a concern, so missing data
  cannot become a finding. Every similarity-threshold merge is reported, since a
  wrong merge moves sources between tallies and the tally is the whole output.
  It also runs the distribution backwards: sources **you cite** that sit in
  predatory-flagged or wholly unindexed venues, which is the half nobody asks
  for and the more actionable one. 32 tests in `tests/test_venue_fit.py`.
- **`/journal-check --fit`** — Mode B of the existing skill, with explicit
  instructions not to invent journals the registry does not support and not to
  silently correct a reported merge.

- **English POSITIONING (`POSITIONING.en.md`)**, with both READMEs and both
  positioning documents cross-linked. The English README's scope link previously
  landed an English reader on a Turkish document — at the one place where scope
  boundaries matter most. Four tests pin it: the honest failure-shape sentence
  survives translation, the two files record the **same** refusals (a boundary
  present in one language and absent in the other reads as a deliberately
  different scope), and the English README no longer links the Turkish file.
- **First-run path verified and locked (`tests/test_first_run.py`).** The
  `/plugin install → /new-project → working project` path had never been
  exercised, and it is the one path no other test covered — a drift in
  `/new-project`'s copy list would surface on a new user's very first command
  and nowhere in CI. The suite replays the copy list, then asserts the result
  stands alone: `PROJECT.md` present (without it every hook no-ops), kit
  integrity clean *inside* the new project, `python scripts/...` resolving
  locally, `phase_gate` correctly denying a draft with no approved outline, and
  every hook wired in `settings.json` actually delivered by the copy. It also
  pins the transcribed copy list against the skill's own prose, so the
  transcription cannot go stale silently.

- **CLAUDE.md constitution** — 8 invariants (source discipline, zero
  fabrication, phase gates, token economy, evidence chain, edit discipline,
  bilingual search, template supremacy) plus the subagent dispatch map.
- **9 subagents** (`.claude/agents/`): literature-scout (bilingual search),
  source-analyst (deep-read → evidence cards), citation-verifier (fabrication/
  retraction/orphan-citation audit, read-only), methodology-advisor (study &
  ML experiment design, read-only), data-scientist (write-scoped to
  `analysis/`), reviewer-critic (fresh-context peer review), style-auditor
  (register/clarity, read-only), format-engineer (write-scoped to
  `build/`/`exports/`/`templates/ingested/`), qa-auditor (read-only back-step
  double-check after every SLR stage).
- **26 skills** (`.claude/skills/`): 15 gated workflow commands (`/new-project`
  `/lit-review` `/slr` `/journal-check` `/outline` `/draft` `/analyze-data`
  `/verify-citations` `/critique` `/revise` `/export-excel` `/ingest-template`
  `/submit-check` `/status` `/defense-prep`) plus 11 knowledge skills
  (paper-types, thesis-structure, citation-styles, literature-review,
  evidence-cards, academic-writing, reporting-guidelines, ml-research,
  comparative-analysis, latex-thesis, docx-output).
- **21 scripts** (`scripts/`) — deterministic, dependency-light Python/Bash
  tools the orchestrator and agents execute rather than reason about:
  evidence_db, registry_db, doi2bib (DOI content negotiation + CSL backfill +
  `--verify` fabrication detection), venue_check (layered SCImago/DOAJ/OpenAlex
  datasets + cache + `--set-wos`), bib_doctor, cite_audit, word_budget
  (`--rq-trace`), xlsx_export (styled multi-sheet workbook), prisma_flow,
  pdf2md, qa_inspect, write_verify_status, patch_hook_interpreter,
  docx_style_check, make_reference_docx, validate_kit, skill_routing_eval,
  extract_skill_descriptions, update_data, latex_build.sh / docx_build.sh
  (digested build errors, graceful degradation without pandoc/MiKTeX).
- **6 hooks** wired in `.claude/settings.json`: `protect_data_files`
  (PreToolUse deny on direct writes to script-owned JSONL/bib/status files —
  covers Write/Edit/NotebookEdit and Bash redirection/tee/cp/mv/sed-i/
  PowerShell write cmdlets/Python one-liners), `phase_gate` (blocks drafting
  before outline approval, critique before verify=PASS, formatting before
  Major=0), `agent_write_scope` (per-agent write-surface enforcement for
  data-scientist/format-engineer/source-analyst), `template_supremacy_gate`
  (ingested template rules override kit defaults), `cite_warn` (PostToolUse
  instant undefined-citation feedback), `session_status` (SessionStart
  ≤20-line digest). Hardened against nested-shell/PowerShell-alias/heredoc/
  glob-expansion bypass of the write-sink matcher shared by all of them.
- **Zero-fabrication citation chain**: claim → evidence card (EV-####) →
  `sources/registry.jsonl` entry → DOI-content-negotiated BibTeX →
  `citation-verifier` PASS. Phase gates block drafting before outline
  approval, critique before verify=PASS, and formatting before Major=0.
- **Full SLR pipeline** (`/slr`): per-database advanced queries (Scopus, WoS,
  IEEE, Wiley, PubMed, Google Scholar), screening with logged reasons,
  PDF→Markdown conversion, structured JSON extraction with in-paper
  references, detailed multi-sheet Excel, qa-auditor double-check after
  every stage.
- **Templates**: TR (YÖK front-matter order, Özet↔Abstract equivalence) + EN
  thesis LaTeX skeletons, paper/proposal/response-letter templates, 6 CSL
  citation styles, generated `reference.docx`.
- **Cross-platform hardening**: atomic JSONL writes (temp-file + `os.replace`),
  cross-platform file locking against concurrent-write data loss, Windows
  transient-`PermissionError` retry/backoff, UTF-8 console forcing for
  Turkish characters, LF-normalized scripts with `.gitattributes` pins,
  `INSTALL.sh`/`INSTALL.ps1` hook-interpreter self-patching
  (`python`/`python3`/`py`).
- **CI** (`.github/workflows/ci.yml`): Ubuntu/Windows/macOS × Python
  3.10/3.13, `validate_kit.py` + full pytest suite, SHA-pinned actions.
- **Test suite**: 596 pytest cases (594 passed + 2 live-network smokes
  skipped by default, run with `RUN_LIVE=1`). `validate_kit.py` → 0 problems.
  `skill_routing_eval.py` → 44/44 prompts routed to their intended skill.

### Security

- **The six script-owned data files are now read-only on disk, not just
  hook-protected.** Invariant 6 rested entirely on
  `.claude/hooks/protect_data_files.py` reading a shell command and deciding
  whether it writes — a detector whose own header calls itself the densest
  defect history in the kit, because every bypass it lists (PowerShell `sc`/`ni`
  aliases, a quoted path containing a space, simple variable indirection) shipped
  before it was caught. `scripts/lib_common.py` now clears the write bit after
  every sanctioned write and restores it only for the `os.replace()` that
  performs the next one, so a redirect, `tee`, `Set-Content` or `open(p, "w")`
  the hook never recognised is refused by the operating system regardless.
  Stated boundary, and asserted by a test rather than left to be discovered:
  this does **not** stop `rm`/`Remove-Item -Force` or `mv`, which are governed
  by the directory's permission — those remain the hook's job, and the two
  layers now name each other. `lib_common.unprotect()` is the documented escape
  hatch for anyone who needs to inspect or archive a file by hand.
  [2026-08-13]
- **Static analysis and a secret scan in CI.** A `lint` job runs `ruff` (E,W,F,B)
  and `bandit` at MEDIUM+, and `.pre-commit-config.yaml` runs both plus gitleaks
  on every commit inside a ten-second budget. The 48 findings this surfaced are
  fixed; the only ones with a live failure mode were seven `zip()` calls over
  parallel arrays in `meta_analysis.py`, which would have truncated silently on
  a length mismatch — a pooled estimate over fewer studies than were supplied,
  reported without a word. [2026-08-13]

### Added — epistemic-claim layer (competitive analysis of ARS) [2026-08-12]

- **`claim_check.py` — claim-strength overclaim + uncited-assertion lint.** New
  script closing the defect class citation verification structurally cannot see:
  a citation that is real, resolvable and correctly formatted, attached to a
  sentence the cited work does not support. `overclaim` compares each cited
  sentence's rung on an ordered claim-strength ladder (TR + EN: *associated with
  < predicts < contributes to < affects < causes*) against the evidence card
  drawn from that same source, and flags only **upward** movement — writing more
  cautiously than a source is always safe, so the check is deliberately
  one-directional. `uncited_assertions` flags empirical sentences (a statistic,
  or a rung-4+ causal claim) carrying neither a citation nor an own-work marker.
  Sources with no card are skipped rather than guessed at. WARN-only
  (`--strict` opts into blocking). 35 tests in `tests/test_claim_check.py`.
- **`reference/claim-strength.md` in the academic-writing skill.** The ladder
  itself, the one-directional rule and why it differs from revision-diff tools,
  the attributive-participle trap ("reduced capacity" is an outcome, not a
  claim — in both English and Turkish), an evidence→defensible-rung table, and
  the check's stated coverage limits.
- Wired into `/submit-check` (fifth non-blocking advisory) and `/revise` (after
  any claim rewording — the step where a reviewer's push for a stronger
  contribution gets answered by upgrading a verb instead of adding evidence).

- **`failure_scan.py` — 7-mode AI-research failure-mode scan.** The modes come
  from Lu et al. (2026, Nature 651:914–919), whose autonomous research system
  produced them; they matter because each one **reads like competent work**.
  The script decides the machine-decidable half — implausibly exact metrics, one
  value standing in for several metrics, zero dispersion (M1); a decimal
  narrated as an own result that appears in no `analysis/` artefact, accepting
  prose rounding but not prose more precise than any artefact (M3); an
  unanchored "surprisingly" (M5); a Methods hyperparameter matching no run
  config (M6); hindsight phrasing (M7) — and reports the rest as explicitly
  un-decided rather than silently clean: M2 is DELEGATED to `/verify-citations`,
  M4 (shortcut reliance) is NOT_AUTOMATED because it needs an ablation
  judgement. **Paper-type pre-filter:** the quantitative modes switch off for
  theoretical / qualitative / narrative-review / case-report manuscripts, and
  the skip is reported — a mistyped `PROJECT.md` cannot quietly disable half the
  scan, and an unknown type keeps every mode on. 41 tests in
  `tests/test_failure_scan.py`.
- **`reference/failure-modes.md` in the critique skill.** The seven modes, the
  questions each still needs a human to answer, and the three verdicts
  (CLEAR / SUSPECTED / INSUFFICIENT EVIDENCE) — with the rule that INSUFFICIENT
  EVIDENCE is not a pass: for M1/M3/M5/M6 it means the artefacts that would
  settle the question do not exist, which is a finding about the work.
- **`test_venue_check.py` fixtures no longer expire** — see Fixed, below.
- Wired into `/critique` as a **pre-**dispatch step (its findings are inputs to
  the review: a reviewer told a number is unbacked investigates it; one reading
  the sentence cold cannot) and re-run in `/submit-check` as the final pass.

- **Knowledge isolation: `[MATERIAL GAP]` and `[LLM-SUPPLEMENTED]` tags.** The
  draft skill already bound claims to cards and tagged `[CITATION NEEDED]`, but
  had one tag for two different states. Now three, and they are not
  interchangeable: `[CITATION NEEDED]` = the claim is sound, a source is not
  attached yet; `[MATERIAL GAP]` = no session material covers this and the
  writer **refused to fill it from model memory**; `[LLM-SUPPLEMENTED]` = the
  author explicitly authorized a fill. The first two are holes in a finished
  manuscript and block; the third never blocks but is always reported —
  an authorized fill that leaves no trace is indistinguishable from an
  unauthorized one. Turkish drafts may use `[KANIT YOK]` / `[MODEL BİLGİSİ]`.
  `cite_audit.py` counts all three, and `write_verify_status.py`'s live recheck
  blocks on `[MATERIAL GAP]` too, so the gate can no longer write PASS over a
  draft that `cite_audit.py` itself exits 2 on.

### Added — measurement layer [2026-08-12]

- **`run_evals.py` + `eval/gold/` — the kit now measures its own checkers.**
  Labeled gold sets scored precision / recall / F1: `claim_strength` (22 cases,
  9 positive / 13 negative) and `failure_modes` (27 cases, 13 / 14). Both at
  P=1.00 R=1.00 against declared thresholds of 0.90. `expect` entries are subset
  matches, so a case asserts only what it means to and survives a reworded
  message. The harness refuses to flatter: an empty case list, a duplicate id,
  an unknown entrypoint, or a threshold naming an uncomputed metric are all
  errors rather than a vacuous 1.00.
- **Gated by `pytest`, not by a workflow edit.** `tests/test_run_evals.py` runs
  the shipped sets and asserts their thresholds, that they declare thresholds at
  all, and that they still carry negative cases — so CI gates on checker
  accuracy with no change to `.github/workflows/ci.yml`.
- **`eval/MEASUREMENT.md`** states what the numbers mean and what they do not:
  the sets were labeled by the same person who wrote the checkers, so they
  measure intent rather than real-world coverage; a perfect score on 22 cases is
  a regression guard, not an error-rate estimate; precision is meaningless
  without negatives; and none of it validates the underlying research.

- **`calibration_score.py` + `/critique --calibrate --gold` — reviewer error
  profile.** `--calibrate` previously measured run-to-run *stability*, which a
  consistently-wrong reviewer passes perfectly. It now also measures accuracy
  against papers whose real outcome the user already knows: confusion matrix,
  balanced accuracy, and FNR/FPR with fixed-seed bootstrap CIs, plus the
  Minor/Major boundary sub-matrix the binary split collapses.
  - **Gold-label isolation is architectural.** Labels live in a file the
    reviewer never receives; verdicts are frozen to disk; the script is the only
    place the two meet, afterwards. It additionally **refuses to score** a
    verdict record carrying a label-shaped field (`label`, `GoldLabel`,
    `ground_truth`, … compared with case and punctuation folded away) — a run
    whose reviewer could see the answer is not a measurement.
  - **Refuses rates it cannot support.** The `directional` tier (3 papers, one
    run each) emits direction counts and **no FNR/FPR at all**; a single-class
    gold set is rejected outright rather than reporting one rate as a profile;
    ties break toward the more conservative decision so the measurement is not
    flattered; n<10 carries a non-removable caveat.
  - The positive class (`accept + minor_revision`) is printed in every report
    because reversing it inverts the reading of both rates while leaving the
    formulas unchanged — the standard way these get misquoted.
  - The kit ships **no** reviewer gold set and will not: a label is a claim
    about what a venue actually decided. Protocol and limits in the new
    `.claude/skills/critique/reference/calibration.md`.

### Added — governance & provenance [2026-08-12]

- **Two agents were being dispatched for work their contracts did not cover.**
  `/slr` stage 6b asks `methodology-advisor` whether a set of studies may be
  pooled at all — a question absent from its DESIGN/CRITIQUE/QUESTION modes and
  from its description, so the dispatch relied on the agent improvising. It now
  has a **POOLABILITY** mode that returns `pool` / `pool-with-subgroups` /
  `do-not-pool`, names the specific incomparability per exclusion, and forces the
  model, effect measure and subgroup splits to be pre-registered before any
  output is seen. `style-auditor` was likewise unaware that `tr_style_check.py`
  now runs before it; it is told to skip the machine-decided half and spend its
  budget on what a regex cannot see — agreement, participles, postpositions, and
  whether the two summaries make the same argument.

- **`examples/showcase/` now holds the real run's artifacts.** Ten files from the
  stroke-prediction paper — search log, PRISMA flow, the verification gate's
  output, the citation-verification report, both peer-review rounds, the
  revision changelog, word budget, evidence funnel, and the machine-fetched
  bibliography. Every one is a script or subagent output; nothing was authored
  for the showcase. The README's funnel (103 cards → 23 sources → 20 included →
  19 cited → 19 entries) was re-derived from the project's own registry rather
  than trusted, and now comes back out of `09-evidence-funnel.json`.
  The two artifacts worth reading are the ones that make the kit look fallible:
  `04-verify-report.md` records `doi2bib.py` raising **two false FABRICATED
  flags**, and how each was independently re-derived and overturned with its
  reasoning written down; `07-review-round-2.md` records that once the Round 1
  demand for statistical validation was met, the bootstrap CIs showed the model
  ranking was **not significant** — and the paper said so instead of keeping the
  "best model" framing.
  The final manuscript PDF is deliberately withheld and the index says why:
  publishing it is a journal-policy decision, not a kit decision. Six tests guard
  the directory — every indexed file must exist, the index's quoted figures must
  match the JSON they came from, every bibliography entry must carry
  `verified={true}`, and a contact-details scan runs on every file so a later
  artifact drop cannot reintroduce an address.
- **`docs/RELEASING.md`** — the release and Zenodo-DOI procedure, including the
  reason `CITATION.cff` still carries no DOI and the instruction to *replace* the
  test that enforces that rather than delete it once the archive exists. A guard
  should follow the truth, not be removed when it becomes inconvenient.

- **`POSITIONING.md`** — the recorded scope boundary. Seven mechanisms are
  refused with their reasons: unapproved end-to-end production, bibliographic
  data from model memory, similarity/plagiarism scoring (a heuristic web
  comparison is not a plagiarism rate but reads like one), AI-detection evasion,
  fabricated reviewer gold labels, a specific institution's template content,
  and cross-paper memory. It also records what is deliberately *inside* the
  boundary and why: the kit analyses the user's own data, because the gap
  between where numbers are produced and where they are written is the source of
  the M3/M6 failure modes, and `failure_scan.py` can only check prose against
  `analysis/` artefacts because of that integration.
- **The honest failure shape is stated, not implied:** the kit checks the
  manuscript and the reported process, never that the work was actually done. A
  study built on fabricated data passes every gate if the fabrication is
  reported consistently. Crossing a recorded boundary now requires editing that
  record and logging it in `DECISIONS.md` first — not merely adding a feature.
- **`CITATION.cff`** so the kit is citable. **No DOI field**: a DOI is minted by
  archiving a release, and writing one before that archive exists would be a
  fabricated identifier in the metadata of a kit built to prevent exactly that.
- **`examples/showcase/README.md`** — the artifact index for a real run, plus a
  pre-publication redaction checklist (publication rights, co-author consent,
  personal data, dataset licence). Ships **no** invented artifacts: a sample
  review report authored to fill the directory would read as evidence of a run
  that never happened.
- **13 tests in `tests/test_governance_docs.py`** pin these claims to something
  checkable — the citation version tracks the latest *released* CHANGELOG
  version, the declared licence matches `LICENSE`, no unearned DOI appears, the
  honest-failure sentence still exists, each recorded refusal still matches the
  surface that enforces it, and any file dropped into the showcase must appear
  in its index.

### Added — plugin packaging [2026-08-12]

- **`.claude-plugin/{plugin,marketplace}.json`** — installable in one line via
  `/plugin marketplace add mtvrkan/scholar-kit`. Uses the manifest's custom-path
  fields so the kit keeps its existing `.claude/skills/` + `.claude/agents/`
  layout instead of being restructured for the packaging. Verified with
  `claude plugin validate . --strict`, which is also what caught the first
  attempt: `agents` rejects a bare directory and needs the files listed.
- **Two install paths, documented as giving different things.** A plugin install
  ships the commands, knowledge skills and subagents. It does **not** ship the
  deterministic script layer or the enforcement hooks — those must live inside
  the user's project for `python scripts/...` to resolve and for the hooks to
  see `PROJECT.md`. `/new-project` materialises them, so it is the required
  first command; installing the plugin and never running it yields the prompts
  without the guarantees, and the README now says exactly that.
- **`/new-project` now patches the hook interpreter** after copying the runtime.
  `INSTALL.sh` did this for a cloned kit, but a project created from a plugin
  install never runs INSTALL — so hooks stayed wired to a literal `python` that
  may not resolve. `PreToolUse` hooks fail OPEN, so the failure mode was silent
  absence of enforcement rather than a visible error.
- **11 tests in `tests/test_plugin_manifest.py`** cover what schema validation
  cannot: that the hand-listed agent array still matches the agents on disk (add
  an agent, forget the manifest, and the plugin silently ships without it),
  that every declared path resolves, and that the version tracks `CITATION.cff`.

- **English README (`README.en.md`)** with both files cross-linked. Not a
  mechanical translation — it leads with what differentiates the kit for a
  reader who has other options. Six tests pin the CHECKABLE claims across the
  two (test count, tool count, install commands, the plugin caveat), because a
  translation is the first thing to go stale: one file gets a new number and the
  other keeps the old one for months with nobody reading both.
- **`site/index.html`** — a single-file, dependency-free landing page, TR/EN with
  the toggle defaulting to the browser's language, and theme-aware in all three
  viewer states. The page leads with what the kit refuses rather than what it
  produces, and gives the honest failure shape a pull quote: a landing page that
  opened with "10× your research" would contradict every gate behind it. Every
  figure on it is real — 35 tools, 1147 tests, and the run numbers from the
  stroke-prediction paper. No build step, no CDN, no fonts fetched.
- **`tr_style_check.py` — the Turkish layer stops being a promise.** The kit
  claimed Turkish and English as equal first-class targets while every Turkish
  guarantee rested on prose an agent may or may not follow; every other
  differentiator here has a script behind it. Seven deterministic checks:
  decimal-separator consistency, TDK percent placement, `v.b.`→`vb.`,
  conversational register, **term unity** against a per-project glossary,
  impersonal/first-person voice mixing, and **Özet↔Abstract** equivalence
  (numeric agreement with separators normalized first, keyword counts, length
  ratio — the Özet reporting a figure the Abstract does not is the defect
  reviewers actually catch).
  **Design rule: inconsistency over house style.** Turkish academic convention is
  not uniform — TDK writes `0,95`, many journals require `0.95`; some departments
  demand impersonal `-mIştIr` throughout, others accept first person. Where the
  field is genuinely split the script flags the **mixture** and never the choice,
  because a linter that fires on internally-consistent work teaches its user to
  ignore it. Only settled rules (percent placement, `vb.`) name a correct form.
  Scope is stated in the output: not a grammar checker, no parser, no morphology
  — agreement, participles and postpositions stay with `style-auditor`.
  `templates/tr-terminology.json` ships 45 concepts and is meant to be pruned per
  project. 46 tests.
- **`token_report.py` + `docs/PERFORMANCE.md`** — the cost question, answered by
  shipping the instrument instead of the answer. A per-command token/cost table
  was the obvious thing to publish and would have been invented, in a kit whose
  positioning is that invented numbers are the defect it exists to prevent. The
  script reads Claude Code's own session transcripts for the project and reports
  what was actually recorded: totals, main session vs subagents (the architecture
  claim, made checkable), per model, per slash command, and the cache-read share
  — which matters most, since cache reads bill far below fresh input and a raw
  total therefore **overstates** spend. No prices live in the repo and none are
  inferred; supply `--rates` or no cost column is printed, and a model missing
  from your rates file reports `null`, never `0`. The attribution rule is printed
  with the table because it is a choice, not a measurement. Claude Code's own
  commands are excluded rather than misattributed, and `/status` — a name this
  kit and Claude Code both use, indistinguishable in a transcript — is reported
  as ambiguous instead of guessed at. 32 tests; four governance tests fail the
  build if `PERFORMANCE.md` ever grows a cost table or either file hardcodes a
  price.

### Fixed [2026-08-12]

- **Both READMEs understated the tool count** (30 vs 31 actual). Caught by the
  new cross-README test, which counts `scripts/` directly rather than trusting
  `validate_kit.SCRIPTS` — that list is a required-presence manifest, not an
  inventory, so a newly added tool is legitimately absent from it.
- **`claim_check.py` scanned `drafts/STATUS.md`.** The project's own progress log
  was exempt from the uncited-assertion half but not from overclaim, so a status
  note could be scored against the evidence cards. Now excluded outright,
  matching `consistency_check.py` and `failure_scan.py`. Found by the first-run
  simulation, which ran the checker against a freshly created project.
- **Enforcement hooks leaked outside the project they were written for.**
  `phase_gate`, `protect_data_files` and `cite_warn` gate on `drafts/`, `build/`,
  `exports/`, `reviews/` and `references.bib` — ordinary names everywhere, and
  `references.bib` exists in essentially every LaTeX repository. Harmless while
  the kit was installed per-project; a **defect** the moment it ships as a
  plugin, because a plugin's hooks run in every session: enabling Scholar-Kit
  would have denied edits to an unrelated thesis's bibliography and blocked
  writes to an unrelated `build/`, telling the author to run scripts they do not
  have. All three now consult `.claude/hooks/_project_scope.py` and no-op unless
  the working directory declares `PROJECT.md`. The marker is not searched
  upward, so one stray `PROJECT.md` cannot re-arm the gates for every
  subdirectory beneath it. 14 tests pin both directions.

- **Turkish patterns required diacritics — found by the eval harness on its
  first run.** `claim_check.py` and `failure_scan.py` matched `çalışma` but not
  `calismada`, so ASCII-folded Turkish (common in filenames, quick typing, and
  text round-tripped through diacritic-stripping tools) silently lost every
  own-work exemption and every Turkish tell. A missed own-work marker turns into
  a false positive; a missed tell makes a mode read CLEAR for the wrong reason.
  All Turkish patterns in both scripts are now diacritic-insensitive
  (`[sş]`, `[ıi]`, `[oö]`, `[uü]`, `[gğ]`, `[cç]`).
- **`run_evals.py`'s traversal guard checked the wrong root.** Gold sets are
  kit-owned and read relative to the kit root, but the guard validated against
  the current working directory — the same read-target/guard divergence
  `skill_routing_eval.py` documents — so the harness died anywhere but the kit
  root. Now guarded against the kit directory it actually reads.

- **`test_venue_check.py` cache fixtures were a time bomb.** Two fixtures
  hardcoded `checked_at: 2026-07-01` against a 30-day TTL, so the suite began
  failing on its own on 2026-07-31 — and the ISSN-mismatch test had started
  passing for the wrong reason (staleness, not the ISSN check it exists to
  cover). Both now derive a date relative to today.

Post-1.0.0 hardening from a 3-agent independent audit of the hook/script layer.
This was also the first CI run on Linux/macOS runners for this codebase (prior
development happened on Windows); two latent POSIX-only failures surfaced and
are fixed below.

Additionally, the **first real end-to-end paper run** (a stroke-prediction /
XAI four-model benchmark) exercised the citation, bibliography, venue, and
evidence scripts against live publisher metadata for the first time and surfaced
four script defects, fixed below and locked with
`tests/test_remediation_2026_07_05_kit_improvements.py`.

### Added — consistency &amp; funnel transparency (first end-to-end paper run)

- **`consistency_check.py` — numeric "narrated ≠ presented" lint.** New script
  addressing a real defect from the paper run: prose stated counts that
  contradicted what was actually presented. Reconciles prose numbers (digit and
  spelled-out) bound to canonical quantities — features, models, samples, XAI
  methods, findings — against an `analysis/counts.json` manifest, and flags the
  same quantity stated with different numbers across sections (Abstract vs
  Results drift). WARN-only by default (`--strict` opts into blocking). Tests in
  `tests/test_consistency_check.py`. (Manifest emission by the data-scientist
  agent and submit-check wiring are the remaining follow-up.)
- **`evidence_funnel.py` — cards → sources → cited → bib funnel.** New script
  that makes the (legitimate) narrowing from 100+ evidence cards to ~19
  references explicit, so it no longer reads as a bug, and flags the one case
  that IS actionable: an INCLUDED external source whose card was extracted but
  never cited in any draft. Correctly classifies own-result cards and
  excluded/retracted-source cards as expected-uncited rather than orphans.
  Report-only. Tests in `tests/test_evidence_funnel.py`.
- **`figure_check.py` — figure/table existence, numbering, and caption lint.**
  New script closing the "figure numbering is entirely manual" gap: cross-checks
  every "Figure N"/"Table N" prose mention against actual embedded figures
  (markdown images with a "Figure N." caption) and tables (bold "**Table N.**"
  captions), flagging mentions with no matching figure, figures never referenced
  by number anywhere in the prose, duplicate numbers, sequence gaps, and figures
  missing a corresponding `analysis/captions.md` entry. Found a real, previously
  undetected defect on first run against the actual paper: a bootstrap-CI forest
  plot (Figure 4) was embedded in `results.md` but never referenced by number in
  any draft, even in the paragraph discussing it. WARN-only by default
  (`--strict` opts into blocking). Wired into `/submit-check` Step 5b. Tests in
  `tests/test_figure_check.py`.
- **`qa-auditor` gains a `figures` stage** (visual figure verification, an idea
  harvested from a public multi-agent research-writing kit's "VLM figure
  verification" concept, reimplemented in our own words against our own
  read-only agent, not their code). Reads the actual figure PNG (the agent's
  Read tool renders images) alongside its source CSV/table and the prose claims
  made about it, checking ordering/magnitude claims against what's actually
  plotted, axis labeling, error-bar presence, legend/color-coding accuracy, and
  rough numeric plausibility. Complements `figure_check.py` (existence/
  numbering only) rather than duplicating it. Visually smoke-tested against the
  real project's SHAP beeswarm figure: the plotted feature ordering matched the
  underlying CSV ranking exactly.
- **`tests/gold_citations.jsonl` + `tests/test_gold_citations.py`** — a
  gold-DOI regression harness (live network, `RUN_LIVE=1`) pinning
  `doi2bib.py`'s fetch-then-verify path against 5 well-known, stable DOIs with
  independently-known title/year/first-author metadata. Two entries (XGBoost,
  LIME) are real ACM/Crossref colon-title-split cases — the exact defect class
  fixed below — verified against live data, not just a synthetic fixture.
- **`temporal_check.py` — implausible dates and anachronistic-citation lint.**
  New script (idea harvested from a public multi-agent research kit's
  "anachronistic citation" failure-mode concept, reimplemented as our own
  deterministic arithmetic check, not their code): flags a future-dated or
  impossibly-fetched (`fetched_at` predating its own `year`) bibliography entry,
  and an evidence card whose claim text mentions a year postdating its own
  cited source by more than one year. WARN-only by default (`--strict` opts
  into blocking); this is deliberate, not a placeholder — running it against
  the real project surfaced 2 genuine hits (a scope-clarification mention
  distinguishing a 2017 paper from a later 2020 development, and a retraction
  date on a 2024 paper), both correctly non-issues on inspection, confirming a
  human-adjudicated advisory is the right shape for this check, not a hard
  gate. Also fixed a doc/implementation gap this surfaced: `/submit-check`
  claimed `bib_doctor.py` already checked "year in valid range (1800–2030)" —
  it never did; the doc now correctly attributes future-year detection to
  `temporal_check.py`. Wired into `/submit-check` Step 5b. Tests in
  `tests/test_temporal_check.py`.
- **`citation_triangulate.py` — OpenAlex second-index cross-check** (idea
  harvested from a public multi-agent research kit's "3-index citation
  triangulation" concept — Semantic Scholar was evaluated as a third index and
  rejected: its unauthenticated Graph API returned HTTP 429 on a cold request,
  i.e. its free-tier rate limit is already exhausted at the shared-IP level;
  documented in the script for later addition if an API key becomes available).
  Corroborates `doi2bib.py --verify`'s primary Crossref/doi.org check against a
  second, independent index without overriding it (OpenAlex is a downstream
  aggregator, not a registration authority — disagreement is advisory, never a
  second gate). Fixed a real false-positive found while building this: OpenAlex
  stores only the base title for a colon-subtitled paper ("XGBoost", no
  subtitle field to reconstruct from, unlike Crossref's CSL-JSON), so a naive
  full-title comparison flagged the correct chen2016xgboost/ribeiro2016why
  entries as DISAGREE; `_titles_agree()` now also accepts a near-100
  partial-ratio (prefix/truncation match) while still catching a genuinely
  wrong paper (confirmed live: an unrelated title scores 8, nowhere close).
  Network-per-DOI cost, so recommended rather than run by default; wired into
  `/submit-check` Step 5 as an optional high-stakes-submission step. Tests
  (mocked OpenAlex responses) in `tests/test_citation_triangulate.py`.
- **`compliance_gen.py` + `/disclosures` skill — AI-disclosure, CRediT
  authorship, and funding statement generators** (idea harvested from a public
  multi-agent research kit's disclosure/CRediT/funding-statement generators,
  reimplemented from scratch against the official public CRediT taxonomy —
  credit.niso.org — not their text). Templates three boilerplate statements
  increasingly required at submission; never invents an unset fact — every
  mode requires its inputs explicitly (which AI tool and specific uses, which
  author did which of the 14 official CRediT roles, which funder/grant). CRediT
  role matching is case-insensitive and tolerant of a plain ASCII hyphen where
  the official taxonomy uses an en dash (a real usability gap found while
  testing: "Writing - original draft" was rejected before this fix, since most
  people don't type the Unicode en dash). The AI-disclosure output is
  explicitly flagged as a starting point, not a guarantee of compliance with
  any specific venue's exact wording. Tests in `tests/test_compliance_gen.py`.
- **`/critique --panel` and `/critique --calibrate`** (idea harvested from a
  public multi-agent research kit's 7-role editorial panel and reviewer-
  calibration concepts, reimplemented in our own words as an orchestration-layer
  addition — the `reviewer-critic` agent's own contract is unchanged; only the
  dispatch prompt varies). `--panel` dispatches `reviewer-critic` 4x in parallel
  with distinct persona framings (methodology, domain, generalist, devil's-
  advocate) and synthesizes one `reviews/round-N.md`, with a hard anti-
  sycophancy rule: a devil's-advocate Major finding caps the panel's decision at
  Major Revision regardless of the other 3 panelists. `--calibrate` dispatches
  the plain reviewer 3x on the same draft to report decision/Major-count
  variance as a self-consistency proxy — explicitly NOT a calibration against a
  labeled gold-standard dataset (the kit has none, and fabricating expected
  accept/reject labels would be worse than not measuring this); writes a
  separate `reviews/calibration-report.md`, never mistaken for a real review
  round by `/submit-check`'s round-N gate.

### Fixed — first end-to-end paper run

- **`doi2bib.py --verify` false-FABRICATED colon-titled papers.** Some
  publishers (ACM via Crossref) split a `Title: Subtitle` into separate CSL
  `title` and `subtitle` fields, while doi.org's own BibTeX content negotiation
  (and this script's `cmd_fetch`) returns the combined single field. `cmd_verify`
  compared the local title only against `csl["title"]`, so a correctly-fetched
  entry scored a low title similarity and was reported `FABRICATED` — observed
  live on `chen2016xgboost` (sim 30) and `ribeiro2016why` (sim 49). Added
  `_csl_full_title()` to reconstruct the combined title before comparison; the
  `FIX`/`FABRICATED` reason strings now quote the full title too.
- **`bib_doctor.py` false "missing journal" on preprints.** A preprint
  (arXiv/bioRxiv/medRxiv/chemRxiv/SSRN/…) that doi.org types as `@article` has
  no peer-reviewed journal, yet the `article` required-field set demanded one —
  a false `missing-field` flag on a valid, authoritatively-fetched entry
  (observed on `fisher2018all`). Added `_is_preprint()` (detects the arXiv/
  bioRxiv/chemRxiv DOI prefixes, `archiveprefix`/`eprint`/`primaryclass` fields,
  or a preprint-host name in `journal`/`publisher`/`note`); preprints now require
  a locator (`doi|url`) instead of a journal. A genuine journal article missing
  its journal is still flagged.
- **`venue_check.py` attached the wrong journal's index metadata.** The OpenAlex
  title lookup requested `per-page:1` and blindly took `results[0]` from a
  relevance-ranked full-text `search`, so a short query ("Bioengineering", MDPI)
  picked up a larger differently-named journal's record ("Biotechnology and
  Bioengineering", Wiley) — importing the wrong quartile/ISSN/index status. Now
  fetches five candidates and re-ranks them by actual title similarity via
  `_best_title_match()`, rejecting anything below a close-match threshold rather
  than trusting the top relevance hit.
- **`evidence_db.py add --stdin` corrupted non-ASCII on Windows.** stdin was
  read through the text wrapper, which decodes using the console/locale codepage
  (cp1254 on Turkish Windows), mangling multibyte UTF-8 — Greek/math symbols in a
  card's claim/detail (ξ, π, σ, Ω, Σ) were written to `cards.jsonl` as permanent
  mojibake. Now reads `sys.stdin.buffer` and decodes UTF-8 explicitly (codepage-
  independent), with a clear error if the bytes genuinely aren't UTF-8.

### What Scholar-Kit is

An end-to-end Claude Code kit for academic research, article writing, and
thesis production, built around a twin constraint: **maximum output quality +
minimum token consumption**. A single orchestrating session drafts and
synthesizes; heavy read-once work (search, PDF ingestion, verification,
analysis) is delegated to subagents that die in their own context and return
structured summaries instead of raw dumps.

### Notes

- This is an assistant, not an author — institutional and target-journal AI
  policy compliance is the user's responsibility; `/submit-check` reminds of
  the AI-disclosure requirement every run. Similarity screening
  (Turnitin/iThenticate) is out of scope.
- Full remediation history (every bug found and fixed pre-1.0.0, with
  rationale) is preserved in `DECISIONS.md` for provenance; it is not
  repeated here.
