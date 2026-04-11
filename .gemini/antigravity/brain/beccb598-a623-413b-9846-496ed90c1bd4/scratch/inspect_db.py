import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import json
import uuid
from datetime import datetime

# DB URL from .env
POSTGRES_URL = "postgresql+asyncpg://weighbridge_user:strongpassword@localhost/weighbridge_db"

async def inspect():
    engine = create_async_engine(POSTGRES_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n--- [TABLE: apps] ---")
        apps = await session.execute(text("SELECT id, app_id, app_name, created_at FROM apps ORDER BY created_at DESC LIMIT 5"))
        for row in apps:
            print(f"ID: {row.id} | APP_ID: {row.app_id} | Name: {row.app_name}")

        print("\n--- [TABLE: activation_keys] ---")
        keys = await session.execute(text("SELECT id, app_id, company_name, labels, status, created_at FROM activation_keys ORDER BY created_at DESC LIMIT 5"))
        for row in keys:
            # Format labels for readability
            labels_json = json.dumps(row.labels, indent=2) if row.labels else "[]"
            print(f"ID: {row.id} | Company: {row.company_name} | Status: {row.status}")
            print(f"Labels Config: {labels_json}\n")

        print("\n--- [TABLE: employees] ---")
        # Checking schema for employees table name (usually employees or employee)
        try:
            emps = await session.execute(text("SELECT id, name, username, email, key_id, role, is_active FROM employees ORDER BY created_at DESC LIMIT 5"))
            for row in emps:
                print(f"ID: {row.id} | Name: {row.name} | User: {row.username} | Role: {row.role} | Key_ID: {row.key_id}")
        except Exception as e:
            print(f"Error querying employees: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
