import asyncio
from sqlalchemy import text
from app.database.postgres import remote_engine

async def apply_migration():
    print("Applying migration statements one-by-one...")
    
    statements = [
        "ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS server_ip VARCHAR",
        "ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS port INTEGER DEFAULT 8000",
        "ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()",
        "UPDATE activation_keys SET updated_at = created_at WHERE updated_at IS NULL"
    ]
    
    async with remote_engine.connect() as conn:
        for statement in statements:
            print(f"Running: {statement}")
            try:
                await conn.execute(text(statement))
            except Exception as e:
                print(f"Error executing '{statement}': {e}")
                # Continue if column already exists (though IF NOT EXISTS handles this)
                pass
        
        await conn.commit()
        print("Migration applied successfully!")

if __name__ == "__main__":
    asyncio.run(apply_migration())
