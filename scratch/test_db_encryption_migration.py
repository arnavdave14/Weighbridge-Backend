import os
import sqlite3
import sqlcipher3

PLAINTEXT_DB = "test_plain.db"
ENCRYPTED_DB = "test_encrypted_migration.db"
PASSWORD = "secret_password"

def test_migration():
    print("--- SQLCipher Migration Proof-of-Concept ---")
    
    if os.path.exists(PLAINTEXT_DB): os.remove(PLAINTEXT_DB)
    if os.path.exists(ENCRYPTED_DB): os.remove(ENCRYPTED_DB)
    
    # 1. Create a plaintext DB
    print("Creating plaintext DB...")
    conn = sqlite3.connect(PLAINTEXT_DB)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob')")
    conn.commit()
    conn.close()
    
    # 2. Use SQLCipher to encrypt it
    print(f"Migrating {PLAINTEXT_DB} to encrypted {ENCRYPTED_DB}...")
    # Open the plaintext DB using sqlcipher3 driver
    conn = sqlcipher3.connect(PLAINTEXT_DB)
    # Note: NO PRAGMA key here because it's initially plaintext
    
    # Use ATTACH to create the new encrypted file
    conn.execute(f"ATTACH DATABASE '{ENCRYPTED_DB}' AS encrypted KEY '{PASSWORD}'")
    
    # Export all data to the new DB
    conn.execute("SELECT sqlcipher_export('encrypted')")
    
    # Detach and close
    conn.execute("DETACH DATABASE encrypted")
    conn.close()
    
    # 3. VERIFY
    print("\nVerifying encrypted DB...")
    try:
        conn = sqlite3.connect(ENCRYPTED_DB)
        conn.execute("SELECT * FROM users")
        print("❌ ERROR: Standard sqlite3 read the migrated DB!")
    except Exception as e:
        print(f"✅ SUCCESS: Standard sqlite3 failed to read migrated DB: {e}")
    finally:
        conn.close()

    print("\nReading with SQLCipher + Correct Key...")
    try:
        conn = sqlcipher3.connect(ENCRYPTED_DB)
        conn.execute(f"PRAGMA key = '{PASSWORD}'")
        res = conn.execute("SELECT * FROM users").fetchall()
        print(f"✅ SUCCESS: Read migrated data: {res}")
    except Exception as e:
        print(f"❌ ERROR: SQLCipher failed to read migrated DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_migration()
