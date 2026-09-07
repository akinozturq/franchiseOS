import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.transaction import Transaction

from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def get_bayi_token(username: str = "bayi_admin") -> str:
    return create_access_token({"sub": username})

def test_period_closure_lifecycle_and_transaction_lock():
    f_token = get_auth_token("admin")
    b_token = get_bayi_token("bayi_admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    year, month = 2026, 1

    # Clean up any existing closure for (2026, 1) in test DB
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

    # Ensure a test transaction exists for (2026, 1) before closing
    tx_setup = client.post(
        "/api/v1/transactions",
        json={
            "department_id": 1,
            "date": f"{year}-{month:02d}-10",
            "customer_name": "Test Müşteri Kapama Öncesi",
            "item_name": "Test Hizmet",
            "amount_excl_vat": "2000.00",
            "vat_rate": "0.20",
            "amount_incl_vat": "2400.00"
        },
        headers=b_headers
    )
    assert tx_setup.status_code == 201
    target_tx_id = tx_setup.json()["id"]

    # 1. Bayi admin requests period closure
    req_res = client.post("/api/v1/period-closures/request", json={"year": year, "month": month}, headers=b_headers)
    assert req_res.status_code in [200, 201]

    # Check status endpoint shows request pending
    status_res = client.get(f"/api/v1/period-closures/status?year={year}&month={month}", headers=b_headers)
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["is_closed"] is False
    assert st["status"] == "CLOSURE_REQUESTED"

    # 2. Franchisor admin closes period
    close_res = client.post("/api/v1/period-closures", json={"year": year, "month": month}, headers=f_headers)
    assert close_res.status_code == 201
    closure = close_res.json()
    closure_id = closure["id"]
    assert closure["status"] == "CLOSED"
    assert closure["reconciliation_snapshot"] is not None
    assert closure["bonus_snapshot"] is not None

    frozen_commission = closure["reconciliation_snapshot"]["franchisor_share_excl_vat"]

    # 3. Status endpoint now reports closed
    status_res2 = client.get(f"/api/v1/period-closures/status?year={year}&month={month}", headers=b_headers)
    assert status_res2.status_code == 200
    st2 = status_res2.json()
    assert st2["is_closed"] is True
    assert st2["status"] == "CLOSED"
    assert st2["closure_id"] == closure_id

    # 4. Reconciliation endpoint returns the frozen snapshot
    rec_res = client.get(f"/api/v1/reconciliation?year={year}&month={month}", headers=b_headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["is_closed"] is True
    assert rec_data["franchisor_share_excl_vat"] == frozen_commission

    # 5. Bonus report endpoint returns the frozen snapshot
    bonus_res = client.get(f"/api/v1/bonus?year={year}&month={month}", headers=b_headers)
    assert bonus_res.status_code == 200
    bonus_data = bonus_res.json()
    assert bonus_data["is_closed"] is True

    # 6. Transaction immutability: Attempt to create transaction in closed period -> HTTP 400
    tx_create_res = client.post(
        "/api/v1/transactions",
        json={
            "department_id": 1,
            "date": f"{year}-{month:02d}-15",
            "customer_name": "Yetkisiz İşlem Denemesi",
            "item_name": "Test Hizmet",
            "amount_excl_vat": "1000.00",
            "vat_rate": "0.20",
            "amount_incl_vat": "1200.00"
        },
        headers=b_headers
    )
    assert tx_create_res.status_code == 400
    assert "kapatılmıştır" in tx_create_res.json()["detail"].lower()

    # 7. Transaction immutability: Attempt to delete transaction in closed period -> HTTP 400
    del_res = client.delete(f"/api/v1/transactions/{target_tx_id}", headers=b_headers)
    assert del_res.status_code == 400
    assert "kapatılmıştır" in del_res.json()["detail"].lower()

    # 8. E-invoice data export endpoint
    inv_res = client.get(f"/api/v1/period-closures/{closure_id}/invoice-data", headers=b_headers)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["period"] == f"{year}-{month:02d}"
    assert inv_data["currency"] == "TRY"
    assert "issuer" in inv_data and "recipient" in inv_data
    assert len(inv_data["line_items"]) > 0
    assert inv_data["closure_audit"]["closure_id"] == closure_id

    # 9. Reopening without reason or too short -> 422
    fail_reopen = client.post(f"/api/v1/period-closures/{closure_id}/reopen", json={"reopen_reason": "abc"}, headers=f_headers)
    assert fail_reopen.status_code == 422

    # 10. Reopening with valid reason by Franchisor Admin
    reopen_res = client.post(
        f"/api/v1/period-closures/{closure_id}/reopen",
        json={"reopen_reason": "Ocak ayı ek faturası işlenecek, mutabakat düzeltmesi gerekiyor."},
        headers=f_headers
    )
    assert reopen_res.status_code == 200
    reopened = reopen_res.json()
    assert reopened["status"] == "REOPENED"
    assert reopened["reopen_reason"] is not None

    # Verify transactions can now be modified again
    status_res3 = client.get(f"/api/v1/period-closures/status?year={year}&month={month}", headers=b_headers)
    assert status_res3.status_code == 200
    assert status_res3.json()["is_closed"] is False
