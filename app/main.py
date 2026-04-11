from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import receipts, auth, bhel, sync, admin_apps, activation, notifications, admin_auth, admin_branding, admin_dlq, admin_receipts, employee_auth, integrity
from prometheus_fastapi_instrumentator import Instrumentator
from app.database.sqlite import local_engine
from app.database.postgres import remote_engine
from app.database.base import Base
from app.models.models import (
    Machine, Receipt, ReceiptImage, License, SyncLog, SyncQueue
)
# Employee model must be imported before create_all() so SQLAlchemy
# registers the 'employees' table in Base.metadata for both SQLite and PostgreSQL.
from app.models.employee_model import Employee  # noqa: F401
from app.sync.sync_worker import run_sync_worker_loop
from app.config.settings import settings
import uvicorn
import asyncio
import logging

logger = logging.getLogger(__name__)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database.sqlite import local_engine, verify_encryption, local_session, migrate_sqlite_schema
from app.services.integrity_service import IntegrityService
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: "FastAPI"):
    # --- STARTUP ---
    # 0. Validate Environment & Setup Directories
    settings.validate_and_setup()
    
    # --- [DATABASE INITIALIZATION] ---
    # Automatically create/migrate tables for Local SQLite
    logger.info("Initializing Local Database (SQLite)...")
    async with local_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate_sqlite_schema)
        
    # 1. Proactively verify SQLCipher Encryption (Strict enforcement)
    await verify_encryption()

    # 2. Verify Data Integrity (Dynamic startup check)
    async with local_session() as db:
        startup_report = await IntegrityService.verify_startup_integrity(db)
        app.state.integrity_failed = not startup_report["is_valid"]
        
        if app.state.integrity_failed:
            logger.critical("🚨 DATA INTEGRITY VIOLATION DETECTED DURING STARTUP: %s", startup_report.get("error_msg"))
        else:
            total = startup_report.get("total_checked", 0)
            logger.info("✅ Partial Data Integrity Verified (%s records). Chain is healthy.", total)
            
            # If we only did a partial check, trigger a full background audit
            if total >= IntegrityService.DYNAMIC_STARTUP_THRESHOLD:
                logger.info("⏳ Scheduling full background integrity audit...")
                
                async def full_audit_task():
                    async with local_session() as bg_db:
                        full_report = await IntegrityService.verify_chain_integrity(bg_db)
                        if not full_report["is_valid"]:
                            app.state.integrity_failed = True
                            logger.critical("🚨 BACKGROUND INTEGRITY AUDIT FAILED: %s", full_report.get("error_msg"))
                        else:
                            logger.info("✅ Full Background Integrity Audit Completed Successfully.")

                asyncio.create_task(full_audit_task())

    # Start the background synchronization task ONLY in development mode
    if settings.ENVIRONMENT == "development" and settings.DB_MODE in ["dual", "postgres"]:
        asyncio.create_task(run_sync_worker_loop())
    
    # Initialize Remote Database tables if available
    if remote_engine:
        try:
            from app.database.admin_base import AdminBase
            import app.models.admin_models
            async with remote_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(AdminBase.metadata.create_all)
            logger.info("Successfully initialized Remote Database tables.")
        except Exception as e:
            logger.error(f"Could not connect to Remote Database: {e}")

    yield

    # --- SHUTDOWN ---
    pass

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Weighbridge Backend",
    description="Production-grade backend for industrial Weighbridge system.",
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class LocalAPIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Hardened Local API protection.
        Explicitly allows public utility routes and delegated auth routes (Admin/Sync).
        Mandates X-Local-Secret for all device-facing worker APIs.
        """
        # Strict Allowlist: paths that do NOT require X-Local-Secret
        allowlist = (
            "/health", "/metrics", "/static", "/docs", "/redoc", "/openapi.json",
            "/admin",  # Protected by Admin JWT
            "/sync",   # Protected by HMAC
        )
        
        path = request.url.path
        if path == "/" or any(path.startswith(prefix) for prefix in allowlist):
            return await call_next(request)
            
        # Protect local device APIs (e.g. /receipts, /auth, /employee, /bhel, etc.)
        # strictly when running on an edge device context.
        if settings.DB_MODE in ["local", "dual"]:
            header_secret = request.headers.get("x-local-secret")
            if header_secret != settings.LOCAL_API_SECRET:
                logger.warning(
                    "Blocked unauthorized local API access attempt to %s from %s",
                    path, request.client.host if request.client else "unknown"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Forbidden: Secure Local API Secret missing or invalid."}
                )
                
        return await call_next(request)

app.add_middleware(LocalAPIAuthMiddleware)

# Prometheus Instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

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

# Admin Routes
app.include_router(admin_auth.router)
app.include_router(admin_apps.router)
app.include_router(activation.router)
app.include_router(notifications.router)
app.include_router(admin_branding.router)
app.include_router(admin_dlq.router)
app.include_router(admin_receipts.router)

# Employee Auth (device-facing + admin employee management)
app.include_router(employee_auth.router)

# Integrity Routes
app.include_router(integrity.router)

# Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")







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
