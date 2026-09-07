import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.period_setting import PeriodSetting
from backend.app.models.transaction import Transaction
from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def get_bayi_token(username: str = "bayi_admin") -> str:
    return create_access_token({"sub": username})

def test_invoice_data_skeleton_bayi_collector():
    f_token = get_auth_token("admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {get_bayi_token('bayi_admin')}", "X-Branch-Id": "1"}

    year, month = 2026, 11

    db: Session = SessionLocal()
    try:
        db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
        db.query(PeriodSetting).filter(PeriodSetting.branch_id == 1, PeriodSetting.year == year, PeriodSetting.month == month).delete()
        db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 30)).delete()
        
        # Set collector party = BAYI
        setting = PeriodSetting(
            branch_id=1,
            year=year,
            month=month,
            collector_party="BAYI",
            vat_rate=Decimal("0.20")
        )
        db.add(setting)

        # Add transaction
        tx = Transaction(
            branch_id=1,
            department_id=1,
            date=date(year, month, 10),
            customer_name="Fatura Test Müşteri",
            item_name="Genel Hizmet",
            amount_excl_vat=Decimal("100000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("120000.00")
        )
        db.add(tx)
        db.commit()
    finally:
        db.close()

    # Close period
    close_res = client.post("/api/v1/period-closures", json={"year": year, "month": month}, headers=f_headers)
    assert close_res.status_code == 201
    closure_id = close_res.json()["id"]

    # Fetch e-invoice data skeleton
    inv_res = client.get(f"/api/v1/period-closures/{closure_id}/invoice-data", headers=b_headers)
    assert inv_res.status_code == 200
    inv = inv_res.json()

    assert inv["period"] == f"{year}-{month:02d}"
    assert inv["currency"] == "TRY"
    assert "issuer" in inv
    assert "recipient" in inv
    # When Bayi collects, Franchisor bills Bayi for its share
    assert "Franchisor" in inv["issuer"]["title"]
    assert "Kuzey" in inv["recipient"]["title"]
    
    # Check amounts and VAT consistency
    net = Decimal(str(inv["amount_excl_vat"]))
    vat = Decimal(str(inv["vat_amount"]))
    tot = Decimal(str(inv["total_amount_incl_vat"]))
    assert tot == net + vat
    assert len(inv["line_items"]) > 0

    # Check cryptographic audit envelope
    assert "calculation_engine_version" in inv["closure_audit"]
    assert inv["closure_audit"]["input_hash"] is not None
    assert inv["closure_audit"]["result_hash"] is not None

    # Cleanup
    cleanup_db = SessionLocal()
    try:
        cleanup_db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
        cleanup_db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 30)).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()

def test_invoice_data_skeleton_franchisor_collector():
    f_token = get_auth_token("admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {get_bayi_token('bayi_admin')}", "X-Branch-Id": "1"}

    year, month = 2026, 12

    db: Session = SessionLocal()
    try:
        db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
        db.query(PeriodSetting).filter(PeriodSetting.branch_id == 1, PeriodSetting.year == year, PeriodSetting.month == month).delete()
        db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 31)).delete()
        
        # Set collector party = FRANCHISOR
        setting = PeriodSetting(
            branch_id=1,
            year=year,
            month=month,
            collector_party="FRANCHISOR",
            vat_rate=Decimal("0.20")
        )
        db.add(setting)

        # Add transaction
        tx = Transaction(
            branch_id=1,
            department_id=1,
            date=date(year, month, 15),
            customer_name="Fatura Test 2",
            item_name="Genel Hizmet",
            amount_excl_vat=Decimal("50000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("60000.00")
        )
        db.add(tx)
        db.commit()
    finally:
        db.close()

    # Close period
    close_res = client.post("/api/v1/period-closures", json={"year": year, "month": month}, headers=f_headers)
    assert close_res.status_code == 201
    closure_id = close_res.json()["id"]

    # Fetch e-invoice data skeleton
    inv_res = client.get(f"/api/v1/period-closures/{closure_id}/invoice-data", headers=b_headers)
    assert inv_res.status_code == 200
    inv = inv_res.json()

    # When Franchisor collects, Bayi bills Franchisor for its earned share
    assert "Kuzey" in inv["issuer"]["title"]
    assert "Franchisor" in inv["recipient"]["title"]
    assert inv["currency"] == "TRY"

    # Cleanup
    cleanup_db = SessionLocal()
    try:
        cleanup_db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
        cleanup_db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 31)).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()
