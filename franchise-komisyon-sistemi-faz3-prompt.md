# PROJE: Franchise/Bayi Komisyon Sistemi — FAZ 3 (Çoklu Bayi, Roller/Yetkilendirme, Dashboard)

Faz 1 ve Faz 2 tamamlandı (tek bayi, komisyon+prim motoru, kategori istisnaları çalışır durumda,
sırasıyla 24/24 ve 39/39 test yeşil). Bu fazda hâlâ tanımlanmayan hiçbir özelliği (PDF export,
e-fatura entegrasyonu, bildirimler/hatırlatmalar, kural versiyonlama/dönem snapshot koruması)
**ekleme** — bunlar Faz 4'e ait. YAGNI prensibi burada da geçerli.

## 0. Mimari Karar: Veritabanı İzolasyon Stratejisi (gerekçeli)

Bu proje, farklı bayilere ait finansal/ciro verisi barındıracak. Bir bayinin başka bir bayinin
verisini görmesi (yanlışlıkla eksik `WHERE branch_id = ...` filtresi yüzünden bile olsa) ciddi bir
güven ve olası yasal sorun. Bu yüzden şu stratejiyi seçtim:

**Paylaşılan tablo yapısı (mevcut şema korunur, her tabloya `branch_id` eklenir) + PostgreSQL
Row-Level Security (RLS) ile veritabanı seviyesinde zorunlu izolasyon.**

Gerekçe:
- Sadece uygulama kodunda (`WHERE branch_id = current_user.branch_id`) filtrelemeye güvenmek
  kırılgan: geliştirici yeni bir endpoint/rapor eklerken bu filtreyi bir kez unutursa, veri sızıntısı
  sessizce oluşur ve genelde çok geç fark edilir. Bu tam olarak mutabakat sistemlerinde en sık görülen
  güvenlik açığı sınıfıdır.
- Ayrı şema/ayrı veritabanı (schema-per-tenant / database-per-tenant) bu aşamada gereksiz karmaşıklık
  getirir (migration'ları her tenant için ayrı ayrı çalıştırma, bağlantı havuzu yönetimi vb.) — bayi
  sayısı bu ürünün erken aşamasında büyük olasılıkla onlarca/yüzlerce mertebesinde kalacak, milyonlarca
  değil; paylaşılan tablo + RLS bu ölçekte hem yeterli hem çok daha basit.
- RLS, uygulama kodu filtreyi unutsa bile **veritabanının kendisi** yanlış satırı döndürmeyi
  reddeder — yani hataya karşı ikinci bir savunma katmanı (defense-in-depth) sağlar. Uygulama
  seviyesindeki filtreleri de kaldırmıyoruz, ikisi birlikte çalışacak.

Uygulama şekli:
- Her request'in başında (bir FastAPI dependency/middleware içinde), oturum açmış kullanıcının
  `branch_id`'si PostgreSQL session değişkenine yazılır: `SET LOCAL app.current_branch_id = '<uuid>'`
  (transaction-scoped, request bitince sıfırlanır).
- İlgili tüm tablolarda (`transactions`, `employees`, `roles`, `role_commission_tiers`,
  `transaction_categories`, `commission_tiers`, `period_settings` vb.) RLS policy tanımlanır:
  `USING (branch_id = current_setting('app.current_branch_id')::uuid)`.
- Franchisor Admin rolü için ayrı bir policy: birden fazla bayiyi görebilmesi gerektiğinden, bu rol
  için `current_setting('app.current_branch_id')` tek bir bayiye değil, kullanıcının yetkili olduğu
  bayi listesine bakan bir policy kullanır (ör. `branch_id = ANY(current_setting('app.accessible_branch_ids')::uuid[])`).
- Migration'larda RLS'i açma (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) ve policy tanımları da yer
  alsın; bu bir "sonra eklenecek" güvenlik önlemi değil, şemanın parçası.

## 1. Kapsam — Çoklu Bayi (Multi-Tenant)

- **Franchisor** kavramı eklenir: bir Franchisor, birden fazla **Branch** (bayi) sahibi olabilir.
  Mevcut tek-bayi kurulum, bu yapıya geriye dönük uyumlu migrate edilir (mevcut `branches` satırı,
  otomatik oluşturulan bir Franchisor'a bağlanır — veri kaybı olmaz, Faz 1/2'deki migration
  raporlama alışkanlığı burada da uygulanır: öncesi/sonrası kayıt sayısı ve toplam ciro karşılaştırması
  raporlansın).
- Franchisor Admin, kendi bünyesindeki tüm bayileri listeleyebilir, yeni bayi ekleyebilir
  (ad, vergi bilgileri, departman/rol/kategori/dilim kurallarını o bayi için ayrıca tanımlar —
  kurallar bayiler arası paylaşılmaz, her bayinin kendi kademeli dilimleri, kategorileri, rolleri
  olabilir; bir "şablon kopyalama" özelliği eklenebilir ama zorunlu değil — basit tutulsun).
- Bayi seçici: Franchisor Admin arayüzde hangi bayinin verisini görüntülediğini bir dropdown'dan
  seçer; seçim değiştiğinde tüm ekranlar (işlemler, mutabakat, prim raporu) o bayiye göre filtrelenir.

## 2. Kapsam — Roller ve Yetkilendirme (Kullanıcı Erişim Rolleri)

Not: Bu, Faz 2'deki **personel iş rolleri** (Satış Danışmanı vb.) ile karıştırılmasın — bunlar
sisteme **giriş yapan kullanıcıların** erişim seviyesi.

- **Franchisor Admin:** Tüm bayileri görür/yönetir, komisyon+prim kurallarını tanımlar
  (Faz 1/2'deki tüm CRUD ekranlarına erişir), kullanıcı yönetimi yapabilir.
- **Bayi Admin:** Sadece kendi bayisinin verisini görür/yönetir. Komisyon dilimlerini/kategori
  istisnalarını **görebilir ama değiştiremez** (bunlar franchisor tarafından belirlenir — referans
  iş modelinde oranları merkez belirler). İşlem kaydı, personel, import gibi günlük operasyonel
  işleri yapabilir.
- **Salt Okunur (Viewer):** Hem franchisor hem bayi seviyesinde olabilir (bir bayrakla ayrılır);
  hiçbir CRUD işlemi yapamaz, sadece raporları görüntüler/export eder.
- Yetkilendirme, hem API seviyesinde (endpoint bazlı izin kontrolü — FastAPI dependency ile) hem
  arayüzde (yetkisi olmayan butonlar/menüler gösterilmez) uygulanmalı. **API seviyesindeki kontrol
  zorunlu, UI'daki gizleme sadece kullanıcı deneyimi içindir** — bir Bayi Admin, UI'da buton görmese
  bile API'yi doğrudan çağırarak komisyon dilimi değiştiremiyor olmalı (test edilsin).
- Kullanıcı yönetimi ekranı: Franchisor Admin, yeni kullanıcı oluşturabilir, rol atayabilir, hangi
  bayi(ler)e erişimi olduğunu belirleyebilir.

## 3. Kapsam — Dashboard

- **Franchisor Admin görünümü:** Tüm bayilerin seçilen dönemdeki toplam cirosu, franchisor payı,
  bayi payı karşılaştırmalı tablo/grafik (bayi bazında sıralanabilir — en yüksek/düşük cirolu bayi).
- **Bayi Admin görünümü:** Kendi bayisinin son birkaç dönemlik ciro trendi (basit çizgi grafik),
  departman kırılımı (pasta/bar grafik), en yüksek prim alan personel listesi (üst 5).
- Grafik kütüphanesi olarak hafif ve React ile iyi entegre olan bir kütüphane kullanılsın (ör.
  Recharts) — karmaşık bir BI aracı kurulmasın, MVP seviyesinde basit özet grafikler yeterli.
- Dashboard verileri gerçek zamanlı hesaplanabilir (Faz 1/2'deki hesaplama motorları zaten var,
  bunlar dashboard için de çağrılabilir) — ayrı bir önbellekleme/agregasyon tablosu bu fazda
  gerekmiyor, performans sorunu çıkarsa (çok fazla bayi/dönem olursa) sonraki bir fazda ele alınır.

## 4. Bu Fazda YAPILMAYACAKLAR

- Kural versiyonlama / geçmiş dönem snapshot koruması (kurallar hâlâ "canlı" — değişirse geçmiş
  raporlar yeniden hesaplanabilir; bu hâlâ bilinen ve kabul edilen bir sınırlama, Faz 4'e bırakıldı)
- PDF export (Excel export yeterli, PDF Faz 4'te)
- E-fatura entegrasyonu, bildirimler/hatırlatmalar
- Bayiler arası kural/şablon kopyalama otomasyonu (manuel tanımlama yeterli, otomasyon gerekirse
  sonraki bir fazda)
- Franchisor'ın kendisinin de çoklu-franchisor bir üst yapıya bağlanması (yani üçüncü bir hiyerarşi
  seviyesi) — iki seviye (Franchisor → Branch) bu faz için yeterli

## 5. Teknik Gereksinimler

- RLS policy'leri için ayrı, izole edilmiş bir test seti yazılsın: iki farklı bayiye ait test
  kullanıcısı oluşturup, birinin diğerinin verisine (hem normal sorgu hem "kazara filtre unutulmuş"
  gibi kasıtlı olarak filtre eklenmemiş bir sorgu ile) erişemediğini doğrulayan testler — bu, RLS'in
  gerçekten çalıştığını kanıtlayan en kritik test grubu.
- Rol bazlı API yetkilendirme testleri: her üç kullanıcı rolü için, izinli/izinsiz endpoint
  kombinasyonlarını deneyen bir test matrisi (ör. Bayi Admin'in `PUT /commission-tiers` çağrısının
  403 dönmesi gibi).
- Migration (tek bayiden çoklu bayiye geçiş) geri alınabilir olsun ve mevcut Faz 1/2 seed verisi
  üzerinde çalıştırılıp öncesi/sonrası kayıt+ciro karşılaştırması raporlansın.

## 6. Kabul Kriterleri

- [ ] Franchisor → Branch hiyerarşisi kurulu, mevcut tek-bayi verisi kayıpsız migrate edilmiş
      (sayısal karşılaştırma raporlanmış).
- [ ] RLS açık ve policy'ler tanımlı; iki farklı bayi arasında çapraz erişim denemesi başarısız
      oluyor — test edilmiş (hem uygulama filtresi hem RLS ayrı ayrı devre dışı bırakılıp test
      edilerek RLS'in tek başına da koruduğu gösterilmiş olmalı).
- [ ] Üç kullanıcı rolü (Franchisor Admin, Bayi Admin, Salt Okunur) çalışıyor; her biri için
      izin matrisi API seviyesinde test edilmiş.
- [ ] Bayi Admin, komisyon dilimi/kategori kuralı değiştirme endpoint'ine API üzerinden doğrudan
      istek atsa bile engelleniyor (403).
- [ ] Franchisor Admin dashboard'u: birden fazla bayinin karşılaştırmalı ciro/pay verisini
      doğru gösteriyor.
- [ ] Bayi Admin dashboard'u: kendi bayisinin trend/departman/top-personel verilerini doğru
      gösteriyor.
- [ ] Kullanıcı yönetimi ekranından yeni kullanıcı oluşturulup rol/bayi erişimi atanabiliyor.
- [ ] Faz 1 ve Faz 2'den kalan tüm testler hâlâ yeşil (regresyon yok).

## 7. Çalışma Şekli (agent için)

- Önce RLS + multi-tenant veri modelini kur ve izolasyon testlerini yaz/geçir — bu fazın en riskli
  parçası, en başta sağlamlaştırılmalı.
- Sonra roller/yetkilendirme (API seviyesi önce, sonra UI).
- Son olarak dashboard (mevcut hesaplama motorlarını yeniden kullanarak, yeni bir hesaplama
  mantığı icat etmeden).
- Migration'dan sonra mutlaka öncesi/sonrası sayısal karşılaştırma raporla.
- Emin olmadığın bir tasarım kararında (ör. Bayi Admin'in tam olarak hangi ekranlarda "görebilir
  ama değiştiremez" olacağı, dashboard'da hangi metriklerin öncelikli olacağı) varsayım yapıp
  öylece devam etmek yerine sor.
