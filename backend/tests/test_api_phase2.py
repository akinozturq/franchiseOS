import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import get_db, SessionLocal
from backend.app.models.branch import Branch
from backend.app.models.role import Role
from backend.app.models.employee import Employee
from backend.app.models.transaction_category import TransactionCategory

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_roles_crud_and_tiers(client, auth_headers):
    # 1. List roles
    res = client.get("/api/v1/roles", headers=auth_headers)
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) >= 1
    role_names = [r["name"] for r in roles]
    assert "Genel Müdür" in role_names
    assert "Satış Danışmanı" in role_names

    # 2. Create custom role
    new_role_payload = {
        "name": "Test Uzmanı",
        "turnover_source": "kendi_islemleri",
        "is_active": True,
        "tiers": [
            {"min_amount": 0, "max_amount": 100000, "rate": 0.05},
            {"min_amount": 100000.01, "max_amount": None, "rate": 0.08}
        ]
    }
    create_res = client.post("/api/v1/roles", json=new_role_payload, headers=auth_headers)
    assert create_res.status_code == 201
    created_role = create_res.json()
    assert created_role["name"] == "Test Uzmanı"
    assert len(created_role["commission_tiers"]) == 2
    role_id = created_role["id"]

    # 3. Get single role
    get_res = client.get(f"/api/v1/roles/{role_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Uzmanı"

    # 4. Update role
    upd_res = client.put(f"/api/v1/roles/{role_id}", json={"name": "Kıdemli Test Uzmanı"}, headers=auth_headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == "Kıdemli Test Uzmanı"

    # 5. Delete role
    del_res = client.delete(f"/api/v1/roles/{role_id}", headers=auth_headers)
    assert del_res.status_code == 204

def test_categories_crud(client, auth_headers):
    # 1. List categories
    res = client.get("/api/v1/categories", headers=auth_headers)
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) >= 1

    # 2. Create category with overrides
    payload = {
        "name": "Özel Seramik Koruma Pro",
        "general_override_rate": 0.18,
        "bonus_override_rate": 0.08,
        "is_active": True
    }
    c_res = client.post("/api/v1/categories", json=payload, headers=auth_headers)
    assert c_res.status_code == 201
    cat_data = c_res.json()
    assert cat_data["name"] == "Özel Seramik Koruma Pro"
    assert float(cat_data["general_override_rate"]) == 0.18
    assert float(cat_data["bonus_override_rate"]) == 0.08
    cat_id = cat_data["id"]

    # 3. Update category
    u_res = client.put(f"/api/v1/categories/{cat_id}", json={"general_override_rate": 0.20}, headers=auth_headers)
    assert u_res.status_code == 200
    assert float(u_res.json()["general_override_rate"]) == 0.20

    # 4. Delete category
    d_res = client.delete(f"/api/v1/categories/{cat_id}", headers=auth_headers)
    assert d_res.status_code == 204

def test_employees_crud(client, auth_headers):
    # 1. List employees
    res = client.get("/api/v1/employees", headers=auth_headers)
    assert res.status_code == 200
    employees = res.json()
    assert len(employees) >= 1

    # Find a role ID
    roles_res = client.get("/api/v1/roles", headers=auth_headers)
    role_id = roles_res.json()[0]["id"]

    # 2. Create employee
    payload = {
        "full_name": "Test Personel Ali",
        "role_id": role_id,
        "department_id": None,
        "is_active": True
    }
    create_res = client.post("/api/v1/employees", json=payload, headers=auth_headers)
    assert create_res.status_code == 201
    emp = create_res.json()
    assert emp["full_name"] == "Test Personel Ali"
    emp_id = emp["id"]

    # 3. Update employee
    upd_res = client.put(f"/api/v1/employees/{emp_id}", json={"full_name": "Ali Veli Test"}, headers=auth_headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["full_name"] == "Ali Veli Test"

    # 4. Delete employee
    del_res = client.delete(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert del_res.status_code == 204

def test_bonus_report_endpoint(client, auth_headers):
    # January 2024
    res = client.get("/api/v1/bonus?year=2024&month=1", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "2024-01"
    assert "total_employees" in data
    assert "grand_total_bonus" in data
    assert "items" in data
    assert isinstance(data["items"], list)

    # Check export endpoint
    exp_res = client.get("/api/v1/bonus/export?year=2024&month=1", headers=auth_headers)
    assert exp_res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in exp_res.headers["content-type"]
    assert len(exp_res.content) > 1000

def test_transactions_returns_employee_and_category_names(client, auth_headers):
    res = client.get("/api/v1/transactions?limit=10", headers=auth_headers)
    assert res.status_code == 200
    txs = res.json()
    assert len(txs) > 0
    first = txs[0]
    assert "employee_name" in first
    assert "category_name" in first
