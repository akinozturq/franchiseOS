# PROJE: Franchise/Bayi Komisyon Sistemi — FAZ 4 (Kural Versiyonlama & Dönem Kapama, PDF Export, Bildirim/E-Fatura Altyapısı)

Faz 1-2-3 tamamlandı (54/54 test yeşil): tek/çoklu bayi, komisyon+prim motoru, kategori istisnaları,
RLS ile veri izolasyonu, RBAC, dashboard. Bu faz, sistemin son bilinen kapsamlı eksiğini kapatıyor:
**geçmiş dönem raporlarının kurallardan bağımsız/değişmez olması.**

## 0. Mimari Karar: Geçmiş Dönemleri Koruma Stratejisi (gerekçeli)

Bu sorunun **tek bir doğru çözümü yok, iki farklı riski birden kapatmak gerekiyor** — bu yüzden iki
mekanizmayı **birlikte** kuruyoruz, biri diğerinin yerine geçmiyor:

**A) Kural Versiyonlama (effective_from / effective_to) — "doğru hesaplama" sorununu çözer.**
Şu anki sistemde `CommissionTier`, `RoleCommissionTier`, `TransactionCategory` (istisna oranları)
kayıtları "canlı" — bir satır güncellenirse eski değeri kaybolur. Biri Mart ayı kuralını bugün
değiştirirse, Mart raporu yarın yeniden hesaplansa **yanlış** (bugünkü) oranla hesaplanır. Bunu
çözmek için: kural tablolarına `effective_from` (zorunlu) ve `effective_to` (nullable — boşsa "hâlâ
geçerli") eklenir. Bir kural "değiştirildiğinde" satır UPDATE edilmez; mevcut satırın
`effective_to`'su o güne ayarlanır ve yeni değerlerle **yeni bir satır** eklenir. Herhangi bir
geçmiş dönem, hesaplama motoruna her zaman "bu tarihte hangi kural geçerliydi" sorusu sorularak
doğru şekilde yeniden üretilebilir.

**B) Dönem Kapama + Snapshot — "resmi belge" sorununu çözer.**
Versiyonlama tek başına yeterli değil, çünkü: (1) versiyonlama mantığında ileride bir kod hatası
olursa (ör. tarih aralığı sorgusu yanlış yazılırsa) geçmiş raporlar yine sessizce değişebilir,
(2) muhasebe/hukuki açıdan "resmen kesilen/onaylanan" bir mutabakat raporunun, versiyonlama sistemi
ne kadar sağlam olursa olsun, **tek bir donmuş kopyası** olmalı — bu, kanıt niteliğinde bir belge.
Bu yüzden: bir dönem "kapatıldığında" (`PeriodClosure` kaydı oluşturulduğunda), o anki mutabakat +
prim raporlarının **tam sonucu** (kullanılan kural değerleri dahil) JSON olarak donup saklanır.
Kapatılmış bir dönem açıldığında sistem **canlı hesaplama yapmaz**, doğrudan bu donmuş JSON'u
gösterir. Kapatma işlemi geri alınamaz olmasa da (düzeltme gerekebilir), geri almak ayrı bir yetki
(sadece Franchisor Admin) ve zorunlu bir gerekçe metni gerektirir, ve işlem audit log'a yazılır.

Özet: **versiyonlama = motorun her zaman doğru hesaplayabilmesi; snapshot+kapama = resmi olarak
onaylanmış bir dönemin bir daha asla değişmemesi.** İkisi tamamlayıcı, tek başına hiçbiri yeterli
değil.

## 1. Kapsam — Kural Versiyonlama

- `CommissionTier`, `RoleCommissionTier`, `TransactionCategory.general_override_rate` ve
  `TransactionCategory.bonus_override_rate` alanları versiyonlanabilir hale getirilir (yukarıdaki
  effective_from/to modeliyle).
- Kural düzenleme ekranlarında (Faz 1/2'deki CommissionTiersView, StaffView'daki rol dilimleri,
  CategoriesView) artık "güncelle" işlemi arka planda "eskiyi kapat + yenisini aç" olarak çalışır;
  kullanıcı arayüzünde bu şeffaf olsun (kullanıcı hâlâ tek bir "Kaydet" butonuna basar), ama bir
  "Kural Geçmişi" görünümü eklenir — bir kuralın zaman içindeki tüm değişiklikleri (kim, ne zaman,
  eski değer, yeni değer) listelenebilsin.
- Hesaplama motorları (`commission_service.py`, `bonus_service.py`) artık "şu an geçerli kural"
  yerine "**parametre olarak verilen tarihte** geçerli olan kural" ile çalışacak şekilde
  güncellenir. Bu, geriye dönük tüm testlerin (Faz 1-2-3) hâlâ doğru sonucu verdiğini garanti
  edecek şekilde yapılmalı — mevcut testler bugünün tarihiyle çağrıldığında hâlâ aynı sonucu
  vermeli (regresyon testi).

## 2. Kapsam — Dönem Kapama (Period Closure)

- Yeni model: `PeriodClosure` (branch_id, year, month, closed_at, closed_by_user_id,
  reconciliation_snapshot [JSON], bonus_snapshot [JSON], reopened_at [nullable],
  reopened_by_user_id [nullable], reopen_reason [nullable]).
- Sadece Franchisor Admin bir dönemi kapatabilir (Bayi Admin talep edebilir ama onay
  Franchisor'da — basit bir "Kapatma Talep Et" / "Onayla ve Kapat" akışı yeterli, karmaşık bir
  workflow motoru kurulmasın).
- Kapatma anında: o dönemin mutabakat raporu ve personel prim raporu, o an geçerli kurallarla
  hesaplanıp **tam sonuç** (tüm ara değerler dahil — hangi tutara hangi oranın uygulandığı, kim
  kime ne kadar fatura kesti, personel bazlı prim detayları) JSON olarak `PeriodClosure`'a yazılır.
- Kapalı bir dönem: (a) işlem eklenemez/düzenlenemez/silinemez (API seviyesinde engellenir), (b)
  raporlar canlı hesaplama yerine snapshot'tan gösterilir, (c) arayüzde belirgin bir "🔒 Kapalı
  Dönem" rozetiyle işaretlenir.
- Yeniden açma (reopen): sadece Franchisor Admin, zorunlu bir gerekçe metniyle. Yeniden açıldığında
  dönem tekrar düzenlenebilir hale gelir ama **eski snapshot silinmez**, `PeriodClosure` kaydı
  `reopened_at` ile işaretlenip arşivde tutulur (aynı dönem tekrar kapatılırsa yeni bir
  `PeriodClosure` satırı oluşur — böylece "bu dönem kaç kez açılıp kapandı, her seferinde ne
  değişti" tam olarak izlenebilir).

## 3. Kapsam — PDF Export

- Mutabakat raporu ve personel prim raporu için PDF çıktısı (Excel export'a ek olarak, onun yerine
  değil). Kapalı bir dönem için PDF, snapshot'taki donmuş veriden üretilir (canlı hesaplamadan
  değil) — bu, "resmi belge" tutarlılığını PDF'e de taşır.
- PDF'de bayi/franchisor unvan-vergi bilgileri, dönem, hesaplama detayları (hangi dilime göre
  hangi oran uygulandı, kategori istisnaları varsa ayrıca gösterilsin) ve rapor üretim/kapatma
  tarihi + kapatan kullanıcı bilgisi yer alsın (audit izlenebilirliği PDF'e de yansısın).
- Kullanılacak kütüphane: WeasyPrint veya ReportLab (agent, projenin mevcut Python stack'iyle en
  uyumlu olanı seçip gerekçesini kısaca belirtsin — HTML şablon + WeasyPrint genelde daha az
  bakım gerektirir, ama karar agent'a bırakılabilir).

## 4. Kapsam — Bildirim ve E-Fatura Altyapısı (yalnızca altyapı, tam entegrasyon değil)

Bu maddede **gerçek bir e-fatura entegratörüne (ör. bir GİB e-fatura API'si) bağlanmıyoruz** —
sadece ileride böyle bir entegrasyonun takılabileceği bir iskelet kuruyoruz:

- `Notification` modeli (branch_id, type, payload [JSON], created_at, sent_at [nullable],
  channel: email/in-app) ve basit bir in-app bildirim listesi (arayüzde bir zil ikonu — "Mart
  dönemi kapatılmaya hazır", "Yeni bayi eklendi" gibi olaylarda tetiklenir).
- Dönem sonu hatırlatması: her ayın belirli bir gününde (ör. ayın 3'ü), henüz kapatılmamış bir
  önceki dönem varsa ilgili Bayi Admin ve Franchisor Admin'lere in-app bildirim üretilsin (gerçek
  e-posta gönderimi gerekmiyor, altyapı + in-app yeterli — e-posta entegrasyonu istenirse ayrı bir
  faz/eklenti olarak ele alınır).
- E-fatura için: `PeriodClosure` snapshot'ı zaten "kimin kime ne kadar fatura kesmesi gerektiği"
  bilgisini JSON olarak içerdiğinden, bu veriyi dışarıya **standart bir JSON/webhook formatında**
  export edebilen bir endpoint (`GET /api/v1/period-closures/{id}/invoice-data`) eklensin — bu,
  ileride bir e-fatura sistemine bu endpoint'i çağırarak entegre olma imkânı bırakır, ama entegrasyonun
  kendisi bu fazın kapsamında değil.

## 5. Bu Fazda YAPILMAYACAKLAR

- Gerçek e-fatura entegratörü bağlantısı (sadece madde 4'teki iskelet/endpoint)
- Gerçek e-posta gönderimi (sadece in-app bildirim + ileride eklenebilecek altyapı)
- Workflow/onay motoru (dönem kapama onayı basit bir buton + rol kontrolü, ayrı bir "approval
  engine" kurulmuyor)
- Franchisor'ın üstüne üçüncü bir hiyerarşi seviyesi eklenmesi

## 6. Teknik Gereksinimler

- Versiyonlama migration'ı geriye dönük çalıştırılıp mevcut tüm kural satırları
  `effective_from = <ilk oluşturulma tarihi>`, `effective_to = NULL` olarak taşınmalı — hiçbir
  mevcut kural kaybolmamalı (yine öncesi/sonrası sayısal karşılaştırma raporlanacak).
  Regresyon testi olarak: Faz 1-2-3'teki tüm mevcut testler bu migration sonrası hâlâ yeşil kalmalı.
- Dönem kapama testleri: kapalı bir döneme işlem eklemeye çalışmanın engellendiği, snapshot'ın
  canlı kural değişikliğinden etkilenmediği (kapatıldıktan sonra kural değiştirilip rapor tekrar
  açılırsa hâlâ eski/donmuş değerleri gösterdiği) açıkça test edilsin.
- PDF export testleri: en azından "hata vermeden üretiliyor" ve "kapalı dönem için snapshot
  verisiyle, açık dönem için canlı hesaplamayla üretiliyor" ayrımı test edilsin.

## 7. Kabul Kriterleri

- [ ] Kural versiyonlama kurulu; mevcut kurallar kayıpsız migrate edilmiş (sayısal karşılaştırma
      raporlanmış), Faz 1-2-3 testleri hâlâ yeşil.
- [ ] Bir kural değiştirildiğinde eski değer korunuyor (yeni effective_to ile kapanıyor), geçmiş
      dönem hâlâ eski oranla doğru hesaplanabiliyor — test edilmiş.
- [ ] "Kural Geçmişi" ekranı bir kuralın zaman içindeki değişikliklerini gösteriyor.
- [ ] Dönem kapama: Franchisor Admin bir dönemi kapatabiliyor, snapshot doğru üretiliyor, kapalı
      döneme işlem eklenemiyor/düzenlenemiyor (API seviyesinde engellenmiş, test edilmiş).
- [ ] Kapalı dönem raporu, kapatıldıktan sonra kurallar değişse bile hep aynı (donmuş) sonucu
      gösteriyor — test edilmiş.
- [ ] Yeniden açma: gerekçe zorunlu, eski snapshot arşivde kalıyor, kim ne zaman açtı/kapattı tam
      izlenebilir.
- [ ] PDF export: mutabakat ve prim raporları için çalışıyor, kapalı dönemde snapshot'tan, açık
      dönemde canlı hesaplamadan üretildiği doğrulanmış.
- [ ] In-app bildirim: kapatılmamış önceki dönem için hatırlatma üretiliyor.
- [ ] `GET /api/v1/period-closures/{id}/invoice-data` endpoint'i kapalı bir dönem için doğru
      JSON döndürüyor.
- [ ] Tüm önceki fazlardan kalan testler (54 test + bu fazda eklenenler) yeşil.

## 8. Çalışma Şekli (agent için)

- Önce kural versiyonlama modelini ve hesaplama motorlarının "tarihe göre kural bulma" mantığını
  kur, mevcut testlerin hâlâ geçtiğini kanıtla — bu fazın temel taşı, geri kalan her şey buna
  dayanıyor.
- Sonra dönem kapama + snapshot mekanizmasını kur.
- PDF export ve bildirim/e-fatura iskeleti en son, çünkü bunlar önceki iki mekanizmanın üzerine
  ince bir katman.
- Migration'dan sonra mutlaka öncesi/sonrası sayısal karşılaştırma raporla.
- Emin olmadığın bir tasarım kararında (ör. PDF kütüphanesi seçimi, bildirim tetikleme sıklığı)
  varsayım yapıp öylece devam etmek yerine sor.
