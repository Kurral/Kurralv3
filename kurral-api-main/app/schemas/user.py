"""
User schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: Optional[str] = None
    tenant_id: str
    organization_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    is_active: Optional[bool] = None
    api_call_limit: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    api_call_limit: int
    storage_limit_gb: int
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    settings: Dict[str, Any]
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data"""
    user_id: Optional[str] = None
    email: Optional[str] = None

