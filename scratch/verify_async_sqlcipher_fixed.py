import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sqlcipher3
import aiosqlite

DB_NAME = "test_async_hacker_fixed.db"
PASSWORD = "secret_password"

async def test_async_sqlcipher_fixed():
    print("--- Async SQLCipher (aiosqlite + SQLCIPHER FACTORY) Proof-of-Concept ---")
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    # 1. Custom Creator that forces aiosqlite to use sqlcipher3's Connection
    async def custom_creator():
        print("Creating connection with sqlcipher3 factory...")
        # sqlcipher3.dbapi2 is the module-level entry for sqlcipher3
        return await aiosqlite.connect(DB_NAME, factory=sqlcipher3.dbapi2.Connection)

    # Note: We still use sqlite+aiosqlite but with our custom connection factory
    engine = create_async_engine(
        "sqlite+aiosqlite:///",
        async_creator=custom_creator
    )

    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        # dbapi_connection should now be a sqlcipher3.dbapi2.Connection
        print(f"Injecting key into {type(dbapi_connection)}...")
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA key = '{PASSWORD}'")
        # Force a write to ensure encryption is applied
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.close()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE test (val TEXT)"))
        await conn.execute(text("INSERT INTO test VALUES ('FIXED Async Encrypted Data')"))
    
    await engine.dispose()
    
    # VERIFY
    print("\nVerifying if standard sqlite3 can read it...")
    import sqlite3
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("SELECT * FROM test")
        print("❌ ERROR: Standard sqlite3 read it!")
    except Exception as e:
        print(f"✅ SUCCESS: Standard sqlite3 failed (as it should): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(test_async_sqlcipher_fixed())
