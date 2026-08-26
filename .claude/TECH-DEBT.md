# TECH-DEBT — flagged, not fixed

One line per flag. Never a duplicate (same file + same flag = leave the existing
row). Never fixed on sight — that is the point of a flag. Delete the row when
the condition is genuinely gone, not when it becomes inconvenient.

| Tarih | Yer | Bayrak | Nerede fark edildi |
|---|---|---|---|
| 2026-08-15 | `.claude/hooks/agent_write_scope.py` | FWD: hook `PROJECT_ROOT`'u oturumun cwd'sinden çözüyor, yani kit kökünden. Kit'in İÇİNDE bir proje dizini (`runs/<proje>/`) varken ajanlar kendi proje dizinlerine `Write` yapamıyor; ret mesajı "outside declared write scope" diyor ve gerçek sebebi (cwd ≠ proje kökü) söylemiyor. `evidence_db.py` gibi alt süreç yazımları etkilenmiyor, doğrudan `Write` etkileniyor — yani kusur sessiz ve kısmi. | Diyabetik retinopati derlemesi koşusu: iki `source-analyst` ajanı `runs/dr-tarama/evidence/extracts/` ve `sources/pdf/` altına yazamadı, kartlar yazıldı |

## Bu bayrağın gerçek kapsamı

Kit zaten "Claude Code'u proje dizininde açın" diyor, dolayısıyla hook belgelenen
kullanımda doğru davranıyor. Bayrağın konusu davranış değil, **teşhis edilebilirlik**:
cwd proje kökü olmadığında ret mesajı bunu söylemiyor, ve mesajı okuyan (insan ya da
ajan) kendi izninin dar olduğunu sanıyor. En küçük düzeltme, reddin gerekçesine
"cwd `<x>`, proje kökü değil" satırını eklemek olurdu; asıl düzeltme
`runs/<proje>/` yerleşimini tanımak.

---

| 2026-08-15 | `scripts/tr_style_check.py` | ~~FWD: `term_unity` alt dize eşleşmesiyle yanlış pozitif üretiyor~~ ÇÖZÜLDÜ — teşhis de yanlıştı, düzeltildi | Aynı taslakta çıktı |

Aynı taslakta iki yanlış pozitif: "nitelik şikâyeti" ifadesindeki *nitelik*, ML anlamında
*öznitelik* sanıldı (biri diğerinin alt dizesi); "Sonuç şudur" ve "manşet sonucu"
ifadelerindeki *sonuç*, *bulgu* ile eşanlamlı sayıldı. Sözcük sınırı ve —*sonuç* gibi
çok anlamlı terimler için— bağlam gerekiyor. Aksi hâlde terim birliği denetimi, terim
birliği olan metinlerde de konuşur.

**Yukarıdaki üç satırın kapanışı (2026-08-15).** Üçü de düzeltildi ve testlendi;
biri **yanlış teşhis edilmişti** ve o da burada düzeltiliyor:

- `term_unity` sorunu **alt dize eşleşmesi değildi**. Regex zaten sözcük sınırı
  kullanıyor; sorun **çok anlamlılıktı** — "nitelik şikâyeti"ndeki *nitelik* gerçek
  bir sözcük, sadece ML anlamında değil. Bu yüzden ilk denediğim "her varyant en az
  2 kez geçsin" eşiği mevcut bir testi kırdı ("veri seti ×2 / veri kümesi ×1" bilerek
  işaretlenen gerçek bir kayma). Doğru düzeltme sayıya değil **sözcüğe** bağlı:
  yalnızca gündelik anlamı baskın olan varyantlar (`nitelik`, `özellik`, `sonuç`,
  `anma`) iki geçiş istiyor.
- `voice_mixing` sorununun kökü sanılandan derindi: `_fold` zaten `ı→i` yapıyor **ve**
  `re.IGNORECASE` Python'da `ı` ile `i`'yi aynı harf sayıyor (ikisi de `I`'ye
  büyüyor). Yani denetim, dayandığı ayrımı eşleştirmeden önce iki ayrı yerde yok
  ediyormuş. Türkçeye doğru küçültme (`I→ı`) + biçimbilimsel ayrım ile çözüldü.
- `decimal_separator` düzeltmesinin ilk hâli `0.809`'u binlik grup sanıyordu; baştaki
  grup `[1-9]` ile çapalandı.

Ders, ledger'ın kendisi hakkında: **bayrağın gerekçesi de bir iddiadır ve yanlış
olabilir.** Buradaki üç satırdan biri yanlış sebebi gösteriyordu; düzeltmeye
oturulmasa fark edilmeyecekti.

| 2026-08-15 | `scripts/figure_check.py` | ~~FWD: yalnızca İngilizce "Figure N"/"Table N" tanıyor~~ ÇÖZÜLDÜ | Örnek 1'in Bulgular bölümünde çıktı |

Türkçe bir taslakta **sıfır şekil, sıfır tablo** gördü ve "0 uyarı" dedi. Bir
denetleyicinin verebileceği en kötü çıktı budur: sessizlik "kontrol edildi, temiz"
diye okunur. `Şekil`/`Tablo`/`Çizelge` (ve ASCII katlanmış `Sekil`/`Cizelge`) biçimleri
eklendi; Türkçe bahisler ek alır ("Şekil 2'de"), o yüzden sayı sonundaki sınır da
gevşetildi. Düzeltildikten sonra aynı taslakta **üç gerçek bulgu** çıktı: iki şekil
anılıp gömülmemiş, bir tablo gömülüp anılmamış, ve numaralandırmada boşluk vardı
(Şekil 1 ve 3 var, 2 yok).

Bu, kitin Türkçe yolunun İngilizce yolundan zayıf olduğu **dördüncü** vakadır
(`phase_gate` onay işareti, `tr_style_check`'in iki kusuru, ve bu). Örüntü tek tek
düzeltilecek bir hata değil, sınanmayan bir varsayım gibi görünüyor: Türkçe çıktı
üreten bir kitin denetimleri de Türkçe okumak zorunda. `agent_docs/` altında bir
"Türkçe yol denetim listesi" bunu tekrarlanabilir kılardı.

| 2026-08-15 | `scripts/prisma_flow.py` + `registry_db.py` | ~~FWD: arka plan kaynağı eklemek PRISMA akışını bozuyor~~ ÇÖZÜLDÜ | Örnek 1'in [MATERIAL GAP] kapatma turunda çıktı |

Bir sistematik derleme, aramasının döndürmediği şeyleri de alıntılamak zorundadır:
epidemiyolojik arka plan, raporlama kılavuzu, karşılaştırma için anılan bir başka
derleme. Değişmez 1 bunları kayıt defterine girmeye **zorlar**, ama
`identified = len(registry)` onları "aramanın bulduğu kayıt" sayıyordu — ve akışın
bütün kutuları onunla birlikte şişiyordu.

Bu, kitin **iki kuralının birbirini kestiği** bir noktaydı: "kayıtta olmayan
alıntılanamaz" ile "kayıttaki her şey akışta sayılır". İkisi aynı anda doğru olamaz.

`scope: "background"` alanı kaydı akıştan çıkarır; varsayılan akış-içidir, dolayısıyla
mevcut hiçbir projenin sayısı oynamaz. Çıkarılan kayıt sayısı
`background_excluded_from_flow` olarak **raporlanır** — sessizce düşürülmez, çünkü akışı
kayıt defteriyle karşılaştıran bir okur iki toplamın neden farklı olduğunu görebilmelidir.

---

| 2026-08-15 | runs/dr-tarama/scripts/ | FWD: proje dizini kitin betiklerinin ESKİ kopyasını taşıyor — `python scripts/X.py` sessizce düzeltme öncesi sürümü çalıştırıyor | /revise sırasında fark edildi |

Kit kökündeki `scripts/` ile `runs/dr-tarama/scripts/` arasında **7 dosya** farklı:
`claim_check` · `figure_check` · `prisma_flow` · `registry_db` · `screening_score` ·
`temporal_check` · `tr_style_check` — yani tam olarak bu proje sırasında düzelttiğim
yedi betik. Üçünde işaretle doğrulandı: run kopyası düzeltme öncesi sürüm.

Sonucu bir lint gürültüsü değil, **yanlış-temiz denetim**: `figure_check` proje
dizininden çalıştırıldığında Türkçe "Şekil"/"Tablo" sözcüklerini tanımayan eski
sürümü koşuyor, sıfır şekil buluyor ve "0 uyarı" veriyor. `drafts/STATUS.md`'nin
"figure_check 0 · tr_style 0" satırı bu şekilde üretilmiş. Kit kökündeki sürümle
aynı taslak 1 uyarı verdi (Tablo 3 metinde anılmıyor) ve düzeltildi.

Karar bilerek kullanıcıya bırakıldı: kopya kasıtlı bir dondurulmuş anlık görüntü de
olabilir, kazara bir artık da. Sessizce üzerine yazmak ikisini ayırt etmeden 7 dosyayı
değiştirmek olurdu. Ayrım yapılana kadar bu projede denetimler `../../scripts/` ile
çalıştırılmalıdır.

**Kapsam ölçüldü (2026-08-16).** Fark artık **8 dosyadır** (`word_budget.py` de
katıldı) ve sekizinin de proje kopyası daha küçüktür, yani düzeltme öncesi sürümdür.
Ama asıl ölçüm şu: `.gitignore:42` bütün `runs/` ağacını yok saymaktadır — yani bu
kopya **hiçbir zaman sevk edilmiyor**. Bayrak bir dağıtım kusuru değil, **yerel bir
tuzak**: yalnızca bu makinede, yalnızca `python scripts/X.py` yazan birini yanıltır.
Aciliyeti buna göre düşer; tehlikesi düşmez, çünkü yanılttığı şey bir denetim
sonucudur ve sessizce "temiz" der.

### Not — `consistency_check.py`, `n_models` uyarısı (kapatılmayacak)

Aynı çalıştırmanın **ikinci** uyarısı (`n_models` 5 ve 6) ise yanlış pozitif değil,
denetleyicinin bilemeyeceği bir **birim** farkıydı: 5 = küme genelindeki algoritma,
6 = tek bir çalışmadaki kamera modeli. Uyarı gerçek bir belirsizliği gösterdi ve
makale düzeltildi (methods II.7, captions), ama uyarı düzelmeyecek — çünkü iki sayı
gerçekten farklı ve denetleyici birimlerini okuyamıyor. Bu, WARN-only bir lintin
doğru davranışıdır ve öyle raporlanmalıdır; "sıfır uyarı" hedefi bu satırda yanlış
hedeftir.
