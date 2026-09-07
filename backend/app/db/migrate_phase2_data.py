import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.models.branch import Branch
from backend.app.models.department import Department
from backend.app.models.role import Role
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.transaction_category import TransactionCategory
from backend.app.models.employee import Employee
from backend.app.models.transaction import Transaction

def migrate_phase2_data():
    db: Session = SessionLocal()
    try:
        print("🚀 FAZ 2 Veri Taşıma ve Geriye Dönük Eşleştirme Başlatılıyor...")
        
        # 1. Pre-migration check
        pre_count = db.query(Transaction).count()
        pre_turnover = db.query(func.sum(Transaction.amount_excl_vat)).scalar() or Decimal("0.00")
        print(f"📊 Taşıma Öncesi: {pre_count} işlem kaydı, {pre_turnover:,.2f} TL ciro")

        branch = db.query(Branch).first()
        if not branch:
            print("❌ Hata: Bayi bulunamadı.")
            return

        # 2. Seed Default Roles and their Commission Tiers
        roles_config = [
            {
                "name": "Genel Müdür",
                "turnover_source": "tum_bayi",
                "tiers": [
                    (Decimal("0.00"), Decimal("500000.00"), Decimal("0.02")),
                    (Decimal("500000.01"), Decimal("1000000.00"), Decimal("0.03")),
                    (Decimal("1000000.01"), None, Decimal("0.04")),
                ]
            },
            {
                "name": "Satış Müdürü",
                "turnover_source": "kendi_departmani",
                "tiers": [
                    (Decimal("0.00"), Decimal("300000.00"), Decimal("0.04")),
                    (Decimal("300000.01"), None, Decimal("0.05")),
                ]
            },
            {
                "name": "Satış Danışmanı",
                "turnover_source": "kendi_islemleri",
                "tiers": [
                    (Decimal("0.00"), Decimal("150000.00"), Decimal("0.05")),
                    (Decimal("150000.01"), Decimal("300000.00"), Decimal("0.07")),
                    (Decimal("300000.01"), None, Decimal("0.09")),
                ]
            },
            {
                "name": "Servis Müdürü",
                "turnover_source": "kendi_departmani",
                "tiers": [
                    (Decimal("0.00"), Decimal("200000.00"), Decimal("0.03")),
                    (Decimal("200000.01"), None, Decimal("0.04")),
                ]
            },
            {
                "name": "Servis Danışmanı / Teknisyen",
                "turnover_source": "kendi_islemleri",
                "tiers": [
                    (Decimal("0.00"), Decimal("100000.00"), Decimal("0.04")),
                    (Decimal("100000.01"), None, Decimal("0.06")),
                ]
            },
        ]

        role_map = {}
        for rc in roles_config:
            role = db.query(Role).filter(Role.branch_id == branch.id, Role.name == rc["name"]).first()
            if not role:
                role = Role(
                    branch_id=branch.id,
                    name=rc["name"],
                    turnover_source=rc["turnover_source"],
                    is_active=True
                )
                db.add(role)
                db.commit()
                db.refresh(role)
                print(f"✅ Rol oluşturuldu: {role.name} (Ciro Kaynağı: {role.turnover_source})")

                # Add tiers
                for min_a, max_a, rate in rc["tiers"]:
                    tier = RoleCommissionTier(
                        role_id=role.id,
                        min_amount=min_a,
                        max_amount=max_a,
                        rate=rate
                    )
                    db.add(tier)
                db.commit()
                print(f"   ↳ {len(rc['tiers'])} adet kademeli prim dilimi eklendi.")
            role_map[role.name] = role

        # Also add a General Manager employee for testing tum_bayi
        gm_emp = db.query(Employee).filter(Employee.branch_id == branch.id, Employee.full_name == "Serdar Genel Müdür").first()
        if not gm_emp:
            gm_emp = Employee(
                branch_id=branch.id,
                role_id=role_map["Genel Müdür"].id,
                department_id=None,  # All-bayi role has no specific department
                full_name="Serdar Genel Müdür",
                is_active=True
            )
            db.add(gm_emp)
            db.commit()
            print("✅ Genel Müdür personeli eklendi (Serdar Genel Müdür - Tüm Bayi Cirosu)")

        # 3. Migrate Categories from Transaction.item_name
        distinct_items = db.query(Transaction.item_name).distinct().all()
        category_map = {}
        for (item_name,) in distinct_items:
            if not item_name:
                continue
            cat = db.query(TransactionCategory).filter(
                TransactionCategory.branch_id == branch.id,
                TransactionCategory.name == item_name
            ).first()

            if not cat:
                # Referans senaryo: Komple TPU PPF Kaplama için istisna oranları tanımlanır:
                # Genel franchisor-bayi payında sabit %15, personel priminde sabit %7
                if "Komple TPU PPF" in item_name:
                    gen_override = Decimal("0.15")
                    bon_override = Decimal("0.07")
                else:
                    gen_override = None
                    bon_override = None

                cat = TransactionCategory(
                    branch_id=branch.id,
                    name=item_name,
                    general_override_rate=gen_override,
                    bonus_override_rate=bon_override,
                    is_active=True
                )
                db.add(cat)
                db.commit()
                db.refresh(cat)
                override_text = f" (İstisna: Genel %{gen_override*100}, Prim %{bon_override*100})" if gen_override else ""
                print(f"✅ Kategori oluşturuldu: {cat.name}{override_text}")

            category_map[item_name] = cat

        # 4. Migrate Employees from Transaction.staff_name
        departments = db.query(Department).filter(Department.branch_id == branch.id).all()
        dept_by_name = {d.name.lower(): d for d in departments}

        distinct_staff = db.query(Transaction.staff_name).distinct().all()
        employee_map = {}
        for (staff_name,) in distinct_staff:
            if not staff_name:
                continue
            emp = db.query(Employee).filter(
                Employee.branch_id == branch.id,
                Employee.full_name == staff_name
            ).first()

            if not emp:
                # Infer role and department from staff_name
                name_lower = staff_name.lower()
                if "satış" in name_lower:
                    role = role_map.get("Satış Danışmanı")
                    dept = dept_by_name.get("satış") or departments[0]
                elif "usta" in name_lower or "teknisyen" in name_lower:
                    role = role_map.get("Servis Danışmanı / Teknisyen")
                    dept = dept_by_name.get("mekanik servis") or dept_by_name.get("servis") or departments[0]
                elif "danışman" in name_lower:
                    role = role_map.get("Satış Danışmanı")
                    dept = dept_by_name.get("ppf & araç kaplama") or departments[0]
                else:
                    role = role_map.get("Satış Danışmanı")
                    dept = departments[0]

                emp = Employee(
                    branch_id=branch.id,
                    role_id=role.id,
                    department_id=dept.id if dept else None,
                    full_name=staff_name,
                    is_active=True
                )
                db.add(emp)
                db.commit()
                db.refresh(emp)
                print(f"✅ Personel oluşturuldu: {emp.full_name} -> Rol: {role.name}")

            employee_map[staff_name] = emp

        # 5. Backfill Transaction foreign keys (employee_id, category_id)
        transactions = db.query(Transaction).all()
        linked_staff_count = 0
        linked_cat_count = 0

        for tx in transactions:
            if tx.staff_name and tx.staff_name in employee_map and not tx.employee_id:
                tx.employee_id = employee_map[tx.staff_name].id
                linked_staff_count += 1
            if tx.item_name and tx.item_name in category_map and not tx.category_id:
                tx.category_id = category_map[tx.item_name].id
                linked_cat_count += 1

        db.commit()
        print(f"🔗 {linked_staff_count} adet işleme employee_id bağlandı.")
        print(f"🔗 {linked_cat_count} adet işleme category_id bağlandı.")

        # 6. Post-migration verification
        post_count = db.query(Transaction).count()
        post_turnover = db.query(func.sum(Transaction.amount_excl_vat)).scalar() or Decimal("0.00")
        unlinked_employees = db.query(Transaction).filter(Transaction.employee_id.is_(None)).count()
        unlinked_categories = db.query(Transaction).filter(Transaction.category_id.is_(None)).count()

        print("\n" + "="*60)
        print("🔍 DOĞRULAMA RAPORU (Post-Migration Verification):")
        print(f"  Önceki İşlem Sayısı: {pre_count} | Şimdiki: {post_count} -> {'✅ EŞİT (Kayıp Yok)' if pre_count == post_count else '❌ FARK VAR'}")
        print(f"  Önceki Ciro Toplamı: {pre_turnover:,.2f} TL | Şimdiki: {post_turnover:,.2f} TL -> {'✅ EŞİT (0 Kuruş Fark)' if pre_turnover == post_turnover else '❌ FARK VAR'}")
        print(f"  Atanmamış Personel Kaydı: {unlinked_employees}")
        print(f"  Atanmamış Kategori Kaydı: {unlinked_categories}")
        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    migrate_phase2_data()
