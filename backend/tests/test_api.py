import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_unauthorized_access():
    response = client.get("/api/v1/departments")
    assert response.status_code == 401

def test_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"

def test_login_invalid():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.fixture
def auth_headers():
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_list_departments(auth_headers):
    response = client.get("/api/v1/departments", headers=auth_headers)
    assert response.status_code == 200
    depts = response.json()
    assert isinstance(depts, list)
    assert len(depts) >= 1

def test_list_commission_tiers(auth_headers):
    response = client.get("/api/v1/commission-tiers", headers=auth_headers)
    assert response.status_code == 200
    tiers = response.json()
    assert isinstance(tiers, list)
    assert len(tiers) >= 2

def test_list_transactions_with_masking(auth_headers):
    response = client.get("/api/v1/transactions", headers=auth_headers)
    assert response.status_code == 200
    txs = response.json()
    assert isinstance(txs, list)
    assert len(txs) > 0
    sample_tx = next((t for t in txs if t.get("customer_tax_id_masked")), None)
    if not sample_tx:
        # Create a sample transaction with tax id
        post_res = client.post(
            "/api/v1/transactions",
            json={
                "date": "2026-09-01",
                "department_id": 1,
                "customer_name": "Maskeleme Test",
                "customer_tax_id": "12345678901",
                "item_name": "Test Kalemi",
                "amount_excl_vat": "100.00",
                "vat_rate": "0.20",
                "amount_incl_vat": "120.00"
            },
            headers=auth_headers
        )
        sample_tx = post_res.json()

    # KVKK Veri Minimizasyonu: Standart API çıktısında açık customer_tax_id bulunmamalıdır
    assert "customer_tax_id" not in sample_tx
    assert sample_tx.get("customer_tax_id_masked") is not None
    assert "*" in sample_tx.get("customer_tax_id_masked")

    # Yetkili kullanıcı /sensitive endpoint'inden açık TCKN'yi alabilir
    sens_res = client.get(f"/api/v1/transactions/{sample_tx['id']}/sensitive", headers=auth_headers)
    assert sens_res.status_code == 200
    sens_data = sens_res.json()
    assert "customer_tax_id" in sens_data
    assert len(sens_data["customer_tax_id"]) in (10, 11)

def test_reconciliation_report_bayi_collector(auth_headers):
    # Test for September 2026
    response = client.get(
        "/api/v1/reconciliation?year=2026&month=9&collector_party=BAYI",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2026
    assert data["month"] == 9
    assert "total_turnover_excl_vat" in data
    assert "applied_tier" in data
    assert data["invoice_summary"]["issuer"] == "Franchisor (Merkez)"
    assert data["invoice_summary"]["recipient"] == "Bayi"

def test_reconciliation_report_franchisor_collector(auth_headers):
    # Test for September 2026 with Franchisor collector
    response = client.get(
        "/api/v1/reconciliation?year=2026&month=9&collector_party=FRANCHISOR",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["invoice_summary"]["issuer"] == "Bayi"
    assert data["invoice_summary"]["recipient"] == "Franchisor (Merkez)"

def test_reconciliation_export_excel(auth_headers):
    response = client.get(
        "/api/v1/reconciliation/export?year=2026&month=9&collector_party=BAYI",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert len(response.content) > 1000

def test_period_setting_persistence_in_db(auth_headers):
    # 1. Update period setting for October 2026 to FRANCHISOR
    put_res = client.put(
        "/api/v1/reconciliation/setting",
        json={
            "year": 2026,
            "month": 10,
            "collector_party": "FRANCHISOR",
            "vat_rate": 0.20
        },
        headers=auth_headers
    )
    assert put_res.status_code == 200
    assert put_res.json()["collector_party"] == "FRANCHISOR"

    # 2. Query reconciliation without specifying collector_party
    get_res = client.get(
        "/api/v1/reconciliation?year=2026&month=10",
        headers=auth_headers
    )
    assert get_res.status_code == 200
    data = get_res.json()
    # It must return the saved FRANCHISOR setting from the database!
    assert data["invoice_summary"]["collector_party"] == "FRANCHISOR"
    assert data["invoice_summary"]["issuer"] == "Bayi"
    assert data["is_setting_persisted"] is True

