from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "user"
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_locked: Optional[bool] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    is_locked: bool
    failed_login_attempts: int
    last_login_at: Optional[datetime]
    phone: Optional[str]
    whatsapp: Optional[str]
    telegram: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserListResponse(UserResponse):
    # Same fields, can be alias or just use UserResponse
    pass