import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def franchisor_token():
    return create_access_token({"sub": "admin"})

@pytest.fixture
def bayi_token():
    return create_access_token({"sub": "bayi_admin"})

def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}

def test_franchisor_dashboard_multi_branch_comparison(franchisor_token):
    """
    Franchisor Dashboard:
    - Birden fazla bayinin seçilen dönemdeki cirosunu ve paylarını karşılaştırmalı gösterir.
    - Bayiler ciro büyüklüğüne göre azalan sırada sıralanır.
    """
    res = client.get("/api/v1/dashboard/franchisor?year=2026&month=9", headers=auth_header(franchisor_token))
    assert res.status_code == 200
    data = res.json()

    assert data["year"] == 2026
    assert data["month"] == 9
    assert "totals" in data
    assert "branches" in data

    totals = data["totals"]
    assert totals["total_branches"] >= 2
    assert Decimal(str(totals["total_turnover"])) > 0
    assert Decimal(str(totals["total_franchisor_share"])) > 0
    assert Decimal(str(totals["total_bayi_share"])) > 0

    branches = data["branches"]
    assert len(branches) >= 2

    # Verify descending sort order by turnover
    turnovers = [Decimal(str(b["total_turnover"])) for b in branches]
    assert turnovers == sorted(turnovers, reverse=True), "Bayiler ciroya göre azalan sıralı olmalıdır."

    # Verify branch fields
    for b in branches:
        assert b["branch_id"] is not None
        assert b["branch_name"]
        assert "collector_party" in b
        assert "invoice_direction" in b
        assert "invoice_net_payable" in b

def test_branch_dashboard_metrics(bayi_token):
    """
    Bayi Dashboard:
    - Kendi bayisinin son 6 dönemlik ciro trendini (çizgi grafik verisi)
    - Departman kırılımını (pasta/bar grafik verisi)
    - En yüksek prim alan ilk 5 personel listesini sunar
    """
    res = client.get("/api/v1/dashboard/branch?year=2026&month=9", headers=auth_header(bayi_token))
    assert res.status_code == 200
    data = res.json()

    # 1. Summary
    summary = data["summary"]
    assert summary["branch_id"] == 1
    assert Decimal(str(summary["total_turnover"])) > 0
    assert Decimal(str(summary["franchisor_share"])) > 0
    assert Decimal(str(summary["bayi_share"])) > 0
    assert "net_bayi_margin" in summary

    # 2. Monthly Trends (length 6)
    trends = data["monthly_trends"]
    assert len(trends) == 6
    assert trends[-1]["period"] == "2026-09"
    for t in trends:
        assert "turnover" in t
        assert "franchisor_share" in t
        assert "bayi_share" in t
        assert "transaction_count" in t

    # 3. Department Breakdown
    departments = data["department_breakdown"]
    assert len(departments) > 0
    total_pct = sum(Decimal(str(d["percentage"])) for d in departments)
    assert 99.0 <= total_pct <= 101.0

    # 4. Top 5 Bonus Employees
    top_bonus = data["top_bonus_employees"]
    assert len(top_bonus) <= 5
    for idx, emp in enumerate(top_bonus, start=1):
        assert emp["rank"] == idx
        assert emp["employee_name"]
        assert emp["role_name"]
        assert Decimal(str(emp["bonus_amount"])) >= 0
