# PROJE: Franchise/Bayi Komisyon ve Mutabakat Yönetim Sistemi

## 1. Bağlam ve Amaç

Şu anda elle tutulan bir Excel tablosuyla yürütülen bir iş sürecini web uygulamasına dönüştürüyoruz.
Referans aldığımız Excel şu işi yapıyordu (bir oto detaylandırma/PPF-kaplama franchise bayisinin
aylık mutabakat tablosuydu, ama sistemi **sektörden bağımsız, genel bir "franchise/bayi komisyon +
personel prim" motoru** olarak tasarlıyoruz — marka adı, sektör adı hardcode edilmeyecek):

- Bir merkez firma (**Franchisor**) ile bir bayi/şube (**Bayi**) arasında, dönemlik (genelde aylık)
  ciro üzerinden **kademeli oranlı gelir paylaşımı** yapılıyor (ör: 0-750.000 TL cироya kadar %30
  bayi payı, üzeri %35; belirli bir işlem kategorisinde ise sabit %15 gibi farklı bir oran).
- Bu paylaşıma göre **kimin kime, ne tutarda (KDV dahil/hariç) fatura kesmesi gerektiği** otomatik
  hesaplanıyor.
- Ayrıca bayi bünyesindeki **personele** (satış müdürü, satış danışmanları, servis müdürü, servis
  danışmanları, genel müdür gibi roller) **kademeli/basamaklı prim oranları** üzerinden prim
  hesaplanıyor (ör: bir satış danışmanının komple kaplama cirosunda sabit %7, diğer işlemlerde
  cirosuna göre %8/%9/%10 gibi artan dilim oranları).
- Ham veri, işlem bazlı bir kayıt defterinden geliyor: tarih, departman, müşteri, işlem/ürün,
  işlemi yapan personel, tutar (KDV hariç/dahil), tahsilat şekli, fatura durumu.

Bu deseni herhangi bir bayilik/franchise/komisyonlu satış modeline (oto kaplama zincirleri, güzellik
salonu franchise'ları, emlak ofisleri, sigorta acenteleri, servis ağları vb.) uyarlanabilecek genel
bir SaaS ürününe çeviriyoruz. **Gerçek müşteri/bayi verisi veya marka adı kullanılmayacak** — tüm
geliştirme ve demo/seed veri tamamen kurgusal olacak.

## 2. Hedef Kullanıcı ve Kullanım Senaryosu

- **Birincil kullanıcı:** Bir franchisor'ın merkez muhasebe/operasyon ekibi ya da bir bayinin
  kendi ofisi — dönem sonunda (ay sonunda) sisteme işlemleri girer/aktarır, sistem otomatik olarak
  mutabakat raporu ve personel prim tablosu üretir.
- **İkincil kullanıcı:** Birden fazla bayisi olan bir franchisor, tüm bayilerini tek panelden
  karşılaştırmalı görebilir.
- Kullanım sıklığı: Dönemsel (aylık) yoğun kullanım + günlük işlem girişi/takibi.

## 3. Kapsam — Çekirdek Modüller (MVP)

### 3.1. Tenant / Organizasyon Yapısı
- Çoklu kiracı (multi-tenant) mimari: Bir **Franchisor** hesabı altında birden fazla **Bayi/Şube**
  tanımlanabilir. Tek-bayi kullanım da desteklenmeli (küçük işletmeler doğrudan kendi hesabını açar).
- Her bayi için: ad, departman listesi (ör. Satış, Servis — kullanıcı tanımlı, sabit değil),
  vergi/fatura bilgileri.

### 3.2. Komisyon Kural Motoru (en kritik modül — genel/konfigüre edilebilir olmalı)
- Kademeli (tiered) oran tanımlama: dönemlik ciro aralıklarına göre farklı yüzdeler
  (ör. 0-750.000 → %30, 750.001+ → %35). Aralık sayısı ve sınırları sabit kodlanmayacak,
  kullanıcı arayüzünden tanımlanabilecek.
- İşlem kategorisi bazlı özel/sabit oran istisnaları (ör. "komple paket" kategorisi için ciro
  diliminden bağımsız sabit %15 gibi).
- Franchisor-Bayi payı dışında, **personel prim kuralları** için ayrı bir kademeli oran tablosu:
  rol bazlı (ör. Satış Müdürü, Satış Danışmanı, Servis Müdürü, Servis Danışmanı, Genel Müdür),
  her rol için kendi basamak/oran seti.
- Kural setleri **dönem bazlı versiyonlanmalı** — geçmiş ayların hesaplaması, oranlar sonradan
  değişse bile o dönemde geçerli olan kurallarla yeniden üretilebilmeli (audit/tekrarlanabilirlik
  için kritik).

### 3.3. İşlem Kaydı (Transaction Ledger)
- Alanlar: tarih, departman, müşteri adı, müşteri kimlik/vergi no (bkz. KVKK notu aşağıda),
  araç/ürün-hizmet bilgisi, işlem/kategori adı, işlemi yapan personel, KDV hariç tutar,
  KDV dahil tutar, tahsilat şekli, fatura durumu, açıklama.
- Manuel giriş (form) + toplu içe aktarma (CSV/Excel import — mevcut Excel şablonlarından
  geçişi kolaylaştırmak için önemli, satır eşleştirme/sütun mapping ekranı olsun).
- Kategoriler (ör. "komple kaplama" vs "diğer işlemler") kullanıcı tarafından tanımlanabilir
  olmalı, hardcode edilmemeli.

### 3.4. Mutabakat / Hesaplama Motoru
- Seçilen dönem (ay) ve bayi için: toplam ciroyu departman ve kategoriye göre kırar, geçerli
  kademeli kurala göre Franchisor/Bayi payını hesaplar.
- KDV hesaplaması (oran kullanıcı tanımlı olsun, sabit %20 hardcode edilmesin — mevzuat değişebilir).
- "Kim kime ne tutar fatura kesmeli" çıktısı: KDV hariç tutar, KDV tutarı, KDV dahil toplam.
- Sonuç raporu PDF/Excel olarak dışa aktarılabilmeli.

### 3.5. Personel Prim Paneli
- Personel bazlı dönemlik ciro girişi/otomatik toplanması (işlem kayıtlarından personel alanına
  göre otomatik toplanabilir).
- Role ait kademeli oran tablosuna göre otomatik prim hesabı.
- Personel bazlı ve toplam (genel toplam) prim raporu.

### 3.6. Dashboard / Raporlama
- Dönem bazlı ciro trendi, bayi karşılaştırması (franchisor için), departman kırılımı,
  en yüksek cirolu personel/kategori gibi özet göstergeler.

### 3.7. Kullanıcı Rolleri ve Yetkilendirme
- En az 3 rol: Franchisor Admin (tüm bayileri görür, kuralları tanımlar), Bayi Admin (sadece
  kendi bayisini yönetir, kuralları göremez/değiştiremez — sadece uygular), Salt Okunur/Rapor
  görüntüleyici.

## 4. Teknik Gereksinimler

- **Backend:** Python + FastAPI, PostgreSQL (finansal/kademeli hesaplamalar ve ilişkisel veri
  yapısı için uygun). SQLAlchemy + Alembic migration.
- **Frontend:** React (TypeScript), tamamen **Türkçe arayüz**. Tablo-ağırlıklı ekranlar (işlem
  listesi, kural tanımlama, raporlar) için net, GUI-first, sade bir tasarım — süslemeden çok
  okunabilirlik ve veri girişi hızı önceliklidir.
- **Kimlik doğrulama:** JWT tabanlı, çoklu tenant izolasyonu (bir bayi kullanıcısı başka bayinin
  verisini asla göremeyecek şekilde satır/organizasyon bazlı erişim kontrolü — bu güvenlik açığı
  kritik, test edilmeli).
- **Sayısal hassasiyet:** Tüm parasal hesaplamalarda ondalık hata birikimini önlemek için
  `Decimal` kullanılacak, float ile para hesaplanmayacak.
- **Denetim (audit) günlüğü:** Kural değişiklikleri, işlem düzenlemeleri/silmeleri loglanmalı
  (kim, ne zaman, ne değiştirdi) — finansal mutabakat sistemi olduğu için izlenebilirlik şart.
- **Yerelleştirme:** Türkçe ondalık/tarih formatı (virgüllü ondalık, gg.aa.yyyy), TL para birimi
  gösterimi; ama gelecekte başka para birimi/dil eklenebilecek şekilde i18n altyapısı kurulsun.

## 5. Veri Modeli (taslak — geliştirici bu üzerine detaylandırsın)

```
Tenant (Franchisor)
  └── Branch (Bayi/Şube)
        └── Department (Satış, Servis, ... — kullanıcı tanımlı)
        └── Employee (ad, rol, departman)
        └── Period (ay/yıl — dönem)
              └── Transaction (tarih, departman, kategori, personel, müşteri bilgisi,
                                tutar_kdv_hariç, tutar_kdv_dahil, tahsilat_şekli, fatura_durumu)
        └── CommissionRuleSet (versiyonlu — geçerlilik tarihi aralığı ile)
              └── TierRule (alt_sınır, üst_sınır, oran, uygulanan_taraf: franchisor/bayi/personel_rolü)
              └── CategoryOverrideRule (kategori_adı, sabit_oran)
        └── ReconciliationReport (dönem, hesaplanmış sonuçlar — snapshot olarak saklanır,
                                    kural sonradan değişse bile geçmiş rapor sabit kalır)
```

## 6. KVKK / Veri Güvenliği (bu ürünü satılabilir kılmak için zorunlu, atlanmasın)

- Sistem müşteri adı, TC kimlik/vergi numarası gibi kişisel veri saklayacağı için **KVKK
  (6698 sayılı Kanun) uyumluluğu** tasarımın parçası olmalı:
  - TC kimlik no gibi alanlar veritabanında düz metin yerine en azından maskelenmiş
    gösterim (arayüzde son 4 hane hariç gizli) + erişim loglaması.
  - Veri saklama süresi/silme politikası için altyapı (hard delete / anonimleştirme fonksiyonu).
  - Tenant'lar arası veri sızıntısını önleyecek satır bazlı erişim kontrolü (bkz. madde 4).
- Gerçek müşteri verisiyle test/demo yapılmayacak; seed/test verisi Faker (Türkçe locale) ile
  üretilecek.

## 7. Geliştirme Aşaması Önerisi

1. **Faz 1 (MVP):** Tek tenant, işlem kaydı CRUD + CSV import, tek seviyeli kademeli komisyon
   kuralı, temel mutabakat raporu (ekranda + Excel export).
2. **Faz 2:** Personel prim modülü, kategori bazlı istisna kuralları, dönem versiyonlama.
3. **Faz 3:** Çoklu bayi (multi-tenant) yapı, roller/yetkilendirme, dashboard/karşılaştırma.
4. **Faz 4:** PDF rapor üretimi, bildirimler (dönem kapanışı hatırlatması), denetim logu arayüzü.

## 8. Kabul Kriterleri (örnek test senaryoları)

- Bir dönemde 800.000 TL KDV hariç ciro girildiğinde, 0-750.000 için %30 ve 750.001+ için %35
  kuralı tanımlıysa, sistem cironun doğru şekilde dilimlere bölünüp karma oranla hesaplandığını
  (kademeli mi yoksa "tüm tutara en üst dilim oranı" mı uygulanacağı **netleştirilip** buna göre
  kodlanmalı — referans Excel'de tüm tutara tek oran uygulanıyordu, dilimli/marjinal hesaplama
  değildi; bu davranış açıkça UI'da belirtilsin ki kullanıcı hangi mantığın çalıştığını bilsin).
- Kategori istisnası olan bir işlem (ör. "komple paket"), genel kademeli kuralı değil kendi sabit
  oranını kullanmalı.
- Geçmiş bir dönemin raporu, kurallar güncel tarihte değiştirilse bile değişmemeli (snapshot testi).
- Bir bayi kullanıcısı API'den doğrudan endpoint çağırarak başka bir bayinin verisine erişemiyor
  olmalı (yetkilendirme testi).

## 9. Açıkça Dışında Bırakılanlar (scope dışı — MVP'de yapılmayacak)

- Gerçek zamanlı entegre POS/ödeme sistemi entegrasyonu (ileride API ile eklenebilir, MVP'de yok).
- Otomatik e-fatura kesimi (yalnızca "kesilmesi gereken tutar" raporu üretilecek, fatura kesme
  işlemi kullanıcının kendi e-fatura sisteminde manuel yapılacak — entegrasyon ayrı bir faz).

---

**Geliştirici notu:** Kod tabanı temiz, test edilebilir ve bakımı kolay olacak şekilde
yazılmalı (özellikle komisyon hesaplama motoru için unit testler zorunlu — bu modülün hatası
doğrudan para kaybına yol açar). Her yeni özellik için önce veri modeli/API sözleşmesini
netleştir, sonra implementasyona geç.
