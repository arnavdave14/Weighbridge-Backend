import asyncio
import uuid
from app.database.db_manager import get_remote_db
from app.repositories.admin_repo import AdminRepo
from app.core.security import create_access_token

async def generate_token():
    async for db in get_remote_db():
        admin = await AdminRepo.get_admin_by_email(db, "admin@weighbridge.com")
        if not admin:
            print("Admin not found")
            return

        # Generate new session ID
        new_session_id = str(uuid.uuid4())
        await AdminRepo.update_admin_session(db, admin, new_session_id)
        await db.commit()

        # Issue token
        token = create_access_token(data={
            "sub": admin.email, 
            "root_admin": True,
            "session_id": new_session_id
        })
        print(f"TOKEN_START:{token}:TOKEN_END")
        break

if __name__ == "__main__":
    asyncio.run(generate_token())
