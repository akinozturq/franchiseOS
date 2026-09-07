# FranchiseOS — Çoklu Bayi, Komisyon & Hakediş Finans İşletim Sistemi

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL RLS](https://img.shields.io/badge/PostgreSQL-Row--Level%20Security-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Pytest](https://img.shields.io/badge/Tests-90%2F90%20Passed%20(100%25)-success.svg?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org)
[![Coverage](https://img.shields.io/badge/Coverage-85%25%20(pytest--cov)-green.svg?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Franchise ve bayi ağı modeliyle faaliyet gösteren işletmeler için geliştirilmiş; **çok kiracılı (multi-tenant)**, **kademeli ciro payı ve hakediş mutabakatı**, **personel prim motoru**, **PostgreSQL Row-Level Security (RLS)** ile mutlak veri izolasyonu, **tarihsel kural versiyonlama**, **kriptografik denetim zarfı ve donmuş immutable snapshot**, **resmi PDF ihracı** ve **UBL-TR e-fatura veri iskeleti** sunan uçtan uca kurumsal finans platformudur.

---

## 📑 İçindekiler
- [Proje Vizyonu ve Sektör Uyumluluğu](#-proje-vizyonu-ve-sektör-uyumluluğu)
- [Temel Mimari ve Özellikler](#-temel-mimari-ve-özellikler)
- [Yetkilendirme Matrisi (RBAC)](#-yetkilendirme-matrisi-rbac)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Ekran Görüntüleri ve Arayüz Tasarımı](#-ekran-görüntüleri-ve-arayüz-tasarımı)
- [Kurulum ve Hızlı Başlangıç](#-kurulum-ve-hızlı-başlangıç)
- [Demo Kullanıcı Bilgileri](#-demo-kullanıcı-bilgileri)
- [Test ve Kalite Güvencesi](#-test-ve-kalite-güvencesi)
- [Dizin Yapısı](#-dizin-yapısı)
- [Lisans](#-lisans)

---

## 🎯 Proje Vizyonu ve Sektör Uyumluluğu

FranchiseOS, temel finansal mutabakat ve prim algoritmaları açısından **sektör bağımsız (domain-agnostic)** bir motor olarak tasarlanmıştır.

| Sektör | Örnek Departmanlar | Personel Rolleri | Kategori İstisna Senaryosu |
| :--- | :--- | :--- | :--- |
| **Araç Bakım & Detailing** | PPF Kaplama, Mekanik Servis, Seramik Kaplama | Usta, Servis Danışmanı, Şube Müdürü | Özel TPU PPF kaplama için sabit %15 bayi payı; mekanik bakım için standart barem. |
| **Güzellik, Estetik & Klinik** | Lazer Epilasyon, Cilt Bakımı, Kalıcı Makyaj | Uzman Estetisyen, Dermatolog, Klinik Müdürü | Cihaz maliyetli işlemlerde %20 sabit merkez payı; kozmetik ürün satışında %5 personel primi. |
| **Kafe & Restoran (F&B)** | Mutfak, Bar / İçecek, Paket Servis, Perakende | Barista, Şef, Restoran Müdürü | Paket kahve satışında düşük sabit royalty (%5); alakart yemekte standart ciro dilimi. |
| **Spor, Pilates & Wellness** | Personal Training (PT), Reformer, Grup Dersi | PT Eğitmeni, Diyetisyen, Stüdyo Müdürü | Bireysel PT seanslarında eğitmene yüksek prim (%40); üyeliklerde standart franchise payı. |
| **Perakende & Mağazacılık** | Kadın Giyim, Erkek Giyim, Aksesuar, Outlet | Satış Danışmanı, Kasiyer, Mağaza Müdürü | Konsinye dış markalara özel royalty; iç üretim ürünlerde standart barem. |

---

## ⚡ Temel Mimari ve Özellikler

### 1. Kademeli Ciro ve Dinamik Fatura Yönü Motoru
- **Tüm Döneme Tek Oran Kuralı:** İlgili ayın kümülatif ciro tutarı hangi bareme düşerse, dönemin tüm standart işlemleri o dilim oranından hesaplanır (parça parça dilimlere bölünmez).
- **Dinamik Fatura Yönü:** *"Tahsilatı yapan taraf değil, tahsilat etmeyen taraf kendi payını faturalar"*:
  - **Tahsilat Bayide ise:** Bayi tüm parayı kasasına koymuştur; Franchisor merkez kendi royalty komisyonunu bayiye faturalar (`Franchisor -> Bayi`).
  - **Tahsilat Franchisor'da ise:** Merkez parayı toplamıştır; Bayi kazandığı işletme payını merkeze faturalar (`Bayi -> Franchisor`).

### 2. Personel Prim Motoru ve Bağımsız Çift İstisna
- **3 Seviyeli Ciro Kaynağı (`turnover_source`):**
  - `kendi_islemleri`: Doğrudan personelin kendi yaptığı işlemler (uzman, teknisyen, satış danışmanı).
  - `kendi_departmani`: İlgili departmanın toplam cirosu (bölüm şefi, baş kuaför, servis müdürü).
  - `tum_bayi`: Bayinin toplam cirosu (genel müdür, şube yöneticisi).
- **Bağımsız Çift İstisna Matrisi:** Bir işlem kategorisi, genel bayi-merkez mutabakatında genel dilime tabi olurken, personel priminde sabit orana (`bonus_override_rate`) tabi olabilir (veya tam tersi).
- **Atanmamış İşlemler Eşleştirme:** Personel eşleşmesi eksik kalan kayıtların mutabakat bütünlüğünü bozmadan personele geriye dönük bağlanabilmesi.

### 3. Çoklu Bayi Mimarisi ve PostgreSQL RLS İzolasyonu
- **Row-Level Security (RLS):** Her sorguda PostgreSQL oturum değişkeni (`app.current_branch_id`) üzerinden veritabanı motoru seviyesinde tenant filtrelemesi uygulanır. Uygulama kodunda `WHERE branch_id = ...` filtresi unutulsa dahi diğer bayinin verisi asla sızamaz.
- **İki Katmanlı Koruma:** Hem veritabanı seviyesinde RLS politikaları hem de uygulama seviyesinde FastAPI bağımlılıkları bağımsız olarak devrededir.

### 4. Kural Versiyonlama ve Denetim İzi (Audit Log)
- Komisyon baremleri, rol primleri ve kategori istisnaları `effective_from` ve `effective_to` tarih aralıklarıyla versiyonlanır.
- Kural değiştirildiğinde mevcut kural satırı arşive kapatılır, yeni kural oluşturulur.
- Geçmiş aylar sorgulandığında ilgili dönemin son günündeki tarihsel kurallarla kuruşu kuruşuna deterministik hesaplama yapılır.
- Tüm değişiklikler [`RuleChangeLog`](backend/app/models/rule_change_log.py) üzerinde eski/yeni JSON değer farkları ile loglanır.

### 5. Dönem Kapama, Donmuş Snapshot ve Kriptografik Denetim Zarfı
- **Kriptografik Bütünlük ve Denetim Zarfı (Audit Envelope):** Dönem kapama anında (`PeriodClosure`), hesaplama motorlarının versiyonları (`COMMISSION_ENGINE_VERSION`, `BONUS_ENGINE_VERSION`), tüm girdi işlemlerinin kanonik sıralı SHA-256 özeti (`input_hash`) ve üretilen finansal sonuçların SHA-256 özeti (`result_hash`) mühürlenir. Dış mali denetçiler, hesaplama formüllerinin ve girdi verilerinin değişmediğini matematiksel olarak doğrulayabilir.
- **Donmuş JSONB Snapshot:** Dönem kapatıldığında o anki mutabakat ve prim tabloları **JSONB snapshot** olarak mühürlenir.
- **Mutasyon Kilidi:** Kapatılmış bir döneme ait işlemlerde `POST`, `PUT`, `DELETE` ve toplu Excel/CSV içe aktarımları **HTTP 400** ile engellenir.
- **Kural Değişikliği Bağışıklığı:** Dönem kapatıldıktan sonra sistemdeki kurallar değişse dahi, kapalı dönemin mutabakat, prim ve PDF raporları donmuş snapshot'tan servis edilir; hiçbir kural değişikliği geçmiş kapalı döneme nüfuz edemez.
- **Gerekçeli Yeniden Açma (Reopen):** Yalnızca Franchisor Admin tarafından, zorunlu gerekçe (`reopen_reason`, min 5 karakter) girilerek yapılabilir.

### 6. Resmi PDF Export & UBL-TR E-Fatura Veri İskeleti
- **ReportLab PDF:** Kaşe ve imza kutuları, resmi durum rozeti, departman/kategori dökümleri ve mali özet kartları içeren kurumsal mutabakat ve prim belgeleri (`/reconciliation/export-pdf`, `/bonus/export-pdf`).
- **Dinamik Franchisor & E-Fatura JSON:** Sistem genel merkez verilerini statik kod yerine veritabanındaki `Franchisor` master modelinden dinamik çeker. UBL-TR standartlarında satıcı, alıcı, %20 KDV, matrah, fatura yönü ve kriptografik denetim zarfını (`input_hash`, `result_hash`, `engine_version`) içeren entegratör uyumlu payload üretir (`/period-closures/{id}/invoice-data`).

### 7. Bildirim Merkezi (Notification Center)
- Okunmamış sayaç rozeti, tekil/toplu okundu işaretleme ve ay sonu yaklaşan kapanmamış dönemler için otomatik hatırlatıcı taraması.

### 8. Akıllı Veri İçe Aktarımı ve KVKK Maskeleme
- CSV/XLSX dosyalarındaki sütun başlıklarını otomatik tahminleyen akıllı eşleştirme motoru.
- Türkçe tarih (`GG.AA.YYYY`, `YYYY-AA-GG`) ve ondalık (`1.250,50 TL`) format toleransı.
- KVKK uyumlu TCKN/VKN maskeleme (`*******8901`).

### 9. Yüksek Başarımlı Toplu Ön Yükleme (N+1 Query Eliminasyonu)
- Mutabakat ve prim hesaplama pipeline'larında döngü içi sorgular (`N+1`) tamamen kaldırılmıştır.
- Tüm kategori kural istisnaları ve kademeli rol baremleri tek bir veritabanı sorgusunda toplu ön yüklenir (`bulk preloading`), bellek içi haritalama (in-memory lookup) ile $O(1)$ sürede eşleştirilir.

---

## 🛡️ Yetkilendirme Matrisi (RBAC)

| İşlem / Ekran | Franchisor Yöneticisi (`FRANCHISOR_ADMIN`) | Bayi Yöneticisi (`BAYI_ADMIN`) | Denetçi / İzleyici (`VIEWER`) |
| :--- | :---: | :---: | :---: |
| **Çoklu Bayi Dashboard (Karşılaştırmalı)** | ✅ Evet (Tüm bayiler) | ❌ Hayır | ❌ Hayır |
| **Kendi Bayi Dashboard'u** | ✅ Evet | ✅ Evet | ✅ Evet |
| **Dönem Mutabakatı Görüntüleme** | ✅ Evet | ✅ Evet | ✅ Evet |
| **Tahsilatçı & KDV Ayarı Değiştirme** | ✅ Evet | ✅ Evet | ❌ Hayır (Salt Okunur) |
| **Dönem Kapatma / Reopen** | ✅ Evet (Doğrudan) | ❌ Hayır (Yalnızca Talep Edebilir) | ❌ Hayır |
| **Komisyon Baremleri & Roller Tanımlama** | ✅ Evet | ❌ Hayır | ❌ Hayır |
| **İşlem Girişi / Excel İçe Aktarma** | ✅ Evet | ✅ Evet (Kendi Bayisi) | ❌ Hayır |
| **Personel / Rol Atama** | ✅ Evet | ✅ Evet (Kendi Bayisi) | ❌ Hayır |
| **PDF & Excel Rapor İhracı** | ✅ Evet | ✅ Evet | ✅ Evet |
| **Bayi ve Kullanıcı Yönetimi** | ✅ Evet | ❌ Hayır | ❌ Hayır |

---

## 🛠️ Teknoloji Yığını

- **Backend:**
  - [Python 3.12](https://www.python.org/)
  - [FastAPI](https://fastapi.tiangolo.com/) (Asenkron REST API & Pydantic v2 validasyon)
  - [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/) (ORM & Şema göçleri)
  - [PostgreSQL](https://www.postgresql.org/) (Row-Level Security ve JSONB depolama)
  - [ReportLab](https://www.reportlab.com/) (Resmi PDF üretim motoru)
  - [OpenPyXL](https://openpyxl.readthedocs.io/) (Biçimlendirilmiş Excel ihracı ve içe aktarımı)
  - [Pytest](https://docs.pytest.org/) (75 adet kapsamlı birim ve entegrasyon testi)
- **Frontend:**
  - [React 19](https://react.dev/) & [TypeScript](https://www.typescriptlang.org/)
  - [Vite](https://vite.dev/)
  - [Lucide React](https://lucide.dev/) (Modern ikon seti)
  - [Axios](https://axios-http.com/) (JWT auth & X-Branch-Id tenant interceptor)
  - Anthropic `frontend-design` prensipleri ve 2 katmanlı modern kurumsal navbar mimarisi.

---

## 💻 Kurulum ve Hızlı Başlangıç

### 1. Ön Koşullar
- Python 3.12+
- Node.js 18+ ve npm
- PostgreSQL 14+ (veya Docker)

### 2. Veritabanı ve Backend Kurulumu

```powershell
# Proje ana dizininde sanal ortamı aktif edin:
.\.venv\Scripts\Activate.ps1

# Bağımlılıkları yükleyin:
pip install -r backend/requirements.txt

# Veritabanı şemasını uygulayın (PostgreSQL RLS politikaları dahil):
alembic upgrade head

# Kurgusal demo verisini yükleyin:
python -m backend.app.db.seed

# Backend API sunucusunu başlatın:
uvicorn backend.app.main:app --reload --port 8000
```
- API Swagger UI: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

### 3. Frontend Kurulumu

Ayrı bir terminalde:
```powershell
cd frontend
npm install
npm run dev
```
- Web Arayüzü: [http://localhost:5173](http://localhost:5173)

---

## 🔐 Demo Kullanıcı Bilgileri

Sistem seed çalıştırıldığında aşağıdaki test kullanıcılarıyla hazır gelir:

| Kullanıcı Adı | Şifre | Rol | Yetki Kapsamı |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | `FRANCHISOR_ADMIN` | Tüm bayiler, kurallar, dönem kapama ve kullanıcı yönetimi |
| `bayi_admin` | `bayi123` | `BAYI_ADMIN` | Kuzey Detailing & Servis Bayisi operasyonel yetkisi |
| `viewer` | `viewer123` | `VIEWER` | Kuzey Detailing & Servis Bayisi salt okunur denetçi erişimi |

---

## 🧪 Test ve Kalite Güvencesi

FranchiseOS, **90 adet otomatikleştirilmiş test** ile %100 test başarı oranı (pass rate) ve %85 kod kapsamı (pytest-cov) ile güvence altındadır.

```powershell
# Tüm backend testlerini çalıştırmak ve kod kapsamını (coverage) ölçmek için:
cd backend
..\.venv\Scripts\pytest --cov=app --cov-report=term-missing -v
```

### Kalite ve Kapsam Metrikleri
* **Test Başarı Oranı (Pass Rate):** `%100` (90 / 90 test yeşil)
* **Kod Kapsamı (Code Coverage):** `%85` (`pytest-cov` ile ölçülmüştür; Veri Modelleri & Şemalar `%99-%100`, Hesaplama & Finans Motorları `%96-%100`, PDF & Export `%97-%100`)
* **Finansal Yuvarlama Politikası:** `ROUND_HALF_UP` (Bankacılık ve Vergi Usul Kanunu standartlarında işlem bazında ve toplamda 2 hane ondalık kesinliği)

### Test Paketi Dağılımı (90 / 90 PASSED):
- **IDOR & Çapraz Bayi Penetrasyon Testleri (`test_idor_penetration.py` - 9 Test):** Header ve sorgu parametresi manipülasyonu (`X-Branch-Id`, `?branch_id=2`), doğrudan IDOR işlem sorgulaması, KVKK TCKN/VKN sızıntı denemeleri, çapraz şube işlem güncelleme/atama girişimi, yetkisiz dönem kapama ve mutabakat ihracı blokajları, finansal `ROUND_HALF_UP` yuvarlama tutarlılığı.
- **P0 Güvenlik & Finansal Sertleştirme (`test_p0_hardening.py`):** Kapalı dönem işlem atama bypass engeli, kilitli dönem mutasyon koruması, KDV dahil/hariç matematiksel invariant validasyonu, KVKK veri minimizasyonu (`customer_tax_id` gizleme ve yetkili `/sensitive` endpoint'i), yarı-açık kural aralığı `[from, to)` sınır günü çakışma önlemi, production JWT secret & CORS kısıtları.
- **Donmuş Snapshot Kanıtı (`test_frozen_snapshot_proof.py`):** Dönem kapandıktan sonra kurallar değişse bile mutabakatın ve PDF'in donmuş kaldığının, reopen ile canlıya döndüğünün kanıtı.
- **Dönem Kilitleri & İmmutability (`test_closed_period_restrictions.py`):** Kapalı döneme işlem ekleme, güncelleme, silme ve Excel aktarım engelleri; bayi reopen yasağı ve gerekçe validasyonu.
- **E-Fatura & Kriptografik Denetim İskeleti (`test_invoice_data_skeleton.py`):** Dinamik Franchisor tüzel unvanı, bayi ve franchisor tahsilat yönlerinde UBL-TR uyumlu alıcı/satıcı, KDV, satır hesapları ve `audit_envelope` (`input_hash`, `result_hash`).
- **Uygulama İçi Bildirimler (`test_notifications.py`):** Sayaç, okundu işaretleme, kapatma hatırlatma taraması ve kapatma talebi bildirimleri.
- **Rol Prim Kademesi Versiyonlama (`test_role_tier_versioning.py`):** `ADD_TIER` ve `DELETE_TIER` işlemleri ve audit log takibi.
- **Kural Versiyonlama (`test_rule_versioning.py`):** Komisyon baremleri ve kategori istisnalarının tarihsel ayrımı.
- **Resmi PDF İhracı (`test_pdf_export.py`):** Açık dönem ve kapalı snapshot'tan ReportLab PDF üretimi.
- **Dönem Kapama Yaşam Döngüsü (`test_period_closure.py`):** Talep, kapama, kilit ve audit kaydı.
- **PostgreSQL RLS Güvenliği (`test_rls_isolation.py`):** PostgreSQL veritabanı seviyesinde çapraz bayi veri izolasyonu testleri.
- **RBAC Yetkilendirme (`test_rbac_permissions.py`):** 9 adet rol erişim kısıtı doğrulaması.
- **Matematik Motoru & Hesaplama (`test_commission.py`, `test_bonus.py`):** Kademeli ciro payları, prim havuzları ve sınır değer testleri.
- **Veri İçe Aktarma & Maskeleme (`test_import.py`):** Esnek tarih, ondalık parsing ve KVKK TCKN/VKN maskeleme.

---

## 📂 Dizin Yapısı

```
franchiseOS/
├── backend/
│   ├── alembic/                       # Şema versiyonları (Migration)
│   ├── app/
│   │   ├── api/                       # REST endpoint router'ları
│   │   │   ├── auth.py                # JWT kimlik doğrulama
│   │   │   ├── bonus.py               # Personel prim raporları & PDF
│   │   │   ├── branches.py            # Bayi yönetimi
│   │   │   ├── categories.py          # İşlem kategorileri & istisnalar
│   │   │   ├── commission_tiers.py    # Kademeli komisyon dilimleri
│   │   │   ├── dashboard.py           # Karşılaştırmalı ve bayi dashboard metrikleri
│   │   │   ├── departments.py         # Departman yönetimi
│   │   │   ├── employees.py           # Personel & işlem atama
│   │   │   ├── notifications.py       # Bildirim merkezi & hatırlatıcılar
│   │   │   ├── period_closures.py     # Dönem kapama, snapshot, reopen & e-fatura
│   │   │   ├── reconciliation.py      # Dönem mutabakatı, Excel & PDF ihracı
│   │   │   ├── roles.py               # Personel rolleri & kademeli prim baremleri
│   │   │   ├── transactions.py        # İşlem defteri CRUD & kilitler
│   │   │   └── users.py               # RBAC kullanıcı yönetimi
│   │   ├── core/                      # Ayarlar, veritabanı oturumu & güvenlik
│   │   ├── db/                        # Kurgusal Faker demo veri scripti
│   │   ├── models/                    # SQLAlchemy ORM tabloları
│   │   ├── schemas/                   # Pydantic v2 DTO modelleri
│   │   └── services/                  # Hesaplama motorları, PDF, Excel & CSV import
│   ├── tests/                         # 90 adet Pytest entegrasyon, IDOR penetrasyon & birim testi
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                       # Axios client & JWT/Tenant interceptor
│   │   ├── components/                # React görünüm bileşenleri
│   │   │   ├── BonusReportView.tsx    # Personel prim hakediş tablosu
│   │   │   ├── BranchManagementView.tsx # Bayi yönetim paneli
│   │   │   ├── CategoriesView.tsx     # Kategoriler & istisna geçmişi
│   │   │   ├── CommissionTiersView.tsx# Komisyon dilimleri & kural geçmişi
│   │   │   ├── DashboardView.tsx      # Karşılaştırmalı performans paneli
│   │   │   ├── DepartmentsView.tsx    # Departman yönetimi
│   │   │   ├── ImportModal.tsx        # Akıllı Excel/CSV yükleme sihirbazı
│   │   │   ├── InvoiceDataModal.tsx   # E-Fatura UBL-TR JSON görüntüleyici
│   │   │   ├── LoginPage.tsx          # Giriş ekranı
│   │   │   ├── Navbar.tsx             # 2 katmanlı kurumsal navigasyon
│   │   │   ├── NotificationCenter.tsx # Bildirim merkezi paneli
│   │   │   ├── ReconciliationView.tsx # Mutabakat, kapama & PDF ihracı
│   │   │   ├── RuleHistoryModal.tsx   # Kural versiyon denetim modalı
│   │   │   ├── StaffView.tsx          # Personel, roller & atama
│   │   │   ├── TransactionsView.tsx   # İşlem defteri & filtreler
│   │   │   └── UserManagementView.tsx # Kullanıcı & yetki yönetimi
│   │   ├── types/                     # TypeScript arayüz tanımları
│   │   ├── utils/                     # Türkçe para, tarih ve yüzde formatlayıcılar
│   │   ├── App.tsx                    # Ana uygulama konteyneri
│   │   └── index.css                  # Tasarım sistemi & duyarlı stiller
│   ├── package.json
│   └── vite.config.ts
├── alembic.ini
├── .gitignore
└── README.md
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında lisanslanmıştır.
