import React, { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, Building2, Check, X, AlertCircle } from "lucide-react";
import { apiClient } from "../api/client";
import type { Department, User } from "../types";

interface DepartmentsViewProps {
  user?: User | null;
}

export const DepartmentsView: React.FC<DepartmentsViewProps> = ({ user }) => {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [name, setName] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchDepartments = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<Department[]>("/departments");
      setDepartments(res.data);
    } catch (err) {
      console.error("Departmanlar alınamadı", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDepartments();
  }, []);

  const openCreateModal = () => {
    setEditingDept(null);
    setName("");
    setFormError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (dept: Department) => {
    setEditingDept(dept);
    setName(dept.name);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Bu departmanı silmek istediğinize emin misiniz?")) return;
    try {
      const res = await apiClient.delete(`/departments/${id}`);
      if (res.data?.detail) {
        alert(res.data.detail);
      }
      fetchDepartments();
    } catch (err) {
      alert("Departman silinemedi.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    setFormError(null);

    try {
      if (editingDept?.id) {
        await apiClient.put(`/departments/${editingDept.id}`, { name: name.trim() });
      } else {
        await apiClient.post("/departments", { name: name.trim() });
      }
      setIsModalOpen(false);
      fetchDepartments();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Departman kaydedilirken hata oluştu.");
    } finally {
      setSaving(false);
    }
  };

  const isViewer = user?.role === "VIEWER";

  return (
    <div>
      {isViewer && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            background: "#f8fafc",
            border: "1px solid #cbd5e1",
            borderRadius: "8px",
            color: "#475569",
            fontSize: "13px",
            marginBottom: "16px"
          }}
        >
          <AlertCircle size={18} color="#64748b" />
          <span>
            <strong>Salt Okunur (İzleyici) Modu:</strong> Departman tanımları merkezi referans tablosudur. Yeni departman ekleme, düzenleme veya silme yetkiniz bulunmamaktadır.
          </span>
        </div>
      )}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800 }}>Departman Tanımları</h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              İşletmenizde ciro kırılımı yapılan departman ve hizmet alanları (Satış, Servis, PPF vb.).
            </p>
          </div>

          {!isViewer && (
            <button className="btn btn-primary" onClick={openCreateModal}>
              <Plus size={15} />
              Yeni Departman Ekle
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Building2 size={18} />
            Kayıtlı Departmanlar
          </div>
          <span className="badge badge-info">Toplam {departments.length} Departman</span>
        </div>

        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: "80px" }}>ID</th>
                <th>Departman Adı</th>
                <th className="text-center">Durum</th>
                <th className="text-center" style={{ width: "120px" }}>İşlem</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    Departmanlar yükleniyor...
                  </td>
                </tr>
              ) : departments.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    Kayıtlı departman bulunamadı.
                  </td>
                </tr>
              ) : (
                departments.map((dept) => (
                  <tr key={dept.id}>
                    <td style={{ fontWeight: 600, color: "#64748b" }}>#{dept.id}</td>
                    <td style={{ fontWeight: 600 }}>{dept.name}</td>
                    <td className="text-center">
                      <span className="badge badge-success">Aktif</span>
                    </td>
                    <td className="text-center">
                      {isViewer ? (
                        <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Salt Okunur</span>
                      ) : (
                        <>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "4px 8px", marginRight: "6px" }}
                            onClick={() => openEditModal(dept)}
                            title="Düzenle"
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ padding: "4px 8px" }}
                            onClick={() => handleDelete(dept.id)}
                            title="Sil"
                          >
                            <Trash2 size={13} />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: "420px" }}>
            <div className="modal-header">
              <h3>{editingDept ? "Departmanı Düzenle" : "Yeni Departman Ekle"}</h3>
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

                <div className="form-group">
                  <label className="form-label">Departman Adı *</label>
                  <input
                    type="text"
                    placeholder="Örn: Satış, Servis, PPF Kaplama"
                    className="form-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    autoFocus
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
                  {saving ? "Kaydediliyor..." : "Kaydet"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
