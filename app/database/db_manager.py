from app.database.sqlite import local_session
from app.database.postgres import remote_session

async def get_db():
    """Dependency for Main SQLite Database (Local)"""
    async with local_session() as session:
        yield session

async def get_remote_db():
    """Dependency for Remote PostgreSQL Database (Cloud)"""
    if not remote_session:
        raise Exception("Remote Database URL not configured")
    print("DEBUG: Opening remote DB session...")
    try:
        async with remote_session() as session:
            print("DEBUG: Remote DB session opened.")
            yield session
    except Exception as e:
        print(f"DEBUG: Remote DB session failed: {e}")
        raise e
    finally:
        print("DEBUG: Remote DB session closed.")
