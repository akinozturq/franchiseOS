# FranchiseOS — Frontend Tasarım Rehberi (Design System)

Bu tasarım rehberi, [`anthropics/frontend-design`](https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md) skill standartları ve ilkelerine dayanmaktadır.

## 1. Konu ve Kitleye Dayalı Tasarım (Subject Matter Grounding)
- **Sektör / Konu:** Franchise & Bayi Ağı Finansal Mutabakat ve Kademeli Hakediş Yönetimi.
- **Kullanıcı Kitlesi:** Bayi işletmecileri, franchise muhasebe uzmanları ve merkez finans kontrolörleri.
- **Tasarım Amacı:** Yüksek işlem hacminde hatasız, net, kuruşu kuruşuna denetlenebilir ve hızlı veri girişine imkan veren finansal kontrol paneli.

## 2. Temel Tasarım İlkeleri

### A. Tipografi ve Rakam Hizalaması
- **Tabular Rakamlar (`font-variant-numeric: tabular-nums`):** Tüm parasal tutarlar, yüzdeler, tarihler ve miktarlar dikeyde tam basamak hizalıdır.
- **Tek / Çift Karakterli Tipografi Ailesi:** Temiz, yüksek okunabilirlikli arayüz fontu.
- **Metin Kutlaması ve AI Klişelerinden Kaçınma:**
  - Başlıklarda tek bir kelimeyi renklendirme veya italik yapma gibi şablonik efektler kullanılmaz.
  - Etiketlerde gereksiz BÜYÜK HARF (ALL-CAPS) kullanılmaz; doğal Türkçe cümle düzeni (Sentence case) esastır.
  - Gereksiz süsleyici boşluklar veya sahte rozetler eklenmez.

### B. "Cesaretini Tek Bir Yerde Harca" (Spend Your Boldness in One Place)
- Sayfanın görsel kahramanı: **Dönem Mutabakat ve Fatura Dağılım Matrisi**'dir.
- Geri kalan tüm bileşenler (işlem defteri, filtreler, modal pencereler) sakin, nötr, işlevsel ve disiplinlidir.

### C. Bilgi Olarak Görsel Yapı
- Çizgiler, çerçeveler ve ayraçlar dekoratif değil, bilginin hiyerarşisini (borçlu/alacaklı, bayi payı/merkez payı) gösteren mantıksal sınırlardır.
- Numaralandırma (1, 2, 3) yalnızca Excel içe aktarma sihirbazı gibi gerçekten sıralı olan süreçlerde kullanılır.

### D. Dil ve Metin Yazımı (Copywriting)
- Kullanıcı merkezli, doğrudan ve etken Türkçe fiiller:
  - "Kaydet", "Filtreleri Temizle", "Excel İndir (.xlsx)", "Aktarımı Başlat".
- Hata durumları özür dilemez; neyin hatalı olduğunu ve nasıl düzeltileceğini net biçimde belirtir.

## 3. Renk Paleti

| Token | Değer | Kullanım Amacı |
|---|---|---|
| `--ink-900` | `#0f172a` | Ana metin, yüksek kontrastlı parasal rakamlar |
| `--steel-700` | `#334155` | İkincil başlıklar ve form etiketleri |
| `--steel-500` | `#64748b` | Açıklama metinleri ve pasif göstergeler |
| `--canvas-bg` | `#f8fafc` | Soğuk tonlu temiz çalışma zemini |
| `--surface` | `#ffffff` | Tablo ve kart yüzeyleri |
| `--primary` | `#1e3a8a` | Kurumsal franchise laciverti (güvenilirlik) |
| `--settlement-teal` | `#0f766e` | Fatura ve mutabakat sonuç vurgusu |
| `--amber-duty` | `#92400e` | KDV ve fatura yükümlülük alanı |
| `--border` | `#e2e8f0` | Muhasebe ızgara çizgileri |
