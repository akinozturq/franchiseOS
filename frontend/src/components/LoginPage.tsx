import React, { useState } from "react";
import { Lock, User, ArrowRight, AlertCircle } from "lucide-react";
import { apiClient } from "../api/client";

interface LoginPageProps {
  onLoginSuccess: (user: any, token: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await apiClient.post("/auth/login", {
        username,
        password
      });

      const { access_token, username: uName, full_name, role, branch_id, franchisor_id } = res.data;
      localStorage.setItem("franchise_token", access_token);
      const userObj = {
        id: 0,
        username: uName,
        full_name,
        role: role || "BAYI_ADMIN",
        branch_id: branch_id || null,
        franchisor_id: franchisor_id || null,
        is_active: true
      };
      localStorage.setItem("franchise_user", JSON.stringify(userObj));
      onLoginSuccess(userObj, access_token);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Giriş yapılamadı. Kullanıcı adı veya şifre hatalı."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%)",
        padding: "20px"
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          background: "#ffffff",
          borderRadius: "12px",
          padding: "36px 32px",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "48px",
              height: "48px",
              borderRadius: "10px",
              background: "#eff6ff",
              color: "#1d4ed8",
              marginBottom: "12px"
            }}
          >
            <Lock size={24} />
          </div>
          <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a" }}>
            FranchiseOS
          </h2>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
            Bayi Komisyon ve Dönem Mutabakat Portalı
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 14px",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: "6px",
              color: "#dc2626",
              fontSize: "13px",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "8px"
            }}
          >
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Kullanıcı Adı</label>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: "36px" }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
              <User
                size={16}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: "24px" }}>
            <label className="form-label">Şifre</label>
            <div style={{ position: "relative" }}>
              <input
                type="password"
                className="form-input"
                style={{ paddingLeft: "36px" }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock
                size={16}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", padding: "11px", fontSize: "15px" }}
            disabled={loading}
          >
            {loading ? "Giriş yapılıyor..." : "Sisteme Giriş Yap"}
            <ArrowRight size={16} />
          </button>
        </form>

        <div
          style={{
            marginTop: "24px",
            padding: "14px",
            background: "#f8fafc",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#64748b",
            border: "1px dashed #cbd5e1"
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "8px", color: "var(--text-main)", textAlign: "center" }}>
            Hızlı Rol Girişi (Test & Demo):
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ justifyContent: "space-between", padding: "6px 10px" }}
              onClick={() => {
                setUsername("admin");
                setPassword("admin123");
              }}
            >
              <span><strong>admin</strong> (Franchisor Admin)</span>
              <span className="badge badge-primary" style={{ fontSize: "10px" }}>Merkez</span>
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ justifyContent: "space-between", padding: "6px 10px" }}
              onClick={() => {
                setUsername("bayi_admin");
                setPassword("admin123");
              }}
            >
              <span><strong>bayi_admin</strong> (Bayi Yöneticisi)</span>
              <span className="badge badge-info" style={{ fontSize: "10px" }}>Merkez Bayi</span>
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ justifyContent: "space-between", padding: "6px 10px" }}
              onClick={() => {
                setUsername("viewer");
                setPassword("admin123");
              }}
            >
              <span><strong>viewer</strong> (Denetçi / İzleyici)</span>
              <span className="badge" style={{ fontSize: "10px", background: "#e2e8f0" }}>Salt Okunur</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
