"""
API Key schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class APIKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["read:artifacts", "write:artifacts"])
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)"""
    id: str
    key_prefix: str
    name: str
    description: Optional[str]
    is_active: bool
    scopes: List[str]
    rate_limit_per_minute: int
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    
    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes the actual key once)"""
    api_key: str  # Full key - only returned once at creation


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    scopes: Optional[List[str]] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)

