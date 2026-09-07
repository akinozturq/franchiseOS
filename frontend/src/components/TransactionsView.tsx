import React, { useState, useEffect } from "react";
import {
  Plus,
  Upload,
  Search,
  Edit2,
  Trash2,
  X,
  Check,
  AlertCircle
} from "lucide-react";
import { apiClient } from "../api/client";
import type { Transaction, Department, Employee, TransactionCategory, User } from "../types";
import { formatCurrency, formatDate } from "../utils/formatters";

interface TransactionsViewProps {
  onOpenImport: () => void;
  user?: User | null;
}

export const TransactionsView: React.FC<TransactionsViewProps> = ({ onOpenImport, user }) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [categories, setCategories] = useState<TransactionCategory[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [search, setSearch] = useState<string>("");
  const [departmentId, setDepartmentId] = useState<string>("");
  const [employeeId, setEmployeeId] = useState<string>("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [month, setMonth] = useState<string>("9");
  const [year, setYear] = useState<string>("2026");

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingTx, setEditingTx] = useState<Transaction | null>(null);
  const [formData, setFormData] = useState<Partial<Transaction>>({
    date: new Date().toISOString().split("T")[0],
    customer_name: "",
    customer_tax_id: "",
    category_id: null,
    item_name: "",
    employee_id: null,
    staff_name: "",
    amount_excl_vat: "",
    vat_rate: "0.20",
    amount_incl_vat: "",
    payment_method: "Kredi Kartı",
    invoice_status: "Faturalandı",
    description: ""
  });
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchAuxData = async () => {
    try {
      const [deptRes, empRes, catRes] = await Promise.all([
        apiClient.get<Department[]>("/departments"),
        apiClient.get<Employee[]>("/employees"),
        apiClient.get<TransactionCategory[]>("/categories")
      ]);
      setDepartments(deptRes.data);
      setEmployees(empRes.data);
      setCategories(catRes.data);
      if (deptRes.data.length > 0 && !formData.department_id) {
        setFormData((prev) => ({ ...prev, department_id: deptRes.data[0].id }));
      }
    } catch (err) {
      console.error("Yardımcı veriler alınamadı", err);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { limit: 200 };
      if (search.trim()) params.search = search.trim();
      if (departmentId) params.department_id = departmentId;
      if (employeeId) params.employee_id = employeeId;
      if (categoryId) params.category_id = categoryId;
      if (month) params.month = month;
      if (year) params.year = year;

      const res = await apiClient.get<Transaction[]>("/transactions", { params });
      setTransactions(res.data);
    } catch (err) {
      console.error("İşlemler alınamadı", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuxData();
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [search, departmentId, employeeId, categoryId, month, year]);

  const handleExclAmountChange = (val: string) => {
    const rate = parseFloat(String(formData.vat_rate || "0.20")) || 0.20;
    const num = parseFloat(val);
    let autoIncl = "";
    if (!isNaN(num)) {
      autoIncl = (num * (1 + rate)).toFixed(2);
    }
    setFormData((prev) => ({
      ...prev,
      amount_excl_vat: val,
      amount_incl_vat: autoIncl
    }));
  };

  const handleVatRateChange = (val: string) => {
    const rate = parseFloat(val) || 0.20;
    const excl = parseFloat(String(formData.amount_excl_vat || "0"));
    let autoIncl = "";
    if (!isNaN(excl) && excl > 0) {
      autoIncl = (excl * (1 + rate)).toFixed(2);
    }
    setFormData((prev) => ({
      ...prev,
      vat_rate: val,
      amount_incl_vat: autoIncl
    }));
  };

  const openCreateModal = () => {
    setEditingTx(null);
    setFormError(null);
    setFormData({
      date: new Date().toISOString().split("T")[0],
      department_id: departments[0]?.id || 1,
      customer_name: "",
      customer_tax_id: "",
      category_id: categories[0]?.id || null,
      item_name: categories[0]?.name || "",
      employee_id: employees[0]?.id || null,
      staff_name: employees[0]?.full_name || "",
      amount_excl_vat: "",
      vat_rate: "0.20",
      amount_incl_vat: "",
      payment_method: "Kredi Kartı",
      invoice_status: "Faturalandı",
      description: ""
    });
    setIsModalOpen(true);
  };

  const openEditModal = (tx: Transaction) => {
    setEditingTx(tx);
    setFormError(null);
    setFormData({
      date: tx.date,
      department_id: tx.department_id,
      customer_name: tx.customer_name,
      customer_tax_id: tx.customer_tax_id || "",
      category_id: tx.category_id || null,
      item_name: tx.item_name,
      employee_id: tx.employee_id || null,
      staff_name: tx.staff_name || "",
      amount_excl_vat: String(tx.amount_excl_vat),
      vat_rate: String(tx.vat_rate),
      amount_incl_vat: String(tx.amount_incl_vat),
      payment_method: tx.payment_method || "Kredi Kartı",
      invoice_status: tx.invoice_status || "Faturalandı",
      description: tx.description || ""
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Bu işlem kaydını silmek istediğinize emin misiniz?")) return;
    try {
      await apiClient.delete(`/transactions/${id}`);
      fetchTransactions();
    } catch (err) {
      alert("Silme işlemi başarısız.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);

    try {
      const payload = {
        ...formData,
        amount_excl_vat: parseFloat(String(formData.amount_excl_vat)),
        vat_rate: parseFloat(String(formData.vat_rate)),
        amount_incl_vat: parseFloat(String(formData.amount_incl_vat))
      };

      if (editingTx?.id) {
        await apiClient.put(`/transactions/${editingTx.id}`, payload);
      } else {
        await apiClient.post("/transactions", payload);
      }

      setIsModalOpen(false);
      fetchTransactions();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Kaydedilirken bir hata oluştu.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      {/* Top Action & Filter Bar */}
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "16px",
            marginBottom: "16px"
          }}
        >
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800 }}>İşlem Defteri (Transaction Ledger)</h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Dönemlik satış, servis ve kaplama işlemlerinin tam kayıt listesi.
            </p>
          </div>

          {user?.role !== "VIEWER" && (
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button className="btn btn-secondary" onClick={onOpenImport}>
                <Upload size={15} />
                Excel / CSV İçe Aktar
              </button>
              <button className="btn btn-primary" onClick={openCreateModal}>
                <Plus size={15} />
                Yeni İşlem Ekle
              </button>
            </div>
          )}
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ flex: "1 1 240px", position: "relative" }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "10px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#94a3b8"
              }}
            />
            <input
              type="text"
              placeholder="Müşteri, personel veya işlem ara..."
              className="form-input"
              style={{ paddingLeft: "34px" }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            className="form-select"
            style={{ width: "150px" }}
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
          >
            <option value="">Tüm Departmanlar</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>

          <select
            className="form-select"
            style={{ width: "150px" }}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
          >
            <option value="">Tüm Kategoriler</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            className="form-select"
            style={{ width: "150px" }}
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
          >
            <option value="">Tüm Personeller</option>
            {employees.map((e) => (
              <option key={e.id} value={e.id}>{e.full_name}</option>
            ))}
          </select>

          <select
            className="form-select"
            style={{ width: "110px" }}
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          >
            <option value="">Tüm Aylar</option>
            <option value="1">Ocak</option>
            <option value="2">Şubat</option>
            <option value="3">Mart</option>
            <option value="4">Nisan</option>
            <option value="5">Mayıs</option>
            <option value="6">Haziran</option>
            <option value="7">Temmuz</option>
            <option value="8">Ağustos</option>
            <option value="9">Eylül</option>
            <option value="10">Ekim</option>
            <option value="11">Kasım</option>
            <option value="12">Aralık</option>
          </select>

          <select
            className="form-select"
            style={{ width: "95px" }}
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            <option value="">Tüm Yıllar</option>
            <option value="2023">2023</option>
            <option value="2024">2024</option>
            <option value="2025">2025</option>
            <option value="2026">2026</option>
          </select>

          {(search || departmentId || employeeId || categoryId || month) && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSearch("");
                setDepartmentId("");
                setEmployeeId("");
                setCategoryId("");
                setMonth("");
              }}
            >
              Filtreleri Temizle
            </button>
          )}
        </div>
      </div>

      {/* Transactions Table */}
      <div className="table-responsive">
        <table className="table">
          <thead>
            <tr>
              <th>Tarih</th>
              <th>Departman</th>
              <th>Müşteri Adı</th>
              <th>TCKN / VKN (Maskeli)</th>
              <th>İşlem / Hizmet</th>
              <th>Personel</th>
              <th className="text-right">KDV Hariç</th>
              <th className="text-center">KDV %</th>
              <th className="text-right">KDV Dahil</th>
              <th>Tahsilat</th>
              <th className="text-center">Fatura</th>
              {user?.role !== "VIEWER" && (
                <th className="text-center">İşlem</th>
              )}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={12} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                  İşlemler yükleniyor...
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={12} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                  Kayıtlı işlem bulunamadı.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => (
                <tr key={tx.id}>
                  <td>{formatDate(tx.date)}</td>
                  <td>
                    <span className="badge badge-gray">{tx.department_name}</span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{tx.customer_name}</td>
                  <td style={{ fontFamily: "monospace", fontSize: "12px", color: "#64748b" }}>
                    {tx.customer_tax_id_masked || "-"}
                  </td>
                  <td>{tx.category_name || tx.item_name}</td>
                  <td style={{ fontWeight: 500 }}>{tx.employee_name || tx.staff_name || "-"}</td>
                  <td className="text-right" style={{ fontWeight: 600 }}>
                    {formatCurrency(tx.amount_excl_vat)}
                  </td>
                  <td className="text-center">
                    %{Number(tx.vat_rate) * 100}
                  </td>
                  <td className="text-right" style={{ fontWeight: 600, color: "#1e3a8a" }}>
                    {formatCurrency(tx.amount_incl_vat)}
                  </td>
                  <td>
                    <span className="badge badge-info">{tx.payment_method || "Nakit"}</span>
                  </td>
                  <td className="text-center">
                    <span className={`badge ${tx.invoice_status === "Faturalandı" ? "badge-success" : "badge-warning"}`}>
                      {tx.invoice_status}
                    </span>
                  </td>
                  {user?.role !== "VIEWER" && (
                    <td className="text-center" style={{ whiteSpace: "nowrap" }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: "3px 6px", marginRight: "4px" }}
                        onClick={() => openEditModal(tx)}
                        title="Düzenle"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        style={{ padding: "3px 6px" }}
                        onClick={() => handleDelete(tx.id!)}
                        title="Sil"
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingTx ? "İşlem Kaydını Düzenle" : "Yeni İşlem Kaydı Ekle"}</h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ border: "none", padding: "4px" }}
                onClick={() => setIsModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && (
                  <div className="info-box warning" style={{ marginBottom: "16px" }}>
                    <AlertCircle size={16} />
                    {formError}
                  </div>
                )}

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Tarih *</label>
                    <input
                      type="date"
                      className="form-input"
                      value={formData.date || ""}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Departman *</label>
                    <select
                      className="form-select"
                      value={formData.department_id || ""}
                      onChange={(e) => setFormData({ ...formData, department_id: Number(e.target.value) })}
                      required
                    >
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Müşteri Adı *</label>
                    <input
                      type="text"
                      placeholder="Örn: Ahmet Yılmaz"
                      className="form-input"
                      value={formData.customer_name || ""}
                      onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Müşteri TC Kimlik / Vergi No</label>
                    <input
                      type="text"
                      placeholder="11 haneli TCKN veya 10 haneli VKN"
                      className="form-input"
                      value={formData.customer_tax_id || ""}
                      onChange={(e) => setFormData({ ...formData, customer_tax_id: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Kategori / Hizmet Adı *</label>
                    <select
                      className="form-select"
                      value={formData.category_id || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val) {
                          const cat = categories.find((c) => c.id === parseInt(val));
                          setFormData({
                            ...formData,
                            category_id: parseInt(val),
                            item_name: cat ? cat.name : (formData.item_name || "")
                          });
                        } else {
                          setFormData({ ...formData, category_id: null });
                        }
                      }}
                    >
                      <option value="">Özel / Serbest Metin</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} {c.general_override_rate ? `(Genel İstisna: %${Number(c.general_override_rate) * 100})` : ""}
                        </option>
                      ))}
                    </select>
                    {!formData.category_id && (
                      <input
                        type="text"
                        placeholder="Örn: Komple TPU PPF Kaplama"
                        className="form-input"
                        style={{ marginTop: "6px" }}
                        value={formData.item_name || ""}
                        onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                        required
                      />
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label">İşlemi Yapan Personel</label>
                    <select
                      className="form-select"
                      value={formData.employee_id || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val) {
                          const emp = employees.find((em) => em.id === parseInt(val));
                          setFormData({
                            ...formData,
                            employee_id: parseInt(val),
                            staff_name: emp ? emp.full_name : (formData.staff_name || "")
                          });
                        } else {
                          setFormData({ ...formData, employee_id: null });
                        }
                      }}
                    >
                      <option value="">Özel / Serbest Metin</option>
                      {employees.map((em) => (
                        <option key={em.id} value={em.id}>
                          {em.full_name} ({em.role_name || "Rol Yok"})
                        </option>
                      ))}
                    </select>
                    {!formData.employee_id && (
                      <input
                        type="text"
                        placeholder="Örn: Emre Teknisyen"
                        className="form-input"
                        style={{ marginTop: "6px" }}
                        value={formData.staff_name || ""}
                        onChange={(e) => setFormData({ ...formData, staff_name: e.target.value })}
                      />
                    )}
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">KDV Hariç Tutar (TL) *</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      className="form-input"
                      value={formData.amount_excl_vat || ""}
                      onChange={(e) => handleExclAmountChange(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">KDV Oranı</label>
                    <select
                      className="form-select"
                      value={formData.vat_rate || "0.20"}
                      onChange={(e) => handleVatRateChange(e.target.value)}
                    >
                      <option value="0.20">%20 (Genel)</option>
                      <option value="0.10">%10</option>
                      <option value="0.01">%1</option>
                      <option value="0.00">%0 (KDV Muaf)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">KDV Dahil Tutar (TL)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Otomatik hesaplanır"
                      className="form-input"
                      value={formData.amount_incl_vat || ""}
                      onChange={(e) => setFormData({ ...formData, amount_incl_vat: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Tahsilat Şekli</label>
                    <select
                      className="form-select"
                      value={formData.payment_method || "Kredi Kartı"}
                      onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                    >
                      <option value="Kredi Kartı">Kredi Kartı</option>
                      <option value="Havale / EFT">Havale / EFT</option>
                      <option value="Nakit">Nakit</option>
                      <option value="Cari Hesap">Cari Hesap</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Fatura Durumu</label>
                    <select
                      className="form-select"
                      value={formData.invoice_status || "Faturalandı"}
                      onChange={(e) => setFormData({ ...formData, invoice_status: e.target.value })}
                    >
                      <option value="Faturalandı">Faturalandı</option>
                      <option value="Bekliyor">Bekliyor</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Açıklama (Opsiyonel)</label>
                  <textarea
                    rows={2}
                    className="form-input"
                    placeholder="Ek notlar..."
                    value={formData.description || ""}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Vazgeç
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  <Check size={16} />
                  {saving ? "Kaydediliyor..." : editingTx ? "Güncelle" : "Kaydet"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
