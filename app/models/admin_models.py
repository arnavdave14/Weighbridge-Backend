"""
Admin Models — PostgreSQL ONLY via AdminBase.
Architecture:
  App      = Product/Software (e.g. "Weighbridge Software")
  ActivationKey = One company license, holds ALL company-specific data.
"""
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.admin_base import AdminBase


class AdminUser(AdminBase):
    """Superuser who logs into the SaaS Admin Panel."""
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class App(AdminBase):
    """
    Represents a SOFTWARE PRODUCT (not a company).
    Example: "Weighbridge Pro", "Weighbridge Lite"
    One App can have many ActivationKeys, each for a different company.
    """
    __tablename__ = "apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(String, unique=True, index=True, nullable=False)  # e.g. WB-APP-XXXX
    app_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    keys = relationship("ActivationKey", back_populates="app", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="app", cascade="all, delete-orphan")


class ActivationKey(AdminBase):
    """
    ONE KEY = ONE COMPANY LICENSE.
    All company-specific data (branding, billing, contact) lives HERE.

    When a user activates their weighbridge device, they receive
    all configuration from this record — not from the App.
    """
    __tablename__ = "activation_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False, index=True)

    # --- Security ---
    key_hash = Column(String, nullable=False)           # bcrypt hash of WB-XXXX-XXXX-XXXX
    token = Column(String, unique=True, nullable=False)  # Secure internal JWT/token

    # --- License Status ---
    status = Column(String, default="active", nullable=False)  # active | expired | revoked
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # Track when a license is cancelled

    # ──────────────────────────────────────────────────
    # ALL COMPANY DATA LIVES HERE (Activation Key Level)
    # ──────────────────────────────────────────────────

    # --- Company Identity ---
    company_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    signup_image_url = Column(String, nullable=True)

    # --- Company Contact ---
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    mobile_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)

    # --- Bill / Receipt Configuration ---
    labels = Column(JSON, nullable=True, server_default="[]")  # Dynamic label array
    bill_header_1 = Column(String, nullable=True)
    bill_header_2 = Column(String, nullable=True)
    bill_header_3 = Column(String, nullable=True)
    bill_footer = Column(String, nullable=True)

    # Relationship
    app = relationship("App", back_populates="keys")
    notifications = relationship("Notification", back_populates="activation_key")


class Notification(AdminBase):
    """System alerts: invalid activations, wrong app selections, system events."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=True, index=True)
    activation_key_id = Column(UUID(as_uuid=True), ForeignKey("activation_keys.id"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    type = Column(String, default="warning", nullable=False)  # warning | error | info
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    app = relationship("App", back_populates="notifications")
    activation_key = relationship("ActivationKey", back_populates="notifications")
