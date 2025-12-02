"""
API Key database model
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class APIKey(Base):
    """API Key model for authentication"""
    
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_prefix = Column(String(20), nullable=False, index=True)  # First 8 chars for display
    hashed_key = Column(String, nullable=False, unique=True)
    
    # Ownership
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Metadata
    name = Column(String, nullable=False)  # Friendly name like "Production API Key"
    description = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Permissions
    scopes = Column(JSON, default=list, nullable=False)  # ["read:artifacts", "write:artifacts"]
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey {self.key_prefix}... ({self.name})>"
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active, not expired, not revoked)"""
        if not self.is_active or self.revoked_at:
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        
        return True

