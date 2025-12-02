"""
Artifact management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from uuid import UUID
import json

from app.core.database import get_db
from app.core.deps import get_current_user_from_api_key
from app.models import User, Artifact
from app.schemas import ArtifactUpload, ArtifactMetadata, ArtifactList, UploadResponse
from app.services import r2_service


router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_artifact(
    upload_data: ArtifactUpload,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Upload a new artifact
    
    Uploads a kurral artifact to R2 storage and saves metadata to database.
    """
    artifact_data = upload_data.artifact_data
    
    # Validate artifact data
    required_fields = ["kurral_id", "tenant_id", "created_at", "deterministic", "replay_level"]
    for field in required_fields:
        if field not in artifact_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # Extract key fields
    kurral_id = UUID(artifact_data["kurral_id"])
    tenant_id = artifact_data["tenant_id"]
    created_at = datetime.fromisoformat(artifact_data["created_at"].replace("Z", "+00:00"))
    
    # Check if artifact already exists
    existing = db.query(Artifact).filter(Artifact.kurral_id == kurral_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Artifact already exists"
        )
    
    # Upload to R2
    try:
        object_storage_uri = r2_service.upload_artifact(
            artifact_data=artifact_data,
            tenant_id=tenant_id,
            kurral_id=kurral_id,
            created_at=created_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to R2: {str(e)}"
        )
    
    # Get artifact size
    artifact_size = len(json.dumps(artifact_data).encode("utf-8"))
    
    # Extract tool call summary
    tool_calls = artifact_data.get("tool_calls", [])
    tool_call_summary = {}
    for tool_call in tool_calls:
        tool_name = tool_call.get("tool_name", "unknown")
        tool_call_summary[tool_name] = tool_call_summary.get(tool_name, 0) + 1
    
    # Extract token usage
    token_usage = artifact_data.get("token_usage", {})
    
    # Create metadata record
    artifact_metadata = Artifact(
        kurral_id=kurral_id,
        run_id=artifact_data.get("run_id", ""),
        tenant_id=tenant_id,
        semantic_buckets=artifact_data.get("semantic_buckets", []),
        environment=artifact_data.get("environment", "production"),
        deterministic=artifact_data["deterministic"],
        replay_level=artifact_data["replay_level"],
        determinism_score=artifact_data.get("determinism_report", {}).get("overall_score", 0.0),
        model_name=artifact_data.get("llm_config", {}).get("model_name"),
        model_provider=artifact_data.get("llm_config", {}).get("provider"),
        temperature=artifact_data.get("llm_config", {}).get("parameters", {}).get("temperature"),
        duration_ms=artifact_data.get("duration_ms"),
        cost_usd=artifact_data.get("cost_usd"),
        error_message=artifact_data.get("error"),
        prompt_tokens=token_usage.get("prompt_tokens", 0),
        completion_tokens=token_usage.get("completion_tokens", 0),
        total_tokens=token_usage.get("total_tokens", 0),
        cached_tokens=token_usage.get("cached_tokens"),
        tool_call_count=len(tool_calls),
        tool_call_summary=tool_call_summary,
        object_storage_uri=object_storage_uri,
        artifact_size_bytes=artifact_size,
        created_at=created_at,
        created_by=artifact_data.get("created_by"),
        tags=artifact_data.get("tags", {}),
        graph_hash=artifact_data.get("graph_version", {}).get("graph_hash"),
        prompt_hash=artifact_data.get("resolved_prompt", {}).get("final_text_hash"),
    )
    
    db.add(artifact_metadata)
    db.commit()
    db.refresh(artifact_metadata)
    
    return UploadResponse(
        kurral_id=kurral_id,
        object_storage_uri=object_storage_uri,
        message="Artifact uploaded successfully"
    )


@router.get("/", response_model=ArtifactList)
def list_artifacts(
    tenant_id: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    semantic_bucket: Optional[str] = Query(None),
    deterministic: Optional[bool] = Query(None),
    replay_level: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    List artifacts with filtering and pagination
    
    Returns a paginated list of artifacts matching the specified filters.
    """
    # Build query
    query = db.query(Artifact)
    
    # Apply filters
    if tenant_id:
        query = query.filter(Artifact.tenant_id == tenant_id)
    else:
        # Default to user's tenant
        query = query.filter(Artifact.tenant_id == current_user.tenant_id)
    
    if environment:
        query = query.filter(Artifact.environment == environment)
    
    if semantic_bucket:
        query = query.filter(Artifact.semantic_buckets.contains([semantic_bucket]))
    
    if deterministic is not None:
        query = query.filter(Artifact.deterministic == deterministic)
    
    if replay_level:
        query = query.filter(Artifact.replay_level == replay_level)
    
    if model_name:
        query = query.filter(Artifact.model_name == model_name)
    
    if start_date:
        query = query.filter(Artifact.created_at >= start_date)
    
    if end_date:
        query = query.filter(Artifact.created_at <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    artifacts = query.order_by(Artifact.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return ArtifactList(
        items=artifacts,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{kurral_id}", response_model=dict)
def get_artifact(
    kurral_id: UUID,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Get full artifact by ID
    
    Downloads the complete artifact from R2 storage.
    """
    # Get metadata
    artifact = db.query(Artifact).filter(Artifact.kurral_id == kurral_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    # Check tenant access
    if artifact.tenant_id != current_user.tenant_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Download from R2
    try:
        artifact_data = r2_service.download_artifact(artifact.object_storage_uri)
        return artifact_data
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact file not found in storage"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download artifact: {str(e)}"
        )


@router.get("/{kurral_id}/metadata", response_model=ArtifactMetadata)
def get_artifact_metadata(
    kurral_id: UUID,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Get artifact metadata only
    
    Returns metadata without downloading the full artifact from R2.
    """
    artifact = db.query(Artifact).filter(Artifact.kurral_id == kurral_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    # Check tenant access
    if artifact.tenant_id != current_user.tenant_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return artifact


@router.delete("/{kurral_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    kurral_id: UUID,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Delete an artifact
    
    Deletes the artifact from both R2 storage and database.
    """
    # Get metadata
    artifact = db.query(Artifact).filter(Artifact.kurral_id == kurral_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    # Check tenant access
    if artifact.tenant_id != current_user.tenant_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete from R2
    try:
        r2_service.delete_artifact(artifact.object_storage_uri)
    except Exception as e:
        # Log error but continue to delete metadata
        print(f"Warning: Failed to delete from R2: {e}")
    
    # Delete metadata
    db.delete(artifact)
    db.commit()
    
    return None


@router.get("/semantic-buckets/list", response_model=list[str])
def list_semantic_buckets(
    tenant_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    List all unique semantic buckets
    
    Returns a list of all semantic bucket names for the tenant.
    """
    # Build query
    query = db.query(Artifact.semantic_buckets).distinct()
    
    # Filter by tenant
    if tenant_id:
        query = query.filter(Artifact.tenant_id == tenant_id)
    else:
        query = query.filter(Artifact.tenant_id == current_user.tenant_id)
    
    # Get all distinct bucket arrays
    results = query.all()
    
    # Flatten and deduplicate
    buckets = set()
    for (bucket_list,) in results:
        if bucket_list:
            buckets.update(bucket_list)
    
    return sorted(buckets)

