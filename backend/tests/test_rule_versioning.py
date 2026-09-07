import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.branch import Branch
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.role import Role
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.transaction_category import TransactionCategory
from backend.app.models.rule_change_log import RuleChangeLog

from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def test_commission_tier_versioning_and_history():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "X-Branch-Id": "1"}
    today = date.today()

    # 1. Fetch current commission tiers
    res = client.get("/api/v1/commission-tiers", headers=headers)
    assert res.status_code == 200
    tiers = res.json()
    assert len(tiers) > 0
    first_tier = tiers[0]
    tier_id = first_tier["id"]
    old_rate = first_tier["rate"]
    new_rate = "0.075" if old_rate != "0.075" else "0.085"

    # 2. Update tier
    update_res = client.put(
        f"/api/v1/commission-tiers/{tier_id}",
        json={
            "min_amount": first_tier["min_amount"],
            "max_amount": first_tier["max_amount"],
            "rate": new_rate,
            "change_reason": "2026 Q3 oran güncellemesi"
        },
        headers=headers
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    new_tier_id = updated_data["id"]

    # Verify old tier row was NOT overwritten, but closed with effective_to
    db: Session = SessionLocal()
    try:
        old_row = db.query(CommissionTier).filter(CommissionTier.id == tier_id).first()
        assert old_row is not None
        assert old_row.effective_to == today
        assert str(old_row.rate) == str(Decimal(old_rate))

        # Verify new tier row has effective_from = today and effective_to = None
        new_row = db.query(CommissionTier).filter(CommissionTier.id == new_tier_id).first()
        assert new_row is not None
        assert new_row.effective_from == today
        assert new_row.effective_to is None
        assert Decimal(str(new_row.rate)) == Decimal(new_rate)

        # Verify rule change log was recorded
        log = db.query(RuleChangeLog).filter(
            RuleChangeLog.rule_type == "COMMISSION_TIER",
            RuleChangeLog.entity_id == new_tier_id
        ).first()
        assert log is not None
        assert "oran" in (log.description or "").lower() or log.old_values is not None
    finally:
        db.close()

    # 3. Verify history endpoint
    hist_res = client.get("/api/v1/commission-tiers/history", headers=headers)
    assert hist_res.status_code == 200
    hist_logs = hist_res.json()
    assert any(l["rule_type"] == "COMMISSION_TIER" and l["entity_id"] == new_tier_id for l in hist_logs)

def test_category_override_versioning():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "X-Branch-Id": "1"}
    today = date.today()

    # 1. Fetch categories
    res = client.get("/api/v1/categories", headers=headers)
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) > 0
    cat = cats[0]
    cat_id = cat["id"]

    old_gen = Decimal(str(cat.get("general_override_rate") or "0.00"))
    old_bon = Decimal(str(cat.get("bonus_override_rate") or "0.00"))
    new_gen = str((old_gen + Decimal("0.02")) if old_gen < Decimal("0.30") else Decimal("0.05"))
    new_bon = str((old_bon + Decimal("0.01")) if old_bon < Decimal("0.15") else Decimal("0.03"))

    # 2. Update category override
    update_res = client.put(
        f"/api/v1/categories/{cat_id}",
        json={
            "general_override_rate": new_gen,
            "bonus_override_rate": new_bon,
            "change_reason": "Özel kategori oran revizyonu"
        },
        headers=headers
    )
    assert update_res.status_code == 200
    new_cat_data = update_res.json()
    new_cat_id = new_cat_data["id"]

    # Verify database state
    db: Session = SessionLocal()
    try:
        old_cat = db.query(TransactionCategory).filter(TransactionCategory.id == cat_id).first()
        assert old_cat.effective_to == today

        new_cat = db.query(TransactionCategory).filter(TransactionCategory.id == new_cat_id).first()
        assert new_cat.effective_from == today
        assert new_cat.effective_to is None
        assert Decimal(str(new_cat.general_override_rate)) == Decimal(new_gen)
        assert Decimal(str(new_cat.bonus_override_rate)) == Decimal(new_bon)
    finally:
        db.close()

    # 3. Category history endpoint
    hist_res = client.get("/api/v1/categories/history", headers=headers)
    assert hist_res.status_code == 200
    logs = hist_res.json()
    assert any(l["rule_type"] == "CATEGORY_OVERRIDE" for l in logs)
