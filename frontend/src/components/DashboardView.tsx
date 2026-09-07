import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";
import {
  Award,
  PieChart as PieIcon,
  ChevronRight,
  AlertCircle
} from "lucide-react";
import { apiClient } from "../api/client";
import { formatCurrency, formatNumber } from "../utils/formatters";
import type {
  User,
  FranchisorDashboardData,
  BranchDashboardData
} from "../types";

interface DashboardViewProps {
  user: User;
  activeBranchId: number | null;
  onSelectBranch: (branchId: number | null) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  user,
  activeBranchId,
  onSelectBranch
}) => {
  const [year, setYear] = useState<number>(2026);
  const [month, setMonth] = useState<number>(9);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [franchisorData, setFranchisorData] = useState<FranchisorDashboardData | null>(null);
  const [branchData, setBranchData] = useState<BranchDashboardData | null>(null);

  const isFranchisorComparison = user.role === "FRANCHISOR_ADMIN" && activeBranchId === null;

  useEffect(() => {
    fetchDashboardData();
  }, [year, month, activeBranchId, user.role]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isFranchisorComparison) {
        const res = await apiClient.get<FranchisorDashboardData>("/dashboard/franchisor", {
          params: { year, month }
        });
        setFranchisorData(res.data);
        setBranchData(null);
      } else {
        const params: any = { year, month };
        if (activeBranchId) {
          params.branch_id = activeBranchId;
        }
        const res = await apiClient.get<BranchDashboardData>("/dashboard/branch", {
          params
        });
        setBranchData(res.data);
        setFranchisorData(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Dashboard verileri yüklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header & Filter Controls */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          padding: "16px 20px"
        }}
      >
        <div>
          {!isFranchisorComparison && user.role === "FRANCHISOR_ADMIN" && (
            <button
              className="btn btn-secondary btn-sm"
              style={{ marginBottom: "8px" }}
              onClick={() => onSelectBranch(null)}
            >
              ← Tüm Bayiler Karşılaştırmasına Dön
            </button>
          )}
          <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
            {isFranchisorComparison
              ? "Tüm Bayiler Karşılaştırmalı Performans Özeti"
              : `${branchData?.summary?.branch_name || "Bayi"} Finans & Trend Paneli`}
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
            {isFranchisorComparison
              ? "Merkez genelindeki bayilerin ciro, mutabakat ve paylaşılan gelir kırılımı."
              : "Dönemsel ciro trendleri, departman payları ve personel prim dağılımı."}
          </p>
        </div>

        {/* Period Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-muted)" }}>
            Dönem:
          </label>
          <select
            className="form-input"
            style={{ width: "120px", padding: "6px 10px" }}
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            {months.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          <select
            className="form-input"
            style={{ width: "90px", padding: "6px 10px" }}
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            <option value={2024}>2024</option>
            <option value={2025}>2025</option>
            <option value={2026}>2026</option>
          </select>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: "14px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "8px",
            color: "#b91c1c",
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            gap: "10px"
          }}
        >
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Dashboard verileri hesaplanıyor...
        </div>
      ) : isFranchisorComparison && franchisorData ? (
        /* ======================================================== */
        /* 1. FRANCHISOR ADMIN: MULTI-BRANCH COMPARATIVE VIEW        */
        /* ======================================================== */
        <>
          {/* Top KPI Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #1e3a8a" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Toplam Ağ Cirosu</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(franchisorData.totals.total_turnover)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                {franchisorData.totals.active_branches} aktif bayi genelinde
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #b45309" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Toplam Merkez Payı</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#b45309", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(franchisorData.totals.total_franchisor_share)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Franchisor komisyon geliri
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #0f766e" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Toplam Bayi Payı</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#0f766e", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(franchisorData.totals.total_bayi_share)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Bayilerde kalan net pay
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #475569" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Toplam İşlem Sayısı</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#334155", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatNumber(franchisorData.totals.total_transactions)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Faturalandırılan işlem hacmi
              </div>
            </div>
          </div>

          {/* Comparative Bar Chart */}
          <div className="card" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "16px", color: "var(--text-main)" }}>
              Bayiler Arası Ciro ve Paylaşım Karşılaştırması
            </h3>
            <div style={{ height: "300px", width: "100%" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={franchisorData.branches.map((b) => ({
                    name: b.branch_name,
                    "Ciro (KDV Hariç)": Number(b.total_turnover),
                    "Bayi Payı": Number(b.bayi_share),
                    "Merkez Payı": Number(b.franchisor_share)
                  }))}
                  margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(val) => `${(val / 1000).toFixed(0)}k TL`} />
                  <Tooltip formatter={(value: any) => [formatCurrency(value), ""]} />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Bar dataKey="Ciro (KDV Hariç)" fill="#1e3a8a" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Bayi Payı" fill="#0f766e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Merkez Payı" fill="#b45309" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Ranked Table */}
          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, margin: 0 }}>
                Bayi Sıralama Listesi (Ciroya Göre Azalan)
              </h3>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Detay görmek istediğiniz bayiye tıklayın
              </span>
            </div>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: "40px" }}>#</th>
                    <th>Bayi Adı</th>
                    <th style={{ textAlign: "right" }}>Ciro (KDV Hariç)</th>
                    <th style={{ textAlign: "right" }}>Merkez Payı</th>
                    <th style={{ textAlign: "right" }}>Bayi Payı</th>
                    <th style={{ textAlign: "center" }}>İşlem Adedi</th>
                    <th style={{ textAlign: "center" }}>Tahsilatçı</th>
                    <th>Fatura Akışı</th>
                    <th style={{ textAlign: "right" }}>Ödenecek Tutar</th>
                    <th style={{ textAlign: "center" }}>İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {franchisorData.branches.map((b, idx) => (
                    <tr key={b.branch_id} style={{ cursor: "pointer" }} onClick={() => onSelectBranch(b.branch_id)}>
                      <td style={{ fontWeight: 700, color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                        {idx + 1}
                      </td>
                      <td style={{ fontWeight: 600, color: "#1e3a8a" }}>
                        {b.branch_name}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(b.total_turnover)}
                      </td>
                      <td style={{ textAlign: "right", color: "#b45309", fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(b.franchisor_share)}
                      </td>
                      <td style={{ textAlign: "right", color: "#0f766e", fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(b.bayi_share)}
                      </td>
                      <td style={{ textAlign: "center", fontVariantNumeric: "tabular-nums" }}>
                        {formatNumber(b.transaction_count)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className={`badge ${b.collector_party === "BAYI" ? "badge-info" : "badge-warning"}`}>
                          {b.collector_party === "BAYI" ? "Bayi Tahsil Etti" : "Merkez Tahsil Etti"}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px" }}>
                        {b.invoice_direction}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(b.invoice_net_payable)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectBranch(b.branch_id);
                          }}
                        >
                          İncele <ChevronRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : branchData ? (
        /* ======================================================== */
        /* 2. BAYI ADMIN / VIEWER / BRANCH DETAIL VIEW               */
        /* ======================================================== */
        <>
          {/* Top KPI Cards for Branch */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #1e3a8a" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Dönem Toplam Cirosu</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(branchData.summary.total_turnover)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                {branchData.summary.transaction_count} adet işlem kaydı
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #0f766e" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Hak Edilen Bayi Payı</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#0f766e", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(branchData.summary.bayi_share)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Merkez payı: {formatCurrency(branchData.summary.franchisor_share)}
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #4f46e5" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Toplam Personel Primi</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#4f46e5", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(branchData.summary.total_bonuses)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Hak edişlerden personele dağıtılan prim
              </div>
            </div>

            <div className="card" style={{ padding: "18px", borderLeft: "4px solid #16a34a" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Net Bayi Marjı (Kalan Kâr)</div>
              <div style={{ fontSize: "22px", fontWeight: 800, color: "#16a34a", marginTop: "4px", fontVariantNumeric: "tabular-nums" }}>
                {formatCurrency(branchData.summary.net_bayi_margin)}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Bayi payı eksi personel primleri
              </div>
            </div>
          </div>

          {/* Monthly Turnover & Shares Trend Line Chart */}
          <div className="card" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "16px", color: "var(--text-main)" }}>
              Son 6 Aylık Ciro ve Gelir Paylaşımı Trendi
            </h3>
            <div style={{ height: "300px", width: "100%" }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={branchData.monthly_trends.map((t) => ({
                    period: t.period,
                    "Toplam Ciro": Number(t.turnover),
                    "Bayi Payı": Number(t.bayi_share),
                    "Merkez Payı": Number(t.franchisor_share)
                  }))}
                  margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(val) => `${(val / 1000).toFixed(0)}k TL`} />
                  <Tooltip formatter={(value: any) => [formatCurrency(value), ""]} />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Line type="monotone" dataKey="Toplam Ciro" stroke="#1e3a8a" strokeWidth={3} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="Bayi Payı" stroke="#0f766e" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="Merkez Payı" stroke="#b45309" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Lower Grid: Department Breakdown & Top 5 Bonus Earners */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "20px" }}>
            {/* Department Breakdown */}
            <div className="card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <PieIcon size={18} color="#1e3a8a" />
                <h3 style={{ fontSize: "15px", fontWeight: 700, margin: 0, color: "var(--text-main)" }}>
                  Departman Bazlı Ciro Kırılımı
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {branchData.department_breakdown.map((d) => (
                  <div key={d.department_id} style={{ padding: "10px", background: "#f8fafc", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontWeight: 600, fontSize: "13px" }}>{d.department_name}</span>
                      <span style={{ fontWeight: 700, fontSize: "13px", fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(d.turnover)} ({d.percentage}%)
                      </span>
                    </div>
                    {/* Visual Progress Bar */}
                    <div style={{ height: "6px", width: "100%", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                      <div
                        style={{
                          height: "100%",
                          width: `${Math.min(100, Math.max(0, Number(d.percentage)))}%`,
                          background: "#1e3a8a",
                          borderRadius: "3px"
                        }}
                      />
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                      {d.transaction_count} adet işlem gerçekleştirildi
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top 5 Bonus Earners */}
            <div className="card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <Award size={18} color="#b45309" />
                <h3 style={{ fontSize: "15px", fontWeight: 700, margin: 0, color: "var(--text-main)" }}>
                  En Çok Prim Kazanan Personeller (Top 5)
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {branchData.top_bonus_employees.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", fontSize: "13px", padding: "20px 0", textAlign: "center" }}>
                    Bu dönemde prim kazanan personel bulunamadı.
                  </div>
                ) : (
                  branchData.top_bonus_employees.map((emp) => (
                    <div
                      key={emp.employee_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 14px",
                        background: emp.rank === 1 ? "#fefce8" : "#f8fafc",
                        border: emp.rank === 1 ? "1px solid #fef08a" : "1px solid var(--border)",
                        borderRadius: "6px"
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div
                          style={{
                            width: "26px",
                            height: "26px",
                            borderRadius: "50%",
                            background: emp.rank === 1 ? "#eab308" : emp.rank === 2 ? "#94a3b8" : emp.rank === 3 ? "#b45309" : "#e2e8f0",
                            color: emp.rank <= 3 ? "#ffffff" : "#475569",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: "12px",
                            fontVariantNumeric: "tabular-nums"
                          }}
                        >
                          {emp.rank}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: "13px" }}>{emp.employee_name}</div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            {emp.role_name} {emp.department_name ? `• ${emp.department_name}` : ""}
                          </div>
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontWeight: 700, color: "#0f766e", fontSize: "14px", fontVariantNumeric: "tabular-nums" }}>
                          {formatCurrency(emp.bonus_amount)}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                          Ciro: {formatCurrency(emp.turnover)}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
