# FranchiseOS — Frontend (React & TypeScript)

Bu dizin, Franchise / Bayi Kademeli Komisyon ve Mutabakat Sistemi'nin kullanıcı arayüzüdür. Tamamen Türkçe, GUI-first, finansal tablo odaklı ve hızlı veri girişine uygun olarak geliştirilmiştir.

## Ekranlar ve Özellikler (Faz 1 MVP)

1. **Dönem Mutabakatı (Reconciliation):**
   - Ay/Yıl seçimi (örn. Eylül 2026).
   - "Tahsilatı Yapan Taraf" seçimi (Bayi / Franchisor).
   - Prompt 2.5 kuralı: *"Seçilen dilim oranı, dönem cirosunun tamamına uygulanır."*
   - Kullanıcı kuralı: *"Tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar."* (KDV hariç, KDV ve KDV dahil genel toplam).
   - Departman bazlı ciro kırılımı (toplamı genel ciro ile birebir eşleşir).
   - **Excel İndir (.xlsx):** Ekrandaki rakamlarla birebir aynı formatlı dosya üretir.

2. **İşlem Defteri (Transaction Ledger):**
   - Satış, servis, kaplama işlem kayıtları listesi.
   - KVKK gereği müşteri TC/Vergi No maskeli gösterilir (`*******8901`).
   - Arama (müşteri, personel, işlem adı), departman, ay ve yıl filtreleri.
   - Yeni İşlem Ekleme & Düzenleme (KDV hariç tutar girildiğinde KDV dahil tutar otomatik hesaplanır).

3. **CSV / Excel İçe Aktarma Sihirbazı:**
   - Dosya yükleme (.csv veya .xlsx).
   - Akıllı sütun eşleştirme (Tarih, Müşteri, Tutar vb. otomatik tanınır, kullanıcı onayına sunulur).
   - İlk 5 satır önizleme.
   - Hatalı satırlar raporu (hatalı satırlar işlemi durdurmaz, geçerli satırlar aktarılır).

4. **Komisyon Dilimleri:**
   - Kademeli komisyon dilimleri (Alt sınır, Üst sınır, Bayi %, Franchisor %).
   - Sınır değer kuralı: `[alt_sınır, üst_sınır]` aralıkları dahilidir (0 - 750.000 TL %30, 750.000,01 TL ve üzeri %35).

5. **Departmanlar:**
   - Departman listesi, ekleme, düzenleme ve pasife alma.

## Kurulum ve Çalıştırma

### 1. Gereksinimler
- Node.js v18+ (v24+ test edildi)
- npm v9+

### 2. Kurulum
```bash
cd frontend
npm install
```

### 3. Geliştirme Sunucusu (Dev Server)
```bash
npm run dev
```
Uygulama `http://localhost:5173` adresinde açılır.

### 4. Üretim Derlemesi (Build)
```bash
npm run build
```
Derleme çıktısı `frontend/dist/` klasöründe üretilir.

### 5. Giriş Bilgileri (Demo Seed)
- Kullanıcı Adı: `admin`
- Şifre: `admin123`
