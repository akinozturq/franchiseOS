import React, { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, Sliders, Info, Check, X, AlertCircle, History } from "lucide-react";
import { apiClient } from "../api/client";
import type { CommissionTier, User } from "../types";
import { formatCurrency, formatPercent } from "../utils/formatters";
import { RuleHistoryModal } from "./RuleHistoryModal";

interface CommissionTiersViewProps {
  user?: User | null;
}

export const CommissionTiersView: React.FC<CommissionTiersViewProps> = ({ user }) => {
  const [tiers, setTiers] = useState<CommissionTier[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [editingTier, setEditingTier] = useState<CommissionTier | null>(null);

  const [minAmount, setMinAmount] = useState<string>("");
  const [maxAmount, setMaxAmount] = useState<string>("");
  const [ratePercent, setRatePercent] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchTiers = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<CommissionTier[]>("/commission-tiers");
      setTiers(res.data);
    } catch (err) {
      console.error("Komisyon dilimleri alınamadı", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTiers();
  }, []);

  const openCreateModal = () => {
    setEditingTier(null);
    setFormError(null);
    
    // Suggest next min_amount based on existing highest tier's max_amount
    if (tiers.length > 0) {
      const lastTier = tiers[tiers.length - 1];
      if (lastTier.max_amount !== null && lastTier.max_amount !== undefined) {
        const nextMin = (parseFloat(String(lastTier.max_amount)) + 0.01).toFixed(2);
        setMinAmount(nextMin);
      } else {
        setMinAmount("");
      }
    } else {
      setMinAmount("0.00");
    }

    setMaxAmount("");
    setRatePercent("30");
    setIsModalOpen(true);
  };

  const openEditModal = (tier: CommissionTier) => {
    setEditingTier(tier);
    setFormError(null);
    setMinAmount(String(tier.min_amount));
    setMaxAmount(tier.max_amount !== null ? String(tier.max_amount) : "");
    const rateNum = typeof tier.rate === "string" ? parseFloat(tier.rate) : tier.rate;
    setRatePercent(String(rateNum <= 1 ? (rateNum * 100).toFixed(0) : rateNum));
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (tiers.length <= 1) {
      alert("Sistemde en az bir komisyon dilimi bulunmalıdır.");
      return;
    }
    if (!window.confirm("Bu dilimi silmek istediğinize emin misiniz?")) return;

    try {
      await apiClient.delete(`/commission-tiers/${id}`);
      fetchTiers();
    } catch (err) {
      alert("Dilim silinemedi.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);

    try {
      const minNum = parseFloat(minAmount);
      const maxNum = maxAmount.trim() ? parseFloat(maxAmount) : null;
      const rateNum = parseFloat(ratePercent) / 100;

      if (isNaN(minNum) || minNum < 0) {
        setFormError("Geçerli bir alt sınır giriniz.");
        setSaving(false);
        return;
      }

      if (maxNum !== null && maxNum <= minNum) {
        setFormError("Üst sınır, alt sınırdan büyük olmalıdır.");
        setSaving(false);
        return;
      }

      if (isNaN(rateNum) || rateNum < 0 || rateNum > 1) {
        setFormError("Oran %0 ile %100 arasında olmalıdır.");
        setSaving(false);
        return;
      }

      const payload = {
        min_amount: minNum,
        max_amount: maxNum,
        rate: rateNum
      };

      if (editingTier?.id) {
        await apiClient.put(`/commission-tiers/${editingTier.id}`, payload);
      } else {
        await apiClient.post("/commission-tiers", payload);
      }

      setIsModalOpen(false);
      fetchTiers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Kural kaydedilirken bir hata oluştu.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800 }}>Kademeli Komisyon Kural Motoru</h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Dönemlik ciroya göre Franchisor ve Bayi arasındaki gelir paylaşım dilimleri.
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsHistoryOpen(true)}
            >
              <History size={15} />
              Kural Geçmişi
            </button>

            {user?.role === "FRANCHISOR_ADMIN" && (
              <button className="btn btn-primary" onClick={openCreateModal}>
                <Plus size={15} />
                Yeni Dilim Ekle
              </button>
            )}
          </div>
        </div>
      </div>

      {user?.role !== "FRANCHISOR_ADMIN" && (
        <div style={{ padding: "12px 16px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "10px", margin: "16px 0" }}>
          <Info size={18} color="#1e3a8a" />
          <span>Komisyon dilimleri <strong>Merkez Franchisor</strong> tarafından belirlenmektedir. Bayi ve izleyici kullanıcıları bu ekranda yalnızca geçerli oranları görüntüleyebilir.</span>
        </div>
      )}

      {/* Critical Prompt Rules Banner */}
      <div className="info-box">
        <Info size={20} style={{ flexShrink: 0 }} />
        <div>
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>
            Hesaplama Mantığı ve Sınır Değer Kuralı (Faz 1):
          </div>
          <div>
            • <strong>Tüm Tutara Tek Oran:</strong> Dönem cirosunun tamamı hangi dilime düşerse, o dilimin oranı <em>tüm ciroya</em> uygulanır (marjinal/dilimli vergi gibi parçalanmaz).
          </div>
          <div style={{ marginTop: "4px" }}>
            • <strong>Sınır Değerleri:</strong> Dilimler <code>[Alt Sınır, Üst Sınır]</code> aralığında dahilidir. Örneğin 0 - 750.000 TL dilimi tam 750.000,00 TL'yi kapsar; 750.000,01 TL ve üzeri ise bir sonraki dilime geçer.
          </div>
        </div>
      </div>

      {/* Tiers Table */}
      <div className="card">
        <div className="card-title">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Sliders size={18} />
            Tanımlı Komisyon Dilimleri
          </div>
          <span className="badge badge-info">Toplam {tiers.length} Dilim</span>
        </div>

        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: "80px" }}>Dilim No</th>
                <th>Alt Sınır (TL)</th>
                <th>Üst Sınır (TL)</th>
                <th className="text-center">Bayi Payı Oranı</th>
                <th className="text-center">Franchisor (Merkez) Payı</th>
                {user?.role === "FRANCHISOR_ADMIN" && (
                  <th className="text-center" style={{ width: "120px" }}>İşlem</th>
                )}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    Dilimler yükleniyor...
                  </td>
                </tr>
              ) : tiers.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    Tanımlı dilim bulunamadı. Lütfen "Yeni Dilim Ekle" butonu ile dilim oluşturun.
                  </td>
                </tr>
              ) : (
                tiers.map((tier, idx) => {
                  const rateNum = typeof tier.rate === "string" ? parseFloat(tier.rate) : tier.rate;
                  const franchisorRate = 1 - rateNum;

                  return (
                    <tr key={tier.id}>
                      <td style={{ fontWeight: 700 }}>#{idx + 1}</td>
                      <td style={{ fontWeight: 600 }}>{formatCurrency(tier.min_amount)}</td>
                      <td style={{ fontWeight: 600 }}>
                        {tier.max_amount !== null && tier.max_amount !== undefined ? (
                          formatCurrency(tier.max_amount)
                        ) : (
                          <span className="badge badge-gray">Sonsuz (Üst Sınır Yok)</span>
                        )}
                      </td>
                      <td className="text-center">
                        <span className="badge badge-success" style={{ fontSize: "13px", fontWeight: 700 }}>
                          {formatPercent(rateNum)}
                        </span>
                      </td>
                      <td className="text-center">
                        <span className="badge badge-info" style={{ fontSize: "13px" }}>
                          {formatPercent(franchisorRate)}
                        </span>
                      </td>
                      {user?.role === "FRANCHISOR_ADMIN" && (
                        <td className="text-center">
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "4px 8px", marginRight: "6px" }}
                            onClick={() => openEditModal(tier)}
                            title="Düzenle"
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ padding: "4px 8px" }}
                            onClick={() => handleDelete(tier.id!)}
                            title="Sil"
                          >
                            <Trash2 size={13} />
                          </button>
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

      {/* Add / Edit Tier Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: "480px" }}>
            <div className="modal-header">
              <h3>{editingTier ? "Komisyon Dilimini Düzenle" : "Yeni Komisyon Dilimi Ekle"}</h3>
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
                  <label className="form-label">Alt Sınır (TL) *</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Örn: 0 veya 750000.01"
                    className="form-input"
                    value={minAmount}
                    onChange={(e) => setMinAmount(e.target.value)}
                    required
                  />
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    Bu tutar dilime dahildir (örn: 750.000,01 TL).
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Üst Sınır (TL)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Boş bırakılırsa sonsuz kabul edilir"
                    className="form-input"
                    value={maxAmount}
                    onChange={(e) => setMaxAmount(e.target.value)}
                  />
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    En üst basamak için boş bırakabilirsiniz.
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Bayi Payı Oranı (%) *</label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="Örn: 30 veya 35"
                      className="form-input"
                      value={ratePercent}
                      onChange={(e) => setRatePercent(e.target.value)}
                      required
                    />
                    <span
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        fontWeight: 700,
                        color: "#64748b"
                      }}
                    >
                      %
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    Kalan oran otomatik olarak Franchisor (Merkez) payı olur (örn: %30 Bayi → %70 Merkez).
                  </div>
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

      {/* Rule History Modal */}
      <RuleHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        title="Bayi Kademeli Komisyon Kural Geçmişi"
        fetchUrl="/commission-tiers/history"
      />
    </div>
  );
};
