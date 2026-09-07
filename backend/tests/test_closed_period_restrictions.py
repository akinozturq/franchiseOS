import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import io

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.transaction import Transaction
from backend.app.core.security import create_access_token
from backend.app.services.import_service import execute_import, UPLOAD_CACHE

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def get_bayi_token(username: str = "bayi_admin") -> str:
    return create_access_token({"sub": username})

@pytest.fixture(scope="module")
def closed_period_setup():
    f_token = get_auth_token("admin")
    b_token = get_bayi_token("bayi_admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    year, month = 2026, 6

    db: Session = SessionLocal()
    try:
        db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == 1,
            PeriodClosure.year == year,
            PeriodClosure.month == month
        ).delete()
        db.query(Transaction).filter(
            Transaction.branch_id == 1,
            Transaction.date >= date(year, month, 1),
            Transaction.date <= date(year, month, 30)
        ).delete()
        db.commit()

        # Create one baseline transaction before closing
        tx = Transaction(
            branch_id=1,
            department_id=1,
            employee_id=1,
            date=date(year, month, 10),
            customer_name="Kilit Test Müşteri",
            item_name="Ön Kaput PPF",
            amount_excl_vat=Decimal("25000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("30000.00")
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        tx_id = tx.id
    finally:
        db.close()

    # Close period
    close_res = client.post(
        "/api/v1/period-closures",
        json={"year": year, "month": month},
        headers=f_headers
    )
    assert close_res.status_code == 201
    closure_id = close_res.json()["id"]

    yield {
        "year": year,
        "month": month,
        "tx_id": tx_id,
        "closure_id": closure_id,
        "f_headers": f_headers,
        "b_headers": b_headers
    }

    # Cleanup
    cleanup_db = SessionLocal()
    try:
        cleanup_db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
        cleanup_db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 30)).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()

def test_cannot_create_transaction_in_closed_period(closed_period_setup):
    data = closed_period_setup
    res = client.post(
        "/api/v1/transactions",
        json={
            "department_id": 1,
            "date": f"{data['year']}-{data['month']:02d}-15",
            "customer_name": "Engellenen İşlem",
            "item_name": "PPF Kaplama",
            "amount_excl_vat": "10000.00",
            "vat_rate": "0.20",
            "amount_incl_vat": "12000.00"
        },
        headers=data["b_headers"]
    )
    assert res.status_code == 400
    assert "kapatılmıştır" in res.json()["detail"].lower()

def test_cannot_update_transaction_in_closed_period(closed_period_setup):
    data = closed_period_setup
    res = client.put(
        f"/api/v1/transactions/{data['tx_id']}",
        json={
            "amount_excl_vat": "35000.00",
            "amount_incl_vat": "42000.00"
        },
        headers=data["b_headers"]
    )
    assert res.status_code == 400
    assert "kapatılmıştır" in res.json()["detail"].lower()

def test_cannot_delete_transaction_in_closed_period(closed_period_setup):
    data = closed_period_setup
    res = client.delete(
        f"/api/v1/transactions/{data['tx_id']}",
        headers=data["b_headers"]
    )
    assert res.status_code == 400
    assert "kapatılmıştır" in res.json()["detail"].lower()

def test_csv_import_rejects_closed_period_rows(closed_period_setup):
    data = closed_period_setup
    db: Session = SessionLocal()
    try:
        file_id = "test-closed-import-uuid"
        UPLOAD_CACHE[file_id] = {
            "rows": [
                {
                    "Tarih": f"{data['year']}-{data['month']:02d}-12",
                    "Müşteri": "Excel Kapalı Dönem Müşteri",
                    "Departman": "PPF & Araç Kaplama",
                    "İşlem": "Komple TPU PPF Kaplama",
                    "Tutar": "40.000,00",
                    "KDV Oranı": "20"
                }
            ],
            "filename": "test.xlsx"
        }
        mapping = {
            "date": "Tarih",
            "customer_name": "Müşteri",
            "department_name": "Departman",
            "item_name": "İşlem",
            "amount_excl_vat": "Tutar",
            "vat_rate": "KDV Oranı"
        }
        result = execute_import(
            file_id=file_id,
            column_mapping=mapping,
            default_department_id=1,
            branch_id=1,
            db=db
        )
        assert result.total_rows == 1
        assert result.successful_count == 0
        assert result.failed_count == 1
        assert "kapatılmıştır" in result.errors[0].error_message.lower()
    finally:
        db.close()

def test_bayi_admin_cannot_reopen_period_forbidden(closed_period_setup):
    data = closed_period_setup
    res = client.post(
        f"/api/v1/period-closures/{data['closure_id']}/reopen",
        json={"reopen_reason": "Bayi yetkisiz açma denemesi"},
        headers=data["b_headers"]
    )
    assert res.status_code == 403

def test_franchisor_admin_reopen_validation_requires_reason(closed_period_setup):
    data = closed_period_setup
    # Empty reason
    res1 = client.post(
        f"/api/v1/period-closures/{data['closure_id']}/reopen",
        json={"reopen_reason": ""},
        headers=data["f_headers"]
    )
    assert res1.status_code == 422

    # Short reason (< 5 chars)
    res2 = client.post(
        f"/api/v1/period-closures/{data['closure_id']}/reopen",
        json={"reopen_reason": "kısa"},
        headers=data["f_headers"]
    )
    assert res2.status_code == 422
