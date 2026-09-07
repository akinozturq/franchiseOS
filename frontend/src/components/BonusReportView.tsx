import React, { useState, useEffect } from "react";
import { Download, RefreshCw, AlertCircle, Award, Users, TrendingUp, DollarSign, Lock, FileSpreadsheet } from "lucide-react";
import api from "../api/client";
import type { PeriodBonusReport, TurnoverSource, User } from "../types";

interface BonusReportViewProps {
  user?: User | null;
}

export const BonusReportView: React.FC<BonusReportViewProps> = ({ user: _user }) => {
  const [selectedYear, setSelectedYear] = useState<number>(2026);
  const [selectedMonth, setSelectedMonth] = useState<number>(9);
  const [report, setReport] = useState<PeriodBonusReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);

  const fetchReport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<PeriodBonusReport>(
        `/bonus?year=${selectedYear}&month=${selectedMonth}`
      );
      setReport(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Personel prim raporu yüklenirken hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [selectedYear, selectedMonth]);

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const response = await api.get(
        `/bonus/export?year=${selectedYear}&month=${selectedMonth}`,
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `Personel_Prim_Raporu_${selectedYear}_${String(selectedMonth).padStart(2, "0")}.xlsx`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Excel dışa aktarılırken bir hata oluştu.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportPdf = async () => {
    setIsExportingPdf(true);
    try {
      const response = await api.get(
        `/bonus/export-pdf?year=${selectedYear}&month=${selectedMonth}`,
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `Personel_Prim_Raporu_${selectedYear}_${String(selectedMonth).padStart(2, "0")}.pdf`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("PDF dışa aktarılırken bir hata oluştu.");
    } finally {
      setIsExportingPdf(false);
    }
  };

  const formatMoney = (val: string | number | undefined | null): string => {
    if (val === undefined || val === null || val === "") return "0,00 TL";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      minimumFractionDigits: 2
    }).format(num);
  };

  const formatPercent = (val: string | number | undefined | null): string => {
    if (val === undefined || val === null || val === "") return "%0,00";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return `%${(num * 100).toFixed(2)}`;
  };

  const getSourceBadge = (source: TurnoverSource) => {
    switch (source) {
      case "kendi_islemleri":
        return <span className="status-badge" style={{ background: "#e0f2fe", color: "#0369a1" }}>Kendi İşlemleri</span>;
      case "kendi_departmani":
        return <span className="status-badge" style={{ background: "#fef3c7", color: "#92400e" }}>Kendi Departmanı</span>;
      case "tum_bayi":
        return <span className="status-badge" style={{ background: "#f3e8ff", color: "#6b21a8" }}>Tüm Bayi</span>;
      default:
        return <span className="status-badge">{source}</span>;
    }
  };

  return (
    <div className="view-container">
      {/* Header & Controls */}
      <div className="card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h1 className="page-title" style={{ margin: 0 }}>Personel Prim ve Hakediş Raporu</h1>
            <p className="page-description" style={{ margin: "4px 0 0 0" }}>
              Bayi personelinin kademeli prim kuralları ve kategori bazlı sabit istisna oranlarına göre dönemlik prim hakedişleri
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>Dönem:</label>
              <select
                className="input"
                style={{ width: "120px" }}
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                  <option key={m} value={m}>
                    {new Date(2000, m - 1, 1).toLocaleString("tr-TR", { month: "long" })}
                  </option>
                ))}
              </select>

              <select
                className="input"
                style={{ width: "90px" }}
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
              >
                {[2023, 2024, 2025, 2026].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>

            <button
              className="btn btn-secondary"
              onClick={fetchReport}
              disabled={isLoading}
              title="Raporu Yenile"
            >
              <RefreshCw size={14} className={isLoading ? "spin" : ""} />
              Yenile
            </button>

            <button
              className="btn btn-success"
              onClick={handleExportExcel}
              disabled={isExporting || isLoading || !report}
              title="Excel (.xlsx) İndir"
            >
              <FileSpreadsheet size={14} />
              {isExporting ? "İndiriliyor..." : "Excel"}
            </button>

            <button
              className="btn btn-primary"
              onClick={handleExportPdf}
              disabled={isExportingPdf || isLoading || !report}
              style={{ background: "#dc2626", borderColor: "#dc2626" }}
              title="Resmi Personel Prim Raporu PDF İndir"
            >
              <Download size={14} />
              {isExportingPdf ? "İndiriliyor..." : "PDF İndir"}
            </button>
          </div>
        </div>
      </div>

      {report?.is_closed && (
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: "8px",
            padding: "10px 14px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "#166534",
            fontSize: "13px",
            fontWeight: 600
          }}
        >
          <Lock size={16} color="#16a34a" />
          <span>
            🔒 Bu dönem resmi olarak kapatılmış ve dondurulmuştur. (Onay: {report.closed_by_name || "Franchisor Admin"} - {report.closed_at ? new Date(report.closed_at).toLocaleString("tr-TR") : ""}) Primler dondurulmuş JSON snapshot üzerinden gösterilmektedir.
          </span>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      {report && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
          <div className="card" style={{ padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-muted)", fontSize: "12px", fontWeight: 600 }}>
              <Users size={16} color="var(--primary)" />
              TOPLAM PERSONEL
            </div>
            <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "8px", fontVariantNumeric: "tabular-nums" }}>
              {report.total_employees} <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-muted)" }}>kişi</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              {report.total_transactions} adet işlem gerçekleşti
            </div>
          </div>

          <div className="card" style={{ padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-muted)", fontSize: "12px", fontWeight: 600 }}>
              <DollarSign size={16} color="var(--primary)" />
              TOPLAM DÖNEM CİROSU
            </div>
            <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "8px", fontVariantNumeric: "tabular-nums" }}>
              {formatMoney(report.total_turnover_excl_vat)}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              KDV Hariç net satış cirosu
            </div>
          </div>

          <div className="card" style={{ padding: "16px", background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)", border: "1px solid #bbf7d0" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#166534", fontSize: "12px", fontWeight: 600 }}>
              <Award size={16} color="#16a34a" />
              TOPLAM DAĞITILAN PRİM
            </div>
            <div style={{ fontSize: "24px", fontWeight: 700, color: "#15803d", marginTop: "8px", fontVariantNumeric: "tabular-nums" }}>
              {formatMoney(report.grand_total_bonus)}
            </div>
            <div style={{ fontSize: "11px", color: "#166534", marginTop: "4px" }}>
              Hak edilen toplam brüt prim
            </div>
          </div>

          <div className="card" style={{ padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-muted)", fontSize: "12px", fontWeight: 600 }}>
              <TrendingUp size={16} color="var(--primary)" />
              ORTALAMA PRİM ORANI
            </div>
            <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "8px", fontVariantNumeric: "tabular-nums" }}>
              {report.total_turnover_excl_vat && parseFloat(report.total_turnover_excl_vat) > 0
                ? formatPercent(parseFloat(report.grand_total_bonus) / parseFloat(report.total_turnover_excl_vat))
                : "%0,00"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              Ciro / prim oranı
            </div>
          </div>
        </div>
      )}

      {/* Bonus Breakdown Table */}
      <div className="card" style={{ overflow: "hidden", padding: 0 }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>Personel Prim Hakediş Tablosu</h2>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Dönem: {selectedMonth}/{selectedYear}
          </span>
        </div>

        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Personel Adı</th>
                <th>Rol</th>
                <th>Departman</th>
                <th>Ciro Kaynağı</th>
                <th style={{ textAlign: "center" }}>İşlem Ad.</th>
                <th style={{ textAlign: "right" }}>Standart Ciro</th>
                <th style={{ textAlign: "right" }}>Dilim Oranı</th>
                <th style={{ textAlign: "right" }}>Standart Prim</th>
                <th style={{ textAlign: "right" }}>İstisnalı Ciro</th>
                <th style={{ textAlign: "right" }}>İstisnalı Prim</th>
                <th style={{ textAlign: "right" }}>Toplam Ciro</th>
                <th style={{ textAlign: "right", background: "#f8fafc" }}>TOPLAM PRİM</th>
                <th style={{ textAlign: "right" }}>Efektif Oran</th>
                <th>Açıklama</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={14} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    <RefreshCw size={20} className="spin" style={{ margin: "0 auto 10px" }} />
                    Prim raporu hesaplanıyor...
                  </td>
                </tr>
              ) : !report || report.items.length === 0 ? (
                <tr>
                  <td colSpan={14} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    Bu dönem için personel prim kaydı bulunamadı.
                  </td>
                </tr>
              ) : (
                <>
                  {report.items.map((item) => (
                    <tr key={item.employee_id}>
                      <td style={{ fontWeight: 600 }}>{item.employee_name}</td>
                      <td>{item.role_name}</td>
                      <td>{item.department_name || "—"}</td>
                      <td>{getSourceBadge(item.turnover_source)}</td>
                      <td style={{ textAlign: "center", fontVariantNumeric: "tabular-nums" }}>{item.transaction_count}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatMoney(item.standard_turnover_excl_vat)}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {parseFloat(item.standard_tier_rate) > 0 ? formatPercent(item.standard_tier_rate) : "—"}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatMoney(item.standard_bonus)}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: parseFloat(item.override_turnover_excl_vat) > 0 ? "var(--primary)" : undefined }}>
                        {formatMoney(item.override_turnover_excl_vat)}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: parseFloat(item.override_bonus) > 0 ? "var(--primary)" : undefined }}>
                        {formatMoney(item.override_bonus)}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                        {formatMoney(item.total_turnover_excl_vat)}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 700, color: "#166534", background: "#f0fdf4", fontVariantNumeric: "tabular-nums" }}>
                        {formatMoney(item.total_bonus)}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatPercent(item.effective_bonus_rate)}
                      </td>
                      <td style={{ fontSize: "11px", color: "var(--text-muted)", maxWidth: "250px" }}>
                        {item.tier_explanation}
                      </td>
                    </tr>
                  ))}
                  {/* Grand Total Row */}
                  <tr style={{ background: "#f1f5f9", fontWeight: 700, borderTop: "2px solid var(--border)" }}>
                    <td colSpan={4} style={{ textAlign: "center" }}>GENEL TOPLAM</td>
                    <td style={{ textAlign: "center", fontVariantNumeric: "tabular-nums" }}>
                      {report.items.reduce((acc, curr) => acc + curr.transaction_count, 0)}
                    </td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {formatMoney(report.items.reduce((acc, curr) => acc + parseFloat(curr.standard_turnover_excl_vat), 0))}
                    </td>
                    <td style={{ textAlign: "right" }}>—</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {formatMoney(report.items.reduce((acc, curr) => acc + parseFloat(curr.standard_bonus), 0))}
                    </td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {formatMoney(report.items.reduce((acc, curr) => acc + parseFloat(curr.override_turnover_excl_vat), 0))}
                    </td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {formatMoney(report.items.reduce((acc, curr) => acc + parseFloat(curr.override_bonus), 0))}
                    </td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {formatMoney(report.total_turnover_excl_vat)}
                    </td>
                    <td style={{ textAlign: "right", color: "#166534", background: "#dcfce7", fontVariantNumeric: "tabular-nums", fontSize: "14px" }}>
                      {formatMoney(report.grand_total_bonus)}
                    </td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {parseFloat(report.total_turnover_excl_vat) > 0
                        ? formatPercent(parseFloat(report.grand_total_bonus) / parseFloat(report.total_turnover_excl_vat))
                        : "%0,00"}
                    </td>
                    <td style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      {report.total_employees} personelin toplam hak edişi
                    </td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
