import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.notification import Notification
from backend.app.models.period_closure import PeriodClosure
from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def get_bayi_token(username: str = "bayi_admin") -> str:
    return create_access_token({"sub": username})

def test_notification_listing_and_unread_count():
    b_token = get_bayi_token("bayi_admin")
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    # Seed a test notification for bayi_admin (user_id=2)
    db: Session = SessionLocal()
    try:
        n = Notification(
            user_id=2,
            branch_id=1,
            title="Test Bildirimi",
            message="Bu bir test bildirim mesajıdır.",
            type="SYSTEM",
            is_read=False
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        notif_id = n.id
    finally:
        db.close()

    # 1. Check unread count
    count_res = client.get("/api/v1/notifications/unread-count", headers=b_headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] >= 1

    # 2. List notifications
    list_res = client.get("/api/v1/notifications", headers=b_headers)
    assert list_res.status_code == 200
    notifications = list_res.json()
    assert any(item["id"] == notif_id for item in notifications)

def test_notification_mark_single_as_read():
    b_token = get_bayi_token("bayi_admin")
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    db: Session = SessionLocal()
    try:
        n = Notification(
            user_id=2,
            branch_id=1,
            title="Okunacak Bildirim",
            message="Okundu testi için oluşturuldu.",
            type="PERIOD_CLOSED",
            is_read=False
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        notif_id = n.id
    finally:
        db.close()

    # Mark as read
    patch_res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=b_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True

    # Verify in DB
    db = SessionLocal()
    try:
        updated = db.query(Notification).filter(Notification.id == notif_id).first()
        assert updated.is_read is True
    finally:
        db.close()

def test_notification_mark_all_as_read():
    b_token = get_bayi_token("bayi_admin")
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    db: Session = SessionLocal()
    try:
        n1 = Notification(user_id=2, branch_id=1, type="SYSTEM", title="Toplu 1", message="m1", is_read=False)
        n2 = Notification(user_id=2, branch_id=1, type="SYSTEM", title="Toplu 2", message="m2", is_read=False)
        db.add_all([n1, n2])
        db.commit()
    finally:
        db.close()

    # Mark all read
    res = client.post("/api/v1/notifications/mark-all-read", headers=b_headers)
    assert res.status_code == 200

    # Unread count should now be 0
    count_res = client.get("/api/v1/notifications/unread-count", headers=b_headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] == 0

def test_bayi_closure_request_generates_franchisor_notification():
    f_token = get_auth_token("admin")
    b_token = get_bayi_token("bayi_admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    year, month = 2026, 7

    # Cleanup past closure
    db: Session = SessionLocal()
    try:
        db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == 1,
            PeriodClosure.year == year,
            PeriodClosure.month == month
        ).delete()
        db.commit()
    finally:
        db.close()

    # Bayi admin requests period closure
    req_res = client.post(
        "/api/v1/period-closures/request",
        json={"year": year, "month": month},
        headers=b_headers
    )
    assert req_res.status_code in [200, 201]

    # Franchisor admin should receive a notification
    f_notifs_res = client.get("/api/v1/notifications", headers=f_headers)
    assert f_notifs_res.status_code == 200
    f_notifs = f_notifs_res.json()
    assert any("kapatma talebi" in n["title"].lower() or "kapatma talebi" in n["message"].lower() for n in f_notifs)

def test_notification_closure_reminder_scan():
    f_token = get_auth_token("admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}

    # Trigger closure reminder check
    scan_res = client.post("/api/v1/notifications/check-closure-reminders", headers=f_headers)
    assert scan_res.status_code == 200
    data = scan_res.json()
    assert "created_reminders_count" in data
    assert isinstance(data["created_reminders_count"], int)
