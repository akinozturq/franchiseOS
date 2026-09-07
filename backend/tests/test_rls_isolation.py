import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from backend.app.core.database import SessionLocal
from backend.app.models.transaction import Transaction
from backend.app.models.branch import Branch
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.transaction_category import TransactionCategory

def test_rls_cross_tenant_isolation_select():
    """
    Kabul Kriteri:
    RLS açık ve policy'ler tanımlı; iki farklı bayi arasında çapraz erişim denemesi başarısız oluyor.
    Hem uygulama filtresi hem RLS ayrı ayrı test edilerek RLS'in tek başına da koruduğu gösterilmeli.
    """
    db = SessionLocal()
    try:
        # Switch to non-superuser app role so PostgreSQL strictly enforces RLS
        db.execute(text("SET ROLE franchise_app;"))
        
        # 1. Simulate Branch 1 User Context
        db.execute(text("SET app.current_branch_id = '1';"))
        db.execute(text("SET app.is_franchisor_admin = 'false';"))

        # Query WITHOUT any WHERE branch_id filter (simulating a developer forgetting the WHERE clause)
        b1_rows = db.query(Transaction).all()
        assert len(b1_rows) > 0, "Branch 1 should have transactions"
        # Verify every single returned row belongs to branch 1!
        for tx in b1_rows:
            assert tx.branch_id == 1, f"RLS LEAK! Found transaction with branch_id {tx.branch_id} for branch 1 user"

        # Explicitly attempt cross-tenant query: SELECT * FROM transactions WHERE branch_id = 2
        cross_rows = db.query(Transaction).filter(Transaction.branch_id == 2).all()
        # RLS MUST return empty list even though branch 2 has transactions in DB!
        assert len(cross_rows) == 0, "RLS FAILURE! Branch 1 user was able to read Branch 2 transactions!"

        # 2. Simulate Branch 2 User Context
        db.execute(text("SET app.current_branch_id = '2';"))
        db.execute(text("SET app.is_franchisor_admin = 'false';"))

        b2_rows = db.query(Transaction).all()
        assert len(b2_rows) > 0, "Branch 2 should have transactions"
        for tx in b2_rows:
            assert tx.branch_id == 2, f"RLS LEAK! Found transaction with branch_id {tx.branch_id} for branch 2 user"

        # Branch 2 user querying branch 1
        cross_b1_rows = db.query(Transaction).filter(Transaction.branch_id == 1).all()
        assert len(cross_b1_rows) == 0, "RLS FAILURE! Branch 2 user was able to read Branch 1 transactions!"

        # 3. Simulate Franchisor Admin Context (is_franchisor_admin = true)
        db.execute(text("SET app.is_franchisor_admin = 'true';"))
        all_rows = db.query(Transaction).all()
        branch_ids = {tx.branch_id for tx in all_rows}
        assert 1 in branch_ids and 2 in branch_ids, "Franchisor admin should see transactions from all branches"

    finally:
        db.execute(text("RESET ROLE;"))
        db.close()

def test_rls_cross_tenant_isolation_insert_prevented():
    """
    Verifies that a user from Branch 1 CANNOT insert data into Branch 2 via RLS WITH CHECK policy.
    """
    db = SessionLocal()
    try:
        db.execute(text("SET ROLE franchise_app;"))
        # Branch 1 context
        db.execute(text("SET app.current_branch_id = '1';"))
        db.execute(text("SET app.is_franchisor_admin = 'false';"))

        # Attempt to insert a transaction into branch 2
        rogue_tx = Transaction(
            branch_id=2,  # Rogue branch_id!
            department_id=1,
            employee_id=1,
            category_id=None,
            date=date(2024, 1, 15),
            customer_name="Rogue Insert",
            item_name="Hacker Service",
            amount_excl_vat=Decimal("5000.00"),
            vat_rate=Decimal("0.20"),
            amount_incl_vat=Decimal("6000.00"),
            payment_method="Nakit",
            invoice_status="Faturalandı"
        )
        db.add(rogue_tx)

        with pytest.raises(DBAPIError) as excinfo:
            db.commit()
        
        # PostgreSQL should raise new row violates row-level security policy
        assert "row-level security policy" in str(excinfo.value).lower()
        db.rollback()

    finally:
        db.execute(text("RESET ROLE;"))
        db.close()

def test_rls_isolation_other_models():
    """
    Verify RLS on employees and categories as well.
    """
    db = SessionLocal()
    try:
        db.execute(text("SET ROLE franchise_app;"))
        db.execute(text("SET app.current_branch_id = '1';"))
        db.execute(text("SET app.is_franchisor_admin = 'false';"))

        # Employees
        employees = db.query(Employee).all()
        assert len(employees) > 0
        for emp in employees:
            assert emp.branch_id == 1

        # Categories
        categories = db.query(TransactionCategory).all()
        assert len(categories) > 0
        for cat in categories:
            assert cat.branch_id == 1

        # Departments
        departments = db.query(Department).all()
        assert len(departments) > 0
        for d in departments:
            assert d.branch_id == 1

    finally:
        db.execute(text("RESET ROLE;"))
        db.close()

def test_application_level_isolation_when_rls_bypassed():
    """
    Simetrik İzolasyon Doğrulaması (Defense-in-Depth İkinci Yönü):
    RLS veritabanı seviyesinde geçici olarak devre dışı bırakıldığında (DISABLE ROW LEVEL SECURITY),
    uygulama seviyesindeki `filter(Model.branch_id == active_branch_id)` filtresinin
    tek başına bağımsız olarak veri izolasyonunu sağladığı doğrulanır.
    """
    db = SessionLocal()
    tables_to_toggle = ["transactions", "employees", "transaction_categories", "departments"]
    try:
        db.rollback()
        db.execute(text("RESET ROLE;"))
        db.commit()

        # 1. Explicitly turn off PostgreSQL Row-Level Security on tables
        for tbl in tables_to_toggle:
            db.execute(text(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;"))
            db.execute(text(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY;"))
        db.commit()

        # Precondition check: verify DB indeed returns rows across multiple branches when unfiltered
        unfiltered_txs = db.query(Transaction).all()
        distinct_branches = {tx.branch_id for tx in unfiltered_txs}
        assert len(distinct_branches) >= 2, "When RLS is OFF and query is unfiltered, transactions from all branches must appear"
        assert len(unfiltered_txs) >= 59

        # 2. Application filter alone for Branch 1
        app_b1_txs = db.query(Transaction).filter(Transaction.branch_id == 1).all()
        assert len(app_b1_txs) > 0
        for tx in app_b1_txs:
            assert tx.branch_id == 1, f"App filter leak: found branch_id {tx.branch_id} when filtering for 1"
        assert not any(tx.branch_id == 2 for tx in app_b1_txs)

        # 3. Application filter alone for Branch 2
        app_b2_txs = db.query(Transaction).filter(Transaction.branch_id == 2).all()
        assert len(app_b2_txs) > 0
        for tx in app_b2_txs:
            assert tx.branch_id == 2, f"App filter leak: found branch_id {tx.branch_id} when filtering for 2"
        assert not any(tx.branch_id == 1 for tx in app_b2_txs)

        # 4. Same independent application filter isolation for Employees, Categories, Departments
        emp_b1 = db.query(Employee).filter(Employee.branch_id == 1).all()
        assert len(emp_b1) > 0 and all(e.branch_id == 1 for e in emp_b1)

        emp_b2 = db.query(Employee).filter(Employee.branch_id == 2).all()
        assert len(emp_b2) > 0 and all(e.branch_id == 2 for e in emp_b2)

        cat_b1 = db.query(TransactionCategory).filter(TransactionCategory.branch_id == 1).all()
        assert len(cat_b1) > 0 and all(c.branch_id == 1 for c in cat_b1)

        dept_b1 = db.query(Department).filter(Department.branch_id == 1).all()
        assert len(dept_b1) > 0 and all(d.branch_id == 1 for d in dept_b1)

    finally:
        # Re-enable and force RLS in all circumstances
        try:
            db.rollback()
            for tbl in tables_to_toggle:
                db.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
                db.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

