from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declared_attr
from datetime import datetime, timezone

from app.database.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SoftwareVersion(Base):
    __tablename__ = "software_versions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) 
    features = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserActivation(Base):
    __tablename__ = "user_activations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("software_versions.id"), nullable=False, index=True)
    activation_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Base Mixin for future transactional data (like Receipts) to enforce strong filtering
class TenantVersionMixin:
    
    @declared_attr
    def tenant_id(cls):
        return Column(Integer, ForeignKey('tenants.id'), nullable=False)
        
    @declared_attr
    def version_id(cls):
        return Column(Integer, ForeignKey('software_versions.id'), nullable=False)
        
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
        
    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False)
        
    @declared_attr
    def __table_args__(cls):
        from sqlalchemy import Index
        # Composite index for high-speed row-level filtering
        return (Index(f'ix_{cls.__tablename__}_tenant_version', 'tenant_id', 'version_id'),)
