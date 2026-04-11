import os
import sqlcipher3
import sqlite3

DB_NAME = "test_encrypted.db"
PASSWORD = "secret_password"

def test_sqlcipher():
    print("--- SQLCipher Proof-of-Concept ---")
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    
    # 1. Create encrypted DB
    print(f"Creating encrypted DB: {DB_NAME}")
    conn = sqlcipher3.connect(DB_NAME)
    conn.execute(f"PRAGMA key = '{PASSWORD}'")
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO test (val) VALUES ('Sensitive Data')")
    conn.commit()
    conn.close()
    
    # 2. Try to read with standard sqlite3 (MUST FAIL)
    print("Attempting to read with standard sqlite3...")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")
        data = cursor.fetchall()
        print(f"❌ ERROR: Standard sqlite3 read data: {data}")
    except sqlite3.DatabaseError as e:
        print(f"✅ SUCCESS: Standard sqlite3 failed as expected: {e}")
    finally:
        conn.close()

    # 3. Try to read with SQLCipher but WRONG key
    print("Attempting to read with SQLCipher + WRONG key...")
    try:
        conn = sqlcipher3.connect(DB_NAME)
        conn.execute("PRAGMA key = 'wrong_password'")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")
        data = cursor.fetchall()
        print(f"❌ ERROR: SQLCipher with wrong key read data: {data}")
    except Exception as e:
        print(f"✅ SUCCESS: SQLCipher with wrong key failed as expected: {e}")
    finally:
        conn.close()

    # 4. Try to read with SQLCipher + CORRECT key
    print("Attempting to read with SQLCipher + CORRECT key...")
    try:
        conn = sqlcipher3.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{PASSWORD}'")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")
        data = cursor.fetchall()
        print(f"✅ SUCCESS: Correctly read data: {data}")
    except Exception as e:
        print(f"❌ ERROR: SQLCipher with correct key failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_sqlcipher()
