import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.transaction import Transaction
from backend.app.models.employee import Employee
from backend.app.models.period_closure import PeriodClosure
from backend.app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def b1_admin_headers():
    """Bayi 1 (Kuzey Bayisi) Yöneticisi"""
    token = create_access_token({"sub": "bayi_admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def franchisor_headers():
    """Genel Merkez Yöneticisi"""
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def b2_sample_data():
    """Bayi 2'ye (Kadıköy) ait örnek işlem ve personel"""
    db: Session = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.branch_id == 2).first()
        if not emp:
            emp = Employee(
                branch_id=2,
                full_name="Kadıköy Personel Test",
                department_id=1,
                role_id=1,
                is_active=True
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)

        tx = db.query(Transaction).filter(Transaction.branch_id == 2).first()
        if not tx:
            tx = Transaction(
                branch_id=2,
                department_id=1,
                employee_id=emp.id,
                date=date(2026, 9, 5),
                customer_name="Kadıköy Gizli Müşteri",
                customer_tax_id="99988877766",
                item_name="Özel PPF Kaplama B2",
                amount_excl_vat=Decimal("50000.00"),
                vat_rate=Decimal("0.20"),
                amount_incl_vat=Decimal("60000.00")
            )
            db.add(tx)
            db.commit()
            db.refresh(tx)

        return {"tx_id": tx.id, "emp_id": emp.id}
    finally:
        db.close()

def test_idor_crafted_header_branch_leak_forbidden(b1_admin_headers):
    """
    Penetrasyon Testi 1:
    Bayi 1 yöneticisi, X-Branch-Id: 2 header'ı göndererek Bayi 2'nin işlemlerini
    listelemeye çalışırsa sistem 403 Forbidden döndürmelidir.
    """
    res = client.get(
        "/api/v1/transactions",
        headers={**b1_admin_headers, "X-Branch-Id": "2"}
    )
    assert res.status_code == 403
    assert "farklı bir bayi" in res.json()["detail"].lower()

def test_idor_query_parameter_branch_leak_forbidden(b1_admin_headers):
    """
    Penetrasyon Testi 2:
    Bayi 1 yöneticisi, ?branch_id=2 parametresi ile Bayi 2'nin işlemlerini
    çekmeye çalışırsa sistem 403 Forbidden döndürmelidir.
    """
    res = client.get(
        "/api/v1/transactions?branch_id=2",
        headers=b1_admin_headers
    )
    assert res.status_code == 403
    assert "farklı bir bayi" in res.json()["detail"].lower()

def test_idor_direct_transaction_lookup_prevented(b1_admin_headers, b2_sample_data):
    """
    Penetrasyon Testi 3 (Direct Object Reference):
    Bayi 1 yöneticisi, Bayi 2'ye ait transaction ID'sini doğrudan GET /transactions/{id}
    ile sorgularsa 404 Not Found dönmeli; veri kesinlikle sızmamalıdır.
    """
    b2_tx_id = b2_sample_data["tx_id"]
    res = client.get(
        f"/api/v1/transactions/{b2_tx_id}",
        headers=b1_admin_headers
    )
    assert res.status_code == 404
    assert "bulunamadı" in res.json()["detail"].lower()

def test_idor_sensitive_tax_id_cross_branch_lookup_prevented(b1_admin_headers, b2_sample_data):
    """
    Penetrasyon Testi 4 (Sensitive Data IDOR):
    Bayi 1 yöneticisi, Bayi 2'ye ait transaction ID'sini GET /transactions/{id}/sensitive
    ile sorgulayıp açık TCKN/VKN çekmeye çalışırsa 404 Not Found dönmelidir.
    """
    b2_tx_id = b2_sample_data["tx_id"]
    res = client.get(
        f"/api/v1/transactions/{b2_tx_id}/sensitive",
        headers=b1_admin_headers
    )
    assert res.status_code == 404

def test_idor_cross_branch_employee_assignment_prevented(b1_admin_headers, b2_sample_data):
    """
    Penetrasyon Testi 5 (Cross-Tenant Mutation):
    Bayi 1 yöneticisi, Bayi 2'ye ait bir işlemi kendi personeline bağlamaya çalışırsa
    işlem güncellenmemeli (updated_count = 0).
    """
    db = SessionLocal()
    try:
        b1_emp = db.query(Employee).filter(Employee.branch_id == 1).first()
        b2_tx_id = b2_sample_data["tx_id"]

        res = client.post(
            "/api/v1/employees/assign-transactions",
            json={"transaction_ids": [b2_tx_id], "employee_id": b1_emp.id},
            headers=b1_admin_headers
        )
        assert res.status_code == 200
        assert res.json()["updated_count"] == 0

        # Doğrula: Bayi 2 transaction'ı hala Bayi 2'ye ve eski personeline ait
        tx_check = db.query(Transaction).filter(Transaction.id == b2_tx_id).first()
        assert tx_check.branch_id == 2
        assert tx_check.employee_id != b1_emp.id
    finally:
        db.close()

def test_idor_cross_branch_employee_profile_lookup_prevented(b1_admin_headers, b2_sample_data):
    """
    Penetrasyon Testi 6:
    Bayi 1 yöneticisi, Bayi 2'ye ait bir personelin profilini GET /employees/{id} ile
    görmeye çalışırsa 404 Not Found dönmelidir.
    """
    b2_emp_id = b2_sample_data["emp_id"]
    res = client.get(
        f"/api/v1/employees/{b2_emp_id}",
        headers=b1_admin_headers
    )
    assert res.status_code == 404

def test_idor_cross_branch_period_closure_request_forbidden(b1_admin_headers):
    """
    Penetrasyon Testi 7:
    Bayi 1 yöneticisi, Bayi 2 için dönem kapatma talebi göndermeye çalışırsa
    (X-Branch-Id: 2) 403 Forbidden ile reddedilmelidir.
    """
    res = client.post(
        "/api/v1/period-closures/request",
        json={"year": 2026, "month": 8},
        headers={**b1_admin_headers, "X-Branch-Id": "2"}
    )
    assert res.status_code == 403

def test_idor_cross_branch_reconciliation_export_forbidden(b1_admin_headers):
    """
    Penetrasyon Testi 8:
    Bayi 1 yöneticisi, Bayi 2'nin mutabakat raporunu ihraç etmeye çalışırsa
    (GET /reconciliation/export?year=2026&month=9&branch_id=2) 403 Forbidden dönmelidir.
    """
    res = client.get(
        "/api/v1/reconciliation/export?year=2026&month=9&branch_id=2",
        headers=b1_admin_headers
    )
    assert res.status_code == 403

def test_financial_rounding_consistency_invariant():
    """
    Finansal Yuvarlama Tutarlılığı:
    quantize_money(amount) standardının ROUND_HALF_UP ve 2 ondalık hane olduğunu doğrular.
    Tek dilim kuralında ara basamakların kuruş hassasiyetini koruduğunu gösterir.
    """
    from backend.app.services.bonus_service import quantize_money

    # Standart Bankacılık/Muhasebe Half-Up Testleri
    assert quantize_money(Decimal("100.005")) == Decimal("100.01")
    assert quantize_money(Decimal("100.004")) == Decimal("100.00")
    assert quantize_money(Decimal("1250.355")) == Decimal("1250.36")
    assert quantize_money(Decimal("0.0001")) == Decimal("0.00")
