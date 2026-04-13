
import asyncio
import uuid
from sqlalchemy import select, func
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey

async def generate_duplicate_report():
    print("\n" + "="*50)
    print("SaaS DATA AUDIT: DUPLICATE DETECTION REPORT")
    print("="*50)

    async with remote_session() as db:
        # 1. Check for Duplicate App Names
        app_sub = select(App.app_name, func.count(App.id).label("count")).group_by(App.app_name).having(func.count(App.id) > 1).subquery()
        app_stmt = select(App).join(app_sub, App.app_name == app_sub.c.app_name).order_by(App.app_name)
        app_result = await db.execute(app_stmt)
        apps = app_result.scalars().all()

        print(f"\n[1] DUPLICATE APPLICATIONS ({len(apps)} found)")
        if not apps:
            print("  ✅ All application names are globally unique.")
        else:
            current_name = None
            for app in apps:
                if app.app_name != current_name:
                    print(f"\n  Name: '{app.app_name}'")
                    current_name = app.app_name
                print(f"    - ID: {app.id} | AppID: {app.app_id} | Created: {app.created_at}")

        # 2. Check for Duplicate Licenses
        # Identity = (app_id, company_name, email, whatsapp_number)
        license_sub = (
            select(
                ActivationKey.app_id, 
                ActivationKey.company_name, 
                ActivationKey.email, 
                ActivationKey.whatsapp_number, 
                func.count(ActivationKey.id).label("count")
            )
            .group_by(
                ActivationKey.app_id, 
                ActivationKey.company_name, 
                ActivationKey.email, 
                ActivationKey.whatsapp_number
            )
            .having(func.count(ActivationKey.id) > 1)
            .subquery()
        )
        
        license_stmt = (
            select(ActivationKey, App.app_name)
            .join(App, ActivationKey.app_id == App.id)
            .join(
                license_sub, 
                (ActivationKey.app_id == license_sub.c.app_id) & 
                (ActivationKey.company_name == license_sub.c.company_name) & 
                (ActivationKey.email == license_sub.c.email) & 
                (ActivationKey.whatsapp_number == license_sub.c.whatsapp_number)
            )
            .order_by(ActivationKey.company_name, ActivationKey.created_at)
        )
        
        license_result = await db.execute(license_stmt)
        licenses = license_result.all()

        print(f"\n[2] DUPLICATE LICENSES ({len(licenses)} found)")
        if not licenses:
            print("  ✅ All license identities are unique.")
        else:
            current_key = None
            for key, app_name in licenses:
                identity = (key.app_id, key.company_name, key.email, key.whatsapp_number)
                if identity != current_key:
                    print(f"\n  Company: '{key.company_name}' | App: '{app_name}'")
                    print(f"  Contact: {key.email or 'N/A'} | {key.whatsapp_number or 'N/A'}")
                    current_key = identity
                print(f"    - ID: {key.id} | Status: {key.status} | Created: {key.created_at}")

        print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(generate_duplicate_report())
