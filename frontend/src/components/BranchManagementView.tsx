import React, { useState, useEffect } from "react";
import { Plus, Edit2, Building2, Phone, Mail, MapPin } from "lucide-react";
import { apiClient } from "../api/client";
import type { Branch } from "../types";

export const BranchManagementView: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    tax_id: "",
    tax_office: "",
    address: "",
    phone: "",
    email: "",
    is_active: true
  });

  useEffect(() => {
    fetchBranches();
  }, []);

  const fetchBranches = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<Branch[]>("/branches");
      setBranches(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Bayiler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingBranch(null);
    setFormData({
      name: "",
      tax_id: "",
      tax_office: "",
      address: "",
      phone: "",
      email: "",
      is_active: true
    });
    setIsModalOpen(true);
  };

  const openEditModal = (b: Branch) => {
    setEditingBranch(b);
    setFormData({
      name: b.name,
      tax_id: b.tax_id || "",
      tax_office: b.tax_office || "",
      address: b.address || "",
      phone: b.phone || "",
      email: b.email || "",
      is_active: b.is_active
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingBranch) {
        await apiClient.put(`/branches/${editingBranch.id}`, formData);
      } else {
        await apiClient.post("/branches", formData);
      }
      setIsModalOpen(false);
      fetchBranches();
    } catch (err: any) {
      alert(err.response?.data?.detail || "İşlem başarısız oldu.");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* View Header */}
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
          <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0, color: "var(--text-main)" }}>
            Bayi Yönetimi (Franchise Ağı)
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
            Merkez Franchisor bünyesindeki tüm şube ve bayilerin kayıtları, vergi bilgileri ve durumları.
          </p>
        </div>

        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          Yeni Bayi Ekle
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#b91c1c", borderRadius: "6px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Bayiler yükleniyor...
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
          {branches.map((b) => (
            <div
              key={b.id}
              className="card"
              style={{
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                borderTop: b.is_active ? "4px solid #1e3a8a" : "4px solid #94a3b8"
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                      BAYİ #{b.id}
                    </span>
                    <h3 style={{ fontSize: "16px", fontWeight: 700, margin: "2px 0 0 0", color: "var(--text-main)" }}>
                      {b.name}
                    </h3>
                  </div>
                  <span className={`badge ${b.is_active ? "badge-success" : "badge-danger"}`}>
                    {b.is_active ? "Aktif" : "Pasif"}
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px", color: "var(--text-main)", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                    <Building2 size={14} />
                    <span>VKN: <strong style={{ color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>{b.tax_id || "Belirtilmedi"}</strong> {b.tax_office ? `(${b.tax_office})` : ""}</span>
                  </div>
                  {b.phone && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                      <Phone size={14} />
                      <span style={{ color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>{b.phone}</span>
                    </div>
                  )}
                  {b.email && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                      <Mail size={14} />
                      <span style={{ color: "var(--text-main)" }}>{b.email}</span>
                    </div>
                  )}
                  {b.address && (
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "8px", color: "var(--text-muted)" }}>
                      <MapPin size={14} style={{ marginTop: "2px", flexShrink: 0 }} />
                      <span style={{ color: "var(--text-main)", fontSize: "12px" }}>{b.address}</span>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px", display: "flex", justifyContent: "flex-end" }}>
                <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(b)}>
                  <Edit2 size={13} />
                  Düzenle
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>
                {editingBranch ? "Bayi Bilgilerini Güncelle" : "Yeni Bayi Tanımla"}
              </h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsModalOpen(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div className="form-group">
                  <label className="form-label">Bayi / Şube Ünvanı *</label>
                  <input
                    type="text"
                    className="form-input"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Örn. Kadıköy Detailing & Servis"
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div className="form-group">
                    <label className="form-label">Vergi Kimlik No (VKN / TCKN)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.tax_id}
                      onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                      placeholder="10 veya 11 hane"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Vergi Dairesi</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.tax_office}
                      onChange={(e) => setFormData({ ...formData, tax_office: e.target.value })}
                      placeholder="Örn. Kadıköy VD"
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div className="form-group">
                    <label className="form-label">Telefon</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="0216 555 0000"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">E-posta</label>
                    <input
                      type="email"
                      className="form-input"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="bayi@otobakim.com"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Adres</label>
                  <textarea
                    className="form-input"
                    rows={2}
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="Adres bilgisi"
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "13px" }}>
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    />
                    <span>Bayi Aktif Durumda</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Vazgeç
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingBranch ? "Güncelle" : "Bayiyi Kaydet"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
