from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import receipts, auth
from app.db.session import engine, Base
from app.models import models
import uvicorn

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
app.include_router(receipts.router)

@app.on_event("startup")
async def startup():
    # Automatically create tables (for demo/quick-start, in prod use Alembic)
    # WARNING: THIS WILL OVERWRITE EXISTING TABLES if they conflict.
    # But for a fresh project like this, it ensures the DB is ready.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {
        "message": "Weighbridge API is operational",
        "docs": "/docs",
        "system": "Production-Grade"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
