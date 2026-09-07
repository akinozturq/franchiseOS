# FranchiseOS — Backend (API & Hesaplama Motoru)

Bu dizin, Franchise / Bayi Kademeli Komisyon ve Mutabakat Sistemi'nin FastAPI, SQLAlchemy ve PostgreSQL tabanlı backend çekirdeğidir.

## Özellikler (Faz 1 MVP)

- **Kademeli Komisyon Motoru:** Dönem cirosunun tamamına tek dilim oranı uygulanır (virgüllü hassas para hesabı için `Decimal` ve `ROUND_HALF_UP`).
- **Dinamik Fatura Yönü:** "Tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar" kuralı işletilir (Bayi tahsilatında Franchisor faturalar, Franchisor tahsilatında Bayi hakediş faturası keser).
- **KVKK Maskeleme:** Müşteri kimlik/vergi no listelerde son 4 hane hariç maskeli sunulur.
- **CSV & Excel İçe Aktarma:** Otomatik kolon tahmini, önizleme ve kullanıcı onaylı toplu içe aktarma; bozuk satırlar diğer satırları durdurmaz ve raporlanır.
- **Excel Rapor Export:** Ekranda hesaplanan mutabakat ve departman kırılımını birebir eşleşen `.xlsx` formatında dışa aktarma.
- **JWT Kimlik Doğrulama:** bcrypt ile şifrelenmiş tek kullanıcı oturumu.

## Kurulum ve Çalıştırma

### 1. Gereksinimler
- Python 3.10+
- PostgreSQL 14+

### 2. Sanal Ortam ve Paketler
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### 3. Veritabanı ve Migration
PostgreSQL'de `franchise_os` isimli UTF-8 bir veritabanı oluşturun ve migration'ı çalıştırın:
```bash
alembic upgrade head
```

### 4. Seed Verisi Yükleme (Kurgusal Demo Verisi)
```bash
python backend/app/db/seed.py
```
*Bu komut kurgusal bayi, varsayılan komisyon dilimleri (0-750k -> %30, 750k+ -> %35), departmanlar, admin kullanıcısı (`admin` / `admin123`) ve kurgusal işlem kayıtlarını oluşturur.*

> ⚠️ **ÖNEMLİ GÜVENLİK UYARISI:** `admin` / `admin123` hesabı yalnızca yerel geliştirme ve Faz 1 MVP testleri içindir. Uygulama canlı (prodüksiyon) ortama alınmadan önce bu şifre veritabanından veya yönetim panelinden **MUTLAKA** güçlü bir şifre ile değiştirilmelidir.


### 5. Sunucuyu Başlatma
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Dokümantasyonu: `http://localhost:8000/api/v1/docs`

### 6. Testleri Çalıştırma
```bash
pytest -v backend/tests
```
