import asyncio
import argparse
import random
import uuid
import os
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

# Project Imports
from app.config.settings import settings
from app.database.postgres import remote_engine, remote_session
from app.database.admin_base import AdminBase
from app.database.base import Base

from app.models.admin_models import (
    AdminUser, App, ActivationKey, Notification, 
    FailedNotification, DocumentDeliveryLog, ActivationKeySchema
)
from app.models.models import Machine, Receipt
from app.models.employee_model import Employee
from app.core.security import get_password_hash, encrypt_password
from app.services.notification_service import NotificationService
from app.services.pdf_service import PDFService

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataSeeder")

# --- Tracking Utility ---
class SeedingSummary:
    def __init__(self):
        self.tenants = 0
        self.machines = 0
        self.employees = 0
        self.receipts = 0
        self.notifications = 0
        self.logs = 0
        self.emails_sent = 0
        self.emails_failed = 0
        self.start_time = datetime.now()

    def print_report(self):
        duration = datetime.now() - self.start_time
        print("\n" + "="*50)
        print("🚀 SEEDING EXECUTION SUMMARY")
        print("="*50)
        print(f"{'Tenants Created:':<25} {self.tenants}")
        print(f"{'Machines Created:':<25} {self.machines}")
        print(f"{'Employees Created:':<25} {self.employees}")
        print(f"{'Receipts Created:':<25} {self.receipts}")
        print(f"{'Notifications:':<25} {self.notifications}")
        print(f"{'Delivery Logs:':<25} {self.logs}")
        divider = "-" * 50
        print(divider)
        print(f"{'E2E Emails Sent:':<25} {self.emails_sent}")
        print(f"{'E2E Emails Failed:':<25} {self.emails_failed}")
        print(divider)
        print(f"{'Total Duration:':<25} {duration.total_seconds():.2f} seconds")
        print("="*50 + "\n")

summary = SeedingSummary()

# --- Constants for Realistic Generation ---
INDIAN_STATES = ["MH", "MP", "DL", "KA", "GJ", "RJ", "UP", "TN", "TS", "WB"]
MATERIALS = ["Coal", "Iron Ore", "Cement", "Sand", "Steel Rails", "Bauxite", "Clinker"]
TENANT_NAMES = [
    "Ambuja Cement Ltd", "Tata Steel Plant", "JSW Infrastructure", 
    "Shree Cements", "UltraTech Concrete", "Adani Ports", 
    "Mahindra Logistics", "Larsen & Toubro", "Reliance Industries"
]
OPERATOR_NAMES = [
    "Arjun Sharma", "Sanjay Patel", "Deepak Gupta", 
    "Rahul Verma", "Amit Singh", "Priya Das", 
    "Vikram Rao", "Karan Malhotra", "Sneha Kulkarni"
]

class WeighbridgeDataFactory:
    """Utility class to generate realistic weighbridge data."""
    
    @staticmethod
    def generate_truck_no() -> str:
        state = random.choice(INDIAN_STATES)
        district = f"{random.randint(1, 99):02d}"
        series = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        number = f"{random.randint(1000, 9999)}"
        return f"{state}-{district}-{series}-{number}"

    @staticmethod
    def generate_weight_pair() -> Dict[str, float]:
        tare = float(random.randint(5000, 15000))
        net = float(random.randint(10000, 35000))
        gross = tare + net
        return {"tare": tare, "gross": gross, "net": net}

    @staticmethod
    def generate_timestamp(days_back: int = 90) -> datetime:
        seconds_ago = random.randint(0, days_back * 24 * 3600)
        return datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)

    @staticmethod
    def generate_receipt_payload(truck_no: str, weights: Dict[str, float]) -> Dict[str, Any]:
        return {
            "truck_no": truck_no,
            "material": random.choice(MATERIALS),
            "supplier": f"{random.choice(TENANT_NAMES)} Vendor",
            "gross": weights["gross"],
            "tare": weights["tare"],
            "net": weights["net"],
            "unit": "kg",
            "charges": float(random.randint(100, 500)),
            "notes": "Generated for testing"
        }

    @staticmethod
    def generate_test_pdf(truck_no: str, weights: Dict[str, float]) -> bytes:
        """Generates a real PDF receipt using PDFService."""
        # Create a mock receipt object
        mock_receipt = Receipt(
            local_id=random.randint(1000, 9999),
            date_time=datetime.now(),
            truck_no=truck_no,
            gross_weight=weights["gross"],
            tare_weight=weights["tare"],
            payload_json={"data": {
                "truck_no": truck_no,
                "gross": weights["gross"],
                "tare": weights["tare"],
                "net": weights["net"],
                "material": random.choice(MATERIALS)
            }}
        )
        # Create a mock machine with headers
        mock_machine = Machine(
            settings={
                "header1": "Production Test Plant",
                "header2": "Sector 14, Industrial Area",
                "footer": "Thank you for using our Weighbridge System"
            }
        )
        try:
            pdf_content = PDFService.generate_receipt_pdf(mock_receipt, mock_machine)
            # Ensure return type is bytes
            if isinstance(pdf_content, str):
                return pdf_content.encode('latin-1')
            return pdf_content
        except Exception as e:
            logger.error(f"PDF Generation failed: {e}")
            return b"Dummy PDF Content"

    @staticmethod
    def generate_test_image() -> bytes:
        """Generates a tiny 1x1 white PNG image."""
        import base64
        return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")

    @staticmethod
    def get_receipt_html(truck_no: str, weights: Dict[str, float], company: str) -> str:
        return f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2c3e50; line-height: 1.6; background-color: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e1e8ed;">
                <div style="background: linear-gradient(135deg, #3498db, #2980b9); padding: 30px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">Weighment Receipt</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Digital Proof of Transaction</p>
                </div>
                <div style="padding: 30px;">
                    <div style="margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
                        <p style="margin: 0 0 5px 0; color: #7f8c8d; font-size: 12px; text-transform: uppercase; font-weight: bold;">Company</p>
                        <p style="margin: 0; font-size: 18px; font-weight: 600;">{company}</p>
                    </div>
                    
                    <div style="background: #f8f9fa; border-left: 4px solid #3498db; padding: 20px; border-radius: 4px; margin-bottom: 25px;">
                        <p style="margin: 0 0 10px 0; font-size: 14px;"><strong>Vehicle Number:</strong> <span style="background: #ffeaa7; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-weight: bold; color: #d35400;">{truck_no}</span></p>
                        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 10px 0; color: #636e72;">Gross Weight</td>
                                <td style="padding: 10px 0; text-align: right; font-weight: 600;">{weights['gross']:,} kg</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 10px 0; color: #636e72;">Tare Weight</td>
                                <td style="padding: 10px 0; text-align: right; font-weight: 600;">{weights['tare']:,} kg</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 0; color: #2980b9; font-weight: bold; font-size: 18px;">Net Weight</td>
                                <td style="padding: 10px 0; text-align: right; font-weight: 800; color: #2980b9; font-size: 20px;">{weights['net']:,} kg</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="text-align: center; font-size: 13px; color: #95a5a6; margin-top: 20px;">
                        <p style="margin: 0;">Date: {datetime.now().strftime('%d %b %Y, %H:%M')}</p>
                        <p style="margin: 10px 0 0 0;">System Verified | E2E Production Validation</p>
                    </div>
                </div>
                <div style="background: #34495e; color: #bdc3c7; text-align: center; padding: 15px; font-size: 11px;">
                    This is an automated production-grade test email generated by the Weighbridge Admin Panel.
                </div>
            </div>
        </body>
        </html>
        """

# --- Seeding Modules ---

async def seed_admin_users(db: AsyncSession):
    """Seed the default super admin."""
    email = "admin@example.com"
    existing = await db.execute(select(AdminUser).where(AdminUser.email == email))
    if existing.scalars().first():
        logger.info("Admin user already exists. Skipping.")
        return
    
    hashed_pass = get_password_hash("admin123")
    admin = AdminUser(email=email, hashed_password=hashed_pass)
    db.add(admin)
    logger.info(f"Seeded Admin User: {email}")

async def seed_apps(db: AsyncSession) -> List[App]:
    """Seed standard product tiers."""
    apps_data = [
        {"id": "WB-APP-LITE", "name": "Weighbridge Lite", "desc": "Entry-level weighbridge software"},
        {"id": "WB-APP-PRO", "name": "Weighbridge Professional", "desc": "Standard industrial weighbridge sync system"},
        {"id": "WB-APP-ENT", "name": "Weighbridge Enterprise", "desc": "Full-scale multi-site weighment management"}
    ]
    
    db_apps = []
    for app in apps_data:
        existing = await db.execute(select(App).where(App.app_id == app["id"]))
        obj = existing.scalars().first()
        if not obj:
            obj = App(app_id=app["id"], app_name=app["name"], description=app["desc"])
            db.add(obj)
            logger.info(f"Seeded App: {app['name']}")
        db_apps.append(obj)
    
    await db.flush()
    return db_apps

async def seed_tenants(db: AsyncSession, apps: List[App], count: int = 5) -> List[ActivationKey]:
    """Seed companies (Tenants)."""
    tenants = []
    for i in range(count):
        name = random.choice(TENANT_NAMES) + f" {uuid.uuid4().hex[:4].upper()}"
        app = random.choice(apps)
        token = f"TOKEN-{uuid.uuid4().hex[:8].upper()}"
        
        # In this system, ActivationKey represents the tenant configuration
        key = ActivationKey(
            app_id=app.id,
            company_name=name,
            email=f"contact@{name.lower().replace(' ', '')}.com",
            token=token,
            key_hash="MOCKED_HASH",
            status="ACTIVE",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365)
        )
        db.add(key)
        tenants.append(key)
        
        schema = ActivationKeySchema(
            activation_key=key,
            version=1,
            labels=[{"key": "truck_no", "label": "Vehicle Number"}, {"key": "material", "label": "Commodity"}],
            etag=uuid.uuid4().hex
        )
        db.add(schema)
        
    await db.flush()
    summary.tenants += len(tenants)
    logger.info(f"Seeded {len(tenants)} Tenants.")
    return tenants

async def seed_employees(db: AsyncSession, tenants: List[ActivationKey]) -> List[Employee]:
    """Seed operators for each tenant."""
    employees = []
    hashed_pass = get_password_hash("operator123")
    
    for tenant in tenants:
        emp_count = random.randint(3, 8)
        for j in range(emp_count):
            name = random.choice(OPERATOR_NAMES)
            username = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:4]}"
            emp = Employee(
                name=name,
                username=username,
                email=f"{username}@test.com",
                password_hash=hashed_pass,
                key_id=tenant.token,
                role="operator"
            )
            db.add(emp)
            employees.append(emp)
            
    await db.flush()
    summary.employees += len(employees)
    logger.info(f"Seeded {len(employees)} Employees across tenants.")
    return employees

async def seed_machines(db: AsyncSession, tenants: List[ActivationKey]) -> List[Machine]:
    """Seed machines for each tenant."""
    machines = []
    for tenant in tenants:
        m_count = random.randint(2, 5)
        for j in range(m_count):
            unique_suffix = tenant.token.split('-')[-1][:4]
            m_id = f"WB-MCH-{unique_suffix}-{j:02d}"
            machine = Machine(
                machine_id=m_id,
                name=f"Weighbridge {j+1}",
                location=f"Gate {random.randint(1, 5)}",
                key_id=tenant.token,
                is_active=True
            )
            db.add(machine)
            machines.append(machine)
            
    await db.flush()
    summary.machines += len(machines)
    logger.info(f"Seeded {len(machines)} Machines.")
    return machines

async def seed_receipts(db: AsyncSession, machines: List[Machine], employees: List[Employee], scale_count: int):
    """Seed receipts with batch processing."""
    total_receipts = scale_count
    batch_size = 500
    tenant_employees = {}
    for emp in employees:
        if emp.key_id not in tenant_employees: tenant_employees[emp.key_id] = []
        tenant_employees[emp.key_id].append(emp)

    logger.info(f"Starting batch insertion of {total_receipts} receipts...")
    for start in range(0, total_receipts, batch_size):
        end = min(start + batch_size, total_receipts)
        batch = []
        for _ in range(start, end):
            machine = random.choice(machines)
            tenant_token = machine.key_id
            potential_emps = tenant_employees.get(tenant_token, employees)
            emp = random.choice(potential_emps)
            truck_no = WeighbridgeDataFactory.generate_truck_no()
            weights = WeighbridgeDataFactory.generate_weight_pair()
            ts = WeighbridgeDataFactory.generate_timestamp()
            batch.append({
                "machine_id": machine.machine_id,
                "local_id": random.randint(1000, 999999),
                "date_time": ts,
                "truck_no": truck_no,
                "gross_weight": weights["gross"],
                "tare_weight": weights["tare"],
                "payload_json": WeighbridgeDataFactory.generate_receipt_payload(truck_no, weights),
                "user_id": emp.id,
                "share_token": uuid.uuid4().hex,
                "search_text": f"{truck_no} {emp.name}".lower(),
                "created_at": ts,
                "is_synced": True
            })
        await db.execute(insert(Receipt).values(batch))
        summary.receipts += len(batch)
        logger.info(f"  Inserted batch: {start} to {end}")

async def seed_notifications_and_logs(db: AsyncSession, tenants: List[ActivationKey]):
    """Seed alerts, DLQ, and delivery logs."""
    for tenant in tenants:
        db.add(Notification(
            activation_key_id=tenant.id,
            message=f"System Alert: Hardware heartbeat missing for {tenant.company_name}",
            type="warning"
        ))
        summary.notifications += 1
        
        log_count = 10
        for _ in range(log_count):
            outcome = random.random()
            status, retry = ("SUCCESS", random.randint(0, 2)) if outcome < 0.95 else ("FAILED", 3)
            db.add(DocumentDeliveryLog(
                key_id=tenant.id, company_name=tenant.company_name,
                document_type="receipt", document_name=f"Receipt_{uuid.uuid4().hex[:6]}.pdf",
                delivery_channel=random.choice(["email", "whatsapp"]),
                status=status, retry_count=retry, created_at=WeighbridgeDataFactory.generate_timestamp(10)
            ))
            summary.logs += 1

async def send_test_emails(db: AsyncSession, app: App):
    """E2E validation with HTML support and cleanup."""
    logger.info("--- Starting E2E Email Validation ---")
    host, user, password, receiver = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"), os.getenv("TEST_RECEIVER_EMAIL")
    from_name = os.getenv("SMTP_FROM_NAME", "Weighbridge Test")
    
    if not all([host, user, password, receiver]):
        logger.warning("SMTP environment variables missing. Skipping email test.")
        return

    test_tenant = ActivationKey(
        app_id=app.id, company_name="System E2E Validator", token="SYSTEM-E2E-TOKEN",
        key_hash="SYSTEM", status="ACTIVE", expiry_date=datetime.now(timezone.utc) + timedelta(days=90),
        smtp_enabled=True, smtp_host=host, smtp_port=int(os.getenv("SMTP_PORT", 587)),
        smtp_user=user, smtp_password=encrypt_password(password), from_email=user, from_name=from_name, smtp_status="VALID"
    )
    db.add(test_tenant)
    await db.commit()
    await db.refresh(test_tenant)
    
    for i in range(3):
        truck = WeighbridgeDataFactory.generate_truck_no()
        weights = WeighbridgeDataFactory.generate_weight_pair()
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Attachment 1: Real PDF Receipt
        pdf_content = WeighbridgeDataFactory.generate_test_pdf(truck, weights)
        # Attachment 2: Sample Image
        img_content = WeighbridgeDataFactory.generate_test_image()
        
        key_data = {
            "id": str(test_tenant.id), "company_name": test_tenant.company_name, "email": receiver,
            "subject": f"E2E Production Test #{i+1} | Vehicle {truck}",
            "body": f"Validation Success. Vehicle: {truck}. Weight: {weights['net']} kg",
            "html": WeighbridgeDataFactory.get_receipt_html(truck, weights, test_tenant.company_name),
            "attachments": [
                {
                    "filename": f"receipt_{truck.replace('-', '_')}_{ts_str}.pdf",
                    "content": pdf_content,
                    "mime_type": "application/pdf"
                },
                {
                    "filename": f"truck_sample_{ts_str}.png",
                    "content": img_content,
                    "mime_type": "image/png"
                }
            ]
        }
        try:
            status = await NotificationService._send_email_license_async(key_data, "Production Validation")
            if status == "sent": summary.emails_sent += 1
            else: summary.emails_failed += 1
            logger.info(f"Test Email #{i+1}: {status} with 2 attachments")
        except Exception as e:
            summary.emails_failed += 1
            logger.error(f"Test Email #{i+1} failure: {e}")
        await asyncio.sleep(random.uniform(0.3, 0.5))

    # Automatic Cleanup with Foreign Key handling
    logger.info("Cleaning up System E2E Validator tenant and related logs...")
    from app.models.admin_models import ActivationKeyHistory, ActivationKeySchema
    
    # 1. Delete history logs created during the test
    await db.execute(delete(ActivationKeyHistory).where(ActivationKeyHistory.activation_key_id == test_tenant.id))
    # 2. Delete delivery logs created during the test
    await db.execute(delete(DocumentDeliveryLog).where(DocumentDeliveryLog.key_id == test_tenant.id))
    # 3. Delete schemas
    await db.execute(delete(ActivationKeySchema).where(ActivationKeySchema.activation_key_id == test_tenant.id))
    # 4. Finally delete the tenant
    await db.execute(delete(ActivationKey).where(ActivationKey.id == test_tenant.id))
    await db.commit()
    logger.info("Cleanup complete.")

async def reset_database():
    """Wipe the database clean."""
    logger.info("!!! RESETTING DATABASE !!!")
    async with remote_engine.begin() as conn:
        await conn.run_sync(AdminBase.metadata.drop_all)
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(AdminBase.metadata.create_all)
    logger.info("Database reset complete.")

async def main():
    parser = argparse.ArgumentParser(description="Production-Grade Weighbridge Data Seeder")
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="small", help="Seed volume")
    parser.add_argument("--reset", action="store_true", help="Clear DB before seeding")
    parser.add_argument("--force", action="store_true", help="Required for --reset")
    parser.add_argument("--send-test-email", action="store_true", help="Run E2E email validation")
    args = parser.parse_args()
    
    if args.reset and not args.force:
        logger.error("DANGER: --reset flag requires --force to proceed. Operation aborted.")
        sys.exit(1)

    if args.reset:
        await reset_database()

    async with remote_session() as session:
        async with session.begin():
            try:
                await seed_admin_users(session)
                apps = await seed_apps(session)
                tenants = await seed_tenants(session, apps)
                employees = await seed_employees(session, tenants)
                machines = await seed_machines(session, tenants)
                await seed_receipts(session, machines, employees, {"small": 100, "medium": 1000, "large": 10000}[args.scale])
                await seed_notifications_and_logs(session, tenants)
            except Exception as e:
                logger.error(f"Seeding critical failure: {e}")
                await session.rollback()
                return

        if args.send_test_email:
            async with remote_session() as email_session:
                res = await email_session.execute(select(App).limit(1)); valid_app = res.scalars().first()
                if valid_app: await send_test_emails(email_session, valid_app)

    summary.print_report()

if __name__ == "__main__":
    asyncio.run(main())
