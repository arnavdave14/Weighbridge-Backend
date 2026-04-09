from datetime import datetime
from typing import Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    JSON,
    Text,
    UniqueConstraint,
    Boolean,
    Index,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base



class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    # Tenant linkage: stores ActivationKey.token (String, not UUID FK)
    # Avoids cross-DB FK issue — Machine lives in Base (SQLite+PG),
    # ActivationKey lives in AdminBase (PG only).
    # Populated during hardware activation. NULL for pre-existing machines.
    key_id = Column(String, nullable=True, index=True)

    # New Sync Fields
    is_synced = Column(Boolean, default=False, index=True)
    sync_attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    receipts = relationship("Receipt", back_populates="machine")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False, index=True)
    local_id = Column(Integer, nullable=False)
    date_time = Column(DateTime(timezone=True), nullable=False, index=True)
    gross_weight = Column(Numeric(precision=10, scale=2), nullable=False)
    tare_weight = Column(Numeric(precision=10, scale=2), nullable=False)
    rate = Column(Numeric(precision=10, scale=2), nullable=True)
    custom_data = Column(JSON, nullable=False)
    image_paths = Column(JSON, nullable=False, server_default='[]')
    image_urls = Column(JSON, nullable=True, server_default='[]')
    share_token = Column(String, unique=True, index=True, nullable=False)
    whatsapp_status = Column(String, default="pending", nullable=False)
    
    # Sync status
    is_synced = Column(Boolean, default=False, index=True)
    sync_attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "local_id", name="uq_machine_receipt"),
    )

    machine = relationship("Machine", back_populates="receipts")
    images = relationship("ReceiptImage", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptImage(Base):
    """
    Stores raw image bytes locally in SQLite (offline-first).
    One row per image. After cloud sync, image_data is cleared and image_url is set.
    PostgreSQL only ever sees image_url — never the binary.
    """
    __tablename__ = "receipt_images"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, default=0)           # Order of image (0, 1, 2 ...)
    image_data = Column(LargeBinary, nullable=True)  # Raw bytes — LOCAL ONLY, cleared after cloud sync
    image_url = Column(String, nullable=True)        # Cloud URL — set after successful upload
    is_uploaded = Column(Boolean, default=False, index=True)  # True once image_data uploaded to cloud
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    receipt = relationship("Receipt", back_populates="images")

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False)
    license_key = Column(String, unique=True, nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)  # "batch_sync", "manual", etc.
    status = Column(String, nullable=False)  # "success", "failed"
    synced_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SyncQueue(Base):
    """
    Refined Sync Queue table based on strict database design rules.
    """
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, nullable=False, index=True)   # "receipts", "machines"
    record_id = Column(Integer, nullable=False, index=True)    # The local sqlite ID
    operation = Column(String, nullable=False)                # "INSERT", "UPDATE"
    status = Column(String, default="PENDING", nullable=False, index=True) # PENDING, FAILED, DONE
    retry_count = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # Locking (optional but helpful for multi-worker safety, keeping hidden if not in primary request)
    worker_id = Column(String, nullable=True)
    
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

