import React, { useState, useEffect } from "react";
import { Plus, Edit2, User, Building } from "lucide-react";
import { apiClient } from "../api/client";
import type { User as UserType, Branch } from "../types";

export const UserManagementView: React.FC = () => {
  const [users, setUsers] = useState<UserType[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<UserType | null>(null);

  const [formData, setFormData] = useState({
    username: "",
    password: "",
    full_name: "",
    role: "BAYI_ADMIN",
    branch_id: "" as number | string,
    is_active: true
  });

  useEffect(() => {
    fetchUsersAndBranches();
  }, []);

  const fetchUsersAndBranches = async () => {
    setLoading(true);
    try {
      const [usersRes, branchesRes] = await Promise.all([
        apiClient.get<UserType[]>("/users"),
        apiClient.get<Branch[]>("/branches")
      ]);
      setUsers(usersRes.data);
      setBranches(branchesRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Kullanıcılar veya bayiler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingUser(null);
    setFormData({
      username: "",
      password: "",
      full_name: "",
      role: "BAYI_ADMIN",
      branch_id: branches.length > 0 ? branches[0].id : "",
      is_active: true
    });
    setIsModalOpen(true);
  };

  const openEditModal = (u: UserType) => {
    setEditingUser(u);
    setFormData({
      username: u.username,
      password: "",
      full_name: u.full_name || "",
      role: u.role,
      branch_id: u.branch_id || "",
      is_active: u.is_active
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        full_name: formData.full_name.trim(),
        role: formData.role,
        branch_id: formData.role === "FRANCHISOR_ADMIN" ? null : (formData.branch_id ? Number(formData.branch_id) : null),
        is_active: formData.is_active
      };

      if (editingUser) {
        if (formData.password) {
          payload.password = formData.password;
        }
        await apiClient.put(`/users/${editingUser.id}`, payload);
      } else {
        payload.username = formData.username.trim();
        payload.password = formData.password;
        await apiClient.post("/users", payload);
      }

      setIsModalOpen(false);
      fetchUsersAndBranches();
    } catch (err: any) {
      alert(err.response?.data?.detail || "İşlem başarısız oldu.");
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "FRANCHISOR_ADMIN":
        return <span className="badge badge-primary">Franchisor Yöneticisi</span>;
      case "BAYI_ADMIN":
        return <span className="badge badge-info">Bayi Yöneticisi</span>;
      case "VIEWER":
        return <span className="badge" style={{ background: "#f1f5f9", color: "#475569" }}>İzleyici (Salt Okunur)</span>;
      default:
        return <span className="badge">{role}</span>;
    }
  };

  const branchMap = new Map<number, string>(branches.map((b) => [b.id, b.name]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
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
            Kullanıcı & Yetki Yönetimi (RBAC)
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
            Sistem kullanıcıları, rolleri ve bayi erişim yetkilendirme tablosu.
          </p>
        </div>

        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          Yeni Kullanıcı Oluştur
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#b91c1c", borderRadius: "6px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Kullanıcılar yükleniyor...
        </div>
      ) : (
        <div className="card" style={{ overflow: "hidden" }}>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: "50px" }}>#</th>
                  <th>Kullanıcı Adı</th>
                  <th>Ad Soyad</th>
                  <th>Sistem Rolü</th>
                  <th>Yetkili Olduğu Bayi</th>
                  <th style={{ textAlign: "center" }}>Durum</th>
                  <th style={{ textAlign: "right" }}>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>{u.id}</td>
                    <td style={{ fontWeight: 600 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <User size={15} color="var(--text-muted)" />
                        <span>{u.username}</span>
                      </div>
                    </td>
                    <td>{u.full_name || "-"}</td>
                    <td>{getRoleBadge(u.role)}</td>
                    <td>
                      {u.role === "FRANCHISOR_ADMIN" ? (
                        <span style={{ fontWeight: 600, color: "#1e3a8a" }}>Tüm Bayiler (Merkez)</span>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <Building size={13} color="var(--text-muted)" />
                          <span>{u.branch_id ? branchMap.get(u.branch_id) || `Bayi #${u.branch_id}` : "Atanmadı"}</span>
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>
                        {u.is_active ? "Aktif" : "Pasif"}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(u)}>
                        <Edit2 size={13} />
                        Düzenle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "480px" }}>
            <div className="modal-header">
              <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>
                {editingUser ? "Kullanıcıyı Düzenle" : "Yeni Kullanıcı Oluştur"}
              </h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsModalOpen(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {!editingUser && (
                  <div className="form-group">
                    <label className="form-label">Kullanıcı Adı *</label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      placeholder="Örn. kadikoy_admin"
                    />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Ad Soyad</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="Örn. Ahmet Yılmaz"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    {editingUser ? "Yeni Şifre (Değiştirmek istemiyorsanız boş bırakın)" : "Şifre *"}
                  </label>
                  <input
                    type="password"
                    className="form-input"
                    required={!editingUser}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder={editingUser ? "••••••••" : "En az 6 karakter"}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Sistem Rolü *</label>
                  <select
                    className="form-input"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  >
                    <option value="FRANCHISOR_ADMIN">Franchisor Admin (Tüm bayileri görür, kuralları yönetir)</option>
                    <option value="BAYI_ADMIN">Bayi Admin (Sadece kendi bayisini yönetir)</option>
                    <option value="VIEWER">İzleyici / Denetçi (Sadece görüntüleme yapar)</option>
                  </select>
                </div>

                {formData.role !== "FRANCHISOR_ADMIN" && (
                  <div className="form-group">
                    <label className="form-label">Bağlı Olduğu Bayi *</label>
                    <select
                      className="form-input"
                      required
                      value={formData.branch_id}
                      onChange={(e) => setFormData({ ...formData, branch_id: e.target.value })}
                    >
                      <option value="">Bayi Seçiniz</option>
                      {branches.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {editingUser && (
                  <div className="form-group">
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "13px" }}>
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      />
                      <span>Kullanıcı Hesabı Aktif</span>
                    </label>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Vazgeç
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingUser ? "Güncelle" : "Kullanıcıyı Kaydet"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
