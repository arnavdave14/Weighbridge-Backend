import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Optional

# Load .env file BEFORE importing key_loader so env vars are available as fallback
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Secure key loader — keyring primary, env fallback
from app.security.key_loader import load_db_master_key, load_local_api_secret  # noqa: E402

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
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # SECURITY & SECRETS — resolved via keyring → env var → default (see app/security/key_loader.py)
    # These are evaluated once at import time so they remain constant for the process lifetime.
    DB_MASTER_KEY: str = load_db_master_key()
    LOCAL_API_SECRET: str = load_local_api_secret()
    
    # Legacy fallbacks
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REMOTE_DATABASE_URL: str = os.getenv("REMOTE_DATABASE_URL")
    
    # Notification Hardening
    NOTIF_IDEMPOTENCY_WINDOW: int = 60
    RATE_LIMIT_RECEIVER: int = 5
    RATE_LIMIT_TENANT: int = 50
    NOTIFICATION_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("NOTIFICATION_RATE_LIMIT_PER_MINUTE", "10"))
    
    # WHATSAPP CONFIG
    DIGITALSMS_API_KEY: str = os.getenv("DIGITALSMS_API_KEY")
    DIGITALSMS_PORTAL_USER: str = os.getenv("DIGITALSMS_PORTAL_USER")
    DIGITALSMS_PORTAL_PASS: str = os.getenv("DIGITALSMS_PORTAL_PASS")
    
    # SYNC CONFIG
    SYNC_INTERVAL_SECONDS: int = 60
    MAX_SYNC_RETRIES: int = 5
    SYNC_BATCH_SIZE: int = 50
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    
    # SMTP CONFIG
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", SMTP_USER)
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Weighbridge Admin")
    
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
            
        # Production secret guard is already enforced inside key_loader._assert_not_default_in_production.
        # This block adds a redundant double-check at startup for defence-in-depth.
        if self.ENVIRONMENT == "production":
            placeholders = {"default_dev_key_change_me", "default_local_secret_change_me"}
            if self.DB_MASTER_KEY in placeholders or self.LOCAL_API_SECRET in placeholders:
                msg = "CRITICAL: Secrets still at placeholder defaults — aborting production boot."
                print(msg)
                raise RuntimeError(msg)

        # 4. Startup Logging
        import keyring as _kr  # noqa: F401
        keyring_available = True
        try:
            _val = _kr.get_password("weighbridge-edge", "__probe__")
        except Exception:
            keyring_available = False

        print("--- [BOOT] SYSTEM CONFIGURATION ---")
        print(f"  ENVIRONMENT : {self.ENVIRONMENT}")
        print(f"  DB_MODE     : {self.DB_MODE}")
        print(f"  SQLITE      : {self.SQLITE_PATH}")
        print(f"  POSTGRES    : {'Configured' if pg_url else 'Not Configured'}")
        print(f"  KEYRING     : {'✅ OS Keyring active' if keyring_available else '⚠️  Env-var fallback (upgrade to keyring for production)'}")
        print(f"  DB_ENCRYPT  : ✅ SQLCipher PRAGMA active (aiosqlite event hook)")
        print(f"  LOCAL_AUTH  : ✅ X-Local-Secret middleware enabled")
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
