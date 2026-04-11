
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_engine
from app.database.sqlite import local_engine

async def make_columns_nullable():
    # PostgreSQL
    if remote_engine:
        print("--- Updating PostgreSQL Columns ---")
        async with remote_engine.connect() as conn:
            for col in ["gross_weight", "tare_weight", "rate", "truck_no"]:
                try:
                    await conn.execute(text(f"ALTER TABLE receipts ALTER COLUMN {col} DROP NOT NULL"))
                    print(f"Fixed {col} in PostgreSQL")
                except Exception as e:
                    print(f"PostgreSQL {col} update skip/fail: {e}")
            await conn.commit()

    # SQLite (Attempting simple ALTER TABLE - might fail depending on SQLite version)
    if local_engine:
        print("--- Updating SQLite Columns (Attempt) ---")
        async with local_engine.connect() as conn:
            # Note: SQLite doesn't support DROP NOT NULL via ALTER TABLE easily.
            # We will try a simple rename/recreate approach if needed, 
            # but first let's see if we can just set them to nullable.
            cols = ["gross_weight", "tare_weight", "rate", "truck_no"]
            
            # Since SQLite is fragile with ALTER TABLE, we'll use a safer approach:
            # We'll check if we CAN just provide a default value in SyncService instead.
            # BUT, for the sake of completeness, let's try to detect current NULL-ability.
            print("SQLite doesn't support 'DROP NOT NULL'. We will handle this by providing default 0.0 in SyncService.")

if __name__ == "__main__":
    asyncio.run(make_columns_nullable())
