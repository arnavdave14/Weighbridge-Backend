import asyncio
import os
import sys

# Ensure 'app' is in path
sys.path.append(os.getcwd())

from app.database.postgres import remote_session
from app.models.admin_models import DocumentDeliveryLog
from sqlalchemy import select

async def check_logs():
    print("Checking DocumentDeliveryLog in PostgreSQL...")
    try:
        async with remote_session() as db:
            res = await db.execute(select(DocumentDeliveryLog))
            logs = res.scalars().all()
            print(f"Total Logs found: {len(logs)}")
            for log in logs[:10]:
                print(f" - {log.company_name} | {log.document_name} | {log.status} | {log.created_at}")
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_logs())
