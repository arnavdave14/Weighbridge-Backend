from pydantic import BaseModel, UUID4, field_validator
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────
# App (Product) Schemas
# ─────────────────────────────────────────────

class AppCreate(BaseModel):
    app_name: str
    description: Optional[str] = None
    whatsapp_sender_channel: Optional[str] = None
    email_sender: Optional[str] = None


class AppUpdate(BaseModel):
    app_name: Optional[str] = None
    description: Optional[str] = None
    whatsapp_sender_channel: Optional[str] = None
    email_sender: Optional[str] = None


class AppRead(BaseModel):
    id: UUID4
    app_id: str
    app_name: str
    description: Optional[str] = None
    whatsapp_sender_channel: Optional[str] = None
    email_sender: Optional[str] = None
    created_at: datetime
    keys_count: int = 0

    class Config:
        from_attributes = True


class CustomLabel(BaseModel):
    name: str
    type: str = "text"  # text, alphanumeric, alphabetical, numeric, date
    required: bool = False

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
    labels: Optional[List[CustomLabel]] = []
    bill_header_1: Optional[str] = None
    bill_header_2: Optional[str] = None
    bill_header_3: Optional[str] = None
    # Notification / Messaging - Frontend Controlled
    notification_type: str = "both" # whatsapp | email | both
    message: Optional[str] = None  # For WhatsApp
    subject: Optional[str] = None  # For Email
    body: Optional[str] = None     # For Email

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
    labels: Optional[List[CustomLabel]] = None
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
    company_name: str
    status: str
    expiry_date: datetime
    created_at: datetime
    logo_url: Optional[str] = None
    signup_image_url: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    labels: Optional[List[CustomLabel]] = []
    bill_header_1: Optional[str] = None
    bill_header_2: Optional[str] = None
    bill_header_3: Optional[str] = None
    bill_footer: Optional[str] = None
    whatsapp_status: str = "pending"
    email_status: str = "pending"

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
    notification_type: str = "general"
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Failed Notification (DLQ) Schemas
# ─────────────────────────────────────────────

class FailedNotificationRead(BaseModel):
    id: UUID4
    channel: str
    target: str
    payload: dict
    error_reason: Optional[str]
    retry_count: int
    status: str
    notification_type: str = "general"
    failed_at: datetime
    resolved_at: Optional[datetime]

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
    """Sent by weighbridge device to activate against a specific App.

    GAP-1 FIX: machine_id is optional. If provided, the server immediately
    pre-registers the Machine in PostgreSQL with key_id set, so tenant
    enrichment in the admin panel works from the very first receipt sync —
    no separate machine-sync step required.

    Backward-compatible: existing devices not sending machine_id receive
    the same response as before; the new upsert path is completely skipped.
    """
    activation_key: str   # Raw WB-XXXX-XXXX-XXXX string
    app_id: str           # The app_id string (e.g. WB-APP-XXXX) user selects on device
    machine_id: Optional[str] = None  # Optional: device's own machine identifier



class HardwareActivationResponse(BaseModel):
    status: str
    token: str
    company_name: str
    expiry_date: datetime
    labels: List[CustomLabel]
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


# ─────────────────────────────────────────────
# Receipts Admin Viewer Schemas
# ─────────────────────────────────────────────

from enum import Enum


class SortField(str, Enum):
    created_at = "created_at"
    gross_weight = "gross_weight"
    tare_weight = "tare_weight"
    date_time = "date_time"


class SortDir(str, Enum):
    asc = "asc"
    desc = "desc"


class ReceiptAdminRead(BaseModel):
    """Enriched receipt row returned to the Admin Panel."""
    id: int
    local_id: int
    machine_id: str
    date_time: datetime
    gross_weight: float
    tare_weight: float
    net_weight: float           # Computed: gross - tare
    rate: Optional[float]
    truck_no: Optional[str]     # Extracted from custom_data JSON
    custom_data: dict           # Full dynamic fields (labels)
    share_token: str
    whatsapp_status: str
    is_synced: bool
    sync_attempts: int
    last_error: Optional[str]
    synced_at: Optional[datetime]
    created_at: datetime

    # Enriched tenant fields (from JOIN — may be None for legacy machines)
    app_name: Optional[str] = None
    app_id_str: Optional[str] = None       # e.g. "WB-APP-XXXX"
    company_name: Optional[str] = None
    key_status: Optional[str] = None       # active | expired | revoked

    # Employee enrichment (from JOIN — None for pre-auth receipts)
    user_id: Optional[str] = None          # Employee.id (UUID string)
    employee_name: Optional[str] = None    # Employee.name — shown in admin table
    employee_username: Optional[str] = None  # Employee.username — for cross-reference

    class Config:
        from_attributes = True


class PaginatedReceiptsResponse(BaseModel):
    """Pagination envelope for all receipt list endpoints."""
    total: int
    page: int
    limit: int
    pages: int
    items: List[ReceiptAdminRead]


class MachineAdminRead(BaseModel):
    """Machine summary for drill-down navigation."""
    id: int
    machine_id: str
    name: Optional[str]
    location: Optional[str]
    is_active: bool
    is_synced: bool
    last_sync_at: Optional[datetime]
    receipt_count: int = 0          # Aggregated JOINed count
    created_at: datetime

    class Config:
        from_attributes = True
