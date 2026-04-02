import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Optional

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class Settings:
    PROJECT_NAME: str = "Weighbridge Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() == "true"
    
    # DATABASE CONFIG (Standardized)
    DB_MODE: str = os.getenv("DB_MODE", "dual")  # dual / local / postgres
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "./data/app.db")
    POSTGRES_URL: str = os.getenv("POSTGRES_URL")
    
    # Legacy fallbacks
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REMOTE_DATABASE_URL: str = os.getenv("REMOTE_DATABASE_URL")
    
    # WHATSAPP CONFIG
    DIGITALSMS_API_KEY: str = os.getenv("DIGITALSMS_API_KEY")
    DIGITALSMS_PORTAL_USER: str = os.getenv("DIGITALSMS_PORTAL_USER")
    DIGITALSMS_PORTAL_PASS: str = os.getenv("DIGITALSMS_PORTAL_PASS")
    
    # SYNC CONFIG
    SYNC_INTERVAL_SECONDS: int = 60
    MAX_SYNC_RETRIES: int = 5
    SYNC_BATCH_SIZE: int = 50
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    
    # UPLOAD CONFIG
    UPLOAD_DIR: str = "static/uploads"

    def validate_and_setup(self):
        """Ensures the environment is valid and ready for operation."""
        # 1. Directory Setup for SQLite
        sqlite_file = Path(self.SQLITE_PATH)
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)

        # 2. Directory Setup for Uploads (including subfolders)
        upload_path = Path(self.UPLOAD_DIR)
        upload_path.mkdir(parents=True, exist_ok=True)
        (upload_path / "logos").mkdir(parents=True, exist_ok=True)
        (upload_path / "signups").mkdir(parents=True, exist_ok=True)
        
        # 3. Environment Validation
        pg_url = self.POSTGRES_URL or self.REMOTE_DATABASE_URL
        if self.DB_MODE in ["dual", "postgres"] and not pg_url:
            msg = f"CRITICAL: POSTGRES_URL is required when DB_MODE is '{self.DB_MODE}'."
            print(msg)
            raise RuntimeError(msg)

        # 3. Startup Logging
        print("--- [BOOT] SYSTEM CONFIGURATION ---")
        print(f"MODE: {self.DB_MODE}")
        print(f"SQLITE: {self.SQLITE_PATH}")
        print(f"POSTGRES: {'Configured' if pg_url else 'Not Configured'}")
        print(f"ENVIRONMENT: {self.ENVIRONMENT}")
        print("-----------------------------------")

    @property
    def sqlite_url(self) -> str:
        """
        Derive SQLite adapter URL.
        Priority: 
        1. DATABASE_URL (if exists in .env)
        2. SQLITE_PATH (converted to aiosqlite format)
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
            
        if self.SQLITE_PATH:
            if self.SQLITE_PATH.startswith("sqlite"):
                return self.SQLITE_PATH
            # Ensure it uses absolute path if not prefixed
            abs_path = os.path.abspath(self.SQLITE_PATH)
            return f"sqlite+aiosqlite:///{abs_path}"
            
        return "sqlite+aiosqlite:///./data/app.db"

    @property
    def postgres_url(self) -> Optional[str]:
        """Standardized access to PostgreSQL remote engine URL."""
        url = self.POSTGRES_URL or self.REMOTE_DATABASE_URL
        if not url:
            return None
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url.replace("?sslmode=disable", "")

settings = Settings()
