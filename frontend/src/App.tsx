import React, { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { LoginPage } from "./components/LoginPage";
import { DashboardView } from "./components/DashboardView";
import { ReconciliationView } from "./components/ReconciliationView";
import { BonusReportView } from "./components/BonusReportView";
import { TransactionsView } from "./components/TransactionsView";
import { StaffView } from "./components/StaffView";
import { CategoriesView } from "./components/CategoriesView";
import { CommissionTiersView } from "./components/CommissionTiersView";
import { DepartmentsView } from "./components/DepartmentsView";
import { BranchManagementView } from "./components/BranchManagementView";
import { UserManagementView } from "./components/UserManagementView";
import { ImportModal } from "./components/ImportModal";
import type { User } from "./types";

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);
  const [activeBranchId, setActiveBranchId] = useState<number | null>(() => {
    const saved = localStorage.getItem("franchise_active_branch_id");
    return saved ? Number(saved) : null;
  });

  const handleBranchChange = (branchId: number | null) => {
    setActiveBranchId(branchId);
    if (branchId !== null) {
      localStorage.setItem("franchise_active_branch_id", branchId.toString());
    } else {
      localStorage.removeItem("franchise_active_branch_id");
    }
  };

  useEffect(() => {
    const savedUser = localStorage.getItem("franchise_user");
    const token = localStorage.getItem("franchise_token");
    if (savedUser && token) {
      try {
        const u: User = JSON.parse(savedUser);
        setUser(u);
        if (u.role !== "FRANCHISOR_ADMIN" && u.branch_id) {
          setActiveBranchId(u.branch_id);
          localStorage.setItem("franchise_active_branch_id", u.branch_id.toString());
        }
      } catch {
        localStorage.removeItem("franchise_user");
        localStorage.removeItem("franchise_token");
        localStorage.removeItem("franchise_active_branch_id");
      }
    }

    const handleAuthChanged = () => {
      setUser(null);
      setActiveBranchId(null);
    };

    window.addEventListener("auth-changed", handleAuthChanged);
    return () => window.removeEventListener("auth-changed", handleAuthChanged);
  }, []);

  const handleLoginSuccess = (userData: User) => {
    setUser(userData);
    if (userData.role === "FRANCHISOR_ADMIN") {
      setActiveBranchId(null);
      localStorage.removeItem("franchise_active_branch_id");
    } else if (userData.branch_id) {
      setActiveBranchId(userData.branch_id);
      localStorage.setItem("franchise_active_branch_id", userData.branch_id.toString());
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("franchise_token");
    localStorage.removeItem("franchise_user");
    localStorage.removeItem("franchise_active_branch_id");
    setUser(null);
    setActiveBranchId(null);
  };

  if (!user) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      <Navbar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeBranchId={activeBranchId}
        onBranchChange={handleBranchChange}
        onLogout={handleLogout}
      />

      <main className="main-content">
        {activeTab === "dashboard" && (
          <DashboardView
            user={user}
            activeBranchId={activeBranchId}
            onSelectBranch={handleBranchChange}
          />
        )}
        {activeTab === "reconciliation" && <ReconciliationView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "bonus" && <BonusReportView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "transactions" && (
          <TransactionsView
            key={activeBranchId ?? "all"}
            user={user}
            onOpenImport={() => setIsImportModalOpen(true)}
          />
        )}
        {activeTab === "staff" && <StaffView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "categories" && <CategoriesView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "tiers" && <CommissionTiersView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "departments" && <DepartmentsView key={activeBranchId ?? "all"} user={user} />}
        {activeTab === "branches" && user.role === "FRANCHISOR_ADMIN" && <BranchManagementView />}
        {activeTab === "users" && user.role === "FRANCHISOR_ADMIN" && <UserManagementView />}
      </main>

      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={() => {
          setIsImportModalOpen(false);
          setActiveTab("transactions");
        }}
      />

      <footer
        style={{
          textAlign: "center",
          padding: "20px",
          borderTop: "1px solid var(--border)",
          color: "var(--text-muted)",
          fontSize: "12px",
          background: "#ffffff"
        }}
      >
        <div>
          FranchiseOS v0.4.0 (Faz 4) — Kural Versiyonlama, Dönem Kapama & Donmuş Snapshot, PDF Export ve E-Fatura Desteği
        </div>
        <div style={{ marginTop: "4px" }}>
          Tüm bayi verileri, ciro kayıtları ve hesaplamalar kurgusal test ortamıdır.
        </div>
      </footer>
    </div>
  );
};

export default App;
