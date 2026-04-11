import asyncio
import json
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.postgres import remote_engine
from app.database.sqlite import local_engine

def flatten_values(obj):
    """Flattens all values from a dict/list into a space-separated string."""
    if isinstance(obj, dict):
        return " ".join(flatten_values(v) for v in obj.values())
    elif isinstance(obj, list):
        return " ".join(flatten_values(i) for i in obj)
    else:
        return str(obj)

async def migrate_postgres():
    if not remote_engine:
        print("PostgreSQL engine not configured. Skipping.")
        return

    print("--- Migrating PostgreSQL ---")
    async with remote_engine.begin() as conn:
        # 1. Add columns
        await conn.execute(text("ALTER TABLE receipts ADD COLUMN IF NOT EXISTS payload_json JSONB;"))
        await conn.execute(text("ALTER TABLE receipts ADD COLUMN IF NOT EXISTS image_urls JSONB DEFAULT '[]';"))
        await conn.execute(text("ALTER TABLE receipts ADD COLUMN IF NOT EXISTS search_text TEXT;"))
        print("Columns added.")

        # 2. Fetch existing receipts for migration
        result = await conn.execute(text("SELECT id, gross_weight, tare_weight, rate, custom_data FROM receipts"))
        receipts = result.fetchall()
        
        # 3. Fetch images for migration
        img_result = await conn.execute(text("SELECT receipt_id, image_url FROM receipt_images WHERE image_url IS NOT NULL"))
        images = {}
        for rid, url in img_result.fetchall():
            if rid not in images: images[rid] = []
            images[rid].append(url)

        # 4. Update each receipt
        for r in receipts:
            rid, gross, tare, rate, custom = r
            
            # Construct payload
            data = {
                "gross": float(gross) if gross else 0,
                "tare": float(tare) if tare else 0,
                "net": float(gross - tare) if (gross and tare) else 0,
                "rate": float(rate) if rate else 0
            }
            if custom:
                data.update(custom)
            
            payload = {"data": data}
            payload_str = json.dumps(payload)
            
            # Image URLs
            urls = images.get(rid, [])
            urls_str = json.dumps(urls)
            
            # Search text
            search_text = flatten_values(data)
            
            await conn.execute(text("""
                UPDATE receipts 
                SET payload_json = :payload, 
                    image_urls = :urls, 
                    search_text = :search 
                WHERE id = :id
            """), {"payload": payload_str, "urls": urls_str, "search": search_text, "id": rid})
        
        print(f"Migrated {len(receipts)} receipts in PostgreSQL.")

async def migrate_sqlite():
    if not local_engine:
        print("SQLite engine not configured. Skipping.")
        return

    print("--- Migrating SQLite ---")
    async with local_engine.begin() as conn:
        # SQLite doesn't support JSONB, we'll use TEXT
        # Check if columns exists first (SQLite doesn't have IF NOT EXISTS for ALTER TABLE ADD COLUMN in some versions)
        res = await conn.execute(text("PRAGMA table_info(receipts)"))
        cols = [c[1] for c in res.fetchall()]
        
        if "payload_json" not in cols:
            await conn.execute(text("ALTER TABLE receipts ADD COLUMN payload_json TEXT;"))
        if "image_urls" not in cols:
            await conn.execute(text("ALTER TABLE receipts ADD COLUMN image_urls TEXT DEFAULT '[]';"))
        if "search_text" not in cols:
            await conn.execute(text("ALTER TABLE receipts ADD COLUMN search_text TEXT;"))
        
        print("Columns added/verified.")

        # Sync same logic as Postgres
        result = await conn.execute(text("SELECT id, gross_weight, tare_weight, rate, custom_data FROM receipts"))
        receipts = result.fetchall()
        
        # Fetch images from local table
        # Note: Local images might still be in binary format if not uploaded, 
        # but the request says migrate URLs. Binary data should probably be handled separately or left.
        # User said: "Extract image URLs from old ReceiptImage table"
        img_result = await conn.execute(text("SELECT receipt_id, image_url FROM receipt_images WHERE image_url IS NOT NULL"))
        images = {}
        for rid, url in img_result.fetchall():
            if rid not in images: images[rid] = []
            images[rid].append(url)

        for r in receipts:
            rid, gross, tare, rate, custom_str = r
            custom = json.loads(custom_str) if custom_str else {}
            
            data = {
                "gross": float(gross) if gross else 0,
                "tare": float(tare) if tare else 0,
                "net": float(gross - tare) if (gross and tare) else 0,
                "rate": float(rate) if rate else 0
            }
            data.update(custom)
            
            payload = {"data": data}
            search_text = flatten_values(data)
            urls = images.get(rid, [])
            
            # SQLite uses strings for JSON
            await conn.execute(text("""
                UPDATE receipts 
                SET payload_json = :payload, 
                    image_urls = :urls, 
                    search_text = :search 
                WHERE id = :id
            """), {
                "payload": json.dumps(payload), 
                "urls": json.dumps(urls), 
                "search": search_text, 
                "id": rid
            })
            
        print(f"Migrated {len(receipts)} receipts in SQLite.")

async def main():
    await migrate_sqlite()
    await migrate_postgres()

if __name__ == "__main__":
    asyncio.run(main())
