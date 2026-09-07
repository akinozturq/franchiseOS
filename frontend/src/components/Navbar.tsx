import React, { useState, useEffect } from "react";
import {
  LogOut,
  BarChart3,
  FileSpreadsheet,
  Sliders,
  Building2,
  Award,
  Users,
  Tag,
  LayoutDashboard,
  UserCheck
} from "lucide-react";
import type { User, Branch } from "../types";
import { apiClient } from "../api/client";
import { NotificationCenter } from "./NotificationCenter";

interface NavbarProps {
  user: User;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  activeBranchId: number | null;
  onBranchChange: (branchId: number | null) => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  activeTab,
  setActiveTab,
  activeBranchId,
  onBranchChange,
  onLogout
}) => {
  const [branches, setBranches] = useState<Branch[]>([]);

  useEffect(() => {
    if (user.role === "FRANCHISOR_ADMIN") {
      apiClient
        .get<Branch[]>("/branches")
        .then((res) => setBranches(res.data))
        .catch(() => {});
    }
  }, [user.role]);

  const getRoleLabel = () => {
    switch (user.role) {
      case "FRANCHISOR_ADMIN":
        return "Franchisor Merkez";
      case "BAYI_ADMIN":
        return "Bayi Yöneticisi";
      case "VIEWER":
        return "Salt Okunur (İzleyici)";
      default:
        return user.role;
    }
  };

  const getBranchLabel = () => {
    if (user.role === "FRANCHISOR_ADMIN") {
      if (!activeBranchId) return "Tüm Bayiler";
      const b = branches.find((item) => item.id === activeBranchId);
      return b ? b.name : `Bayi #${activeBranchId}`;
    }
    return user.branch_id ? `Bayi #${user.branch_id}` : "Bağlı Bayi";
  };

  return (
    <header className="navbar">
      {/* Top Bar: Brand, Branch Selector, Notifications, User Profile & Logout */}
      <div className="nav-top-bar">
        <div className="nav-top-container">
          {/* Brand */}
          <div className="nav-brand">
            <div className="nav-logo">FOS</div>
            <div>
              <div className="nav-title">FranchiseOS</div>
              <div className="nav-subtitle">Çoklu Bayi & Mutabakat Sistemi (Faz 4)</div>
            </div>
          </div>

          {/* Right Action Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {/* Branch Selector for Franchisor Admin */}
            {user.role === "FRANCHISOR_ADMIN" && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  padding: "4px 10px",
                  borderRadius: "8px"
                }}
              >
                <Building2 size={15} color="#1e3a8a" />
                <span style={{ fontSize: "12px", fontWeight: 600, color: "#1e3a8a" }}>Aktif Bayi:</span>
                <select
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "#1e3a8a",
                    background: "#ffffff",
                    border: "1px solid #cbd5e1",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    cursor: "pointer",
                    outline: "none"
                  }}
                  value={activeBranchId ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    onBranchChange(val === "" ? null : Number(val));
                  }}
                >
                  <option value="">Tüm Bayiler (Karşılaştırmalı)</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} (#{b.id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Fixed Branch Badge for Bayi Admin / Viewer */}
            {user.role !== "FRANCHISOR_ADMIN" && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#f1f5f9",
                  border: "1px solid #e2e8f0",
                  padding: "5px 10px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#334155"
                }}
              >
                <Building2 size={14} color="#64748b" />
                <span>{getBranchLabel()}</span>
              </div>
            )}

            <div style={{ width: 1, height: 24, background: "#e2e8f0" }} />

            {/* Notification Center */}
            <NotificationCenter user={user} />

            <div style={{ width: 1, height: 24, background: "#e2e8f0" }} />

            {/* User Profile & Logout */}
            <div className="nav-user">
              <div style={{ textAlign: "right", fontSize: "13px" }}>
                <div style={{ fontWeight: 600, color: "#0f172a" }}>{user.full_name || user.username}</div>
                <div style={{ display: "flex", alignItems: "center", gap: "4px", justifyContent: "flex-end" }}>
                  <span
                    className="badge"
                    style={{
                      fontSize: "10px",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontWeight: 600,
                      background:
                        user.role === "FRANCHISOR_ADMIN"
                          ? "#1e3a8a"
                          : user.role === "BAYI_ADMIN"
                          ? "#0f766e"
                          : "#64748b",
                      color: "#ffffff"
                    }}
                  >
                    {getRoleLabel()}
                  </span>
                </div>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={onLogout}
                title="Güvenli Çıkış Yap"
              >
                <LogOut size={14} />
                Çıkış
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar: Horizontal Nav Tabs */}
      <div className="nav-tabs-bar">
        <div className="nav-tabs-container">
          <nav className="nav-tabs">
            <button
              className={`nav-tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
            >
              <LayoutDashboard size={15} />
              Dashboard
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "reconciliation" ? "active" : ""}`}
              onClick={() => setActiveTab("reconciliation")}
            >
              <BarChart3 size={15} />
              Dönem Mutabakatı
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "bonus" ? "active" : ""}`}
              onClick={() => setActiveTab("bonus")}
            >
              <Award size={15} />
              Personel Primleri
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "transactions" ? "active" : ""}`}
              onClick={() => setActiveTab("transactions")}
            >
              <FileSpreadsheet size={15} />
              İşlemler
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "staff" ? "active" : ""}`}
              onClick={() => setActiveTab("staff")}
            >
              <Users size={15} />
              Personel & Roller
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "categories" ? "active" : ""}`}
              onClick={() => setActiveTab("categories")}
            >
              <Tag size={15} />
              Kategoriler
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "tiers" ? "active" : ""}`}
              onClick={() => setActiveTab("tiers")}
            >
              <Sliders size={15} />
              Bayi Dilimleri
            </button>
            <button
              className={`nav-tab-btn ${activeTab === "departments" ? "active" : ""}`}
              onClick={() => setActiveTab("departments")}
            >
              <Building2 size={15} />
              Departmanlar
            </button>

            {/* Franchisor Admin Exclusive Tabs */}
            {user.role === "FRANCHISOR_ADMIN" && (
              <>
                <button
                  className={`nav-tab-btn ${activeTab === "branches" ? "active" : ""}`}
                  onClick={() => setActiveTab("branches")}
                >
                  <Building2 size={15} />
                  Bayiler
                </button>
                <button
                  className={`nav-tab-btn ${activeTab === "users" ? "active" : ""}`}
                  onClick={() => setActiveTab("users")}
                >
                  <UserCheck size={15} />
                  Kullanıcılar
                </button>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
};
