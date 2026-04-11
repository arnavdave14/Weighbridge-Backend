import os
import sys

def verify_encryption(db_path):
    """
    Standalone script to verify SQLCipher encryption of a SQLite file.
    Checks for the absence of the 'SQLite format 3\x00' magic header.
    """
    if not os.path.exists(db_path):
        print(f"❌ Error: Database file not found at {db_path}")
        sys.exit(1)

    try:
        with open(db_path, "rb") as f:
            header = f.read(16)
        
        SQLITE_MAGIC = b"SQLite format 3\x00"
        
        if header == SQLITE_MAGIC:
            print(f"⚠️  VULNERABLE: Database '{db_path}' is PLAINTEXT (Header matches SQLite magic bytes).")
            return False
        else:
            print(f"✅ SECURE: Database '{db_path}' is ENCRYPTED (Header is ciphertext).")
            return True
            
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Default to data/app.db if no arg provided
    target_db = sys.argv[1] if len(sys.argv) > 1 else "./data/app.db"
    
    print(f"Testing encryption on: {target_db}")
    if verify_encryption(target_db):
        sys.exit(0)
    else:
        sys.exit(1)
