# PROJE: Franchise/Bayi Komisyon Sistemi — FAZ 1 (MVP)

Bu, çok aşamalı bir projenin **sadece ilk fazı**. Bu promptta tanımlanmayan hiçbir özelliği
(çoklu bayi/tenant, personel prim modülü, roller/yetkilendirme, dashboard, PDF export, kategori
istisna kuralları, dönem versiyonlama) **şimdilik ekleme** — bunlar sonraki fazlarda ayrı promptlarla
gelecek. Kapsam dışına çıkıp "ileride lazım olur" diye ekstra modül/tablo/endpoint üretme; YAGNI
prensibiyle çalış. Amaç: küçük, çalışan, test edilmiş bir MVP.

## 1. Bağlam ve Amaç

Franchise/bayilik modeliyle çalışan işletmelerde (oto kaplama, güzellik salonu, servis ağı vb. —
sektörden bağımsız, genel bir sistem), merkez firma (**Franchisor**) ile bayi arasında dönemlik
ciro üzerinden **kademeli oranlı gelir paylaşımı** yapılır (ör: 0-750.000 TL ciroya kadar bayi payı
%30, 750.001 TL ve üzeri %35). Bu MVP, bu sürecin en temel halini — tek bir bayi için, tek seviyeli
kademeli kural ile — dijitalleştiriyor. Şu anda bu iş Excel'de elle yapılıyor; amaç manuel hata
riskini azaltmak ve hesaplamayı otomatikleştirmek.

**Önemli:** Gerçek müşteri/bayi verisi veya marka adı kullanılmayacak. Tüm geliştirme, test ve seed
verisi tamamen kurgusal/anonim olacak (Faker ile üretilmiş Türkçe isimler, uydurma vergi no vb. —
gerçek TC kimlik numarası algoritmasına uyan ama gerçek kişiye ait olmayan test verisi kullan).

## 2. Faz 1 Kapsamı — Tam Liste

Bu fazda **sadece** aşağıdakiler var:

1. **Tek tenant (tek bayi)** — çoklu bayi/franchisor hiyerarşisi yok. Sistemde bir bayi vardır,
   giriş yapan herkes o bayinin verisini görür. (Veri modelinde ileride çoklu tenant'a
   genişleyebilecek şekilde bir `branch_id` alanı bırak ama şimdilik tek satırlık statik/seed veri
   olarak kullan — üzerine karmaşık tenant yönetimi UI'ı kurma.)
2. **Departman tanımı** — kullanıcı tanımlı basit bir liste (ör. "Satış", "Servis") — CRUD.
3. **İşlem kaydı (Transaction) CRUD** — alanlar:
   - tarih
   - departman (departman listesinden seçim)
   - müşteri adı
   - müşteri kimlik/vergi no (metin alanı, format doğrulaması yapma, sadece maskeli göster —
     bkz. madde 6)
   - işlem/kategori adı (serbest metin veya basit bir kategori listesi — kategori bazlı özel oran
     mantığı YOK, bu Faz 2'de)
   - işlemi yapan personel (şimdilik serbest metin alanı, ayrı bir Personel tablosu/CRUD'u YOK —
     Faz 2'de gelecek)
   - KDV hariç tutar
   - KDV oranı (kullanıcı tanımlı, varsayılan %20 ama sabit kodlanmasın)
   - KDV dahil tutar (KDV hariç tutar × (1+KDV oranı) olarak otomatik hesaplanır, kullanıcı elle
     de girebilir/düzeltebilir)
   - tahsilat şekli (serbest metin)
   - fatura durumu (serbest metin veya basit bir seçim listesi: "Faturalandı" / "Bekliyor")
   - açıklama (opsiyonel serbest metin)
4. **CSV/Excel içe aktarma** — kullanıcı bir CSV/XLSX dosyası yükler, sütunları ekrandaki alanlarla
   eşleştirir (basit bir "sütun eşleştirme" ekranı — otomatik sütun adı tahmini yapılabilir ama
   kullanıcı onaylamadan içe aktarma yapılmasın), önizleme gösterilir, onaylanınca toplu kayıt
   oluşturulur. Hatalı/eksik satırlar raporlanır, işlemi durdurmaz (geçerli satırlar aktarılır,
   hatalı satırlar ayrı listelenir).
5. **Tek seviyeli kademeli komisyon kuralı tanımlama** — kullanıcı arayüzünden:
   - Alt sınır / üst sınır / oran üçlüsünden oluşan dilimler tanımlanabilir (ör. 0-750.000 → %30,
     750.001+ (üst sınır boş = sonsuz) → %35). Dilim sayısı sabit değil, en az 1 en fazla makul
     bir sayı (ör. 10) dilim eklenebilsin.
   - **Hesaplama mantığı:** Referans süreçte tüm dönem cirosu tek bir dilime düşer ve o dilimin
     oranı **tüm tutara** uygulanır (marjinal/kademeli vergi dilimi gibi parça parça değil). Yani
     800.000 TL ciro, "750.001+ → %35" dilimine düşüyorsa, 800.000'in tamamına %35 uygulanır,
     ilk 750.000'e %30 + kalan 50.000'e %35 şeklinde bölünmez. Bunu kodda böyle uygula ve arayüzde
     kullanıcıya bu davranışı açıkça belirten kısa bir açıklama metni göster (ör. bir tooltip/info
     kutusu: "Seçilen dilim oranı, dönem cirosunun tamamına uygulanır.").
6. **Mutabakat raporu** — bir dönem (ay-yıl) seçilince:
   - O dönemdeki tüm işlemlerin toplam KDV hariç cirosu hesaplanır.
   - Uygulanan dilim oranına göre Franchisor payı ve Bayi payı (tutar olarak) hesaplanır.
   - "Kesilmesi gereken fatura" bilgisi: hangi tarafın hangi tarafa ne kadar (KDV hariç + KDV +
     KDV dahil toplam) fatura kesmesi gerektiği gösterilir.
   - Departman bazlı kırılım da gösterilsin (her departmanın cirosu ayrı ayrı, toplamı genel
     ciroyla eşleşmeli).
   - Rapor ekranda tablo olarak gösterilir + **Excel'e (xlsx) export** edilebilir.
7. **Basit kimlik doğrulama** — tek kullanıcı rolü yeterli (rol ayrımı yok, Faz 3'te gelecek).
   Kullanıcı adı/şifre ile giriş, JWT ile oturum. Kayıt (signup) ekranı gerekmiyor — ilk kullanıcı
   seed/migration ile oluşturulsun.

## 3. Bu Fazda YAPILMAYACAKLAR (bilinçli olarak dışarıda)

- Çoklu bayi/franchisor hiyerarşisi ve tenant yönetim ekranları
- Personel tablosu, personel prim hesaplama modülü
- Kategori bazlı özel/istisna oran kuralları (ör. "komple paket" için sabit oran)
- Kural versiyonlama / geçmiş dönem snapshot koruması (Faz 1'de kurallar değişirse geçmiş
  raporlar da yeniden hesaplanabilir; bu "sorun" Faz 2'de ele alınacak — şimdilik basit tutulacak)
- Roller/yetkilendirme (admin/salt okunur ayrımı)
- Dashboard, grafikler, bayi karşılaştırmaları
- PDF export (sadece Excel export yeterli)
- E-fatura entegrasyonu
- Bildirimler/hatırlatmalar

## 4. Teknik Gereksinimler

- **Backend:** Python + FastAPI, PostgreSQL, SQLAlchemy + Alembic migration.
- **Frontend:** React (TypeScript), tamamen **Türkçe arayüz**, sade/GUI-first, tablo-ağırlıklı
  ekranlar (veri girişi hızı ve okunabilirlik önceliği; gereksiz görsel süsleme yok).
- **Sayısal hassasiyet:** Tüm parasal alanlarda backend'de `Decimal` kullan, `float` ile para
  hesabı yapma. Frontend'de gösterim Türkçe ondalık formatında (virgül ayraç, binlik nokta) olsun.
- **Test:** Komisyon hesaplama fonksiyonu için kapsamlı unit testler zorunlu — özellikle dilim
  sınırlarındaki (tam sınır değeri, sınırın bir altı/üstü) uç durumlar test edilsin. CSV import
  için de en az birkaç test senaryosu (geçerli dosya, eksik sütun, bozuk satır) olsun.
- **Proje yapısı:** Backend ve frontend ayrı klasörlerde (`backend/`, `frontend/`), her ikisi için
  de README (kurulum + çalıştırma adımları) yaz.

## 5. Veri Modeli (Faz 1 için yeterli olan minimum)

```
Branch (tek satır, seed ile oluşturulur — ad, vergi bilgileri)
  └── Department (ad)
  └── Transaction (tarih, department_id, müşteri_adı, müşteri_kimlik_no,
                     işlem_adı, personel_adı [serbest metin], kdv_hariç_tutar,
                     kdv_oranı, kdv_dahil_tutar, tahsilat_şekli, fatura_durumu, açıklama)
  └── CommissionTier (alt_sınır, üst_sınır [nullable=sonsuz], oran)
User (kullanıcı_adı, şifre_hash)
```

## 6. KVKK / Veri Güvenliği (Faz 1'de dahi atlanmasın)

- Müşteri kimlik/vergi no alanı listelerde/arayüzde **maskeli** gösterilsin (ör. son 4 hane
  hariç `*` ile gizli), detay ekranında yetkili kullanıcı görebilir (Faz 1'de tek rol olduğu için
  bu basit tutulabilir ama maskeleme UI'da olsun).
- Seed/test verisi kesinlikle gerçek kişilere ait olmayacak (Faker/Türkçe locale kullan).

## 7. Kabul Kriterleri (Faz 1 "bitti" sayılması için)

- [ ] Departman CRUD çalışıyor.
- [ ] İşlem kaydı CRUD çalışıyor (liste, ekle, düzenle, sil).
- [ ] CSV/XLSX içe aktarma: sütun eşleştirme ekranı, önizleme, hatalı satır raporu ile birlikte
      uçtan uca çalışıyor.
- [ ] Komisyon dilim kuralları tanımlanabiliyor (en az 2 dilim ile test edilmiş).
- [ ] Bir dönem seçildiğinde: toplam ciro doğru hesaplanıyor, doğru dilim oranı bulunuyor
      (sınır değerinde dahi doğru dilime düşüyor — örn. tam 750.000 TL'nin hangi dilimde
      sayılacağı net tanımlı ve test edilmiş: `>=` mi `>` mi, kodda ve testte tutarlı olsun),
      Franchisor/Bayi payı ve KDV dahil fatura tutarları doğru çıkıyor.
- [ ] Departman bazlı kırılımın toplamı genel ciro ile birebir eşleşiyor (yuvarlama hatası yok).
- [ ] Rapor Excel olarak indirilebiliyor ve indirilen dosyadaki rakamlar ekrandakiyle birebir aynı.
- [ ] Giriş/oturum (JWT) çalışıyor, girişsiz kullanıcı API'ye erişemiyor.
- [ ] Komisyon hesaplama modülü için unit testler yeşil, en az dilim sınırı uç durumları kapsanmış.

## 8. Çalışma Şekli (agent için)

- Önce veri modelini ve komisyon hesaplama fonksiyonunun imzasını/testlerini yaz, onayımı almadan
  ilerleme — küçük, gözden geçirilebilir adımlarla ilerle (önce backend veri modeli + migration,
  sonra hesaplama motoru + testleri, sonra API endpoint'leri, sonra frontend).
- Her adımdan sonra çalıştığını gösteren kısa bir özet ver (hangi dosyalar değişti, testler geçti
  mi).
- Emin olmadığın bir tasarım kararında (ör. sınır değeri davranışı, kategori adlandırması)
  varsayım yapıp öylece devam etmek yerine sor.
