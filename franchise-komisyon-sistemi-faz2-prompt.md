# PROJE: Franchise/Bayi Komisyon Sistemi — FAZ 2 (Personel Prim Modülü ve Kategori İstisnaları)

Bu, Faz 1 (MVP) üzerine inşa edilen ikinci faz. Faz 1'de tanımlanmayan hiçbir özelliği (çoklu
bayi/tenant, roller/yetkilendirme, dashboard, PDF export, kural versiyonlama/dönem snapshot,
e-fatura entegrasyonu) **bu fazda da ekleme** — bunlar hâlâ kapsam dışı, sonraki fazlara ait.
Faz 1'deki YAGNI prensibi burada da geçerli: sadece aşağıda tanımlanan işi yap.

## 1. Bağlam ve Amaç

Faz 1'de franchisor-bayi arası ciro paylaşımı ve mutabakat raporu çalışır hale geldi. Faz 2'nin
amacı, referans süreçteki ikinci büyük parçayı eklemek: **bayi bünyesindeki personelin, kendi
yaptığı işlemlerin cirosuna göre kademeli prim hakkı** kazanması, ve komisyon hesaplamasında
**belirli işlem kategorilerinin genel kademeli kuraldan muaf olup sabit oran kullanması**
(ör. "komple kaplama" kategorisi ciro dilimine bakılmaksızın her zaman sabit bir oran kullanır).

## 2. Faz 2 Kapsamı — Tam Liste

### 2.1. Personel (Employee) Tablosu ve CRUD
- Faz 1'de işlem kaydındaki "personel" alanı serbest metindi. Bunu artık gerçek bir tabloya
  taşıyoruz:
  - Alanlar: ad-soyad, **rol** (ör. Satış Müdürü, Satış Danışmanı, Servis Müdürü, Servis
    Danışmanı, Genel Müdür — roller sabit kodlanmasın, kullanıcı tanımlı bir liste olsun, ama
    Faz 1 seed verisindeki departmanlarla tutarlı bir varsayılan set gelsin), departman
    (departmana bağlı olabilir ama zorunlu olmasın — Genel Müdür gibi roller departmandan
    bağımsız olabilir), aktif/pasif durumu.
- **Geriye dönük veri taşıma (migration):** Faz 1'de girilmiş olan serbest metin personel
  adlarını, mümkün olduğunca otomatik eşleştirip yeni Employee tablosuna bağlayan bir migration/
  script yazın (aynı isim → aynı Employee kaydı). Eşleşmeyenler için "atanmamış personel" listesi
  çıkarın, kullanıcı arayüzden elle eşleştirebilsin. Var olan Transaction kayıtlarının hiçbiri
  kaybolmasın veya sessizce yanlış personele bağlanmasın.
- `Transaction.personel_adı` (serbest metin) alanı artık `Transaction.employee_id` (foreign key)
  olacak şekilde şemayı güncelleyin; import ekranında da personel adı girildiğinde otomatik
  eşleştirme + eşleşmezse "yeni personel oluştur" önerisi sunulsun.

### 2.2. Rol Bazlı Kademeli Prim Kural Tablosu
- Her rol için ayrı bir kademeli oran seti tanımlanabilsin (Faz 1'deki `CommissionTier`
  yapısına benzer ama role bağlı): alt sınır, üst sınır, oran.
- Faz 1'deki genel komisyon dilimlerinden **tamamen ayrı** bir tablo/kavram olduğu net olsun —
  ikisi karıştırılmasın (biri franchisor-bayi payını, diğeri personel primini belirliyor).
- Bir rol için birden fazla "prim türü" olabilir (referans süreçte örneğin bir satış danışmanının
  "komple kaplama" işlemlerinde sabit oran, "diğer işlemler" cirosunda kademeli oran vardı) —
  bu ihtiyacı madde 2.3'teki kategori mekanizmasıyla birlikte çözün: rol bazlı kademeli tablo
  "genel ciro" için, kategori istisnaları ise kendi sabit oranını kullanır (bkz. 2.3).

### 2.3. Kategori Bazlı İstisna/Sabit Oran Kuralları
- Faz 1'de işlem kaydındaki "işlem/kategori adı" serbest metindi. Bunu, tanımlı bir
  **TransactionCategory** listesine bağlayın (kullanıcı yönetebilir: ekle/düzenle/sil), ama
  eski serbest metin verisini de kaybetmeden migrate edin (2.1'deki personel migration'ıyla
  aynı yaklaşım: otomatik eşleştir, eşleşmeyenleri kullanıcıya göster).
- Her kategori için opsiyonel olarak:
  - **Genel komisyon kuralında (franchisor-bayi payı) istisna:** kategoriye ait cironun, genel
    kademeli dilim yerine sabit bir oranla hesaplanacağını işaretleyebilme (Faz 1'deki referans
    örnekte "komple kaplama" için sabit %15 gibi).
  - **Personel prim kuralında istisna:** kategoriye ait cironun, rol bazlı kademeli tablo yerine
    sabit bir oranla prim üreteceğini işaretleyebilme (referans örnekte "komple kaplama" için
    satış danışmanına sabit %7 gibi).
- Bu iki istisna birbirinden bağımsız olsun (bir kategori sadece birinde istisnalı olabilir).
- **Hesaplama sırası netleştirilsin:** Bir dönem hesaplanırken önce işlemler kategoriye göre
  "istisnalı" ve "genel kurala tabi" diye ikiye ayrılır; istisnalı olanlar kendi sabit oranıyla,
  kalanı genel kademeli kuralla (Faz 1'deki mantıkla, tüm tutara tek dilim oranı) hesaplanır;
  ikisinin toplamı nihai payı verir. Bu, hem genel komisyon raporunda hem personel prim
  raporunda ayrı ayrı ama aynı mantıkla uygulanmalı.

### 2.4. Personel Prim Raporu
- Bir dönem seçildiğinde, personel bazında:
  - Genel ciro (kategori istisnası olmayan işlemler) → role ait kademeli tablodan bulunan oran
    ile prim.
  - İstisnalı kategori cirosu → kategoriye tanımlı sabit oran ile prim.
  - Toplam prim (ikisinin toplamı).
- Tüm personelin toplamı (genel toplam prim) ayrıca gösterilsin.
- Rapor ekranda tablo + **Excel export** (Faz 1'deki mutabakat export'uyla aynı kalitede:
  ekrandaki rakamlarla birebir eşleşmeli).
- "Genel Müdür" gibi belirli bir departmana bağlı olmayan roller için ciro kaynağı **tüm bayinin
  toplam cirosu** olmalı (referans süreçte böyleydi) — bunu rol tanımında bir bayrak
  (`ciro_kaynağı: kendi_departmanı | tüm_bayi`) ile ayarlanabilir yapın, sabit kodlamayın.

### 2.5. Mutabakat Raporuna Kategori İstisnasının Yansıması
- Faz 1'deki mutabakat raporu (franchisor-bayi payı), artık kategori istisnalarını da hesaba
  katmalı: istisnalı kategori cirosu kendi sabit oranıyla, kalan genel kurala göre hesaplanıp
  toplanmalı. Departman kırılımı bu değişiklikten sonra da toplamla kuruşu kuruşuna eşleşmeye
  devam etmeli (Faz 1'deki testler burada da geçerli, ek senaryolarla genişletilecek).

## 3. Bu Fazda YAPILMAYACAKLAR

- Çoklu bayi/franchisor hiyerarşisi
- Roller/yetkilendirme (kullanıcı erişim rolleri — bu personelin *iş* rolüyle karıştırılmasın,
  farklı kavramlar; giriş yapan kullanıcı hâlâ tek tip, Faz 3'te ayrışacak)
- Kural versiyonlama / geçmiş dönem snapshot koruması (hâlâ Faz 1'deki gibi basit — kurallar
  değişirse geçmiş rapor yeniden hesaplanabilir; bu Faz 3/4'te ele alınacak)
- Dashboard, grafikler
- PDF export
- Personel için giriş/hesap oluşturma (personel tablosu sadece prim hesaplama amaçlı, personelin
  sisteme giriş yapması gerekmiyor)

## 4. Teknik Gereksinimler (Faz 1 ile aynı, ek olarak)

- Migration'lar (personel ve kategori serbest metinden foreign key'e geçiş) **geri alınabilir**
  (reversible) yazılsın ve mevcut Faz 1 seed verisi üzerinde test edilsin — hiçbir mevcut
  Transaction kaydı migration sonrası kaybolmamalı veya yanlış eşleşmemeli.
- Personel prim hesaplama fonksiyonu, Faz 1'deki `commission_service.py` ile aynı prensiplerle
  yazılsın: `Decimal`, `ROUND_HALF_UP`, kapsamlı unit testler (özellikle rol bazlı dilim sınırları
  ve kategori istisnası olan/olmayan karışık senaryolar için).
- Kategori istisnası + genel kural birlikte çalıştığında toplamın tutarlılığını doğrulayan
  entegrasyon testleri yazılsın (örnek: bir dönemde hem istisnalı hem istisnasız işlemler olsun,
  ikisinin toplamının doğru olduğu test edilsin).

## 5. Veri Modeli — Faz 1'e Eklenenler

```
Employee (ad_soyad, role_id, department_id [nullable], aktif)
Role (ad, ciro_kaynağı: kendi_departmanı | tüm_bayi)
RoleCommissionTier (role_id, alt_sınır, üst_sınır, oran)
TransactionCategory (ad, genel_kural_istisna_oranı [nullable], prim_kural_istisna_oranı [nullable])

Transaction (Faz 1'deki alanlara ek/değişiklik:
  - personel_adı [metin] → employee_id [FK, nullable — eski kayıtlarla uyum için nullable
    bırakılabilir ama yeni kayıtlarda zorunlu olsun]
  - işlem_adı [metin] → category_id [FK, aynı şekilde]
)
```

## 6. Kabul Kriterleri (Faz 2 "bitti" sayılması için)

- [ ] Madde 0'daki üç ön koşul düzeltmesi tamamlanmış/teyit edilmiş.
- [ ] Employee CRUD çalışıyor, Faz 1'deki serbest metin personel verisi kayıpsız migrate edilmiş.
- [ ] Role ve RoleCommissionTier tanımlanabiliyor, en az 2 farklı rol + her biri için en az 2
      dilimli test senaryosu var.
- [ ] TransactionCategory CRUD çalışıyor, Faz 1'deki serbest metin kategori verisi kayıpsız
      migrate edilmiş.
- [ ] Bir kategoriye genel kural istisnası ve/veya prim kuralı istisnası tanımlanabiliyor.
- [ ] Personel prim raporu: karma senaryoda (bir personelin hem istisnalı hem istisnasız
      kategoride işlemi varken) toplam doğru hesaplanıyor — test edilmiş.
- [ ] "Tüm bayi cirosu" kaynaklı rol (ör. Genel Müdür) doğru şekilde departmandan bağımsız
      toplam ciroyu kullanıyor — test edilmiş.
- [ ] Mutabakat raporu (Faz 1), kategori istisnaları eklendikten sonra hâlâ departman kırılımı
      = genel toplam eşitliğini koruyor — mevcut Faz 1 testleri + yeni senaryolarla genişletilmiş
      testler yeşil.
- [ ] Personel prim raporu Excel export ediliyor, ekranla birebir eşleşiyor.
- [ ] Tüm yeni ve eski testler (Faz 1'den kalanlar dahil) yeşil.

## 7. Çalışma Şekli (agent için)

- Önce madde 0'daki düzeltmeleri yap ve kısaca raporla, sonra veri modeli + migration'lara geç.
- Migration'ları yazdıktan sonra, mevcut seed verisi üzerinde çalıştırıp hiçbir kaydın
  kaybolmadığını/yanlış eşleşmediğini göster (ör. migration öncesi/sonrası toplam Transaction
  sayısı ve toplam ciro karşılaştırması).
- Küçük, gözden geçirilebilir adımlarla ilerle: (1) düzeltmeler, (2) veri modeli + migration,
  (3) prim hesaplama motoru + testleri, (4) kategori istisna mantığı + testleri, (5) API
  endpoint'leri, (6) frontend.
- Emin olmadığın bir tasarım kararında (ör. bir rolün ciro kaynağı, bir kategorinin hangi
  kuralda istisnalı olacağının varsayılan değeri) varsayım yapıp öylece devam etmek yerine sor.
