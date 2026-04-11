from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, EmailStr

# Base Schemas
class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Machine Schemas
class MachineBase(BaseModel):
    machine_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class MachineCreate(MachineBase):
    pass

class MachineSchema(MachineBase):
    id: int
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Receipt Schemas
class ReceiptBase(BaseModel):
    local_id: int
    date_time: datetime
    gross_weight: float
    tare_weight: float
    rate: Optional[float] = None
    custom_data: Dict[str, Any]
    image_paths: Optional[List[str]] = []
    # Flutter sends images as Base64 strings. Backend decodes → raw bytes → SQLite BLOB.
    # Base64 strings are NEVER stored in the database directly.
    images_base64: Optional[List[str]] = []
    # Employee linkage: set by Flutter from the logged-in employee's JWT.
    # Optional for backward compatibility — existing clients not sending this
    # field will produce receipts with user_id = NULL (still valid).
    # Correction metadata
    corrected_from_id: Optional[int] = None
    correction_reason: Optional[str] = None
    
    user_id: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    pass

class ReceiptSync(BaseModel):
    machine_id: str
    receipts: List[ReceiptCreate]
    settings: Optional[Dict[str, Any]] = None

class ReceiptResponse(ReceiptBase):
    id: int
    machine_id: str
    share_token: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    synced: int
    failed: int
    duplicates: int = 0
    errors: Optional[List[str]] = None
    error_map: Optional[Dict[int, Dict[str, str]]] = None # local_id -> {field: error}

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
