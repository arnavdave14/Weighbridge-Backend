import asyncio
import os
import sys

# Force a temporary DB for testing
os.environ["SQLITE_PATH"] = "test_startup.db"
os.environ["DEV_MODE"] = "True" # Trigger reset logic

from app.main import startup
from app.database.sqlite import local_engine, local_session
from app.database.base import Base

async def test():
    print("--- Running Startup Logic Test ---")
    try:
        await startup()
        print("✅ Startup logic completed successfully!")
    except Exception as e:
        print(f"❌ Startup logic failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if os.path.exists("test_startup.db"):
            os.remove("test_startup.db")

if __name__ == "__main__":
    asyncio.run(test())
