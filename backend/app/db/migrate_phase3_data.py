import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.models.franchisor import Franchisor
from backend.app.models.branch import Branch
from backend.app.models.department import Department
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.role import Role
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.transaction_category import TransactionCategory
from backend.app.models.employee import Employee
from backend.app.models.transaction import Transaction
from backend.app.models.user import User

def hash_password(pwd: str) -> str:
    pwd_bytes = pwd.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def migrate_phase3_data():
    db: Session = SessionLocal()
    try:
        print("🚀 FAZ 3 Çoklu Bayi ve Kullanıcı Rolleri Taşıma Scripti Başlatılıyor...")

        # 1. Pre-migration check for existing branch
        existing_branch = db.query(Branch).first()
        pre_count = db.query(Transaction).filter(Transaction.branch_id == existing_branch.id).count() if existing_branch else 0
        pre_turnover = db.query(func.sum(Transaction.amount_excl_vat)).filter(Transaction.branch_id == existing_branch.id).scalar() or Decimal("0.00") if existing_branch else Decimal("0.00")
        print(f"📊 Taşıma Öncesi (Mevcut Bayi ID: {existing_branch.id if existing_branch else 'Yok'}): {pre_count} işlem, {pre_turnover:,.2f} TL ciro")

        # 2. Create or get default Franchisor
        franchisor = db.query(Franchisor).first()
        if not franchisor:
            franchisor = Franchisor(
                name="Merkez Franchisor (OtoBakım A.Ş.)",
                tax_id="1234567890",
                tax_office="Büyük Mükellefler VD",
                is_active=True
            )
            db.add(franchisor)
            db.commit()
            db.refresh(franchisor)
            print(f"✅ Franchisor oluşturuldu: {franchisor.name} (ID: {franchisor.id})")
        else:
            print(f"ℹ️ Mevcut Franchisor bulundu: {franchisor.name} (ID: {franchisor.id})")

        # 3. Link Existing Branch (Merkez Bayi) to Franchisor
        if existing_branch:
            existing_branch.franchisor_id = franchisor.id
            db.commit()
            print(f"🔗 Mevcut Bayi ({existing_branch.name}) Franchisor'a bağlandı.")

        # 4. Create Second Branch (Kadıköy Bayi) for Multi-Tenant Testing & Comparison
        branch2 = db.query(Branch).filter(Branch.name == "Kadıköy Bayi").first()
        if not branch2:
            branch2 = Branch(
                franchisor_id=franchisor.id,
                name="Kadıköy Bayi",
                tax_id="9876543210",
                tax_office="Kadıköy VD",
                address="Bağdat Caddesi No:120 Kadıköy / İstanbul",
                phone="0216 555 2020",
                email="kadikoy@otobakim.com",
                is_active=True
            )
            db.add(branch2)
            db.commit()
            db.refresh(branch2)
            print(f"✅ İkinci Bayi oluşturuldu: {branch2.name} (ID: {branch2.id})")

            # Seed Departments for Branch 2
            d1 = Department(branch_id=branch2.id, name="PPF & Araç Kaplama", is_active=True)
            d2 = Department(branch_id=branch2.id, name="Mekanik Servis", is_active=True)
            db.add_all([d1, d2])
            db.commit()
            db.refresh(d1)
            db.refresh(d2)

            # Seed Commission Tiers for Branch 2 (0-500k: %28, 500k+: %33)
            ct1 = CommissionTier(branch_id=branch2.id, min_amount=Decimal("0.00"), max_amount=Decimal("500000.00"), rate=Decimal("0.28"))
            ct2 = CommissionTier(branch_id=branch2.id, min_amount=Decimal("500000.01"), max_amount=None, rate=Decimal("0.33"))
            db.add_all([ct1, ct2])

            # Seed Categories for Branch 2
            cat1 = TransactionCategory(
                branch_id=branch2.id,
                name="Komple TPU PPF Kaplama",
                general_override_rate=Decimal("0.15"),
                bonus_override_rate=Decimal("0.07"),
                is_active=True
            )
            cat2 = TransactionCategory(
                branch_id=branch2.id,
                name="Periyodik Bakım Paketi",
                general_override_rate=None,
                bonus_override_rate=None,
                is_active=True
            )
            db.add_all([cat1, cat2])
            db.commit()
            db.refresh(cat1)
            db.refresh(cat2)

            # Seed Roles & Tiers for Branch 2
            r1 = Role(branch_id=branch2.id, name="Satış Danışmanı", turnover_source="kendi_islemleri", is_active=True)
            r2 = Role(branch_id=branch2.id, name="Servis Müdürü", turnover_source="kendi_departmani", is_active=True)
            db.add_all([r1, r2])
            db.commit()
            db.refresh(r1)
            db.refresh(r2)

            rt1 = RoleCommissionTier(role_id=r1.id, min_amount=Decimal("0.00"), max_amount=Decimal("200000.00"), rate=Decimal("0.05"))
            rt2 = RoleCommissionTier(role_id=r1.id, min_amount=Decimal("200000.01"), max_amount=None, rate=Decimal("0.08"))
            db.add_all([rt1, rt2])

            # Seed Employees for Branch 2
            emp1 = Employee(branch_id=branch2.id, role_id=r1.id, department_id=d1.id, full_name="Ali Kadıköy", is_active=True)
            emp2 = Employee(branch_id=branch2.id, role_id=r2.id, department_id=d2.id, full_name="Kemal Müdür", is_active=True)
            db.add_all([emp1, emp2])
            db.commit()
            db.refresh(emp1)
            db.refresh(emp2)

            # Seed Transactions for Branch 2 (Jan 2024)
            txs_b2 = [
                Transaction(
                    branch_id=branch2.id,
                    department_id=d1.id,
                    employee_id=emp1.id,
                    category_id=cat1.id,
                    date=date(2026, 9, 10),
                    customer_name="Kadıköy Müşteri A",
                    customer_tax_id="11122233344",
                    item_name=cat1.name,
                    staff_name=emp1.full_name,
                    amount_excl_vat=Decimal("95000.00"),
                    vat_rate=Decimal("0.20"),
                    amount_incl_vat=Decimal("114000.00"),
                    payment_method="Kredi Kartı",
                    invoice_status="Faturalandı"
                ),
                Transaction(
                    branch_id=branch2.id,
                    department_id=d1.id,
                    employee_id=emp1.id,
                    category_id=cat1.id,
                    date=date(2026, 9, 18),
                    customer_name="Kadıköy Müşteri B",
                    customer_tax_id="22233344455",
                    item_name=cat1.name,
                    staff_name=emp1.full_name,
                    amount_excl_vat=Decimal("85000.00"),
                    vat_rate=Decimal("0.20"),
                    amount_incl_vat=Decimal("102000.00"),
                    payment_method="Havale / EFT",
                    invoice_status="Faturalandı"
                ),
                Transaction(
                    branch_id=branch2.id,
                    department_id=d2.id,
                    employee_id=emp2.id,
                    category_id=cat2.id,
                    date=date(2026, 9, 22),
                    customer_name="Kadıköy Müşteri C",
                    customer_tax_id="33344455566",
                    item_name=cat2.name,
                    staff_name=emp2.full_name,
                    amount_excl_vat=Decimal("120000.00"),
                    vat_rate=Decimal("0.20"),
                    amount_incl_vat=Decimal("144000.00"),
                    payment_method="Kredi Kartı",
                    invoice_status="Faturalandı"
                ),
            ]
            db.add_all(txs_b2)
            db.commit()
            print(f"   ↳ Kadıköy Bayi için 3 adet örnek işlem ({sum(t.amount_excl_vat for t in txs_b2):,.2f} TL) eklendi.")

        # 5. Update and Seed Users with Roles
        # Admin user -> FRANCHISOR_ADMIN
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            admin_user.role = "FRANCHISOR_ADMIN"
            admin_user.franchisor_id = franchisor.id
            admin_user.branch_id = None  # Access to all branches
            db.commit()
            print("👤 'admin' kullanıcısı FRANCHISOR_ADMIN olarak güncellendi.")

        # Create bayi_admin user for Merkez Bayi
        bayi_user = db.query(User).filter(User.username == "bayi_admin").first()
        if not bayi_user:
            bayi_user = User(
                username="bayi_admin",
                hashed_password=hash_password("admin123"),
                full_name="Merkez Bayi Yöneticisi",
                role="BAYI_ADMIN",
                franchisor_id=franchisor.id,
                branch_id=existing_branch.id if existing_branch else None,
                is_active=True
            )
            db.add(bayi_user)
            db.commit()
            print("👤 'bayi_admin' kullanıcısı BAYI_ADMIN olarak oluşturuldu.")

        # Create viewer user (Salt Okunur)
        viewer_user = db.query(User).filter(User.username == "viewer").first()
        if not viewer_user:
            viewer_user = User(
                username="viewer",
                hashed_password=hash_password("admin123"),
                full_name="Denetçi / İzleyici (Viewer)",
                role="VIEWER",
                franchisor_id=franchisor.id,
                branch_id=existing_branch.id if existing_branch else None,
                is_active=True
            )
            db.add(viewer_user)
            db.commit()
            print("👤 'viewer' kullanıcısı VIEWER olarak oluşturuldu.")

        # 6. Post-migration verification
        post_count = db.query(Transaction).filter(Transaction.branch_id == existing_branch.id).count() if existing_branch else 0
        post_turnover = db.query(func.sum(Transaction.amount_excl_vat)).filter(Transaction.branch_id == existing_branch.id).scalar() or Decimal("0.00") if existing_branch else Decimal("0.00")
        total_branches = db.query(Branch).count()
        total_all_transactions = db.query(Transaction).count()
        total_all_turnover = db.query(func.sum(Transaction.amount_excl_vat)).scalar() or Decimal("0.00")

        print("\n" + "="*60)
        print("🔍 FAZ 3 DOĞRULAMA VE SAYISAL KARŞILAŞTIRMA RAPORU:")
        print(f"  Merkez Bayi Önceki İşlem: {pre_count} | Şimdiki: {post_count} -> {'✅ EŞİT (Kayıp Yok)' if pre_count == post_count else '❌ FARK VAR'}")
        print(f"  Merkez Bayi Önceki Ciro: {pre_turnover:,.2f} TL | Şimdiki: {post_turnover:,.2f} TL -> {'✅ EŞİT (0 Kuruş Fark)' if pre_turnover == post_turnover else '❌ FARK VAR'}")
        print(f"  Sistemdeki Toplam Bayi Sayısı: {total_branches}")
        print(f"  Tüm Bayiler Toplam İşlem: {total_all_transactions} | Toplam Ciro: {total_all_turnover:,.2f} TL")
        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    migrate_phase3_data()
