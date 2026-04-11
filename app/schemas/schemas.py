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
    
    # Flexible Structure
    payload_json: Dict[str, Any] = Field(..., description="Full frontend data in {data: {...}} format")
    image_urls: List[str] = Field(default_factory=list)
    
    # Deprecated (for backward compatibility during migration)
    gross_weight: Optional[float] = None
    tare_weight: Optional[float] = None
    custom_data: Optional[Dict[str, Any]] = None
    
    # Infrastructure Fields
    user_id: Optional[str] = None
    corrected_from_id: Optional[int] = None
    correction_reason: Optional[str] = None
    
    # SQLite local sync artifacts (deprecated in favor of unified image_urls)
    images_base64: Optional[List[str]] = []
    image_paths: Optional[List[str]] = []


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
