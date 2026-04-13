
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_engine

async def run_migrations():
    print("--- Running DB Migrations for Enterprise Hardening ---")
    async with remote_engine.begin() as conn:
        # 1. Add columns to 'apps' for soft-delete
        print("Adding soft-delete columns to 'apps'...")
        try:
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
            print("✅ 'apps' columns added.")
        except Exception as e:
            print(f"⚠️ 'apps' columns error: {e}")

        # 1b. Add SMTP columns to 'apps'
        print("Adding SMTP columns to 'apps'...")
        try:
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_enabled BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_host VARCHAR DEFAULT 'smtp.gmail.com'"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_port INTEGER DEFAULT 587"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_user VARCHAR"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_password VARCHAR"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS from_email VARCHAR"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS from_name VARCHAR"))
            await conn.execute(text("ALTER TABLE apps ADD COLUMN IF NOT EXISTS smtp_status VARCHAR DEFAULT 'UNTESTED'"))
            print("✅ 'apps' SMTP columns added.")
        except Exception as e:
            print(f"⚠️ 'apps' SMTP columns error: {e}")

        # 2. Add lifecycle columns to 'activation_keys'
        print("Adding lifecycle columns to 'activation_keys'...")
        try:
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP WITH TIME ZONE"))
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS expired_at TIMESTAMP WITH TIME ZONE"))
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1"))
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS last_notification_sent TIMESTAMP WITH TIME ZONE"))
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
            print("✅ 'activation_keys' columns added.")
        except Exception as e:
            print(f"⚠️ 'activation_keys' columns error: {e}")

        # 3. Create/Update ActivationKeyHistory Table
        print("Creating/Updating ActivationKeyHistory table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activation_key_history (
                    id UUID PRIMARY KEY,
                    activation_key_id UUID NOT NULL REFERENCES activation_keys(id) ON DELETE CASCADE,
                    prev_status VARCHAR,
                    new_status VARCHAR NOT NULL,
                    prev_expiry TIMESTAMP WITH TIME ZONE,
                    new_expiry TIMESTAMP WITH TIME ZONE,
                    reason VARCHAR NOT NULL,
                    changed_by UUID REFERENCES admin_users(id),
                    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            # Ensure column exists if table was already there
            await conn.execute(text("ALTER TABLE activation_key_history ADD COLUMN IF NOT EXISTS changed_by UUID REFERENCES admin_users(id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_key_id ON activation_key_history(activation_key_id)"))
            print("✅ 'activation_key_history' table updated.")
        except Exception as e:
            print(f"❌ Error updating history table: {e}")

        # 4. Create Partial Unique Index
        print("Creating partial unique index for ACTIVE licenses...")
        try:
            # We use a naming convention for the index
            index_name = "uq_active_license_identity"
            await conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
            await conn.execute(text(f"""
                CREATE UNIQUE INDEX {index_name} 
                ON activation_keys (app_id, company_name, email, whatsapp_number)
                WHERE status IN ('ACTIVE', 'EXPIRING_SOON')
            """))
            print("✅ Partial unique index created.")
        except Exception as e:
            print(f"❌ Error creating index: {e}")

    print("--- Migrations Complete ---")

if __name__ == "__main__":
    asyncio.run(run_migrations())
