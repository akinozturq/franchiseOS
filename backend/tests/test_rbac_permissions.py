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
def bayi_admin_token():
    return create_access_token({"sub": "bayi_admin"})

@pytest.fixture
def viewer_token():
    return create_access_token({"sub": "viewer"})

def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}

# ==========================================
# 1. BAYI_ADMIN RESTRICTIONS (403 FORBIDDEN)
# ==========================================

def test_bayi_admin_cannot_mutate_commission_tiers(bayi_admin_token):
    """Bayi Admin komisyon dilimlerini görebilir ama ekleyemez/değiştiremez/silemez (403)."""
    headers = auth_header(bayi_admin_token)

    # GET is allowed
    res_get = client.get("/api/v1/commission-tiers", headers=headers)
    assert res_get.status_code == 200

    # POST tier -> 403
    res_post = client.post("/api/v1/commission-tiers", headers=headers, json={
        "min_amount": 1000000,
        "max_amount": None,
        "rate": 0.40
    })
    assert res_post.status_code == 403
    assert "yetkiniz bulunmamaktadır" in res_post.json()["detail"].lower()

    # PUT tier -> 403
    res_put = client.put("/api/v1/commission-tiers/1", headers=headers, json={"rate": 0.50})
    assert res_put.status_code == 403

    # DELETE tier -> 403
    res_del = client.delete("/api/v1/commission-tiers/1", headers=headers)
    assert res_del.status_code == 403

    # BATCH PUT -> 403
    res_batch = client.put("/api/v1/commission-tiers/batch/save", headers=headers, json={"tiers": []})
    assert res_batch.status_code == 403

def test_bayi_admin_cannot_mutate_categories(bayi_admin_token):
    """Bayi Admin kategorileri görebilir ama ekleyemez/değiştiremez/silemez (403)."""
    headers = auth_header(bayi_admin_token)

    # GET is allowed
    res_get = client.get("/api/v1/categories", headers=headers)
    assert res_get.status_code == 200

    # POST category -> 403
    res_post = client.post("/api/v1/categories", headers=headers, json={
        "name": "Yeni Kategori",
        "general_override_rate": 0.10,
        "is_active": True
    })
    assert res_post.status_code == 403

    # PUT category -> 403
    res_put = client.put("/api/v1/categories/1", headers=headers, json={"name": "Hacked"})
    assert res_put.status_code == 403

    # DELETE category -> 403
    res_del = client.delete("/api/v1/categories/1", headers=headers)
    assert res_del.status_code == 403

def test_bayi_admin_cannot_mutate_roles(bayi_admin_token):
    """Bayi Admin rolleri görebilir ama ekleyemez/değiştiremez/silemez (403)."""
    headers = auth_header(bayi_admin_token)

    # GET is allowed
    res_get = client.get("/api/v1/roles", headers=headers)
    assert res_get.status_code == 200

    # POST role -> 403
    res_post = client.post("/api/v1/roles", headers=headers, json={
        "name": "Yeni Rol",
        "turnover_source": "kendi_islemleri",
        "is_active": True
    })
    assert res_post.status_code == 403

    # PUT role -> 403
    res_put = client.put("/api/v1/roles/1", headers=headers, json={"name": "Hacked Role"})
    assert res_put.status_code == 403

    # DELETE role -> 403
    res_del = client.delete("/api/v1/roles/1", headers=headers)
    assert res_del.status_code == 403

    # POST role commission tier -> 403 (Bayi Admin cannot change bonus percentage tiers)
    res_tier_post = client.post("/api/v1/roles/1/tiers", headers=headers, json={
        "min_amount": 0,
        "max_amount": 100000,
        "rate": 0.15
    })
    assert res_tier_post.status_code == 403
    assert "yetkiniz bulunmamaktadır" in res_tier_post.json()["detail"].lower()

    # DELETE role commission tier -> 403
    res_tier_del = client.delete("/api/v1/roles/1/tiers/1", headers=headers)
    assert res_tier_del.status_code == 403
    assert "yetkiniz bulunmamaktadır" in res_tier_del.json()["detail"].lower()

def test_bayi_admin_cannot_access_other_branch(bayi_admin_token):
    """Bayi Admin (Branch 1) başka bir bayiye (Branch 2) istek atarsa 403 engellenmeli."""
    headers = auth_header(bayi_admin_token)

    # Attempt to query branch 2
    res = client.get("/api/v1/transactions?branch_id=2", headers=headers)
    assert res.status_code == 403
    assert "yetkiniz yoktur" in res.json()["detail"].lower()

def test_bayi_admin_cannot_manage_users(bayi_admin_token):
    """Bayi Admin kullanıcı yönetimi endpoint'lerine erişemez (403)."""
    headers = auth_header(bayi_admin_token)

    res_get = client.get("/api/v1/users", headers=headers)
    assert res_get.status_code == 403

    res_post = client.post("/api/v1/users", headers=headers, json={
        "username": "new_user",
        "password": "password123",
        "role": "BAYI_ADMIN"
    })
    assert res_post.status_code == 403

def test_bayi_admin_cannot_view_franchisor_dashboard(bayi_admin_token):
    """Bayi Admin çoklu bayi franchisor dashboard'unu göremez (403)."""
    headers = auth_header(bayi_admin_token)
    res = client.get("/api/v1/dashboard/franchisor?year=2024&month=1", headers=headers)
    assert res.status_code == 403

# ==========================================
# 2. BAYI_ADMIN ALLOWED OPERATIONAL ACTIONS
# ==========================================

def test_bayi_admin_can_perform_operational_tasks(bayi_admin_token):
    """Bayi Admin kendi bayisi için işlem ve personel oluşturabilir."""
    headers = auth_header(bayi_admin_token)

    # 1. Create transaction
    tx_res = client.post("/api/v1/transactions", headers=headers, json={
        "department_id": 1,
        "date": "2024-01-28",
        "customer_name": "Test Müşteri BayiAdmin",
        "item_name": "Seramik Kaplama",
        "amount_excl_vat": 15000.0,
        "vat_rate": 0.20,
        "amount_incl_vat": 18000.0,
        "payment_method": "Kredi Kartı",
        "invoice_status": "Faturalandı"
    })
    assert tx_res.status_code == 201
    tx_id = tx_res.json()["id"]

    # 2. Clean up created transaction
    del_res = client.delete(f"/api/v1/transactions/{tx_id}", headers=headers)
    assert del_res.status_code == 200

    # 3. Can view branch dashboard
    dash_res = client.get("/api/v1/dashboard/branch?year=2024&month=1", headers=headers)
    assert dash_res.status_code == 200

# ==========================================
# 3. VIEWER RESTRICTIONS (READ-ONLY)
# ==========================================

def test_viewer_is_strictly_read_only(viewer_token):
    """Viewer hiçbir mutating (POST/PUT/DELETE) işlem yapamaz (403)."""
    headers = auth_header(viewer_token)

    # Reads are 200 OK
    assert client.get("/api/v1/transactions", headers=headers).status_code == 200
    assert client.get("/api/v1/reconciliation?year=2024&month=1", headers=headers).status_code == 200
    assert client.get("/api/v1/bonus?year=2024&month=1", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/branch?year=2024&month=1", headers=headers).status_code == 200

    # Mutations are 403 Forbidden
    res_tx = client.post("/api/v1/transactions", headers=headers, json={
        "department_id": 1,
        "date": "2024-01-28",
        "customer_name": "Viewer Post",
        "item_name": "Test",
        "amount_excl_vat": 1000.0,
        "vat_rate": 0.20,
        "amount_incl_vat": 1200.0,
        "payment_method": "Nakit",
        "invoice_status": "Faturalandı"
    })
    assert res_tx.status_code == 403

    res_emp = client.post("/api/v1/employees", headers=headers, json={
        "role_id": 1,
        "department_id": 1,
        "full_name": "Viewer Emp",
        "is_active": True
    })
    assert res_emp.status_code == 403

    res_setting = client.put("/api/v1/reconciliation/setting", headers=headers, json={
        "year": 2024,
        "month": 1,
        "collector_party": "BAYI",
        "vat_rate": 0.20
    })
    assert res_setting.status_code == 403

# ==========================================
# 4. FRANCHISOR_ADMIN FULL CAPABILITIES
# ==========================================

def test_franchisor_admin_has_full_access(franchisor_token):
    """Franchisor Admin tüm bayileri, kuralları, kullanıcıları ve dashboard'ları yönetebilir."""
    headers = auth_header(franchisor_token)

    # Can list users
    users_res = client.get("/api/v1/users", headers=headers)
    assert users_res.status_code == 200
    assert len(users_res.json()) >= 3

    # Can list branches
    branches_res = client.get("/api/v1/branches", headers=headers)
    assert branches_res.status_code == 200
    assert len(branches_res.json()) >= 2

    # Can view Franchisor Dashboard
    dash_res = client.get("/api/v1/dashboard/franchisor?year=2024&month=1", headers=headers)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert "branches" in data
    assert "totals" in data
    assert data["totals"]["total_branches"] >= 2
