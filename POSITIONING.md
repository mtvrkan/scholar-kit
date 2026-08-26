# Konumlandırma — Scholar-Kit ne yapar, ne yapmaz, neyi bilerek reddeder

**Türkçe** · [English](POSITIONING.en.md)

> Bu belge kapsam sınırlarının **kaydıdır**. Amacı, bir özelliğin neden
> olmadığını her seferinde yeniden tartışmak yerine, kararı bir kez yazıp
> sonraki değişiklikler için ölçüt haline getirmektir. Buradaki bir sınırı
> aşmak, "yeni özellik eklemek" değil, **bu kaydı değiştirmektir**.

## Bu nedir

Scholar-Kit, Claude Code için uçtan uca akademik araştırma, makale ve tez üretim
kitidir: uzman subagent'lar, deterministik Python araç katmanı, hook ile
korunan disk-yerleşik durum ve sıfır-uydurma atıf disiplini. Makalenin çevresindeki
işleri de kapsar — proje önerisi ve raporu, etik kurul başvurusu, veri yönetim
planı, hakem raporu, atama dosyası, ders izlencesi ve akreditasyon matrisi — hepsi
aynı disiplinle: **hiçbir limit, ölçüt, form alanı veya program çıktısı modelin
hafızasından gelmez.** **MIT lisanslı** —
kelimenin tam anlamıyla açık kaynak: ticari kullanım, kurumsal dağıtım ve
türev çalışma serbesttir.

Türkçe ve İngilizce akademik yazımı **eşit derecede** birinci sınıf vatandaş
sayar: YÖK tez yapısı, Özet↔Abstract eşdeğerliği, TR Dizin/DergiPark/YÖK Tez
Merkezi taraması ve Türkçe akademik register, sonradan eklenmiş çeviriler değil,
tasarımın parçasıdır.

## Bu ne değildir

Otonom bir makale yazma sistemi değildir. Araştırmacının yerine geçmez, yazarlık
iddia etmez ve çıktıları insan incelemesi olmadan gönderime hazır değildir. Kit
bir **asistandır, yazar değildir** — ve bu, pazarlama cümlesi değil, faz
kapılarının varlık sebebidir.

## Reddedilen mekanizmalar

Bunlar "kapsam dışı" dipnotları değil; kitin ne olduğunu tanımlayan taşıyıcı
sınırlardır. Her biri teknik olarak yapılabilir olduğu için değil, yapılırsa
kitin sağladığı tek şeyi bozacağı için reddedilmiştir.

**Onaysız uçtan uca üretim.** Bir soruyu, her aşamada kullanıcı onayı olmadan
gönderime hazır bir makaleye taşıyan akış. Reddedildi: araştırmacı, kendi
çalışmasının yazarı olmaktan çıkıp AI çıktısının hakemi haline gelir. Kapılar
(outline onayı → verify=PASS → Major=0) tam olarak bunu engellemek için vardır;
"otomatik" bir bayrakla atlanabilir hale getirilmeleri, kapı olmaktan
çıkmalarıdır.

**Hafızadan bibliyografik veri.** BibTeX yalnızca `doi2bib.py`'nin DOI içerik
müzakeresinden gelir; gelmiyorsa `verified:false` damgası taşır. Reddedildi:
modelin hatırladığı bir künye, doğru göründüğü sürece yanlış olduğunda fark
edilmez — ve atıf uydurma, bu kitin çözmek için var olduğu birincil kusurdur.

**Benzerlik/intihal skoru.** Reddedildi: WebSearch tabanlı sezgisel karşılaştırma
bir intihal oranı **değildir**, ama öyleymiş gibi okunur. Kurumunuzun
Turnitin/iThenticate taraması sizin sorumluluğunuzdur ve `/submit-check` bunu
her seferinde hatırlatır. Yanıltıcı bir yüzde vermektense hiçbir şey vermemeyi
seçiyoruz.

**AI-tespitinden kaçınma.** Stil kalibrasyonu ve yazım denetimi **kaliteyi**
hedefler, tespitten kaçmayı değil. Reddedildi: "insanlaştırıcı" bir araç,
kullanıcıyı beyan yükümlülüğünü ihlal etmeye teşvik eder. `/disclosures` bunun
tam tersini yapar — beyanı **üretmeyi** kolaylaştırır.

**Hakemlik altındaki metnin işlenmesi.** Bir dergi size hakemlik için makale
gönderdiğinde o metin size bir gizlilik taahhüdü altında verilmiştir; Elsevier,
Springer ve NIH bunu açıkça yazar. Reddedildi: metni bir araca vermek yazarın
değil **hakemin** ihlalidir, ve ihlal rapor ne kadar iyi olursa olsun geri
alınmaz. `/review-paper` bu yüzden tersini yapar — makaleyi **hiç okumaz**.
Okuyan sizsiniz; kit notlarınızı yapılandırılmış bir hakem raporuna çevirir ve
raporun kendi kusurlarını denetler: bölüm referansı olmayan Major, derginin kendi
seçenek kümesinde bulunmayan bir karar önerisi, kimliğinizi ifşa eden cümle.
Hakemliğin zor kısmı okumak değil, okuduğunu düzgün yazmaktır — kaldırılabilecek
yük orasıdır.

**Uydurma hakem altın etiketi.** `/critique --calibrate --gold` için kit hiçbir
etiketli makale içermez. Reddedildi: bir etiket, gerçek bir derginin ne karar
verdiğine dair iddiadır; sayı üretmek uğruna uydurulması, kalibrasyonun
sağladığı tek şeyi yok eder. Altın küme kullanıcınındır.

**Belirli bir kurumun şablon içeriği.** Kit, TR/EN jenerik tez şablonları ve
`/ingest-template` mekanizmasını **verir**; belirli bir üniversitenin yazı
tipi/kenar boşluğu/başlık kurallarını **vermez**. Reddedildi: kitin bir kurumun
yönergesine bağlanması, diğer herkes için sessiz bir yanlışa dönüşür. Şablon
kullanıcı tarafından sağlanır, depoda taşınmaz.

**Makaleler arası hafıza.** Kit, proje dizini dışında hiçbir durum tutmaz: geçmiş
iddialarınızın sicili, taşınan bir sınırlılık listesi, hakem geçmişi profili
yoktur. Reddedildi: her koşu, o koşuda açıkça beyan edilmiş malzemeden başlar.
Kimsenin bu koşuda beyan etmediği bir durumu değerlendiren bir kapı, kapı
değildir.

Bu sınır, `/dossier`'ın (doçentlik/atama dosyası, akademik CV) ne olduğunu da
belirler: yayın listenizi ve puan ölçütünüzü **her koşuda siz verirsiniz**, kit
hiçbirini oturumlar arası saklamaz ve proje dizini dışına tek satır yazmaz. Bir
atama dosyası aracı olmanın kalıcı bir sicil tutmayı gerektirdiği sanılıyordu;
gerektirmiyor. Kitin orada eklediği değer hatırlamak değil, aritmetiği yapmak ve
her yayının indeks iddiasını `venue_check.py` ile yeniden doğrulamaktır — bir
dosyanın en sık hatası, ESCI bir makalenin SCIE sayılmasıdır.

### Bilinçli olarak sınırın *içinde* olan şeyler

Rakip sistemlerin çoğundan farklı olarak, bu kit **kullanıcının kendi verisini
analiz eder** (`/analyze-data`, `data-scientist` ajanı, `analysis/` altında
hook ile kapsanmış). Bu bir gözden kaçma değil, bilinçli bir tercihtir: sayıların
üretildiği yer ile yazıldığı yer arasındaki kopukluk, M3 (uydurma sonuç) ve M6
(metodoloji uydurma) hata modlarının kaynağıdır; `failure_scan.py`'nin
`analysis/` çıktılarına karşı kontrol yapabilmesi tam da bu bütünleşme sayesinde
mümkündür.

**2026-08-14'te taşınan sınır (D-097).** Bu belge bir önceki sürümüne kadar "kit
veri **toplamaz**" diyordu ve kastı şuydu: kazıyıcıyı kullanıcı yazar, kit
yalnızca protokolü ve kontrolleri üretir. Gerekçe, bir kazıyıcının hangi durumda
meşru olduğuna karar vermenin araca değil yazara ait olmasıydı — o gerekçe hâlâ
geçerli. Değişen, gerekçenin kurduğu **mekanizmanın onu taşımadığının** görülmesi
oldu: kit kazıyıcı vermeyince kazıma durmuyordu, yalnızca robots kontrolü
olmayan, alan beyaz listesi olmayan, hız sınırı ve isteği loglanmayan bir yere —
her seferinde yeniden yazılan tek kullanımlık bir dosyaya — taşınıyordu.

Sınır artık şurada: karar hâlâ yazarındır ve **istekten önce** verilir — protokol
yazılır, robots yanıtı okunur, alan listesi beyan edilir. Yürütmeyi kit yapar,
gevşetmeyeceği koşullarla: eksik protokol reddedilir, robots yasağının
geçersiz kılma bayrağı **yoktur**, protokolde geçmeyen alan toplanmaz, User-Agent
kiti ve yazarın iletişim adresini dürüstçe taşır, istek tavanı ve hız sınırı
vardır, her istek loglanır. Aynı çizgi indirmede de geçerlidir: `dataset_fetch.py`
yalnızca **kayıtlı** bir veri setini indirir ve **lisans okunmadan** indirmeyi
reddeder.

Bugünkü sınır, tek cümlede: kit **kayıtlı veriyi indirir**, **protokolün tarif
ettiği toplamayı yürütür** ve **sizin verinizi analiz eder**; veri **üretmez**,
**sentetik veri uydurmaz**, kimlik duvarını **aşmaz** (kimlik bilgisi tutmaz,
çerez taşımaz, JS çalıştırmaz, CAPTCHA çözmez), insan katılımcılardan **veri
toplamaz** (anket kurumun platformunda çalışır), bir toplamanın **hukuken meşru
olduğuna karar vermez** ve bir analizin bilimsel olarak doğru olduğunu
**onaylamaz**.

**2026-08-15'te genişleyen kapsam (D-098).** Kit bugüne kadar akademisyenin işinin
tek eksenini — makale ve tez üretimini — kapsıyordu. Oysa aynı kişi proje önerisi
yazar, etik kurul başvurusu yapar, hakemlik üstlenir, atama dosyası hazırlar ve
ders verir. Bu işlerin ortak yanı, kitin zaten iyi olduğu şeydir: her birinin bir
**otorite belgesi** (çağrı metni, etik kurul formu, ÜAK ölçüt tablosu, program
çıktı listesi, derginin hakem formu) ve o belgeye karşı yapılacak bir **aritmetiği**
vardır. Genişleme burayadır ve kapsam dışı bırakılan şey aynı kalır: kit hiçbirinin
içeriğini hatırlamaz.

## Otorite dosyası kuralı

Kitin yeni eksenlerinin tamamı tek bir kurala oturur: **bir dış otoritenin koyduğu
limit, ölçüt, form alanı veya çıktı listesi, yalnızca sizin doldurduğunuz bir
dosyadan okunur** — `source_url` ve `read_on` alanlarıyla birlikte. Kit "Elsevier
özetleri 250 kelimedir", "TÜBİTAK 1001 bütçe tavanı şudur", "doçentlik için şu
kadar puan gerekir" cümlelerini **kurmaz**; bunlar hatırlanan bir DOI ile aynı
hata sınıfındadır ve tam olarak önlemeye çalıştıkları reddi doğururlar.

Bunun sonucu, katlanmaya değer bir sürtünmedir: otorite dosyası yoksa sonuç
`UNCHECKED`'tir, `OK` değil. "Bakılmadı" ile "sorun yok" aynı okunmamalıdır ve bu
ayrım, kitin tüm eksenlerinde aynı biçimde uygulanır.

## Bütünlük denetimlerinin sınırı — dürüst başarısızlık şekli

Kit, **metni ve raporlanan süreci** denetler: atıfın varlığı, iddianın kaynağıyla
uyumu, sayıların `analysis/` çıktılarıyla tutarlılığı, şekil/tablo bütünlüğü,
rapor standardı uyumu. Bunların bir kısmı örneklemelidir, bir kısmı dış
indekslerin kapsamına bağlıdır.

Kit, **gerçekten yapılmış olmayı** doğrulamaz. Prosedürlerin uygulandığını, ham
verinin gerçek olduğunu, analizlerin yeniden üretilebildiğini veya bir
müdahalenin tarif edildiği gibi gerçekleştiğini kanıtlayamaz.

Dürüst başarısızlık şekli açıktır: **uydurulmuş bir veriye dayanan çalışma,
uydurma tutarlı biçimde raporlandığı sürece kitin her kapısından geçer.**

Bu, daha çok kontrol ekleyerek kapatılacak bir boşluk değildir; araçların bittiği
ve insan, kurumsal ve tekrarlanabilirlik denetiminin başladığı yerdir.

## Ölçüm dürüstlüğü

Kitin kendi doğruluğu hakkındaki iddiaları [`eval/MEASUREMENT.md`](eval/MEASUREMENT.md)
içinde, sınırlarıyla birlikte yazılıdır. Özetle: deterministik denetleyiciler
etiketli altın kümelere karşı ölçülür ve her `pytest` koşusunda kapı olarak
çalışır; hakemin doğruluğu ancak **kullanıcının kendi** altın kümesiyle ölçülür;
taslak yazımı ve sentez **ölçülmez** ve öyle yazar.

Bir rakam yayımlamadan önce sorulacak soru şudur: bu sayı neyi ölçtü, ve neyi
ölçmediğini söylüyor mu?

## Uygun kullanım

- Araştırma desteği: literatür taraması, kaynak doğrulama, atıf denetimi
- Kendi verinizin analizi ve sonuçların şeffaf raporlanması
- Tez üretimi (YÖK yapısı, savunma hazırlığı dahil)
- Proje işleri: öneri, iş paketi/bütçe tutarlılığı, gelişme ve sonuç raporu
- Uyum belgeleri: etik kurul başvurusu, onam formu, veri yönetim planı
- Hizmet: hakem raporunuzun yapılandırılması (metni siz okursunuz), danışmanlıkta
  TİK raporu iskeleti
- Kariyer: atama dosyasının puan aritmetiği ve indeks doğrulaması, akademik CV
- Ders işleri: izlence, sınav–çıktı kapsaması, rubrik, akreditasyon matrisi
- Öğretim: araştırma yöntemi, hakemlik süreci ve akademik yazım gösterimi
- Kurumsal/ticari kullanım — MIT lisansı bunu serbest bırakır

## Önerilmeyen kullanım

- AI yardımını beyan etmeden, tümüyle insan-yazımı gibi sunmak
- İçerikle ilgilenmeden makale üretmek (kapılar tam olarak bunu zorlaştırmak
  için vardır)
- Simüle hakem geri bildirimini gerçek hakemlik yerine koymak
- Kitin bütünlük kapılarını, altta yatan araştırmanın doğruluğunun kanıtı
  olarak sunmak

## Bu sınırları değiştirmek

Yukarıdaki bir maddeyi aşan bir öneri, bir özellik talebi değil, bir
**kapsam değişikliği** talebidir. Süreç: bu belgede ilgili maddeyi, neden artık
geçerli olmadığının gerekçesiyle birlikte güncelleyin; kararı tarihli bir
girdiyle [`DECISIONS.md`](DECISIONS.md)'ye işleyin; ancak ondan sonra kod yazın.

Sınırın kendisi kadar önemli olan, sınırın **neden** oraya çizildiğinin
kaydıdır — gerekçesi yazılmamış bir sınır, altı ay sonra keyfi görünür ve sessizce
aşılır.
