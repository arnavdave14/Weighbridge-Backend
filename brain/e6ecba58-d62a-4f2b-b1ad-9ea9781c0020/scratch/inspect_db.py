
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_engine

async def inspect_schema():
    if not remote_engine:
        print("No remote engine configured.")
        return
    
    tables = [
        "admin_users", "apps", "activation_keys", "activation_key_schemas", 
        "machine_nonces", "notifications", "admin_otps", "failed_notifications"
    ]
    
    async with remote_engine.connect() as conn:
        for table in tables:
            print(f"\n--- {table} ---")
            result = await conn.execute(text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """))
            columns = result.fetchall()
            if not columns:
                print("Table does not exist.")
            for col in columns:
                print(f"- {col[0]} ({col[1]})")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
