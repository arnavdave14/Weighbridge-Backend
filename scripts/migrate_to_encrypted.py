import os
import shutil
import sqlite3
import sqlcipher3
import logging
from datetime import datetime
from app.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("migration")

def migrate():
    logger.info("Starting SQLCipher Encryption Migration...")
    
    # 1. Resolve Path
    url = settings.sqlite_url
    db_path = url.split("///", 1)[-1]
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    
    temp_encrypted_path = db_path + ".encrypted.tmp"
    backup_dir = os.path.abspath("./backups")
    backup_path = os.path.join(backup_dir, f"plaintext_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    persistent_backup_path = os.path.join(backup_dir, "plaintext_pre_migration.db")

    if not os.path.exists(db_path):
        logger.error(f"Source database not found at {db_path}. Migration aborted.")
        return

    # 2. Check if already encrypted
    try:
        with open(db_path, "rb") as f:
            header = f.read(16)
        if header != b"SQLite format 3\x00":
            logger.info("✅ Database already appears encrypted (no SQLite magic header). Skipping migration.")
            return
    except Exception as e:
        logger.error(f"Failed to read database header: {e}")
        return

    # 3. Create Backup
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        logger.info(f"Creating backup of plaintext database at {persistent_backup_path}...")
        shutil.copy2(db_path, persistent_backup_path) # Persistent name
        shutil.copy2(db_path, backup_path)           # Timestamped name
        logger.info("✅ Backup successful.")
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}. Migration aborted.")
        return

    # 4. Perform Encryption Migration
    try:
        logger.info(f"Migrating data to encrypted temporary file: {temp_encrypted_path}")
        if os.path.exists(temp_encrypted_path):
            os.remove(temp_encrypted_path)
            
        # Open plaintext DB with sqlcipher3 driver
        conn = sqlcipher3.connect(db_path)
        
        # ATTACH the new encrypted DB
        # Note: We must use the hex-encoded key for safety
        hex_key = settings.DB_MASTER_KEY.encode().hex()
        conn.execute(f"ATTACH DATABASE '{temp_encrypted_path}' AS encrypted KEY \"x'{hex_key}'\"")
        
        # Use SQLCipher's export function to move data
        logger.info("Executing sqlcipher_export...")
        conn.execute("SELECT sqlcipher_export('encrypted')")
        
        # Detach and close
        conn.execute("DETACH DATABASE encrypted")
        conn.close()
        logger.info("✅ Data export successful.")
    except Exception as e:
        logger.error(f"❌ Encryption failed: {e}")
        if os.path.exists(temp_encrypted_path):
            os.remove(temp_encrypted_path)
        return

    # 5. Atomic Swap
    try:
        logger.info("Performing atomic file swap...")
        # Move original to a final backup just in case
        shutil.move(db_path, db_path + ".old")
        # Move encrypted to final destination
        shutil.move(temp_encrypted_path, db_path)
        # Remove the temporary .old file
        os.remove(db_path + ".old")
        logger.info(f"🎉 SUCCESS! Database at {db_path} is now encrypted.")
        logger.info("You can now start the application.")
    except Exception as e:
        logger.error(f"❌ Final swap failed: {e}")
        logger.info(f"Manual recovery might be needed. Temp file: {temp_encrypted_path}")

if __name__ == "__main__":
    migrate()
