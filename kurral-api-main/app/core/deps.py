"""
Dependency injection for FastAPI endpoints
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_access_token, verify_api_key
from app.models import User, APIKey


security = HTTPBearer()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    
    Usage:
        @app.get("/me")
        def get_me(current_user: User = Depends(get_current_user_from_token)):
            return current_user
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from API key header
    
    Usage:
        @app.get("/artifacts")
        def list_artifacts(current_user: User = Depends(get_current_user_from_api_key)):
            return ...
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {settings.API_KEY_HEADER} header"
        )
    
    # Extract key prefix (first 8 chars after "kurral_")
    if not api_key.startswith("kurral_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    key_prefix = api_key[:15]  # "kurral_" + first 8 chars
    
    # Find API key by prefix
    api_key_obj = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Verify full key
    if not verify_api_key(api_key, api_key_obj.hashed_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if key is valid
    if not api_key_obj.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is expired or revoked"
        )
    
    # Update last used timestamp and usage count
    from datetime import datetime
    api_key_obj.last_used_at = datetime.utcnow()
    api_key_obj.usage_count += 1
    db.commit()
    
    # Get user
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user_from_token)
) -> User:
    """Get current active user (must be active)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user_from_token)
) -> User:
    """Get current superuser (must be superuser)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def check_scope(required_scope: str):
    """
    Dependency to check if API key has required scope
    
    Usage:
        @app.post("/artifacts", dependencies=[Depends(check_scope("write:artifacts"))])
        def create_artifact(...):
            ...
    """
    async def scope_checker(
        api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER),
        db: Session = Depends(get_db)
    ):
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        # Get API key
        key_prefix = api_key[:15]
        api_key_obj = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
        
        if not api_key_obj or required_scope not in api_key_obj.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}"
            )
        
        return True
    
    return scope_checker

