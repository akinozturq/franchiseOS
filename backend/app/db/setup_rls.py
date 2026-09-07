import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from backend.app.core.database import SessionLocal

TABLES_WITH_BRANCH_ID = [
    "departments",
    "roles",
    "commission_tiers",
    "transaction_categories",
    "employees",
    "transactions",
    "period_settings",
    "rule_change_logs",
    "period_closures",
]

def setup_rls():
    db = SessionLocal()
    try:
        print("🔐 PostgreSQL Row-Level Security (RLS) Kurulumu Başlatılıyor...")

        # 1. Create franchise_app role if not exists
        db.execute(text("""
            DO $role_block$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'franchise_app') THEN
                    CREATE ROLE franchise_app WITH LOGIN;
                END IF;
            END
            $role_block$;
        """))
        db.commit()

        # Grant permissions to franchise_app
        db.execute(text("GRANT ALL PRIVILEGES ON SCHEMA public TO franchise_app;"))
        db.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO franchise_app;"))
        db.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO franchise_app;"))
        db.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO franchise_app;"))
        db.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO franchise_app;"))
        db.commit()
        print("✅ 'franchise_app' rolü oluşturuldu ve yetkileri verildi.")

        # 2. Setup RLS for tables with direct branch_id
        for table in TABLES_WITH_BRANCH_ID:
            # Enable and force RLS
            db.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            db.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
            
            # Policy
            policy_sql = f"""
                DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                CREATE POLICY tenant_isolation_policy ON {table}
                AS PERMISSIVE
                FOR ALL
                TO PUBLIC
                USING (
                    current_setting('app.is_franchisor_admin', true) = 'true'
                    OR
                    branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
                )
                WITH CHECK (
                    current_setting('app.is_franchisor_admin', true) = 'true'
                    OR
                    branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
                );
            """
            db.execute(text(policy_sql))
            db.commit()
            print(f"✅ RLS aktif edildi: {table}")

        # 3. Setup RLS for role_commission_tiers (via role_id -> roles.branch_id)
        db.execute(text("ALTER TABLE role_commission_tiers ENABLE ROW LEVEL SECURITY;"))
        db.execute(text("ALTER TABLE role_commission_tiers FORCE ROW LEVEL SECURITY;"))
        rct_policy = """
            DROP POLICY IF EXISTS tenant_isolation_policy ON role_commission_tiers;
            CREATE POLICY tenant_isolation_policy ON role_commission_tiers
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                EXISTS (
                    SELECT 1 FROM roles
                    WHERE roles.id = role_commission_tiers.role_id
                      AND roles.branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
                )
            )
            WITH CHECK (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                EXISTS (
                    SELECT 1 FROM roles
                    WHERE roles.id = role_commission_tiers.role_id
                      AND roles.branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
                )
            );
        """
        db.execute(text(rct_policy))
        db.commit()
        print("✅ RLS aktif edildi: role_commission_tiers")

        # 4. Setup RLS for branches table (via id)
        db.execute(text("ALTER TABLE branches ENABLE ROW LEVEL SECURITY;"))
        db.execute(text("ALTER TABLE branches FORCE ROW LEVEL SECURITY;"))
        branch_policy = """
            DROP POLICY IF EXISTS tenant_isolation_policy ON branches;
            CREATE POLICY tenant_isolation_policy ON branches
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
            )
            WITH CHECK (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
            );
        """
        db.execute(text(branch_policy))
        db.commit()
        print("✅ RLS aktif edildi: branches")

        # 5. Setup RLS for notifications table (branch_id nullable for system notifications)
        db.execute(text("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;"))
        db.execute(text("ALTER TABLE notifications FORCE ROW LEVEL SECURITY;"))
        notif_policy = """
            DROP POLICY IF EXISTS tenant_isolation_policy ON notifications;
            CREATE POLICY tenant_isolation_policy ON notifications
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                branch_id IS NULL
                OR
                branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
            )
            WITH CHECK (
                current_setting('app.is_franchisor_admin', true) = 'true'
                OR
                branch_id IS NULL
                OR
                branch_id = NULLIF(current_setting('app.current_branch_id', true), '')::integer
            );
        """
        db.execute(text(notif_policy))
        db.commit()
        print("✅ RLS aktif edildi: notifications")

        print("🎉 Tüm RLS policy'leri başarıyla kuruldu!")

    finally:
        db.close()

if __name__ == "__main__":
    setup_rls()
