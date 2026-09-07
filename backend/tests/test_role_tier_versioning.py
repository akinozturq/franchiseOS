import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.role import Role
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.rule_change_log import RuleChangeLog
from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def test_role_tier_versioning_and_audit_log():
    f_token = get_auth_token("admin")
    f_headers = {"Authorization": f"Bearer {f_token}", "X-Branch-Id": "1"}
    today = date.today()

    # 1. Fetch Role 1
    roles_res = client.get("/api/v1/roles", headers=f_headers)
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) > 0
    role_id = roles[0]["id"]

    # 2. Add a new tier to Role 1
    add_tier_res = client.post(
        f"/api/v1/roles/{role_id}/tiers",
        json={
            "min_amount": "800000.00",
            "max_amount": "1200000.00",
            "rate": "0.085"
        },
        headers=f_headers
    )
    assert add_tier_res.status_code == 201
    created_tier = add_tier_res.json()
    tier_id = created_tier["id"]

    db: Session = SessionLocal()
    try:
        # Verify in DB: effective_from is today, effective_to is None
        tier_row = db.query(RoleCommissionTier).filter(RoleCommissionTier.id == tier_id).first()
        assert tier_row is not None
        assert tier_row.effective_from == today
        assert tier_row.effective_to is None
        assert Decimal(str(tier_row.rate)) == Decimal("0.085")

        # Verify RuleChangeLog entry created
        log = db.query(RuleChangeLog).filter(
            RuleChangeLog.rule_type == "ROLE_TIER",
            RuleChangeLog.entity_id == role_id,
            RuleChangeLog.action == "ADD_TIER"
        ).order_by(RuleChangeLog.id.desc()).first()
        assert log is not None
        assert log.new_values is not None
        assert Decimal(str(log.new_values["rate"])) == Decimal("0.085")
    finally:
        db.close()

    # 3. Delete the tier -> verify it is versioned closed (effective_to = today)
    del_res = client.delete(f"/api/v1/roles/{role_id}/tiers/{tier_id}", headers=f_headers)
    assert del_res.status_code in [200, 204]

    db = SessionLocal()
    try:
        deleted_row = db.query(RoleCommissionTier).filter(RoleCommissionTier.id == tier_id).first()
        assert deleted_row is not None
        assert deleted_row.effective_to == today

        # Verify RuleChangeLog has DELETE_TIER action
        del_log = db.query(RuleChangeLog).filter(
            RuleChangeLog.rule_type == "ROLE_TIER",
            RuleChangeLog.entity_id == role_id,
            RuleChangeLog.action == "DELETE_TIER"
        ).order_by(RuleChangeLog.id.desc()).first()
        assert del_log is not None
    finally:
        db.close()

    # 4. Verify history endpoint
    hist_res = client.get(f"/api/v1/roles/{role_id}/history", headers=f_headers)
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) >= 2
    actions = [h["action"] for h in hist]
    assert "ADD_TIER" in actions
    assert "DELETE_TIER" in actions
