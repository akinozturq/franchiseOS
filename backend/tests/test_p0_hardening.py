import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.transaction import Transaction
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.period_setting import PeriodSetting
from backend.app.models.employee import Employee
from backend.app.models.transaction_category import TransactionCategory

from backend.app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_headers():
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def viewer_headers():
    token = create_access_token({"sub": "viewer"})
    return {"Authorization": f"Bearer {token}"}

def test_closed_period_employee_assignment_blocked(admin_headers):
    """
    P0 Bütünlük Testi:
    Kapalı bir döneme ait transaction, POST /employees/assign-transactions
    üzerinden başka personele atanamaz (400 Bad Request dönmeli).
    """
    db = SessionLocal()
    try:
        # Create a closed period for 2025-11 on Branch 1
        closure = db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == 1,
            PeriodClosure.year == 2025,
            PeriodClosure.month == 11
        ).first()
        if not closure:
            closure = PeriodClosure(
                branch_id=1,
                year=2025,
                month=11,
                status="CLOSED",
                closed_by_user_id=1,
                reconciliation_snapshot={"test": True},
                bonus_snapshot={"test": True}
            )
            db.add(closure)
            db.commit()

        # Create a transaction in this closed period
        tx = Transaction(
            branch_id=1,
            department_id=1,
            date=date(2025, 11, 15),
            customer_name="Kapalı Dönem Müşterisi",
            customer_tax_id="11111111111",
            item_name="Kapalı İşlem",
            staff_name="Eski Personel",
            amount_excl_vat=Decimal("5000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("6000.00")
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        # Get an active employee
        emp = db.query(Employee).filter(Employee.branch_id == 1).first()

        # Attempt to reassign this transaction
        response = client.post(
            "/api/v1/employees/assign-transactions",
            json={"transaction_ids": [tx.id], "employee_id": emp.id},
            headers={**admin_headers, "X-Branch-ID": "1"}
        )

        assert response.status_code == 400
        assert "kapalı" in response.json()["detail"].lower()

    finally:
        db.query(Transaction).filter(Transaction.customer_name == "Kapalı Dönem Müşterisi").delete()
        db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == 1,
            PeriodClosure.year == 2025,
            PeriodClosure.month == 11
        ).delete()
        db.commit()
        db.close()

def test_locked_and_closed_period_setting_mutation_blocked(admin_headers):
    """
    P0 Finansal Kilit Testi:
    Kilitlenmiş (is_locked=True) veya kapatılmış dönemin tahsilatçı/KDV ayarları değiştirilemez.
    """
    db = SessionLocal()
    try:
        # Create a locked period setting
        setting = db.query(PeriodSetting).filter(
            PeriodSetting.branch_id == 1,
            PeriodSetting.year == 2025,
            PeriodSetting.month == 10
        ).first()
        if not setting:
            setting = PeriodSetting(
                branch_id=1,
                year=2025,
                month=10,
                collector_party="BAYI",
                vat_rate=Decimal("0.20"),
                is_locked=True
            )
            db.add(setting)
        else:
            setting.is_locked = True
            setting.collector_party = "BAYI"
        db.commit()

        # Attempt to mutate collector_party while is_locked is True
        res = client.put(
            "/api/v1/reconciliation/setting",
            json={
                "year": 2025,
                "month": 10,
                "collector_party": "FRANCHISOR",
                "vat_rate": "0.20",
                "is_locked": True
            },
            headers={**admin_headers, "X-Branch-ID": "1"}
        )
        assert res.status_code == 400
        assert "kilitli" in res.json()["detail"].lower()

    finally:
        db.query(PeriodSetting).filter(
            PeriodSetting.branch_id == 1,
            PeriodSetting.year == 2025,
            PeriodSetting.month == 10
        ).delete()
        db.commit()
        db.close()

def test_transaction_vat_invariant_enforced(admin_headers):
    """
    P0 Veri Bütünlüğü:
    KDV Dahil tutar, KDV Hariç tutar ve oran ile matematiksel olarak tutarlı olmalıdır.
    Tutarsız tutar gönderildiğinde 422 Unprocessable Entity fırlatılmalıdır.
    """
    payload = {
        "date": "2026-09-01",
        "department_id": 1,
        "customer_name": "Tutarsız Tutar Testi",
        "item_name": "Hatalı KDV İşlemi",
        "amount_excl_vat": "1000.00",
        "vat_rate": "0.20",
        "amount_incl_vat": "5000.00"
    }
    res = client.post(
        "/api/v1/transactions",
        json=payload,
        headers={**admin_headers, "X-Branch-ID": "1"}
    )
    assert res.status_code == 422
    assert "tutarsız" in res.text.lower()

def test_sensitive_tax_id_data_minimization(admin_headers, viewer_headers):
    """
    P0 KVKK & Gizlilik Testi:
    - Standart TransactionOut şemasında raw customer_tax_id alanı bulunmaz.
    - Sadece customer_tax_id_masked döndürülür.
    - Raw TCKN/VKN yalnızca yetkili /sensitive endpoint'inden erişilebilir.
    """
    res = client.get("/api/v1/transactions", headers={**admin_headers, "X-Branch-ID": "1"})
    assert res.status_code == 200
    txs = res.json()
    sample = next((t for t in txs if t.get("customer_tax_id_masked")), None)
    if not sample:
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
            headers={**admin_headers, "X-Branch-ID": "1"}
        )
        sample = post_res.json()

    assert "customer_tax_id" not in sample, "Standart API çıktısında raw customer_tax_id bulunmamalıdır!"
    assert sample.get("customer_tax_id_masked") is not None
    assert "*" in sample["customer_tax_id_masked"]

    sens_res = client.get(
        f"/api/v1/transactions/{sample['id']}/sensitive",
        headers={**admin_headers, "X-Branch-ID": "1"}
    )
    assert sens_res.status_code == 200
    sens_data = sens_res.json()
    assert "customer_tax_id" in sens_data
    assert "*" not in sens_data["customer_tax_id"]

    viewer_res = client.get(
        f"/api/v1/transactions/{sample['id']}/sensitive",
        headers={**viewer_headers, "X-Branch-ID": "1"}
    )
    assert viewer_res.status_code == 403

def test_half_open_interval_boundary_disambiguation(admin_headers):
    """
    P0 Versiyonlama Tarih Modeli: [effective_from, effective_to)
    Eski kural effective_to = today olduğunda, today tarihindeki sorgularda
    çakışma olmadan yalnızca yeni kural (effective_from = today) geçerli olmalıdır.
    """
    db = SessionLocal()
    today = date.today()
    try:
        # Create an old category version closed on today
        old_cat = TransactionCategory(
            branch_id=1,
            name="Interval Test Kategori",
            general_override_rate=Decimal("0.10"),
            bonus_override_rate=Decimal("0.05"),
            effective_from=date(2025, 1, 1),
            effective_to=today
        )
        # Create a new category version active from today
        new_cat = TransactionCategory(
            branch_id=1,
            name="Interval Test Kategori",
            general_override_rate=Decimal("0.25"),
            bonus_override_rate=Decimal("0.12"),
            effective_from=today,
            effective_to=None
        )
        db.add_all([old_cat, new_cat])
        db.commit()

        # Query categories at 'today'
        res = client.get(
            f"/api/v1/categories?target_date={today.isoformat()}",
            headers={**admin_headers, "X-Branch-ID": "1"}
        )
        assert res.status_code == 200
        cats = [c for c in res.json() if c["name"] == "Interval Test Kategori"]
        # Exactly ONE version must match on boundary date!
        assert len(cats) == 1
        assert Decimal(str(cats[0]["general_override_rate"])) == Decimal("0.25")

    finally:
        db.query(TransactionCategory).filter(TransactionCategory.name == "Interval Test Kategori").delete()
        db.commit()
        db.close()

def test_production_config_security_validation():
    """
    P0 Production Güvenlik Doğrulaması:
    ENVIRONMENT=production iken default secret veya wildcard CORS kabul edilmemelidir.
    """
    from backend.app.core.config import Settings

    # Default secret ile production modunda hata vermelidir
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="super-secret-franchise-os-key-change-in-production",
            CORS_ORIGINS=["https://app.franchiseos.com"]
        )

    # 32 karakterden kısa secret ile production modunda hata vermelidir
    with pytest.raises(ValueError, match="en az 32 karakter"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="short-secret-key",
            CORS_ORIGINS=["https://app.franchiseos.com"]
        )

    # Wildcard CORS ile production modunda hata vermelidir
    with pytest.raises(ValueError, match="wildcard"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a_very_secure_production_secret_key_32_chars!",
            CORS_ORIGINS=["*"]
        )

    # Güvenli ayarlarla başarıyla konfigüre edilebilmelidir
    valid_prod = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a_very_secure_production_secret_key_32_chars!",
        CORS_ORIGINS=["https://app.franchiseos.com"]
    )
    assert valid_prod.ENVIRONMENT == "production"

