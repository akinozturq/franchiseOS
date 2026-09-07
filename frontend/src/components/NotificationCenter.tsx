import React, { useState, useEffect, useRef } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  Clock,
  Lock,
  Unlock,
  AlertCircle,
  RefreshCw
} from "lucide-react";
import { apiClient } from "../api/client";
import type { SystemNotification, User } from "../types";

interface NotificationCenterProps {
  user: User;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingReminders, setCheckingReminders] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchUnreadCount = async () => {
    try {
      const res = await apiClient.get<{ unread_count: number }>("/notifications/unread-count");
      setUnreadCount(res.data.unread_count);
    } catch (e) {
      // silent
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<SystemNotification[]>("/notifications", {
        params: { unread_only: unreadOnly, limit: 30 }
      });
      setNotifications(res.data);
      fetchUnreadCount();
    } catch (e) {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000); // 30s poll
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, unreadOnly]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const markAsRead = async (id: number) => {
    try {
      await apiClient.patch(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (e) {}
  };

  const markAllAsRead = async () => {
    try {
      await apiClient.post("/notifications/mark-all-read");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (e) {}
  };

  const handleCheckReminders = async () => {
    setCheckingReminders(true);
    try {
      await apiClient.post("/notifications/check-closure-reminders");
      fetchNotifications();
    } catch (e) {
    } finally {
      setCheckingReminders(false);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "PERIOD_CLOSED":
        return <Lock size={15} color="#16a34a" />;
      case "PERIOD_REOPENED":
        return <Unlock size={15} color="#d97706" />;
      case "PERIOD_CLOSURE_REQUESTED":
        return <Clock size={15} color="#2563eb" />;
      case "PERIOD_CLOSURE_REMINDER":
        return <AlertCircle size={15} color="#9333ea" />;
      default:
        return <Bell size={15} color="#64748b" />;
    }
  };

  const formatTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString("tr-TR", {
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

  return (
    <div style={{ position: "relative" }} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-secondary btn-sm"
        style={{
          position: "relative",
          padding: "6px 9px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}
        title="Sistem Bildirimleri"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "-5px",
              right: "-5px",
              background: "#ef4444",
              color: "#ffffff",
              fontSize: "10px",
              fontWeight: 700,
              minWidth: "16px",
              height: "16px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 4px",
              border: "2px solid #ffffff",
              boxShadow: "0 1px 2px rgba(0,0,0,0.1)"
            }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 8px)",
            width: "380px",
            maxWidth: "90vw",
            background: "#ffffff",
            borderRadius: "10px",
            boxShadow: "0 10px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1)",
            border: "1px solid #e2e8f0",
            zIndex: 1000,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            maxHeight: "520px"
          }}
        >
          {/* Dropdown Header */}
          <div
            style={{
              padding: "12px 16px",
              background: "#f8fafc",
              borderBottom: "1px solid #e2e8f0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontWeight: 700, fontSize: "14px", color: "#0f172a" }}>
                Bildirimler
              </span>
              {unreadCount > 0 && (
                <span
                  style={{
                    background: "#fee2e2",
                    color: "#dc2626",
                    fontSize: "11px",
                    fontWeight: 600,
                    padding: "2px 6px",
                    borderRadius: "10px"
                  }}
                >
                  {unreadCount} yeni
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: "6px" }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: "11px", padding: "2px 6px", height: "24px" }}
                onClick={() => setUnreadOnly(!unreadOnly)}
              >
                {unreadOnly ? "Tümü" : "Sadece Okunmamış"}
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: "11px", padding: "2px 6px", height: "24px" }}
                  onClick={markAllAsRead}
                  title="Tümünü Okundu İşaretle"
                >
                  <CheckCheck size={12} style={{ marginRight: "3px" }} />
                  Tümü
                </button>
              )}
            </div>
          </div>

          {/* Optional: Franchisor Admin Action Bar */}
          {user.role === "FRANCHISOR_ADMIN" && (
            <div
              style={{
                padding: "6px 14px",
                background: "#eff6ff",
                borderBottom: "1px solid #dbeafe",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}
            >
              <span style={{ fontSize: "11px", color: "#1e40af", fontWeight: 500 }}>
                Dönem kapama hatırlatıcı kontrolü
              </span>
              <button
                type="button"
                onClick={handleCheckReminders}
                disabled={checkingReminders}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#2563eb",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px"
                }}
              >
                <RefreshCw size={11} className={checkingReminders ? "animate-spin" : ""} />
                Hatırlatıcıları Tara
              </button>
            </div>
          )}

          {/* List Content */}
          <div style={{ overflowY: "auto", flex: 1, padding: "4px 0" }}>
            {loading ? (
              <div style={{ padding: "24px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                Yükleniyor...
              </div>
            ) : notifications.length === 0 ? (
              <div style={{ padding: "32px 16px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                <Bell size={24} style={{ margin: "0 auto 8px auto", opacity: 0.5 }} />
                Henüz bildirim bulunmuyor.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: "10px 14px",
                    borderBottom: "1px solid #f1f5f9",
                    background: n.is_read ? "#ffffff" : "#f8fafc",
                    transition: "background 0.15s ease",
                    display: "flex",
                    gap: "10px",
                    alignItems: "flex-start"
                  }}
                >
                  <div
                    style={{
                      marginTop: "2px",
                      background: n.is_read ? "#f1f5f9" : "#ffffff",
                      border: "1px solid #e2e8f0",
                      borderRadius: "6px",
                      padding: "6px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    {getNotificationIcon(n.type)}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "baseline",
                        gap: "6px"
                      }}
                    >
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: n.is_read ? 600 : 700,
                          color: "#0f172a"
                        }}
                      >
                        {n.title}
                      </span>
                      <span style={{ fontSize: "10px", color: "#94a3b8", whiteSpace: "nowrap" }}>
                        {formatTime(n.created_at)}
                      </span>
                    </div>

                    <p
                      style={{
                        margin: "3px 0 0 0",
                        fontSize: "12px",
                        color: "#475569",
                        lineHeight: 1.4
                      }}
                    >
                      {n.message}
                    </p>
                  </div>

                  {!n.is_read && (
                    <button
                      type="button"
                      onClick={() => markAsRead(n.id)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#94a3b8",
                        cursor: "pointer",
                        padding: "4px",
                        marginTop: "2px"
                      }}
                      title="Okundu İşaretle"
                    >
                      <Check size={14} />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
