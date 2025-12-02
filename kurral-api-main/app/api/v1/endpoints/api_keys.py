"""
API Key management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user_from_token
from app.core.security import generate_api_key, hash_api_key
from app.models import User, APIKey
from app.schemas import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyUpdate


router = APIRouter()


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Create a new API key
    
    Generates a new API key for the authenticated user.
    The full key is only returned once at creation.
    """
    # Generate API key
    api_key = generate_api_key()
    key_prefix = api_key[:15]  # "kurral_" + first 8 chars
    hashed_key = hash_api_key(api_key)
    
    # Create API key record
    new_key = APIKey(
        key_prefix=key_prefix,
        hashed_key=hashed_key,
        user_id=current_user.id,
        name=key_data.name,
        description=key_data.description,
        scopes=key_data.scopes,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        expires_at=key_data.expires_at,
    )
    
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    # Return response with full key (only time it's shown)
    response = APIKeyCreateResponse(
        id=new_key.id,
        key_prefix=new_key.key_prefix,
        name=new_key.name,
        description=new_key.description,
        is_active=new_key.is_active,
        scopes=new_key.scopes,
        rate_limit_per_minute=new_key.rate_limit_per_minute,
        created_at=new_key.created_at,
        expires_at=new_key.expires_at,
        last_used_at=new_key.last_used_at,
        usage_count=new_key.usage_count,
        api_key=api_key  # Full key - only returned once
    )
    
    return response


@router.get("/", response_model=List[APIKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user
    
    Returns a list of all API keys owned by the authenticated user.
    """
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return keys


@router.get("/{key_id}", response_model=APIKeyResponse)
def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Get API key details
    
    Returns details for a specific API key.
    """
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return key


@router.patch("/{key_id}", response_model=APIKeyResponse)
def update_api_key(
    key_id: str,
    key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Update API key
    
    Update an API key's metadata (name, description, scopes, etc).
    """
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update fields
    update_data = key_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(key, field, value)
    
    db.commit()
    db.refresh(key)
    
    return key


@router.post("/{key_id}/revoke", response_model=APIKeyResponse)
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key
    
    Permanently revoke an API key. This cannot be undone.
    """
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Revoke the key
    key.revoked_at = datetime.utcnow()
    key.is_active = False
    
    db.commit()
    db.refresh(key)
    
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Delete an API key
    
    Permanently delete an API key from the database.
    """
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(key)
    db.commit()
    
    return None

