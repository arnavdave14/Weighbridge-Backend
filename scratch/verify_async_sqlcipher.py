import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import sqlcipher3

DB_NAME = "test_async_encrypted.db"
PASSWORD = "secret_password"

async def test_async_sqlcipher():
    print("--- Async SQLCipher (aiosqlite + custom creator) Proof-of-Concept ---")
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    # The Trick: Tell aiosqlite to use sqlcipher3's connection factory
    import aiosqlite
    
    async def custom_creator():
        # aiosqlite.connect returns a connection object that wraps the worker thread
        # We need it to use sqlcipher3 inside the worker thread
        conn = await aiosqlite.connect(DB_NAME)
        # However, aiosqlite doesn't easily let us inject PRAGMA key BEFORE any other ops
        # without a bit of work.
        
        # Actually, let's try the SQLAlchemy "connect" event approach first
        return conn

    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_NAME}")

    from sqlalchemy import event
    
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        # This runs in the aiosqlite worker thread
        # Important: dbapi_connection is a standard sqlite3 connection unless we swap it
        print("Injecting key via PRAGMA...")
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA key = '{PASSWORD}'")
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.close()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE test (val TEXT)"))
        await conn.execute(text("INSERT INTO test VALUES ('Async Encrypted Data')"))
    
    await engine.dispose()
    
    # VERIFY
    print("\nVerifying if standard sqlite3 can read it...")
    import sqlite3
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("SELECT * FROM test")
        print("❌ ERROR: Standard sqlite3 read it!")
    except Exception as e:
        print(f"✅ SUCCESS: Standard sqlite3 failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(test_async_sqlcipher())
