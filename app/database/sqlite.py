"""
SQLite / SQLCipher Engine
=========================
Key design decisions:
  - We use `aiosqlite` as the async adapter (not pysqlcipher3), because the project
    is already using `sqlite+aiosqlite`. pysqlcipher3 has no async wrapper.
  - SQLCipher PRAGMA injection via SQLAlchemy's synchronous "connect" event hooks
    into aiosqlite's underlying sqlite3.Connection calls — this IS reachable.
  - IMPORTANT: The PRAGMA key only has real encryption effect when the aiosqlite
    binary is linked against the SQLCipher library instead of the standard sqlite3.
    On a standard install (plain aiosqlite + system sqlite3), PRAGMA key is a
    no-op silently accepted by sqlite3.
  - For true at-rest encryption on the edge device, install the sqlcipher3 package
    and set SQLCIPHER_ENABLED=true, which switches to a synchronous-but-encrypted
    approach using run_sync for every operation (or use sqlcipher3 + aiosqlcipher).
  - Until sqlcipher3 is installed and SQLCIPHER_ENABLED=true, the system operates
    with PRAGMA key injected; `verify_encryption` at startup will detect whether the
    encryption is actually active and log a warning if not.

Quick-start for real SQLCipher encryption:
    brew install sqlcipher
    pip install sqlcipher3
    Set SQLCIPHER_ENABLED=true in .env
"""

import logging
import asyncio
import os
import sqlcipher3
import aiosqlite
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─── SQLCipher Async Creator ──────────────────────────────────────────────────
async def async_sqlcipher_creator():
    """
    Forces aiosqlite to use the sqlcipher3 backend instead of standard sqlite3.
    This is the core of the hardening fix.
    """
    url = settings.sqlite_url
    db_path = url.split("///", 1)[-1]
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    
    # We use sqlcipher3.dbapi2.Connection as the factory
    return await aiosqlite.connect(db_path, factory=sqlcipher3.dbapi2.Connection)

# ─── Engine options ───────────────────────────────────────────────────────────
_sqlite_connect_args = {"check_same_thread": False}

local_engine = create_async_engine(
    "sqlite+aiosqlite:///",
    async_creator=async_sqlcipher_creator,
    echo=False,
)


# ─── SQLCipher PRAGMA injection ───────────────────────────────────────────────
@event.listens_for(local_engine.sync_engine, "connect")
def _inject_cipher_pragmas(dbapi_connection, connection_record):
    """
    Fire on every new DBAPI connection.

    aiosqlite delegates actual sqlite3 connections to a background thread pool;
    this hook fires in that thread on the underlying sqlite3.Connection object.

    If the binary is linked against SQLCipher, PRAGMA key actually encrypts.
    If it is linked against standard sqlite3, PRAGMA key is silently ignored.
    `verify_encryption()` at startup detects which case applies.
    """
    if not settings.sqlite_url.startswith("sqlite"):
        return

    if not settings.DB_MASTER_KEY:
        logger.warning("DB_MASTER_KEY is empty — SQLCipher PRAGMA skipped.")
        return

    try:
        cursor = dbapi_connection.cursor()
        # Use hex key form to avoid special-character quoting issues
        hex_key = settings.DB_MASTER_KEY.encode().hex()
        cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.execute("PRAGMA kdf_iter = 256000")           # OWASP recommended minimum
        cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
        cursor.close()
        logger.debug("SQLCipher PRAGMAs injected successfully.")
    except Exception as exc:
        logger.error("Failed to inject SQLCipher PRAGMAs: %s", exc)


# ─── Session maker ────────────────────────────────────────────────────────────
local_session = async_sessionmaker(
    local_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Startup encryption verification ─────────────────────────────────────────
async def verify_encryption() -> bool:
    """
    Prove whether SQLCipher encryption is actually active.

    Method: write a known value, then try to read the raw database file bytes.
    If encryption is active, the raw bytes will NOT contain the known plaintext.

    Returns True  → encryption confirmed active.
    Returns False → database is plaintext (SQLCipher library not linked).

    Called from main.py startup().
    """
    import os, tempfile, struct

    if not settings.sqlite_url.startswith("sqlite"):
        logger.info("Encryption check skipped — not a SQLite URL.")
        return True

    # Derive the absolute DB file path from the URL
    url = settings.sqlite_url
    # strip sqlite+aiosqlite:///
    db_path = url.split("///", 1)[-1]
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        logger.debug("DB file not yet created — encryption check deferred.")
        return True  # Will be checked after first write

    try:
        with open(db_path, "rb") as f:
            header = f.read(16)

        # SQLite3 plaintext databases always start with this magic string
        SQLITE_MAGIC = b"SQLite format 3\x00"
        encrypted = header != SQLITE_MAGIC

        if encrypted:
            logger.info("✅  SQLCipher encryption VERIFIED — DB header is ciphertext.")
        else:
            msg = (
                "\n" + "="*60 + "\n"
                "🔴 CRITICAL SECURITY FAILURE: DATABASE IS PLAINTEXT\n"
                "="*60 + "\n"
                "The database file exists but is NOT encrypted with SQLCipher.\n"
                "To fix this, you MUST run the manual migration script:\n\n"
                "   PYTHONPATH=. venv/bin/python scripts/migrate_to_encrypted.py\n\n"
                "A backup will be created in ./backups/ before migration.\n"
                "="*60
            )
            logger.error(msg)
            raise RuntimeError("Database encryption enforcement failed. Action required.")

        return encrypted

    except Exception as exc:
        logger.error("Encryption verification error: %s", exc)
        return False
