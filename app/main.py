from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes import receipts, auth, bhel, sync
from app.database.sqlite import local_engine
from app.database.postgres import remote_engine
from app.database.base import Base
from app.models.models import (
    Machine, Receipt, ReceiptImage, License, SyncLog, SyncQueue
)
from app.sync.sync_worker import run_sync_worker_loop
from app.config.settings import settings
import uvicorn

import asyncio

app = FastAPI(
    title="Weighbridge Backend",
    description="Production-grade backend for industrial Weighbridge system.",
    version="1.0.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(receipts.router)
app.include_router(bhel.router, tags=["BHEL Integration"])


@app.on_event("startup")
async def startup():
    # 0. Validate Environment & Setup Directories
    settings.validate_and_setup()

    # --- [DEV_MODE] DATABASE RESET LOGIC ---
    if settings.DEV_MODE:
        import os
        print("⚠️  DEV_MODE IS ENABLED: Resetting SQLite Database...")
        db_files = ["./receipts_v2.db", "./data/app.db", "./receipts.db"]
        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                    print(f"   🗑️ Deleted existing database: {db_file}")
                except Exception as e:
                    print(f"   ❌ Error deleting {db_file}: {e}")
        
        # RESET POSTGRESQL SCHEMA (WITH SAFETY)
        if settings.ENVIRONMENT == "development" and remote_engine:
            from sqlalchemy import text
            print("⚠️  DEV_MODE & ENVIRONMENT=development: Resetting PostgreSQL Schema...")
            try:
                async with remote_engine.begin() as conn:
                    await conn.execute(text("DROP SCHEMA public CASCADE;"))
                    await conn.execute(text("CREATE SCHEMA public;"))
                    print("   🗑️ Dropped and recreated PostgreSQL public schema.")
            except Exception as e:
                print(f"   ❌ Error resetting PostgreSQL schema: {e}")
    # ----------------------------------------

    # DEBUG LOGGING (requested by user)
    print("--- [DEBUG] STARTUP TABLE REGISTRATION ---")
    print(f"SQLITE_PATH: {settings.SQLITE_PATH}")
    print(f"SQLITE_URL: {settings.sqlite_url}")
    print(f"Registered tables in Base.metadata: {list(Base.metadata.tables.keys())}")
    
    if "sync_queue" in Base.metadata.tables:
        print("✅ SyncQueue is present in metadata.")
    else:
        print("❌ SyncQueue is MISSING from metadata!")
    print("------------------------------------------")

    # Automatically create tables for Local SQLite
    print(f"Executing create_all() on SQLite engine: {settings.sqlite_url}")
    async with local_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # --- [SCHEMA VERIFICATION] ---
    from sqlalchemy import inspect
    def get_machines_columns(sync_conn):
        inspector = inspect(sync_conn)
        return [c["name"] for c in inspector.get_columns("machines")]

    try:
        async with local_engine.connect() as conn:
            columns = await conn.run_sync(get_machines_columns)
            print(f"✅ SQLite Schema Verification Trace (machines Table): {columns}")
            if "is_synced" in columns:
                print("🚀 Verified: SQLite schema is aligned with models.")
            else:
                print("❗ Warning: New columns are NOT yet visible in SQLite!")
    except Exception as e:
        print(f"⚠️ Could not verify SQLite schema columns: {e}")
    # -----------------------------
    
    # Start the background synchronization task ONLY in development mode with active sync
    if settings.ENVIRONMENT == "development" and settings.DB_MODE in ["dual", "postgres"]:
        asyncio.create_task(run_sync_worker_loop())
    
    # Optionally create tables for Remote PostgreSQL if connected/reachable
    if remote_engine:
        try:
            print(f"Executing create_all() on Remote engine: {settings.postgres_url}")
            async with remote_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Successfully initialized Remote Database tables.")

            # --- [POSTGRESQL SCHEMA VERIFICATION] ---
            try:
                async with remote_engine.connect() as conn:
                    columns = await conn.run_sync(get_machines_columns)
                    print(f"✅ PostgreSQL Schema Verification Trace (machines Table): {columns}")
                    if "is_synced" in columns and "settings" in columns:
                        print("🚀 Verified: PostgreSQL schema is aligned with models.")
                    else:
                        print("❗ Warning: New columns are NOT yet visible in PostgreSQL!")
            except Exception as e:
                print(f"⚠️ Could not verify PostgreSQL schema columns: {e}")
            # ------------------------------------------

        except Exception as e:
            print(f"Could not connect to Remote Database for table creation: {e}")





@app.get("/")
async def root():
    return {
        "message": "Weighbridge API is operational",
        "docs": "/docs",
        "system": "Production-Grade"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
