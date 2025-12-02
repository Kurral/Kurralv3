"""
Statistics and analytics endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user_from_api_key
from app.models import User, Artifact
from app.schemas import ArtifactStats


router = APIRouter()


@router.get("/", response_model=ArtifactStats)
def get_statistics(
    tenant_id: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Get artifact statistics
    
    Returns aggregated statistics about artifacts for the specified filters.
    """
    # Build base query
    query = db.query(Artifact)
    
    # Apply tenant filter
    if tenant_id:
        query = query.filter(Artifact.tenant_id == tenant_id)
    else:
        query = query.filter(Artifact.tenant_id == current_user.tenant_id)
    
    # Apply optional filters
    if environment:
        query = query.filter(Artifact.environment == environment)
    
    if start_date:
        query = query.filter(Artifact.created_at >= start_date)
    
    if end_date:
        query = query.filter(Artifact.created_at <= end_date)
    
    # Total artifacts
    total_artifacts = query.count()
    
    # Total size
    total_size_bytes = query.with_entities(func.sum(Artifact.artifact_size_bytes)).scalar() or 0
    total_size_gb = total_size_bytes / (1024 ** 3)
    
    # By environment
    env_stats = {}
    env_counts = db.query(
        Artifact.environment,
        func.count(Artifact.kurral_id)
    ).filter(
        Artifact.tenant_id == (tenant_id or current_user.tenant_id)
    ).group_by(Artifact.environment).all()
    
    for env, count in env_counts:
        env_stats[env] = count
    
    # By replay level
    level_stats = {}
    level_counts = query.with_entities(
        Artifact.replay_level,
        func.count(Artifact.kurral_id)
    ).group_by(Artifact.replay_level).all()
    
    for level, count in level_counts:
        level_stats[level] = count
    
    # By semantic bucket
    bucket_stats = {}
    artifacts_with_buckets = query.filter(
        Artifact.semantic_buckets != None,
        Artifact.semantic_buckets != []
    ).all()
    
    for artifact in artifacts_with_buckets:
        for bucket in artifact.semantic_buckets:
            bucket_stats[bucket] = bucket_stats.get(bucket, 0) + 1
    
    # By model
    model_stats = {}
    model_counts = query.with_entities(
        Artifact.model_name,
        func.count(Artifact.kurral_id)
    ).filter(
        Artifact.model_name != None
    ).group_by(Artifact.model_name).all()
    
    for model, count in model_counts:
        model_stats[model or "unknown"] = count
    
    # Total cost
    total_cost = query.with_entities(func.sum(Artifact.cost_usd)).scalar() or 0.0
    
    # Total tokens
    total_tokens = query.with_entities(func.sum(Artifact.total_tokens)).scalar() or 0
    
    # Average duration
    avg_duration = query.with_entities(func.avg(Artifact.duration_ms)).scalar() or 0.0
    
    # Error rate
    total_with_errors = query.filter(Artifact.error_message != None).count()
    error_rate = (total_with_errors / total_artifacts * 100) if total_artifacts > 0 else 0.0
    
    # Deterministic rate
    total_deterministic = query.filter(Artifact.deterministic == True).count()
    deterministic_rate = (total_deterministic / total_artifacts * 100) if total_artifacts > 0 else 0.0
    
    return ArtifactStats(
        total_artifacts=total_artifacts,
        total_size_gb=round(total_size_gb, 2),
        by_environment=env_stats,
        by_replay_level=level_stats,
        by_semantic_bucket=bucket_stats,
        by_model=model_stats,
        total_cost_usd=round(total_cost, 2),
        total_tokens=total_tokens,
        avg_duration_ms=round(avg_duration, 2),
        error_rate=round(error_rate, 2),
        deterministic_rate=round(deterministic_rate, 2),
    )


@router.get("/timeseries", response_model=dict)
def get_timeseries_stats(
    tenant_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Get time series statistics
    
    Returns daily statistics for the specified time period.
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Build query
    query = db.query(Artifact)
    
    if tenant_id:
        query = query.filter(Artifact.tenant_id == tenant_id)
    else:
        query = query.filter(Artifact.tenant_id == current_user.tenant_id)
    
    query = query.filter(
        Artifact.created_at >= start_date,
        Artifact.created_at <= end_date
    )
    
    # Get artifacts in date range
    artifacts = query.all()
    
    # Group by date
    daily_stats = {}
    
    for artifact in artifacts:
        date_key = artifact.created_at.date().isoformat()
        
        if date_key not in daily_stats:
            daily_stats[date_key] = {
                "date": date_key,
                "count": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "errors": 0,
                "deterministic": 0,
            }
        
        stats = daily_stats[date_key]
        stats["count"] += 1
        stats["total_cost"] += artifact.cost_usd or 0.0
        stats["total_tokens"] += artifact.total_tokens or 0
        
        if artifact.error_message:
            stats["errors"] += 1
        
        if artifact.deterministic:
            stats["deterministic"] += 1
    
    # Convert to list sorted by date
    timeseries = sorted(daily_stats.values(), key=lambda x: x["date"])
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": days,
        "data": timeseries
    }

