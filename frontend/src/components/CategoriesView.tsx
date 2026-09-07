import React, { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, Tag, AlertCircle, X, HelpCircle, History } from "lucide-react";
import api from "../api/client";
import type { TransactionCategory, User } from "../types";
import { RuleHistoryModal } from "./RuleHistoryModal";

interface CategoriesViewProps {
  user?: User | null;
}

export const CategoriesView: React.FC<CategoriesViewProps> = ({ user }) => {
  const [categories, setCategories] = useState<TransactionCategory[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [editingCategory, setEditingCategory] = useState<TransactionCategory | null>(null);
  const [name, setName] = useState<string>("");
  const [generalOverrideRate, setGeneralOverrideRate] = useState<string>("");
  const [bonusOverrideRate, setBonusOverrideRate] = useState<string>("");
  const [isActive, setIsActive] = useState<boolean>(true);

  const fetchCategories = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<TransactionCategory[]>("/categories");
      setCategories(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Kategoriler yüklenirken hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const openAddModal = () => {
    setEditingCategory(null);
    setName("");
    setGeneralOverrideRate("");
    setBonusOverrideRate("");
    setIsActive(true);
    setIsModalOpen(true);
  };

  const openEditModal = (cat: TransactionCategory) => {
    setEditingCategory(cat);
    setName(cat.name);
    setGeneralOverrideRate(
      cat.general_override_rate !== null && cat.general_override_rate !== undefined
        ? (parseFloat(String(cat.general_override_rate)) * 100).toString()
        : ""
    );
    setBonusOverrideRate(
      cat.bonus_override_rate !== null && cat.bonus_override_rate !== undefined
        ? (parseFloat(String(cat.bonus_override_rate)) * 100).toString()
        : ""
    );
    setIsActive(cat.is_active);
    setIsModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const genRate = generalOverrideRate.trim() !== "" ? parseFloat(generalOverrideRate) / 100 : null;
    const bonRate = bonusOverrideRate.trim() !== "" ? parseFloat(bonusOverrideRate) / 100 : null;

    if (genRate !== null && (isNaN(genRate) || genRate < 0 || genRate > 1)) {
      alert("Lütfen genel istisna oranını 0-100 arasında girin.");
      return;
    }
    if (bonRate !== null && (isNaN(bonRate) || bonRate < 0 || bonRate > 1)) {
      alert("Lütfen prim istisna oranını 0-100 arasında girin.");
      return;
    }

    try {
      if (editingCategory) {
        await api.put(`/categories/${editingCategory.id}`, {
          name: name.trim(),
          general_override_rate: genRate,
          bonus_override_rate: bonRate,
          is_active: isActive
        });
      } else {
        await api.post("/categories", {
          name: name.trim(),
          general_override_rate: genRate,
          bonus_override_rate: bonRate,
          is_active: isActive
        });
      }
      setIsModalOpen(false);
      fetchCategories();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Kategori kaydedilemedi.");
    }
  };

  const handleDelete = async (catId: number) => {
    if (!window.confirm("Bu kategoriyi silmek istediğinize emin misiniz? (İşlem kaydı varsa pasife almanız önerilir)")) return;
    try {
      await api.delete(`/categories/${catId}`);
      fetchCategories();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Kategori silinemedi.");
    }
  };

  return (
    <div className="view-container">
      {/* Header */}
      <div className="card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h1 className="page-title" style={{ margin: 0 }}>İşlem Kategorileri ve İstisnalar</h1>
            <p className="page-description" style={{ margin: "4px 0 0 0" }}>
              Tanımlı işlem kategorileri, franchisor-bayi komisyon istisnaları ve personel prim istisnaları
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <button
              className="btn btn-secondary"
              onClick={() => setIsHistoryOpen(true)}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <History size={14} />
              İstisna Geçmişi
            </button>
            {user?.role === "FRANCHISOR_ADMIN" && (
              <button className="btn btn-primary" onClick={openAddModal}>
                <Plus size={14} />
                Yeni Kategori Ekle
              </button>
            )}
          </div>
        </div>
      </div>

      {user?.role !== "FRANCHISOR_ADMIN" && (
        <div style={{ padding: "12px 16px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "10px", margin: "16px 0" }}>
          <HelpCircle size={18} color="#1e3a8a" />
          <span>İşlem kategorileri ve istisna kuralları <strong>Merkez Franchisor</strong> tarafından belirlenmektedir. Bayi ve izleyici kullanıcıları bu ekranda yalnızca geçerli oranları görüntüleyebilir.</span>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Info Alert explaining the two independent overrides */}
      <div className="card" style={{ background: "#f8fafc", borderLeft: "4px solid var(--primary)", marginBottom: "20px", padding: "14px 18px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
          <HelpCircle size={18} color="var(--primary)" style={{ marginTop: "2px", flexShrink: 0 }} />
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
            <strong>Kategori İstisna Kuralları Nasıl Çalışır?</strong>
            <div style={{ marginTop: "4px" }}>
              • <strong>Genel Komisyon İstisnası:</strong> Belirtilirse, bu kategorideki işlemler ciro dilimine bakılmaksızın bayi payı olarak sabit bu oranı (örn: %15) kullanır. Kalan standart işlemler genel dilimden hesaplanır.
            </div>
            <div style={{ marginTop: "2px" }}>
              • <strong>Personel Prim İstisnası:</strong> Belirtilirse, bu kategorideki işlemler personelin rol kademesine bakılmaksızın personele sabit bu oranda prim (örn: %7) kazandırır.
            </div>
          </div>
        </div>
      </div>

      {/* Categories Table */}
      <div className="card" style={{ overflow: "hidden", padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Kategori / İşlem Adı</th>
                <th>Genel Mutabakat Kuralı</th>
                <th>Personel Prim Kuralı</th>
                <th>Durum</th>
                {user?.role === "FRANCHISOR_ADMIN" && (
                  <th style={{ textAlign: "right" }}>İşlemler</th>
                )}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    Kategoriler yükleniyor...
                  </td>
                </tr>
              ) : categories.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    Kayıtlı kategori bulunamadı.
                  </td>
                </tr>
              ) : (
                categories.map((cat) => {
                  const hasGenOverride = cat.general_override_rate !== null && cat.general_override_rate !== undefined;
                  const hasBonOverride = cat.bonus_override_rate !== null && cat.bonus_override_rate !== undefined;

                  return (
                    <tr key={cat.id}>
                      <td style={{ fontWeight: 600 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <Tag size={14} color="var(--primary)" />
                          {cat.name}
                        </div>
                      </td>
                      <td>
                        {hasGenOverride ? (
                          <span className="status-badge" style={{ background: "#fef3c7", color: "#92400e", fontWeight: 600 }}>
                            Sabit İstisna: %{parseFloat(String(cat.general_override_rate)) * 100}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                            Standart Kademeli Kural
                          </span>
                        )}
                      </td>
                      <td>
                        {hasBonOverride ? (
                          <span className="status-badge" style={{ background: "#e0f2fe", color: "#0369a1", fontWeight: 600 }}>
                            Sabit Prim: %{parseFloat(String(cat.bonus_override_rate)) * 100}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                            Role Göre Kademeli Prim
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`status-badge ${cat.is_active ? "status-success" : "status-warning"}`}>
                          {cat.is_active ? "Aktif" : "Pasif"}
                        </span>
                      </td>
                      {user?.role === "FRANCHISOR_ADMIN" && (
                        <td style={{ textAlign: "right" }}>
                          <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => openEditModal(cat)}
                              title="Düzenle"
                            >
                              <Edit2 size={13} />
                            </button>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleDelete(cat.id)}
                              title="Sil"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ADD / EDIT MODAL */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h2 className="modal-title">{editingCategory ? "Kategoriyi Düzenle" : "Yeni Kategori Ekle"}</h2>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label className="form-label">Kategori / Hizmet Adı</label>
                  <input
                    type="text"
                    required
                    className="input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Örn: Komple TPU PPF Kaplama"
                  />
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                  <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Genel Mutabakat İstisna Oranı (%)</span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 400 }}>İsteğe bağlı</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    className="input"
                    value={generalOverrideRate}
                    onChange={(e) => setGeneralOverrideRate(e.target.value)}
                    placeholder="Boş bırakılırsa standart dilim kullanılır (örn: 15)"
                  />
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    Bu kategoriye ait ciro için uygulanacak sabit bayi payı oranı (örn: 15 girilirse %15).
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                  <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Personel Prim İstisna Oranı (%)</span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 400 }}>İsteğe bağlı</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    className="input"
                    value={bonusOverrideRate}
                    onChange={(e) => setBonusOverrideRate(e.target.value)}
                    placeholder="Boş bırakılırsa role göre kademeli prim kullanılır (örn: 7)"
                  />
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    Bu kategoriye ait ciro için personele ödenecek sabit prim oranı (örn: 7 girilirse %7).
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <input
                    type="checkbox"
                    id="catActive"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  <label htmlFor="catActive" style={{ fontSize: "13px", cursor: "pointer" }}>
                    Kategori aktif
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  İptal
                </button>
                <button type="submit" className="btn btn-primary">
                  Kaydet
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RULE HISTORY MODAL */}
      <RuleHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        title="Kategori İstisna Oranları Değişiklik Geçmişi"
        fetchUrl="/categories/history"
      />
    </div>
  );
};
