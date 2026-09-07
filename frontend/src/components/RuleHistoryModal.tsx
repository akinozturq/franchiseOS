import React, { useState, useEffect } from "react";
import { History, X, Clock, ArrowRight } from "lucide-react";
import { apiClient } from "../api/client";
import type { RuleChangeLog } from "../types";

interface RuleHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  fetchUrl: string;
}

export const RuleHistoryModal: React.FC<RuleHistoryModalProps> = ({
  isOpen,
  onClose,
  title,
  fetchUrl
}) => {
  const [logs, setLogs] = useState<RuleChangeLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      apiClient
        .get<RuleChangeLog[]>(fetchUrl)
        .then((res) => setLogs(res.data))
        .catch((err) => console.error("Kural geçmişi alınamadı", err))
        .finally(() => setLoading(false));
    }
  }, [isOpen, fetchUrl]);

  if (!isOpen) return null;

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString("tr-TR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return dateStr;
    }
  };

  const formatValue = (val: any) => {
    if (val === null || val === undefined) return "-";
    if (typeof val === "number" || (!isNaN(Number(val)) && typeof val === "string" && val.includes("."))) {
      const num = Number(val);
      if (num < 1 && num > 0) {
        return `%${(num * 100).toFixed(1)}`;
      }
      return `${num.toLocaleString("tr-TR")}`;
    }
    return String(val);
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case "CREATE":
        return <span className="badge badge-success" style={{ fontSize: "11px" }}>Oluşturuldu</span>;
      case "UPDATE":
        return <span className="badge" style={{ background: "#3b82f6", color: "#ffffff", fontSize: "11px" }}>Güncellendi (Yeni Versiyon)</span>;
      case "DELETE":
        return <span className="badge badge-danger" style={{ fontSize: "11px" }}>Arşivlendi</span>;
      default:
        return <span className="badge">{action}</span>;
    }
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 1100 }}>
      <div className="modal-content" style={{ maxWidth: "720px", width: "95%", maxHeight: "85vh", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <History size={18} color="#2563eb" />
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#0f172a" }}>
              {title}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: "transparent", border: "none", cursor: "pointer", color: "#64748b" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ overflowY: "auto", flex: 1, paddingRight: "4px" }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
              Geçmiş kayıtlar yükleniyor...
            </div>
          ) : logs.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8" }}>
              Bu kurala ait henüz geçmiş versiyon kaydı bulunmamaktadır.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {logs.map((log) => (
                <div
                  key={log.id}
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    padding: "14px",
                    background: "#f8fafc"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {getActionBadge(log.action)}
                      <span style={{ fontSize: "12px", color: "#64748b", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Clock size={12} />
                        Geçerlilik: <b>{log.effective_from}</b>
                      </span>
                    </div>
                    <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                      İşlem Tarihi: {formatDate(log.created_at)}
                    </span>
                  </div>

                  {log.description && (
                    <p style={{ margin: "0 0 10px 0", fontSize: "13px", color: "#1e293b", fontWeight: 500 }}>
                      {log.description}
                    </p>
                  )}

                  {/* Changes comparison */}
                  {log.old_values && log.new_values && (
                    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "8px 12px", fontSize: "12px" }}>
                      <div style={{ fontWeight: 600, color: "#475569", marginBottom: "4px" }}>Değişen Değerler:</div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        {Object.keys(log.new_values).map((k) => {
                          const oldV = log.old_values ? log.old_values[k] : null;
                          const newV = log.new_values[k];
                          if (oldV === newV) return null;
                          return (
                            <div key={k} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ color: "#64748b", textTransform: "capitalize", minWidth: "120px" }}>{k}:</span>
                              <span style={{ color: "#dc2626", textDecoration: "line-through" }}>{formatValue(oldV)}</span>
                              <ArrowRight size={12} color="#64748b" />
                              <span style={{ color: "#16a34a", fontWeight: 600 }}>{formatValue(newV)}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
};
