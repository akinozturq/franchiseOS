import React, { useState, useEffect } from "react";
import {
  Download,
  AlertCircle,
  RefreshCw,
  Receipt,
  Lock,
  Unlock,
  Clock,
  FileText,
  FileSpreadsheet
} from "lucide-react";
import { apiClient } from "../api/client";
import type {
  ReconciliationReport,
  CollectorParty,
  PeriodClosureStatus,
  InvoiceDataExport,
  User
} from "../types";
import { formatCurrency, formatPercent } from "../utils/formatters";
import { InvoiceDataModal } from "./InvoiceDataModal";

interface ReconciliationViewProps {
  user?: User | null;
}

export const ReconciliationView: React.FC<ReconciliationViewProps> = ({ user }) => {
  const currentDate = new Date();
  const [year, setYear] = useState<number>(currentDate.getFullYear());
  const [month, setMonth] = useState<number>(currentDate.getMonth() + 1);
  const [collectorParty, setCollectorParty] = useState<CollectorParty>("BAYI");
  const [vatRate, setVatRate] = useState<string>("0.20");

  const [report, setReport] = useState<ReconciliationReport | null>(null);
  const [closureStatus, setClosureStatus] = useState<PeriodClosureStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [exportingExcel, setExportingExcel] = useState<boolean>(false);
  const [exportingPdf, setExportingPdf] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false);
  const [isReopenModalOpen, setIsReopenModalOpen] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [invoiceData, setInvoiceData] = useState<InvoiceDataExport | null>(null);
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false);

  const months = [
    { value: 1, label: "Ocak" },
    { value: 2, label: "Şubat" },
    { value: 3, label: "Mart" },
    { value: 4, label: "Nisan" },
    { value: 5, label: "Mayıs" },
    { value: 6, label: "Haziran" },
    { value: 7, label: "Temmuz" },
    { value: 8, label: "Ağustos" },
    { value: 9, label: "Eylül" },
    { value: 10, label: "Ekim" },
    { value: 11, label: "Kasım" },
    { value: 12, label: "Aralık" }
  ];

  const fetchClosureStatus = async () => {
    try {
      const res = await apiClient.get<PeriodClosureStatus>("/period-closures/status", {
        params: { year, month }
      });
      setClosureStatus(res.data);
    } catch (e) {
      console.error("Dönem kapama durumu alınamadı", e);
    }
  };

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<ReconciliationReport>("/reconciliation", {
        params: { year, month }
      });
      setReport(res.data);
      if (res.data.invoice_summary?.collector_party) {
        setCollectorParty(res.data.invoice_summary.collector_party);
      }
      if (res.data.invoice_summary?.vat_rate) {
        setVatRate(String(res.data.invoice_summary.vat_rate));
      }
      fetchClosureStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Mutabakat raporu hesaplanırken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [year, month]);

  const handleUpdateSetting = async (newParty: CollectorParty, newVat: string) => {
    if (closureStatus?.is_closed) {
      alert("Bu dönem kapatılmış ve dondurulmuştur. Kapatılmış dönem ayarları değiştirilemez.");
      return;
    }
    setCollectorParty(newParty);
    setVatRate(newVat);
    try {
      await apiClient.put("/reconciliation/setting", {
        year,
        month,
        collector_party: newParty,
        vat_rate: parseFloat(newVat)
      });
      fetchReport();
    } catch (err) {
      console.error("Dönem ayarı kaydedilemedi", err);
    }
  };

  const handleExportExcel = async () => {
    setExportingExcel(true);
    try {
      const response = await apiClient.get("/reconciliation/export", {
        params: { year, month },
        responseType: "blob"
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Mutabakat_Raporu_${year}_${String(month).padStart(2, "0")}_${collectorParty}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      alert("Excel dosyası indirilirken bir hata oluştu.");
    } finally {
      setExportingExcel(false);
    }
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const response = await apiClient.get("/reconciliation/export-pdf", {
        params: { year, month },
        responseType: "blob"
      });

      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Mutabakat_Raporu_${year}_${String(month).padStart(2, "0")}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      alert("PDF dosyası indirilirken bir hata oluştu.");
    } finally {
      setExportingPdf(false);
    }
  };

  const handleClosePeriod = async () => {
    setActionLoading(true);
    try {
      await apiClient.post("/period-closures", { year, month });
      setIsCloseModalOpen(false);
      fetchReport();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dönem kapatılırken hata oluştu.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestClosure = async () => {
    setActionLoading(true);
    try {
      await apiClient.post("/period-closures/request", { year, month });
      alert("Dönem kapatma talebiniz genel merkeze başarıyla iletildi.");
      fetchClosureStatus();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Kapatma talebi gönderilemedi.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopenPeriod = async () => {
    if (!closureStatus?.closure_id) return;
    if (!reopenReason || reopenReason.trim().length < 5) {
      alert("Lütfen en az 5 karakterden oluşan geçerli bir yeniden açma gerekçesi giriniz.");
      return;
    }
    setActionLoading(true);
    try {
      await apiClient.post(`/period-closures/${closureStatus.closure_id}/reopen`, {
        reopen_reason: reopenReason.trim()
      });
      setIsReopenModalOpen(false);
      setReopenReason("");
      fetchReport();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dönem yeniden açılırken hata oluştu.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleFetchInvoiceData = async () => {
    if (!closureStatus?.closure_id) return;
    try {
      const res = await apiClient.get<InvoiceDataExport>(
        `/period-closures/${closureStatus.closure_id}/invoice-data`
      );
      setInvoiceData(res.data);
      setIsInvoiceModalOpen(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || "E-fatura verisi alınamadı.");
    }
  };

  return (
    <div>
      {/* Period Closure Status Banner */}
      {closureStatus?.is_closed ? (
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: "8px",
            padding: "12px 16px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ background: "#dcfce7", padding: "6px", borderRadius: "50%" }}>
              <Lock size={18} color="#16a34a" />
            </div>
            <div>
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#166534" }}>
                🔒 Resmi Olarak Kapatılmış & Dondurulmuş Dönem (Kayıt #{closureStatus.closure_id})
              </div>
              <div style={{ fontSize: "12px", color: "#15803d" }}>
                Kapatan: <b>{closureStatus.closed_by_name || "Franchisor Admin"}</b> • Tarih:{" "}
                {closureStatus.closed_at ? new Date(closureStatus.closed_at).toLocaleString("tr-TR") : "-"}
                {" "}(Bu dönemin raporları canlı kurallardan bağımsız, dondurulmuş snapshot verisinden sunulmaktadır.)
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleFetchInvoiceData}
              title="Standart E-Fatura JSON Verisi"
            >
              <FileText size={14} />
              E-Fatura JSON
            </button>

            {user?.role === "FRANCHISOR_ADMIN" && (
              <button
                type="button"
                className="btn btn-warning btn-sm"
                onClick={() => setIsReopenModalOpen(true)}
              >
                <Unlock size={14} />
                Dönemi Yeniden Aç
              </button>
            )}
          </div>
        </div>
      ) : closureStatus?.status === "CLOSURE_REQUESTED" ? (
        <div
          style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "8px",
            padding: "12px 16px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Clock size={18} color="#2563eb" />
            <div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#1e40af" }}>
                ⏳ Dönem Kapatma Talebi Gönderildi (Onay Bekliyor)
              </div>
              <div style={{ fontSize: "12px", color: "#3b82f6" }}>
                Bayi yöneticisi tarafından mutabakat kapama onayı talep edilmiştir.
              </div>
            </div>
          </div>

          {user?.role === "FRANCHISOR_ADMIN" && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setIsCloseModalOpen(true)}
            >
              <Lock size={14} />
              Kapatmayı Onayla & Dondur
            </button>
          )}
        </div>
      ) : closureStatus?.status === "REOPENED" ? (
        <div
          style={{
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "8px",
            padding: "12px 16px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Unlock size={18} color="#d97706" />
            <div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#92400e" }}>
                🔓 Dönem Yeniden Açıldı (Düzenlenebilir)
              </div>
              <div style={{ fontSize: "12px", color: "#b45309" }}>
                Gerekçe: <i>"{closureStatus.reopen_reason}"</i>
              </div>
            </div>
          </div>

          {user?.role === "FRANCHISOR_ADMIN" ? (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setIsCloseModalOpen(true)}
            >
              <Lock size={14} />
              Dönemi Tekrar Kapat & Dondur
            </button>
          ) : user?.role === "BAYI_ADMIN" ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleRequestClosure}
              disabled={actionLoading}
            >
              <Clock size={14} />
              Kapatma Talep Et
            </button>
          ) : null}
        </div>
      ) : null}

      {/* Header Controls */}
      <div className="card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a" }}>
              Dönemlik Komisyon ve Mutabakat Raporu
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
              Dönem cirosuna göre kademeli oran hesaplaması, gelir paylaşımı ve fatura kesim tablosu.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <select
              className="form-select"
              style={{ width: "100px" }}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            >
              {[2024, 2025, 2026, 2027].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>

            <select
              className="form-select"
              style={{ width: "120px" }}
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            >
              {months.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>

            <button
              className="btn btn-secondary"
              onClick={fetchReport}
              title="Yeniden Hesapla"
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} />
              Hesapla
            </button>

            {/* Export buttons */}
            <button
              className="btn btn-success"
              onClick={handleExportExcel}
              disabled={exportingExcel || loading}
              title="Excel Raporu İndir (.xlsx)"
            >
              <FileSpreadsheet size={15} />
              {exportingExcel ? "İndiriliyor..." : "Excel"}
            </button>

            <button
              className="btn btn-primary"
              onClick={handleExportPdf}
              disabled={exportingPdf || loading}
              style={{ background: "#dc2626", borderColor: "#dc2626" }}
              title="Resmi Mutabakat Belgesi PDF İndir"
            >
              <Download size={15} />
              {exportingPdf ? "İndiriliyor..." : "PDF İndir"}
            </button>

            {/* Period closure action button if open */}
            {!closureStatus?.is_closed && (
              <>
                {user?.role === "FRANCHISOR_ADMIN" && (
                  <button
                    className="btn btn-primary"
                    onClick={() => setIsCloseModalOpen(true)}
                    style={{ background: "#0f172a", borderColor: "#0f172a" }}
                  >
                    <Lock size={15} />
                    Dönemi Kapat & Dondur
                  </button>
                )}
                {user?.role === "BAYI_ADMIN" && closureStatus?.status !== "CLOSURE_REQUESTED" && (
                  <button
                    className="btn btn-secondary"
                    onClick={handleRequestClosure}
                    disabled={actionLoading}
                  >
                    <Clock size={15} />
                    Kapatma Talep Et
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Collector Party and VAT Setting */}
        <div
          style={{
            marginTop: "16px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "13px", fontWeight: 600, color: "#334155" }}>
              Tahsilatı Yapan Taraf:
            </span>
            <div style={{ display: "inline-flex", background: "#f1f5f9", padding: "3px", borderRadius: "6px" }}>
              <button
                type="button"
                className={`btn btn-sm ${collectorParty === "BAYI" ? "btn-primary" : "btn-secondary"}`}
                style={{ border: "none", boxShadow: collectorParty === "BAYI" ? "0 1px 2px rgba(0,0,0,0.1)" : "none" }}
                onClick={() => handleUpdateSetting("BAYI", vatRate)}
                disabled={closureStatus?.is_closed}
              >
                Bayi Tahsil Ediyor
              </button>
              <button
                type="button"
                className={`btn btn-sm ${collectorParty === "FRANCHISOR" ? "btn-primary" : "btn-secondary"}`}
                style={{ border: "none", boxShadow: collectorParty === "FRANCHISOR" ? "0 1px 2px rgba(0,0,0,0.1)" : "none" }}
                onClick={() => handleUpdateSetting("FRANCHISOR", vatRate)}
                disabled={closureStatus?.is_closed}
              >
                Franchisor (Merkez) Tahsil Ediyor
              </button>
            </div>
            {closureStatus?.is_closed ? (
              <span className="badge" style={{ background: "#f1f5f9", color: "#64748b", fontSize: "11px" }}>
                🔒 Kapatılmış Dönem (Kilitli)
              </span>
            ) : (
              <span className="badge badge-success" style={{ fontSize: "11px" }}>
                ✓ Veritabanında Kalıcı Kayıtlı
              </span>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>KDV Oranı:</span>
            <select
              className="form-select"
              style={{ width: "90px" }}
              value={vatRate}
              disabled={closureStatus?.is_closed}
              onChange={(e) => handleUpdateSetting(collectorParty, e.target.value)}
            >
              <option value="0.20">%20</option>
              <option value="0.18">%18</option>
              <option value="0.10">%10</option>
              <option value="0.08">%8</option>
              <option value="0.01">%1</option>
              <option value="0">%0</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: "20px", background: "#fef2f2", borderColor: "#fecaca" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#b91c1c" }}>
            <AlertCircle size={20} />
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Main Content Report */}
      {report && (
        <>
          {/* Revenue Shares & Invoicing Cards */}
          <div className="grid grid-3" style={{ marginBottom: "20px" }}>
            {/* Total Turnover */}
            <div className="card">
              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                Dönem Net Cirosu (KDV Hariç)
              </div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)" }} className="tabular-nums">
                {formatCurrency(report.total_turnover_excl_vat)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Toplam {report.total_transactions} adet işlem üzerinden
              </div>
            </div>

            {/* Bayi Share */}
            <div className="card">
              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                Bayi Hakediş Payı
              </div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "#16a34a" }} className="tabular-nums">
                {formatCurrency(report.bayi_share_excl_vat)}
              </div>
              <div style={{ fontSize: "12px", color: "#15803d", marginTop: "6px" }}>
                Efektif Oran: {formatPercent(report.bayi_share_rate)}
              </div>
            </div>

            {/* Franchisor Share */}
            <div className="card">
              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                Franchisor Komisyon / Royalty Payı
              </div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--primary)" }} className="tabular-nums">
                {formatCurrency(report.franchisor_share_excl_vat)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--primary-dark)", marginTop: "6px" }}>
                Komisyon Oranı: {formatPercent(report.franchisor_share_rate)}
              </div>
            </div>
          </div>

          {/* Official Invoice Card */}
          <div className="card" style={{ marginBottom: "20px", background: "#f8fafc", border: "1.5px solid #cbd5e1" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <Receipt size={22} color="var(--primary)" />
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "#0f172a" }}>
                  Resmi Dönem Mutabakat & Fatura Emri
                </h3>
                <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                  Tahsilatı yapan taraf kuralına göre düzenlenecek resmi e-fatura detayları
                </p>
              </div>
            </div>

            <div className="grid grid-2" style={{ gap: "20px" }}>
              <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>
                  Fatura Düzenleyen (Satıcı)
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginTop: "4px" }}>
                  {report.invoice_summary.issuer}
                </div>
                <div style={{ fontSize: "13px", color: "#475569", marginTop: "8px" }}>
                  <b>Açıklama:</b> {report.invoice_summary.description}
                </div>
              </div>

              <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>
                  Fatura Muhatabı (Alıcı)
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginTop: "4px" }}>
                  {report.invoice_summary.recipient}
                </div>
                <div style={{ fontSize: "13px", color: "#475569", marginTop: "8px" }}>
                  <b>Tahsilatçı:</b> {report.invoice_summary.collector_party === "BAYI" ? "Bayi (Parayı Bayi Tahsil Etti)" : "Franchisor (Parayı Merkez Tahsil Etti)"}
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: "16px",
                padding: "16px",
                background: "#ffffff",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "16px"
              }}
            >
              <div>
                <div style={{ fontSize: "12px", color: "#64748b" }}>Fatura Matrahı (KDV Hariç)</div>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "#0f172a" }} className="tabular-nums">
                  {formatCurrency(report.invoice_summary.amount_excl_vat)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: "12px", color: "#64748b" }}>
                  Hesaplanan KDV (%{Number(report.invoice_summary.vat_rate) * 100})
                </div>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "#0f172a" }} className="tabular-nums">
                  {formatCurrency(report.invoice_summary.vat_amount)}
                </div>
              </div>

              <div>
                <div style={{ fontSize: "12px", color: "var(--primary)", fontWeight: 600 }}>
                  Ödenecek / Fatura Toplamı (KDV Dahil)
                </div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "var(--primary)" }} className="tabular-nums">
                  {formatCurrency(report.invoice_summary.total_amount_incl_vat)}
                </div>
              </div>
            </div>
          </div>

          {/* Department Breakdown Table */}
          <div className="card" style={{ marginBottom: "20px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginBottom: "12px" }}>
              Departman Bazında Ciro Dağılımı
            </h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Departman Adı</th>
                  <th style={{ textAlign: "right" }}>İşlem Adedi</th>
                  <th style={{ textAlign: "right" }}>Ciro (KDV Hariç)</th>
                  <th style={{ textAlign: "right" }}>Ciro Payı %</th>
                </tr>
              </thead>
              <tbody>
                {report.department_breakdown.map((dept) => (
                  <tr key={dept.department_id}>
                    <td style={{ fontWeight: 600 }}>{dept.department_name}</td>
                    <td style={{ textAlign: "right" }}>{dept.transaction_count}</td>
                    <td style={{ textAlign: "right" }} className="tabular-nums">
                      {formatCurrency(dept.total_turnover_excl_vat)}
                    </td>
                    <td style={{ textAlign: "right" }} className="tabular-nums">
                      {formatPercent(dept.percentage_of_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Period Close Confirmation Modal */}
      {isCloseModalOpen && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: "520px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <div style={{ background: "#fee2e2", padding: "8px", borderRadius: "50%" }}>
                <Lock size={20} color="#dc2626" />
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#0f172a" }}>
                Dönemi Kapat ve Raporları Dondur
              </h3>
            </div>

            <p style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5, margin: "0 0 16px 0" }}>
              <b>{year} - {months.find((m) => m.value === month)?.label}</b> dönemini resmen kapatmak üzeresiniz.
            </p>

            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "12px", fontSize: "12px", color: "#334155", marginBottom: "16px" }}>
              <ul style={{ margin: 0, paddingLeft: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <li>Dönem mutabakat ve personel prim raporu <b>tam sonucu ile JSON snapshot olarak dondurulur</b>.</li>
                <li>Bu döneme ait işlemler kilitlenir; işlem ekleme, düzenleme veya silme engellenir.</li>
                <li>Gelecekte kural veya oran değişiklikleri yapılsa bile bu dönemin resmi raporu <b>asla değişmez</b>.</li>
                <li>Dönemi yeniden açmak gerekirse sadece Franchisor Admin tarafından zorunlu gerekçe ile yapılabilir.</li>
              </ul>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsCloseModalOpen(false)}
                disabled={actionLoading}
              >
                Vazgeç
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ background: "#0f172a", borderColor: "#0f172a" }}
                onClick={handleClosePeriod}
                disabled={actionLoading}
              >
                {actionLoading ? "Kapatılıyor..." : "Onayla ve Dönemi Kapat"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Period Reopen Modal */}
      {isReopenModalOpen && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: "520px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <div style={{ background: "#fef3c7", padding: "8px", borderRadius: "50%" }}>
                <Unlock size={20} color="#d97706" />
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#0f172a" }}>
                Kapatılmış Dönemi Yeniden Aç
              </h3>
            </div>

            <p style={{ fontSize: "13px", color: "#475569", margin: "0 0 12px 0" }}>
              Bu işlem resmi denetim loguna yazılacaktır. Dönemi yeniden açmak için <b>zorunlu bir gerekçe</b> belirtmelisiniz:
            </p>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "#334155", display: "block", marginBottom: "6px" }}>
                Yeniden Açma Gerekçesi (Zorunlu, min 5 karakter):
              </label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Örn: Muhasebe tarafından geç bildirilen servis faturası işlenecek..."
                value={reopenReason}
                onChange={(e) => setReopenReason(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsReopenModalOpen(false)}
                disabled={actionLoading}
              >
                Vazgeç
              </button>
              <button
                type="button"
                className="btn btn-warning"
                onClick={handleReopenPeriod}
                disabled={actionLoading || reopenReason.trim().length < 5}
              >
                {actionLoading ? "Açılıyor..." : "Gerekçeyle Yeniden Aç"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Standardized E-Invoice Data Modal */}
      <InvoiceDataModal
        isOpen={isInvoiceModalOpen}
        onClose={() => setIsInvoiceModalOpen(false)}
        data={invoiceData}
      />
    </div>
  );
};
