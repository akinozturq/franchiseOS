import React, { useState } from "react";
import {
  Upload,
  X,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  HelpCircle
} from "lucide-react";
import { apiClient } from "../api/client";
import type { UploadPreviewResponse, ImportResultResponse } from "../types";

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState<"upload" | "mapping" | "result">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<UploadPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [uploading, setUploading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [importResult, setImportResult] = useState<ImportResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const targetFields = [
    { key: "date", label: "İşlem Tarihi *", required: true },
    { key: "customer_name", label: "Müşteri Adı *", required: true },
    { key: "item_name", label: "İşlem / Hizmet Adı *", required: true },
    { key: "amount_excl_vat", label: "KDV Hariç Tutar *", required: false },
    { key: "amount_incl_vat", label: "KDV Dahil Tutar", required: false },
    { key: "vat_rate", label: "KDV Oranı", required: false },
    { key: "department_name", label: "Departman Adı", required: false },
    { key: "customer_tax_id", label: "TC Kimlik / Vergi No", required: false },
    { key: "staff_name", label: "Personel Adı", required: false },
    { key: "payment_method", label: "Tahsilat Şekli", required: false },
    { key: "invoice_status", label: "Fatura Durumu", required: false },
    { key: "description", label: "Açıklama", required: false }
  ];

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUploadPreview = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiClient.post<UploadPreviewResponse>(
        "/transactions/upload-preview",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" }
        }
      );

      setPreviewData(res.data);
      // Initialize mapping with suggested mapping
      const initialMap: Record<string, string> = {};
      for (const [k, v] of Object.entries(res.data.suggested_mapping)) {
        if (v) initialMap[k] = v;
      }
      setMapping(initialMap);
      setStep("mapping");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Dosya yüklenirken ve önizleme alınırken bir hata oluştu.");
    } finally {
      setUploading(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!previewData) return;

    // Check required fields
    if (!mapping.date || !mapping.customer_name || !mapping.item_name) {
      setError("Lütfen zorunlu alanları (Tarih, Müşteri Adı, İşlem Adı) bir sütunla eşleştirin.");
      return;
    }
    if (!mapping.amount_excl_vat && !mapping.amount_incl_vat) {
      setError("KDV hariç veya KDV dahil tutar alanlarından en az birini eşleştirmelisiniz.");
      return;
    }

    setExecuting(true);
    setError(null);

    try {
      const res = await apiClient.post<ImportResultResponse>("/transactions/import", {
        file_id: previewData.file_id,
        column_mapping: mapping
      });

      setImportResult(res.data);
      setStep("result");
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || "İçe aktarma sırasında bir hata oluştu.");
    } finally {
      setExecuting(false);
    }
  };

  const handleReset = () => {
    setStep("upload");
    setFile(null);
    setPreviewData(null);
    setMapping({});
    setImportResult(null);
    setError(null);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: "800px" }}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FileSpreadsheet size={20} color="#1d4ed8" />
            <h3 style={{ fontSize: "17px", fontWeight: 700 }}>
              Excel / CSV Dosyasından Toplu İşlem Aktarımı
            </h3>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ border: "none", padding: "4px" }}
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="info-box warning" style={{ marginBottom: "16px" }}>
              <AlertTriangle size={18} />
              <div>{error}</div>
            </div>
          )}

          {/* STEP 1: Upload File */}
          {step === "upload" && (
            <div>
              <div
                style={{
                  border: "2px dashed #cbd5e1",
                  borderRadius: "10px",
                  padding: "40px 20px",
                  textAlign: "center",
                  background: "#f8fafc",
                  marginBottom: "20px"
                }}
              >
                <Upload size={36} color="#64748b" style={{ margin: "0 auto 12px auto" }} />
                <div style={{ fontSize: "15px", fontWeight: 600, color: "#1e293b", marginBottom: "6px" }}>
                  CSV veya Excel (.xlsx) Dosyası Seçin
                </div>
                <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px" }}>
                  Mevcut şablonunuzdaki sütunları bir sonraki adımda sistem alanlarıyla eşleştirebilirsiniz.
                </div>

                <input
                  type="file"
                  id="csvExcelFile"
                  accept=".csv, .xlsx, .xls"
                  style={{ display: "none" }}
                  onChange={handleFileSelect}
                />
                <label htmlFor="csvExcelFile" className="btn btn-primary" style={{ cursor: "pointer" }}>
                  Bilgisayardan Dosya Seç
                </label>

                {file && (
                  <div style={{ marginTop: "14px", fontSize: "13px", fontWeight: 600, color: "#059669" }}>
                    ✓ Seçilen Dosya: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </div>
                )}
              </div>

              <div className="info-box">
                <HelpCircle size={18} />
                <div>
                  <strong>Esnek Format Desteği:</strong> Sistem Türkçe tarih formatlarını (GG.AA.YYYY), virgüllü tutarları (1.250,50 TL) ve farklı sütun başlıklarını otomatik tanır.
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Column Mapping & Preview */}
          {step === "mapping" && previewData && (
            <div>
              <div className="info-box" style={{ marginBottom: "18px" }}>
                <CheckCircle2 size={18} />
                <div>
                  <strong>Dosya Başarıyla Okundu:</strong> Toplam <strong>{previewData.total_rows}</strong> satır veri tespit edildi. Lütfen sistem alanları ile dosyanızdaki sütun başlıklarını eşleştirin.
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>
                  1. Sütun Eşleştirme (Mapping)
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
                  {targetFields.map((field) => (
                    <div key={field.key} style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                      <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#334155", marginBottom: "4px" }}>
                        {field.label}
                      </label>
                      <select
                        className="form-select"
                        style={{ fontSize: "13px", padding: "6px 8px" }}
                        value={mapping[field.key] || ""}
                        onChange={(e) => setMapping({ ...mapping, [field.key]: e.target.value })}
                      >
                        <option value="">-- Eşleştirilmedi --</option>
                        {previewData.file_headers.map((header) => (
                          <option key={header} value={header}>{header}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px" }}>
                  2. Dosyadan İlk 5 Satır Önizlemesi
                </h4>
                <div className="table-responsive" style={{ maxHeight: "200px" }}>
                  <table className="table" style={{ fontSize: "12px" }}>
                    <thead>
                      <tr>
                        {previewData.file_headers.map((h, i) => (
                          <th key={i}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.preview_rows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {previewData.file_headers.map((h, cIdx) => (
                            <td key={cIdx}>{row[h] !== null && row[h] !== undefined ? String(row[h]) : ""}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Result & Error Report */}
          {step === "result" && importResult && (
            <div>
              <div
                style={{
                  padding: "20px",
                  borderRadius: "8px",
                  background: importResult.failed_count === 0 ? "#ecfdf5" : "#fffbeb",
                  border: `1px solid ${importResult.failed_count === 0 ? "#a7f3d0" : "#fde68a"}`,
                  marginBottom: "20px",
                  textAlign: "center"
                }}
              >
                <div style={{ fontSize: "20px", fontWeight: 800, color: importResult.failed_count === 0 ? "#065f46" : "#92400e" }}>
                  {importResult.successful_count} Satır Başarıyla İçe Aktarıldı!
                </div>
                <div style={{ fontSize: "13px", color: "#475569", marginTop: "4px" }}>
                  Toplam: {importResult.total_rows} satır | Başarılı: {importResult.successful_count} | Hatalı: {importResult.failed_count}
                </div>
              </div>

              {importResult.failed_count > 0 && (
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#dc2626", marginBottom: "10px" }}>
                    Hatalı / Eksik Satırlar Raporu ({importResult.errors.length} adet)
                  </h4>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "10px" }}>
                    Bu satırlarda eksik veya biçimi bozuk veri olduğundan aktarılamadı. Geçerli diğer tüm satırlar başarıyla kaydedilmiştir.
                  </p>
                  <div className="table-responsive" style={{ maxHeight: "250px" }}>
                    <table className="table" style={{ fontSize: "12px" }}>
                      <thead>
                        <tr>
                          <th style={{ width: "80px" }}>Satır No</th>
                          <th>Hata Nedeni</th>
                          <th>Ham Satır İçeriği</th>
                        </tr>
                      </thead>
                      <tbody>
                        {importResult.errors.map((err, i) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 700, color: "#dc2626" }}>#{err.row_index}</td>
                            <td style={{ color: "#b91c1c", fontWeight: 500 }}>{err.error_message}</td>
                            <td style={{ fontFamily: "monospace", fontSize: "11px", color: "#64748b" }}>
                              {JSON.stringify(err.raw_data)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step === "upload" && (
            <>
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Kapat
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleUploadPreview}
                disabled={!file || uploading}
              >
                {uploading ? "Dosya Okunuyor..." : "Önizleme ve Eşleştirmeye Geç"}
                <ArrowRight size={16} />
              </button>
            </>
          )}

          {step === "mapping" && (
            <>
              <button type="button" className="btn btn-secondary" onClick={() => setStep("upload")}>
                Geri
              </button>
              <button
                type="button"
                className="btn btn-success"
                onClick={handleExecuteImport}
                disabled={executing}
              >
                <CheckCircle2 size={16} />
                {executing ? "Kayıtlar Aktarılıyor..." : "Eşleştirmeyi Onayla & Aktarımı Başlat"}
              </button>
            </>
          )}

          {step === "result" && (
            <>
              <button type="button" className="btn btn-secondary" onClick={handleReset}>
                Yeni Dosya Yükle
              </button>
              <button type="button" className="btn btn-primary" onClick={onClose}>
                Tamamla ve İşlemlere Dön
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
