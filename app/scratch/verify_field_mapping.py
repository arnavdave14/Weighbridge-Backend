import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

# Mock the environment to avoid DB imports if possible
import sys
from unittest.mock import MagicMock
sys.modules['app.database'] = MagicMock()
sys.modules['app.database.db_manager'] = MagicMock()

from app.schemas.admin_schemas import ActivationKeyCreate, ActivationKeyRead

async def verify_mapping():
    print("--- Verifying Schema Mapping (No DB) ---")
    
    # Test Payload with Architecture Keys
    payload = {
        "app_id": str(uuid.uuid4()),
        "company_name": "Test Company Mapping",
        "expiry_date": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "SMTP_HOST": "smtp.mapped.com",
        "SMTP_PORT": 587,
        "SMTP_USER": "test@mapped.com",
        "SMTP_PASS": "secret",
        "EMAILS_FROM_EMAIL": "noreply@mapped.com",
        "EMAILS_FROM_NAME": "Mapped Name",
        "smtp_enabled": True,
        "count": 1
    }
    
    # 1. Test Inbound Mapping (Alias -> Internal)
    print("\n1. Testing Inbound Mapping (JSON -> Schema)")
    try:
        # Pydantic v2 handles aliases automatically on init
        schema_in = ActivationKeyCreate(**payload)
        print(f"  ✓ Schema parsed successfully")
        print(f"  Internal smtp_host: {schema_in.smtp_host}")
        assert schema_in.smtp_host == "smtp.mapped.com"
        assert schema_in.smtp_password == "secret"
        print(f"  ✓ Mapping verified: SMTP_HOST -> {schema_in.smtp_host}")
    except Exception as e:
        print(f"  ✗ Inbound mapping failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Test Outbound Mapping (Model -> JSON)
    print("\n2. Testing Outbound Mapping (Schema -> JSON)")
    # Mock a model instance
    mock_id = uuid.uuid4()
    mock_app_id = uuid.uuid4()
    key_read = ActivationKeyRead(
        id=mock_id,
        app_id=mock_app_id,
        token="test_token",
        company_name="Test Company",
        status="ACTIVE",
        expiry_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        smtp_enabled=True,
        smtp_host="smtp.internal.com",
        smtp_port=587,
        smtp_user="internal@test.com",
        from_email="from@test.com",
        from_name="From Test",
        smtp_status="VALID",
        whatsapp_sender_channel="919893224689:5",
        email_sender="Internal Sender"
    )
    
    # by_alias=True is critical to get the UPPERCASE keys in output
    json_out = key_read.model_dump(by_alias=True, mode='json')
    print(f"  Serialized JSON keys: {list(json_out.keys())}")
    assert "SMTP_HOST" in json_out
    assert json_out["SMTP_HOST"] == "smtp.internal.com"
    assert "EMAILS_FROM_EMAIL" in json_out
    print(f"  ✓ Mapping verified: smtp_host -> SMTP_HOST")

    print("\n--- All Verifications Passed! ---")

if __name__ == "__main__":
    asyncio.run(verify_mapping())
