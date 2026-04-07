from pydantic import BaseModel, UUID4, field_validator
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────
# App (Product) Schemas
# ─────────────────────────────────────────────

class AppCreate(BaseModel):
    app_name: str
    description: Optional[str] = None


class AppRead(BaseModel):
    id: UUID4
    app_id: str
    app_name: str
    description: Optional[str]
    created_at: datetime
    keys_count: int = 0

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# ActivationKey Schemas (Company License Level)
# ─────────────────────────────────────────────

class ActivationKeyCreate(BaseModel):
    """Used by admin to generate one or more keys for an App."""
    app_id: UUID4
    company_name: str
    expiry_date: datetime
    count: int = 1  # Bulk generation

    # Company-specific data (all optional at creation, can edit later)
    logo_url: Optional[str] = None
    signup_image_url: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    labels: Optional[List[str]] = []
    bill_header_1: Optional[str] = None
    bill_header_2: Optional[str] = None
    bill_header_3: Optional[str] = None
    bill_footer: Optional[str] = None


class ActivationKeyUpdate(BaseModel):
    """Update company details, billing config, expiry, or status."""
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    signup_image_url: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    labels: Optional[List[str]] = None
    bill_header_1: Optional[str] = None
    bill_header_2: Optional[str] = None
    bill_header_3: Optional[str] = None
    bill_footer: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[datetime] = None


class ActivationKeyRead(BaseModel):
    id: UUID4
    app_id: UUID4
    token: str
    status: str
    expiry_date: datetime
    created_at: datetime
    company_name: str
    logo_url: Optional[str]
    signup_image_url: Optional[str]
    email: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    mobile_number: Optional[str]
    whatsapp_number: Optional[str]
    labels: Optional[List[str]]
    bill_header_1: Optional[str]
    bill_header_2: Optional[str]
    bill_header_3: Optional[str]
    bill_footer: Optional[str]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Notification Schemas
# ─────────────────────────────────────────────

class NotificationRead(BaseModel):
    id: UUID4
    app_id: Optional[UUID4]
    activation_key_id: Optional[UUID4]
    message: str
    type: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Auth Schemas
# ─────────────────────────────────────────────

class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminOTPVerify(BaseModel):
    email: str
    otp: str


class OTPResponse(BaseModel):
    message: str


# ─────────────────────────────────────────────
# Hardware Activation Verification
# ─────────────────────────────────────────────

class HardwareActivationRequest(BaseModel):
    """Sent by weighbridge device to activate against a specific App."""
    activation_key: str   # Raw WB-XXXX-XXXX-XXXX string
    app_id: str           # The app_id string (e.g. WB-APP-XXXX) user selects on device


class HardwareActivationResponse(BaseModel):
    status: str
    token: str
    company_name: str
    expiry_date: datetime
    labels: List[str]
    bill_header_1: Optional[str]
    bill_header_2: Optional[str]
    bill_header_3: Optional[str]
    bill_footer: Optional[str]
    logo_url: Optional[str]
    signup_image_url: Optional[str]
    email: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    mobile_number: Optional[str]
    whatsapp_number: Optional[str]


# ─────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_apps: int
    total_keys: int
    active_keys: int
    expired_keys: int
    revoked_keys: int
    recent_notifications: int
