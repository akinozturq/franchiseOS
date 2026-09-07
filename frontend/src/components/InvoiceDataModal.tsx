import React, { useState } from "react";
import { FileText, X, Download, Copy, Check } from "lucide-react";
import type { InvoiceDataExport } from "../types";
import { formatCurrency } from "../utils/formatters";

interface InvoiceDataModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: InvoiceDataExport | null;
}

export const InvoiceDataModal: React.FC<InvoiceDataModalProps> = ({
  isOpen,
  onClose,
  data
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !data) return null;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${data.document_id}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 1100 }}>
      <div className="modal-content" style={{ maxWidth: "780px", width: "95%", maxHeight: "90vh", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={18} color="#2563eb" />
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#0f172a" }}>
                E-Fatura Veri Paketi (Standart JSON)
              </h3>
              <span style={{ fontSize: "11px", color: "#64748b" }}>
                Belge No: <b>{data.document_id}</b> | Dönem: <b>{data.period}</b>
              </span>
            </div>
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
        <div style={{ overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "16px", paddingRight: "4px" }}>
          {/* Parties Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {/* Issuer */}
            <div style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px", background: "#f8fafc" }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#2563eb", textTransform: "uppercase", marginBottom: "4px" }}>
                Fatura Düzenleyen (Satıcı / Alacaklı)
              </div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>
                {data.issuer.title}
              </div>
              <div style={{ fontSize: "12px", color: "#475569", marginTop: "4px" }}>
                VKN/TC: <b>{data.issuer.tax_id}</b> | {data.issuer.tax_office}
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                {data.issuer.address}
              </div>
            </div>

            {/* Recipient */}
            <div style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px", background: "#f8fafc" }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#16a34a", textTransform: "uppercase", marginBottom: "4px" }}>
                Fatura Muhatabı (Alıcı / Borçlu)
              </div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>
                {data.recipient.title}
              </div>
              <div style={{ fontSize: "12px", color: "#475569", marginTop: "4px" }}>
                VKN/TC: <b>{data.recipient.tax_id}</b> | {data.recipient.tax_office}
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                {data.recipient.address}
              </div>
            </div>
          </div>

          {/* Line items table */}
          <div>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a", marginBottom: "6px" }}>
              Hizmet Kalemleri
            </div>
            <table className="data-table" style={{ fontSize: "12px" }}>
              <thead>
                <tr>
                  <th>Açıklama</th>
                  <th style={{ textAlign: "right" }}>Miktar</th>
                  <th style={{ textAlign: "right" }}>KDV %</th>
                  <th style={{ textAlign: "right" }}>Matrah</th>
                  <th style={{ textAlign: "right" }}>KDV Tutarı</th>
                  <th style={{ textAlign: "right" }}>Toplam</th>
                </tr>
              </thead>
              <tbody>
                {data.line_items.map((item, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{item.item_name}</td>
                    <td style={{ textAlign: "right" }}>{item.quantity} {item.unit}</td>
                    <td style={{ textAlign: "right" }}>%{Number(item.vat_rate) * 100}</td>
                    <td style={{ textAlign: "right" }} className="tabular-nums">{formatCurrency(item.amount_excl_vat)}</td>
                    <td style={{ textAlign: "right" }} className="tabular-nums">{formatCurrency(item.vat_amount)}</td>
                    <td style={{ textAlign: "right", fontWeight: 700 }} className="tabular-nums">{formatCurrency(item.amount_incl_vat)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals Summary */}
          <div style={{ alignSelf: "flex-end", width: "280px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#475569", marginBottom: "4px" }}>
              <span>Toplam Matrah:</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatCurrency(data.amount_excl_vat)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#475569", marginBottom: "6px" }}>
              <span>Hesaplanan KDV (%{Number(data.vat_rate) * 100}):</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatCurrency(data.vat_amount)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", fontWeight: 800, color: "#0f172a", borderTop: "1px solid #cbd5e1", paddingTop: "6px" }}>
              <span>Ödenecek Tutar:</span>
              <span className="tabular-nums" style={{ color: "#2563eb" }}>{formatCurrency(data.total_amount_incl_vat)}</span>
            </div>
          </div>

          {/* Audit footer */}
          <div style={{ fontSize: "11px", color: "#94a3b8", background: "#f1f5f9", padding: "8px 12px", borderRadius: "6px" }}>
            Kapatma Kaydı #{data.closure_audit.closure_id} • Onay: {data.closure_audit.closed_by} ({data.closure_audit.closed_at.slice(0, 19).replace("T", " ")}) • Durum: {data.closure_audit.status}
          </div>
        </div>

        {/* Footer actions */}
        <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleCopyJson}
            >
              {copied ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
              {copied ? "JSON Kopyalandı!" : "JSON Kopyala"}
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleDownloadJson}
            >
              <Download size={14} />
              JSON İndir (.json)
            </button>
          </div>

          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
};
