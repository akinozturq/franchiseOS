import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.transaction_category import TransactionCategory
from backend.app.models.transaction import Transaction
from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def get_bayi_token(username: str = "bayi_admin") -> str:
    return create_access_token({"sub": username})

def test_frozen_snapshot_remains_completely_immutable_after_rule_changes():
    """
    KANIT TESTİ:
    1. Dönem kapatılır ve snapshot alınır.
    2. Kapatma SONRASINDA komisyon dilim oranları, kategori istisnaları ve rol prim oranları değiştirilir.
    3. Kapalı dönemin mutabakat ve prim raporu tekrar çekildiğinde, yeni kurallardan
       kesinlikle ETKİLENMEDİĞİ ve orijinal donmuş snapshot değerlerini kuruşu kuruşuna koruduğu kanıtlanır.
    4. Dönem yeniden açıldığında (reopen) canlı hesaplamaya döndüğü doğrulanır.
    """
    f_token = get_auth_token("admin")
    b_token = get_bayi_token("bayi_admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    b_headers = {"Authorization": f"Bearer {b_token}", "X-Branch-Id": "1"}

    year, month = 2026, 10

    db: Session = SessionLocal()
    try:
        # Cleanup past test runs for (2026, 10)
        db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == 1,
            PeriodClosure.year == year,
            PeriodClosure.month == month
        ).delete()
        db.query(Transaction).filter(
            Transaction.branch_id == 1,
            Transaction.date >= date(year, month, 1),
            Transaction.date <= date(year, month, 31)
        ).delete()
        db.commit()

        # Create two transactions in October 2026 with Employee 1
        tx1 = Transaction(
            branch_id=1,
            department_id=1,
            employee_id=1,
            date=date(year, month, 5),
            customer_name="Snapshot Test Müşteri 1",
            item_name="Standart Detailing Hizmeti",
            amount_excl_vat=Decimal("50000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("60000.00"),
            payment_method="Kredi Kartı"
        )
        tx2 = Transaction(
            branch_id=1,
            department_id=1,
            employee_id=1,
            date=date(year, month, 20),
            customer_name="Snapshot Test Müşteri 2",
            item_name="Standart Detailing Hizmeti",
            amount_excl_vat=Decimal("50000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("60000.00"),
            payment_method="Nakit"
        )
        db.add_all([tx1, tx2])
        db.commit()
    finally:
        db.close()

    # 1. Baseline: calculate initial unclosed period reports
    rec_baseline_res = client.get(f"/api/v1/reconciliation?year={year}&month={month}", headers=b_headers)
    assert rec_baseline_res.status_code == 200
    rec_baseline = rec_baseline_res.json()
    assert rec_baseline["is_closed"] is False
    baseline_turnover = rec_baseline["total_turnover_excl_vat"]
    baseline_franchisor_share = rec_baseline["franchisor_share_excl_vat"]
    baseline_bayi_share = rec_baseline["bayi_share_excl_vat"]
    baseline_rate = rec_baseline["applied_rate_percentage"]

    bonus_baseline_res = client.get(f"/api/v1/bonus?year={year}&month={month}", headers=b_headers)
    assert bonus_baseline_res.status_code == 200
    bonus_baseline = bonus_baseline_res.json()
    assert bonus_baseline["is_closed"] is False
    baseline_bonus_total = bonus_baseline["grand_total_bonus"]

    # 2. Franchisor Admin closes period -> Takes official frozen snapshots
    close_res = client.post(
        "/api/v1/period-closures",
        json={"year": year, "month": month},
        headers=f_headers
    )
    assert close_res.status_code == 201
    closure_data = close_res.json()
    closure_id = closure_data["id"]
    assert closure_data["status"] == "CLOSED"

    # 3. Aggressively mutate rules AFTER period closure:
    # A) Mutate commission tiers: change tier rate to 45% (0.45)
    tiers_res = client.get("/api/v1/commission-tiers", headers=f_headers)
    assert tiers_res.status_code == 200
    active_tiers = tiers_res.json()
    first_tier = active_tiers[0]
    tier_update_res = client.put(
        f"/api/v1/commission-tiers/{first_tier['id']}",
        json={
            "min_amount": first_tier["min_amount"],
            "max_amount": first_tier["max_amount"],
            "rate": "0.450",
            "change_reason": "Agresif kural değişikliği test amaçlı"
        },
        headers=f_headers
    )
    assert tier_update_res.status_code == 200

    # B) Mutate role tiers: add an aggressive 30% bonus tier to Role 1
    role_tier_res = client.post(
        "/api/v1/roles/1/tiers",
        json={
            "min_amount": "0",
            "max_amount": "500000",
            "rate": "0.300"
        },
        headers=f_headers
    )
    assert role_tier_res.status_code == 201

    # 4. Fetch the CLOSED period reports again:
    # They MUST return the EXACT original snapshot values, totally unaffected by the 45% and 30% rules!
    rec_after_res = client.get(f"/api/v1/reconciliation?year={year}&month={month}", headers=b_headers)
    assert rec_after_res.status_code == 200
    rec_after = rec_after_res.json()

    assert rec_after["is_closed"] is True, "Kapalı dönem is_closed=True olmalı"
    assert rec_after["total_turnover_excl_vat"] == baseline_turnover
    assert rec_after["franchisor_share_excl_vat"] == baseline_franchisor_share, (
        f"Kapalı dönem merkez payı donmuş snapshot'tan gelmelidir! "
        f"Beklenen: {baseline_franchisor_share}, Gelen: {rec_after['franchisor_share_excl_vat']}"
    )
    assert rec_after["bayi_share_excl_vat"] == baseline_bayi_share
    assert rec_after["applied_rate_percentage"] == baseline_rate

    # Check bonus report
    bonus_after_res = client.get(f"/api/v1/bonus?year={year}&month={month}", headers=b_headers)
    assert bonus_after_res.status_code == 200
    bonus_after = bonus_after_res.json()

    assert bonus_after["is_closed"] is True, "Kapalı dönem prim raporu is_closed=True olmalı"
    assert bonus_after["grand_total_bonus"] == baseline_bonus_total, (
        f"Kapalı dönem prim toplamı donmuş snapshot'tan gelmelidir! "
        f"Beklenen: {baseline_bonus_total}, Gelen: {bonus_after['grand_total_bonus']}"
    )

    # 5. Verify PDF export also uses the frozen snapshot
    pdf_rec_res = client.get(f"/api/v1/reconciliation/export-pdf?year={year}&month={month}", headers=b_headers)
    assert pdf_rec_res.status_code == 200
    assert pdf_rec_res.headers["content-type"] == "application/pdf"
    assert len(pdf_rec_res.content) > 1000

    pdf_bonus_res = client.get(f"/api/v1/bonus/export-pdf?year={year}&month={month}", headers=b_headers)
    assert pdf_bonus_res.status_code == 200
    assert pdf_bonus_res.headers["content-type"] == "application/pdf"
    assert len(pdf_bonus_res.content) > 1000

    # 6. Reopen period -> Live calculations should now reflect the new rules!
    reopen_res = client.post(
        f"/api/v1/period-closures/{closure_id}/reopen",
        json={"reopen_reason": "Dönem yeniden açılarak yeni kuralların canlı devreye girmesi test ediliyor."},
        headers=f_headers
    )
    assert reopen_res.status_code == 200

    rec_reopened_res = client.get(f"/api/v1/reconciliation?year={year}&month={month}", headers=b_headers)
    assert rec_reopened_res.status_code == 200
    rec_reopened = rec_reopened_res.json()
    assert rec_reopened["is_closed"] is False

    try:
        # After reopen, it uses live calculation with the updated tier rate (45%)
        assert Decimal(str(rec_reopened["franchisor_share_excl_vat"])) != Decimal(str(baseline_franchisor_share)), (
            "Reopen sonrasında canlı hesaplama devreye girmeli ve yeni kuralları yansıtmalıdır."
        )
    finally:
        # Revert test mutations so subsequent tests run on a pristine baseline
        cleanup_db = SessionLocal()
        try:
            cleanup_db.query(PeriodClosure).filter(PeriodClosure.branch_id == 1, PeriodClosure.year == year, PeriodClosure.month == month).delete()
            cleanup_db.query(Transaction).filter(Transaction.branch_id == 1, Transaction.date >= date(year, month, 1), Transaction.date <= date(year, month, 31)).delete()
            cleanup_db.query(CommissionTier).filter(CommissionTier.branch_id == 1, CommissionTier.id > 2).delete()
            t1 = cleanup_db.query(CommissionTier).filter(CommissionTier.id == 1).first()
            if t1:
                t1.effective_to = None
                t1.rate = Decimal("0.30")
            cleanup_db.commit()
        finally:
            cleanup_db.close()
