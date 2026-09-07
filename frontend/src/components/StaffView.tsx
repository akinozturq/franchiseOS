import React, { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, UserPlus, X, AlertCircle, Link as LinkIcon, UserCheck, RefreshCw, History } from "lucide-react";
import api from "../api/client";
import type { Employee, Role, Department, Transaction, TurnoverSource, User } from "../types";
import { RuleHistoryModal } from "./RuleHistoryModal";

interface StaffViewProps {
  user?: User | null;
}

export const StaffView: React.FC<StaffViewProps> = ({ user }) => {
  const [subTab, setSubTab] = useState<"employees" | "roles">("employees");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [unassignedTxs, setUnassignedTxs] = useState<Transaction[]>([]);
  
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Role History Modal state
  const [isRoleHistoryOpen, setIsRoleHistoryOpen] = useState<boolean>(false);
  const [selectedRoleForHistory, setSelectedRoleForHistory] = useState<Role | null>(null);

  // Employee modal state
  const [isEmpModalOpen, setIsEmpModalOpen] = useState<boolean>(false);
  const [editingEmp, setEditingEmp] = useState<Employee | null>(null);
  const [empFullName, setEmpFullName] = useState<string>("");
  const [empRoleId, setEmpRoleId] = useState<number>(0);
  const [empDeptId, setEmpDeptId] = useState<number | null>(null);
  const [empIsActive, setEmpIsActive] = useState<boolean>(true);

  // Role modal state
  const [isRoleModalOpen, setIsRoleModalOpen] = useState<boolean>(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [roleName, setRoleName] = useState<string>("");
  const [roleTurnoverSource, setRoleTurnoverSource] = useState<TurnoverSource>("kendi_islemleri");
  const [roleIsActive, setRoleIsActive] = useState<boolean>(true);

  // Add tier inline form state for a role
  const [newTierRoleId, setNewTierRoleId] = useState<number | null>(null);
  const [tierMinAmount, setTierMinAmount] = useState<string>("0");
  const [tierMaxAmount, setTierMaxAmount] = useState<string>("");
  const [tierRate, setTierRate] = useState<string>("5");

  // Unassigned modal state
  const [isUnassignedModalOpen, setIsUnassignedModalOpen] = useState<boolean>(false);
  const [selectedTxIds, setSelectedTxIds] = useState<number[]>([]);
  const [targetEmpId, setTargetEmpId] = useState<number>(0);
  const [isAssigning, setIsAssigning] = useState<boolean>(false);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [empRes, rolesRes, deptRes, unassignedRes] = await Promise.all([
        api.get<Employee[]>("/employees"),
        api.get<Role[]>("/roles"),
        api.get<Department[]>("/departments"),
        api.get<Transaction[]>("/employees/unassigned-transactions")
      ]);
      setEmployees(empRes.data);
      setRoles(rolesRes.data);
      setDepartments(deptRes.data);
      setUnassignedTxs(unassignedRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Veriler yüklenirken hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openAddEmployeeModal = () => {
    setEditingEmp(null);
    setEmpFullName("");
    setEmpRoleId(roles[0]?.id || 0);
    setEmpDeptId(departments[0]?.id || null);
    setEmpIsActive(true);
    setIsEmpModalOpen(true);
  };

  const openEditEmployeeModal = (emp: Employee) => {
    setEditingEmp(emp);
    setEmpFullName(emp.full_name);
    setEmpRoleId(emp.role_id);
    setEmpDeptId(emp.department_id || null);
    setEmpIsActive(emp.is_active);
    setIsEmpModalOpen(true);
  };

  const handleSaveEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!empFullName.trim() || !empRoleId) return;

    try {
      if (editingEmp) {
        await api.put(`/employees/${editingEmp.id}`, {
          full_name: empFullName.trim(),
          role_id: empRoleId,
          department_id: empDeptId,
          is_active: empIsActive
        });
      } else {
        await api.post("/employees", {
          full_name: empFullName.trim(),
          role_id: empRoleId,
          department_id: empDeptId,
          is_active: empIsActive
        });
      }
      setIsEmpModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Personel kaydedilemedi.");
    }
  };

  const handleDeleteEmployee = async (empId: number) => {
    if (!window.confirm("Bu personeli silmek istediğinize emin misiniz? (İşlem kaydı varsa pasife almanız önerilir)")) return;
    try {
      await api.delete(`/employees/${empId}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Personel silinemedi.");
    }
  };

  const openAddRoleModal = () => {
    setEditingRole(null);
    setRoleName("");
    setRoleTurnoverSource("kendi_islemleri");
    setRoleIsActive(true);
    setIsRoleModalOpen(true);
  };

  const openEditRoleModal = (role: Role) => {
    setEditingRole(role);
    setRoleName(role.name);
    setRoleTurnoverSource(role.turnover_source);
    setRoleIsActive(role.is_active);
    setIsRoleModalOpen(true);
  };

  const handleSaveRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleName.trim()) return;

    try {
      if (editingRole) {
        await api.put(`/roles/${editingRole.id}`, {
          name: roleName.trim(),
          turnover_source: roleTurnoverSource,
          is_active: roleIsActive
        });
      } else {
        await api.post("/roles", {
          name: roleName.trim(),
          turnover_source: roleTurnoverSource,
          is_active: roleIsActive
        });
      }
      setIsRoleModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Rol kaydedilemedi.");
    }
  };

  const handleDeleteRole = async (roleId: number) => {
    if (!window.confirm("Bu rolü silmek istediğinize emin misiniz?")) return;
    try {
      await api.delete(`/roles/${roleId}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Rol silinemedi.");
    }
  };

  const handleAddTier = async (roleId: number) => {
    const rateNum = parseFloat(tierRate) / 100;
    const minNum = parseFloat(tierMinAmount) || 0;
    const maxNum = tierMaxAmount.trim() !== "" ? parseFloat(tierMaxAmount) : null;

    if (isNaN(rateNum) || rateNum <= 0) {
      alert("Lütfen geçerli bir prim oranı girin.");
      return;
    }

    try {
      await api.post(`/roles/${roleId}/tiers`, {
        min_amount: minNum,
        max_amount: maxNum,
        rate: rateNum
      });
      setNewTierRoleId(null);
      setTierMinAmount("0");
      setTierMaxAmount("");
      setTierRate("5");
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Kademe eklenemedi.");
    }
  };

  const handleDeleteTier = async (roleId: number, tierId: number) => {
    if (!window.confirm("Bu kademe dilimini silmek istediğinize emin misiniz?")) return;
    try {
      await api.delete(`/roles/${roleId}/tiers/${tierId}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Kademe silinemedi.");
    }
  };

  const handleAssignTransactions = async () => {
    if (selectedTxIds.length === 0 || !targetEmpId) {
      alert("Lütfen en az bir işlem ve atanacak personeli seçin.");
      return;
    }
    setIsAssigning(true);
    try {
      await api.post("/employees/assign-transactions", {
        transaction_ids: selectedTxIds,
        employee_id: targetEmpId
      });
      setIsUnassignedModalOpen(false);
      setSelectedTxIds([]);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "İşlemler atanamadı.");
    } finally {
      setIsAssigning(false);
    }
  };

  const formatMoney = (val: string | number | undefined | null): string => {
    if (val === undefined || val === null || val === "") return "0,00 TL";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      minimumFractionDigits: 2
    }).format(num);
  };

  const getSourceBadge = (source: TurnoverSource) => {
    switch (source) {
      case "kendi_islemleri":
        return <span className="status-badge" style={{ background: "#e0f2fe", color: "#0369a1" }}>Kendi İşlemleri</span>;
      case "kendi_departmani":
        return <span className="status-badge" style={{ background: "#fef3c7", color: "#92400e" }}>Kendi Departmanı</span>;
      case "tum_bayi":
        return <span className="status-badge" style={{ background: "#f3e8ff", color: "#6b21a8" }}>Tüm Bayi</span>;
      default:
        return <span className="status-badge">{source}</span>;
    }
  };

  return (
    <div className="view-container">
      {/* Header */}
      <div className="card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h1 className="page-title" style={{ margin: 0 }}>Personel & Rol Yönetimi</h1>
            <p className="page-description" style={{ margin: "4px 0 0 0" }}>
              Bayi personel kadrosu, iş rolleri, ciro kaynakları ve kademeli prim hiyerarşisi
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {user?.role !== "VIEWER" && unassignedTxs.length > 0 && (
              <button
                className="btn"
                style={{ background: "#fffbeb", border: "1px solid #fde68a", color: "#92400e" }}
                onClick={() => {
                  setSelectedTxIds(unassignedTxs.map((t) => t.id!));
                  setTargetEmpId(employees[0]?.id || 0);
                  setIsUnassignedModalOpen(true);
                }}
              >
                <LinkIcon size={14} />
                Atanmamış İşlemler ({unassignedTxs.length})
              </button>
            )}

            {subTab === "employees" ? (
              user?.role !== "VIEWER" && (
                <button className="btn btn-primary" onClick={openAddEmployeeModal}>
                  <UserPlus size={14} />
                  Yeni Personel Ekle
                </button>
              )
            ) : (
              user?.role === "FRANCHISOR_ADMIN" && (
                <button className="btn btn-primary" onClick={openAddRoleModal}>
                  <Plus size={14} />
                  Yeni Rol Tanımla
                </button>
              )
            )}
          </div>
        </div>

        {/* Sub Navigation */}
        <div style={{ display: "flex", gap: "8px", marginTop: "20px", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
          <button
            className={`btn ${subTab === "employees" ? "btn-primary" : "btn-secondary"}`}
            style={{ fontSize: "13px" }}
            onClick={() => setSubTab("employees")}
          >
            Personeller ({employees.length})
          </button>
          <button
            className={`btn ${subTab === "roles" ? "btn-primary" : "btn-secondary"}`}
            style={{ fontSize: "13px" }}
            onClick={() => setSubTab("roles")}
          >
            Roller ve Prim Kademeleri ({roles.length})
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* SUBTAB 1: EMPLOYEES */}
      {subTab === "employees" && (
        <div className="card" style={{ overflow: "hidden", padding: 0 }}>
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Adı Soyadı</th>
                  <th>Rol</th>
                  <th>Ciro Kaynağı</th>
                  <th>Departman</th>
                  <th>Durum</th>
                  {user?.role !== "VIEWER" && (
                    <th style={{ textAlign: "right" }}>İşlemler</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                      <RefreshCw size={20} className="spin" style={{ margin: "0 auto 8px" }} />
                      Personeller yükleniyor...
                    </td>
                  </tr>
                ) : employees.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                      Kayıtlı personel bulunamadı.
                    </td>
                  </tr>
                ) : (
                  employees.map((emp) => (
                    <tr key={emp.id}>
                      <td style={{ fontWeight: 600 }}>{emp.full_name}</td>
                      <td>{emp.role_name || "—"}</td>
                      <td>{emp.role ? getSourceBadge(emp.role.turnover_source) : "—"}</td>
                      <td>{emp.department_name || (emp.role?.turnover_source === "tum_bayi" ? "Tüm Bayi (Bağımsız)" : "—")}</td>
                      <td>
                        <span className={`status-badge ${emp.is_active ? "status-success" : "status-warning"}`}>
                          {emp.is_active ? "Aktif" : "Pasif"}
                        </span>
                      </td>
                      {user?.role !== "VIEWER" && (
                        <td style={{ textAlign: "right" }}>
                          <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => openEditEmployeeModal(emp)}
                              title="Düzenle"
                            >
                              <Edit2 size={13} />
                            </button>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleDeleteEmployee(emp.id)}
                              title="Sil"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUBTAB 2: ROLES & TIERS */}
      {subTab === "roles" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {user?.role !== "FRANCHISOR_ADMIN" && (
            <div style={{ padding: "12px 16px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "10px" }}>
              <AlertCircle size={18} color="#1e3a8a" />
              <span>Personel iş rolleri ve kademeli prim kuralları <strong>Merkez Franchisor</strong> tarafından belirlenmektedir. Bayi ve izleyici kullanıcıları bu ekranda yalnızca geçerli kuralları görüntüleyebilir.</span>
            </div>
          )}

          {roles.map((role) => (
            <div key={role.id} className="card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 600, margin: 0 }}>{role.name}</h3>
                  {getSourceBadge(role.turnover_source)}
                  <span className={`status-badge ${role.is_active ? "status-success" : "status-warning"}`}>
                    {role.is_active ? "Aktif" : "Pasif"}
                  </span>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setSelectedRoleForHistory(role);
                      setIsRoleHistoryOpen(true);
                    }}
                    style={{ display: "flex", alignItems: "center", gap: "4px" }}
                    title="Rol Değişiklik Geçmişi"
                  >
                    <History size={13} />
                    Geçmiş
                  </button>

                  {user?.role === "FRANCHISOR_ADMIN" && (
                    <>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setNewTierRoleId(newTierRoleId === role.id ? null : role.id)}
                      >
                        <Plus size={13} />
                        Kademe Ekle
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => openEditRoleModal(role)}
                        title="Rolü Düzenle"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDeleteRole(role.id)}
                        title="Rolü Sil"
                      >
                        <Trash2 size={13} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Inline Add Tier Form */}
              {newTierRoleId === role.id && (
                <div style={{ padding: "12px", background: "#f8fafc", border: "1px dashed var(--border)", borderRadius: "6px", marginBottom: "16px" }}>
                  <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "8px" }}>Yeni Prim Dilimi Tanımla</div>
                  <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>Alt Sınır (TL)</label>
                      <input
                        type="number"
                        className="input"
                        style={{ width: "130px" }}
                        value={tierMinAmount}
                        onChange={(e) => setTierMinAmount(e.target.value)}
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>Üst Sınır (TL, boş=sonsuz)</label>
                      <input
                        type="number"
                        className="input"
                        style={{ width: "130px" }}
                        value={tierMaxAmount}
                        onChange={(e) => setTierMaxAmount(e.target.value)}
                        placeholder="Sonsuz"
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>Prim Oranı (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="input"
                        style={{ width: "90px" }}
                        value={tierRate}
                        onChange={(e) => setTierRate(e.target.value)}
                        placeholder="5.0"
                      />
                    </div>
                    <div style={{ alignSelf: "flex-end", display: "flex", gap: "6px" }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleAddTier(role.id)}>
                        Kaydet
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => setNewTierRoleId(null)}>
                        İptal
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Tiers Table */}
              <div className="table-responsive">
                <table className="table" style={{ fontSize: "13px" }}>
                  <thead>
                    <tr style={{ background: "#f8fafc" }}>
                      <th>Alt Sınır (KDV Hariç)</th>
                      <th>Üst Sınır</th>
                      <th style={{ textAlign: "right" }}>Prim Oranı (%)</th>
                      {user?.role === "FRANCHISOR_ADMIN" && (
                        <th style={{ textAlign: "right", width: "80px" }}>İşlem</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {role.commission_tiers.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center", color: "var(--text-muted)", padding: "16px" }}>
                          Bu role ait kademeli prim kuralı tanımlanmamış.
                        </td>
                      </tr>
                    ) : (
                      role.commission_tiers.map((t) => (
                        <tr key={t.id}>
                          <td style={{ fontVariantNumeric: "tabular-nums" }}>{formatMoney(t.min_amount)}</td>
                          <td style={{ fontVariantNumeric: "tabular-nums" }}>
                            {t.max_amount !== null ? formatMoney(t.max_amount) : "Sonsuz (ve üzeri)"}
                          </td>
                          <td style={{ textAlign: "right", fontWeight: 600, color: "var(--primary)", fontVariantNumeric: "tabular-nums" }}>
                            %{parseFloat(String(t.rate)) * 100}
                          </td>
                          {user?.role === "FRANCHISOR_ADMIN" && (
                            <td style={{ textAlign: "right" }}>
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDeleteTier(role.id, t.id!)}
                                title="Kademe Dilimini Sil"
                              >
                                <Trash2 size={12} />
                              </button>
                            </td>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* EMPLOYEE MODAL */}
      {isEmpModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "450px" }}>
            <div className="modal-header">
              <h2 className="modal-title">{editingEmp ? "Personel Bilgilerini Düzenle" : "Yeni Personel Ekle"}</h2>
              <button className="modal-close" onClick={() => setIsEmpModalOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSaveEmployee}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label className="form-label">Adı Soyadı</label>
                  <input
                    type="text"
                    required
                    className="input"
                    value={empFullName}
                    onChange={(e) => setEmpFullName(e.target.value)}
                    placeholder="Örn: Merve Satış"
                  />
                </div>

                <div>
                  <label className="form-label">Görevi / Rolü</label>
                  <select
                    className="input"
                    value={empRoleId}
                    onChange={(e) => setEmpRoleId(parseInt(e.target.value))}
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.turnover_source === "tum_bayi" ? "Tüm Bayi" : r.turnover_source === "kendi_departmani" ? "Kendi Departmanı" : "Kendi İşlemleri"})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="form-label">Departmanı</label>
                  <select
                    className="input"
                    value={empDeptId || ""}
                    onChange={(e) => setEmpDeptId(e.target.value ? parseInt(e.target.value) : null)}
                  >
                    <option value="">Departmandan Bağımsız (örn. Genel Müdür)</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
                  <input
                    type="checkbox"
                    id="empActive"
                    checked={empIsActive}
                    onChange={(e) => setEmpIsActive(e.target.checked)}
                  />
                  <label htmlFor="empActive" style={{ fontSize: "13px", cursor: "pointer" }}>
                    Personel aktif (prim hesaplamasına dahil edilir)
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsEmpModalOpen(false)}>
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

      {/* ROLE MODAL */}
      {isRoleModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "450px" }}>
            <div className="modal-header">
              <h2 className="modal-title">{editingRole ? "Rolü Düzenle" : "Yeni Rol Tanımla"}</h2>
              <button className="modal-close" onClick={() => setIsRoleModalOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSaveRole}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label className="form-label">Rol Adı</label>
                  <input
                    type="text"
                    required
                    className="input"
                    value={roleName}
                    onChange={(e) => setRoleName(e.target.value)}
                    placeholder="Örn: Servis Müdürü"
                  />
                </div>

                <div>
                  <label className="form-label">Ciro Kaynağı (Prim Hesabı Havuzu)</label>
                  <select
                    className="input"
                    value={roleTurnoverSource}
                    onChange={(e) => setRoleTurnoverSource(e.target.value as TurnoverSource)}
                  >
                    <option value="kendi_islemleri">Kendi İşlemleri (Danışmanın bizzat yaptığı işlemler)</option>
                    <option value="kendi_departmani">Kendi Departmanı (Departmandaki tüm işlemler - örn. Müdürler)</option>
                    <option value="tum_bayi">Tüm Bayi (Departmandan bağımsız tüm ciro - örn. Genel Müdür)</option>
                  </select>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
                  <input
                    type="checkbox"
                    id="roleActive"
                    checked={roleIsActive}
                    onChange={(e) => setRoleIsActive(e.target.checked)}
                  />
                  <label htmlFor="roleActive" style={{ fontSize: "13px", cursor: "pointer" }}>
                    Rol aktif
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsRoleModalOpen(false)}>
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

      {/* UNASSIGNED TRANSACTIONS MODAL */}
      {isUnassignedModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "700px" }}>
            <div className="modal-header">
              <h2 className="modal-title">Atanmamış İşlem Kayıtlarını Eşleştir</h2>
              <button className="modal-close" onClick={() => setIsUnassignedModalOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                Aşağıdaki işlemler henüz bir personele (Employee) bağlanmamış. Seçilen işlemleri bağlamak istediğiniz personeli belirleyin:
              </p>

              <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "16px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600 }}>Atanacak Personel:</label>
                <select
                  className="input"
                  style={{ flex: 1 }}
                  value={targetEmpId}
                  onChange={(e) => setTargetEmpId(parseInt(e.target.value))}
                >
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name} ({e.role_name || "Rol Yok"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="table-responsive" style={{ maxHeight: "300px", overflowY: "auto" }}>
                <table className="table" style={{ fontSize: "12px" }}>
                  <thead>
                    <tr>
                      <th style={{ width: "30px" }}>
                        <input
                          type="checkbox"
                          checked={selectedTxIds.length === unassignedTxs.length}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedTxIds(unassignedTxs.map((t) => t.id!));
                            else setSelectedTxIds([]);
                          }}
                        />
                      </th>
                      <th>Tarih</th>
                      <th>Müşteri</th>
                      <th>Hizmet / Kategori</th>
                      <th>Serbest Metin Personel</th>
                      <th style={{ textAlign: "right" }}>Tutar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {unassignedTxs.map((tx) => (
                      <tr key={tx.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedTxIds.includes(tx.id!)}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedTxIds([...selectedTxIds, tx.id!]);
                              else setSelectedTxIds(selectedTxIds.filter((id) => id !== tx.id));
                            }}
                          />
                        </td>
                        <td>{tx.date}</td>
                        <td>{tx.customer_name}</td>
                        <td>{tx.item_name}</td>
                        <td style={{ color: "var(--primary)" }}>{tx.staff_name || "—"}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {formatMoney(tx.amount_excl_vat)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="modal-footer">
              <span style={{ marginRight: "auto", fontSize: "12px", color: "var(--text-muted)" }}>
                {selectedTxIds.length} adet işlem seçildi
              </span>
              <button type="button" className="btn btn-secondary" onClick={() => setIsUnassignedModalOpen(false)}>
                İptal
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={isAssigning || selectedTxIds.length === 0}
                onClick={handleAssignTransactions}
              >
                <UserCheck size={14} />
                {isAssigning ? "Atanıyor..." : "Seçilenleri Personele Ata"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ROLE HISTORY MODAL */}
      <RuleHistoryModal
        isOpen={isRoleHistoryOpen}
        onClose={() => {
          setIsRoleHistoryOpen(false);
          setSelectedRoleForHistory(null);
        }}
        title={`${selectedRoleForHistory?.name || "Rol"} - Kural Değişiklik Geçmişi`}
        fetchUrl={selectedRoleForHistory ? `/roles/${selectedRoleForHistory.id}/history` : ""}
      />
    </div>
  );
};
