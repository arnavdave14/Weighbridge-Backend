import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

async def get_token():
    load_dotenv()
    # Use the async URL from .env or construct it
    pg_url = os.getenv("POSTGRES_URL")
    if not pg_url:
        print("POSTGRES_URL not found in .env")
        return

    engine = create_async_engine(pg_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            result = await session.execute(text("SELECT token FROM activation_keys LIMIT 1;"))
            token = result.scalar()
            if token:
                print(f"TOKEN:{token}")
            else:
                print("No tokens found in activation_keys table.")
        except Exception as e:
            print(f"Error fetching token: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_token())
