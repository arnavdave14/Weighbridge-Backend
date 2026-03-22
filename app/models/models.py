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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    receipts = relationship("Receipt", back_populates="machine")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False, index=True)
    local_id = Column(Integer, nullable=False)  # The RST number from local SQLite
    date_time = Column(DateTime(timezone=True), nullable=False, index=True)
    gross_weight = Column(Numeric(precision=10, scale=2), nullable=False)
    tare_weight = Column(Numeric(precision=10, scale=2), nullable=False)
    rate = Column(Numeric(precision=10, scale=2), nullable=True)
    custom_data = Column(JSONB, nullable=False)  # Dynamic fields
    share_token = Column(String, unique=True, index=True, nullable=False)
    whatsapp_status = Column(String, default="pending", nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "local_id", name="uq_machine_receipt"),
        Index("ix_receipt_custom_data", "custom_data", postgresql_using="gin"),
    )

    machine = relationship("Machine", back_populates="receipts")

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
