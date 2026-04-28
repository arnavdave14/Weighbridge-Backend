import asyncio
from app.database.postgres import remote_session
from app.models.admin_models import AdminUser
from sqlalchemy import select, update
from app.core.security import get_password_hash

async def main():
    async with remote_session() as db:
        email = "ticketemailsender01@gmail.com"
        password = "Sahil@1234"
        hashed_pw = get_password_hash(password)
        
        # See if the target email already exists
        result = await db.execute(select(AdminUser).where(AdminUser.email == email))
        target_admin = result.scalar_one_or_none()
        
        if target_admin:
            print("Email already exists. Updating password.")
            target_admin.hashed_password = hashed_pw
        else:
            # Just take the first admin and update their email and password
            result = await db.execute(select(AdminUser).limit(1))
            first_admin = result.scalar_one_or_none()
            if first_admin:
                print(f"Updating admin {first_admin.email} to {email}")
                first_admin.email = email
                first_admin.hashed_password = hashed_pw
            else:
                print("No admin found. Creating new.")
                new_admin = AdminUser(email=email, hashed_password=hashed_pw)
                db.add(new_admin)
            
        await db.commit()
        print("Done!")

if __name__ == '__main__':
    asyncio.run(main())
