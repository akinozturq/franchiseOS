import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import random
from datetime import date, timedelta
from decimal import Decimal
from faker import Faker
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.branch import Branch
from backend.app.models.user import User
from backend.app.models.department import Department
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.transaction import Transaction

fake = Faker("tr_TR")
Faker.seed(42)
random.seed(42)

def seed_database():
    db: Session = SessionLocal()
    try:
        print("🌱 Veritabanı seed işlemi başlatılıyor...")

        # 1. Branch
        branch = db.query(Branch).first()
        if not branch:
            branch = Branch(
                name="Kuzey Detailing & Servis Bayisi",
                tax_id="1234567890",
                tax_office="Zincirlikuyu Vergi Dairesi",
                address="Büyükdere Cad. No: 142 Şişli / İstanbul",
                phone="0212 555 0199",
                email="info@kuzeybayi.com",
                is_active=True
            )
            db.add(branch)
            db.commit()
            db.refresh(branch)
            print(f"✅ Bayi oluşturuldu: {branch.name} (ID: {branch.id})")
        else:
            print(f"ℹ️ Bayi zaten mevcut: {branch.name}")

        # 2. Admin User
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Sistem Yöneticisi",
                is_active=True
            )
            db.add(user)
            db.commit()
            print("✅ Admin kullanıcısı oluşturuldu (Kullanıcı adı: admin, Şifre: admin123)")
            print("⚠️  [GÜVENLİK UYARISI] Bu hesap geliştirme/demo amaçlıdır. Canlı (prodüksiyon) ortama almadan önce şifreyi MUTLAKA değiştirin!")
        else:
            print("ℹ️ Admin kullanıcısı zaten mevcut.")
            print("⚠️  [GÜVENLİK UYARISI] Canlı ortama almadan önce admin şifresinin varsayılan olmadığından emin olun.")


        # 3. Departments
        default_depts = [
            "PPF & Araç Kaplama",
            "Mekanik Servis",
            "Detaylı Bakım & Seramik",
            "Cam Filmi & Aksesuar"
        ]
        created_depts = []
        for d_name in default_depts:
            dept = db.query(Department).filter(
                Department.branch_id == branch.id,
                Department.name == d_name
            ).first()
            if not dept:
                dept = Department(branch_id=branch.id, name=d_name, is_active=True)
                db.add(dept)
                db.commit()
                db.refresh(dept)
                print(f"✅ Departman eklendi: {d_name}")
            created_depts.append(dept)

        # 4. Commission Tiers (Prompt şartı: 0-750.000 TL -> %30, 750.000,01+ TL -> %35)
        existing_tiers = db.query(CommissionTier).filter(CommissionTier.branch_id == branch.id).all()
        if not existing_tiers:
            t1 = CommissionTier(
                branch_id=branch.id,
                min_amount=Decimal("0.00"),
                max_amount=Decimal("750000.00"),
                rate=Decimal("0.30")
            )
            t2 = CommissionTier(
                branch_id=branch.id,
                min_amount=Decimal("750000.01"),
                max_amount=None,
                rate=Decimal("0.35")
            )
            db.add_all([t1, t2])
            db.commit()
            print("✅ Komisyon dilimleri tanımlandı (0-750k -> %30, 750k+ -> %35)")
        else:
            print("ℹ️ Komisyon dilimleri zaten mevcut.")

        # 5. Transactions Seed (Current Month & Previous Month)
        tx_count = db.query(Transaction).filter(Transaction.branch_id == branch.id).count()
        if tx_count == 0:
            print("🌱 Kurgusal işlem kayıtları üretiliyor (Faker TR)...")
            services_by_dept = {
                "PPF & Araç Kaplama": [
                    ("Komple TPU PPF Kaplama", Decimal("75000.00")),
                    ("Ön Kaput & Çamurluk PPF", Decimal("22000.00")),
                    ("Tavan & Ayna Piano Black Kaplama", Decimal("8500.00")),
                    ("Renkli PPF Kaplama", Decimal("85000.00")),
                ],
                "Mekanik Servis": [
                    ("Periyodik Bakım & Filtre Değişimi", Decimal("6500.00")),
                    ("Ön Fren Balata & Disk Yenileme", Decimal("9500.00")),
                    ("Ağır Bakım (Triger Seti)", Decimal("24000.00")),
                    ("Klima Gaz Dolumu & Temizliği", Decimal("3500.00")),
                ],
                "Detaylı Bakım & Seramik": [
                    ("9H Graphene Seramik Kaplama", Decimal("28000.00")),
                    ("Detaylı İç Kuaför & Ozon Temizliği", Decimal("7500.00")),
                    ("Pasta Cila & Çizik Giderme", Decimal("12000.00")),
                    ("Deri Koltuk Bakımı & Koruma", Decimal("5500.00")),
                ],
                "Cam Filmi & Aksesuar": [
                    ("Termal Cam Filmi (Tüm Camlar)", Decimal("11000.00")),
                    ("Ön Cam Isı Kesici Şeffaf Film", Decimal("4500.00")),
                    ("Krom Silme & De-Chrome Kaplama", Decimal("7000.00")),
                ]
            }
            
            staff_list = ["Ahmet Usta", "Burak Danışman", "Emre Teknisyen", "Caner Uzman", "Merve Satış"]
            payment_methods = ["Kredi Kartı", "Havale / EFT", "Nakit"]
            
            today = date.today()
            # Generate for current month (aiming for ~820,000 TL ciro to trigger Tier 2 %35)
            # and previous month (aiming for ~650,000 TL ciro to trigger Tier 1 %30)
            
            # 1) Current month transactions
            current_month_days = [today.replace(day=d) for d in range(1, min(today.day + 1, 28))]
            if not current_month_days:
                current_month_days = [today]

            # Let's add ~25-30 transactions for current month
            for _ in range(32):
                dept = random.choice(created_depts)
                service_choices = services_by_dept.get(dept.name, [("Genel Hizmet", Decimal("10000.00"))])
                item_name, base_price = random.choice(service_choices)
                
                # add slight variation
                variance = Decimal(str(random.randint(90, 115))) / Decimal("100")
                amount_excl = (base_price * variance).quantize(Decimal("0.01"))
                vat_rate = Decimal("0.20")
                amount_incl = (amount_excl * (Decimal("1.00") + vat_rate)).quantize(Decimal("0.01"))
                
                # Fictional TCKN (11 digits, strictly fictional)
                fake_tckn = f"{random.randint(10000000000, 99999999999)}"
                
                tx = Transaction(
                    branch_id=branch.id,
                    department_id=dept.id,
                    date=random.choice(current_month_days),
                    customer_name=fake.name(),
                    customer_tax_id=fake_tckn,
                    item_name=item_name,
                    staff_name=random.choice(staff_list),
                    amount_excl_vat=amount_excl,
                    vat_rate=vat_rate,
                    amount_incl_vat=amount_incl,
                    payment_method=random.choice(payment_methods),
                    invoice_status="Faturalandı" if random.random() > 0.2 else "Bekliyor",
                    description="Kurgusal demo işlem kaydı"
                )
                db.add(tx)
                
            # 2) Previous month transactions (approx 20 transactions)
            first_day_current_month = today.replace(day=1)
            last_day_prev_month = first_day_current_month - timedelta(days=1)
            prev_month_days = [last_day_prev_month.replace(day=d) for d in range(1, min(last_day_prev_month.day, 28))]
            
            for _ in range(24):
                dept = random.choice(created_depts)
                service_choices = services_by_dept.get(dept.name, [("Genel Hizmet", Decimal("10000.00"))])
                item_name, base_price = random.choice(service_choices)
                
                variance = Decimal(str(random.randint(90, 110))) / Decimal("100")
                amount_excl = (base_price * variance).quantize(Decimal("0.01"))
                vat_rate = Decimal("0.20")
                amount_incl = (amount_excl * (Decimal("1.00") + vat_rate)).quantize(Decimal("0.01"))
                fake_tckn = f"{random.randint(10000000000, 99999999999)}"
                
                tx = Transaction(
                    branch_id=branch.id,
                    department_id=dept.id,
                    date=random.choice(prev_month_days),
                    customer_name=fake.name(),
                    customer_tax_id=fake_tckn,
                    item_name=item_name,
                    staff_name=random.choice(staff_list),
                    amount_excl_vat=amount_excl,
                    vat_rate=vat_rate,
                    amount_incl_vat=amount_incl,
                    payment_method=random.choice(payment_methods),
                    invoice_status="Faturalandı",
                    description="Önceki dönem kurgusal işlem kaydı"
                )
                db.add(tx)

            db.commit()
            print("✅ 56 adet kurgusal işlem kaydı oluşturuldu.")
        else:
            print(f"ℹ️ Zaten {tx_count} adet işlem kaydı mevcut.")

        print("🎉 Seed işlemi başarıyla tamamlandı!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
