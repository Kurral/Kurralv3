"""
PostgreSQL storage for Kurral metadata and indexing
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class KurralRunModel(Base):
    """SQLAlchemy model for kurral_runs table"""

    __tablename__ = "kurral_runs"

    kurral_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    run_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    environment = Column(String(50), index=True)
    semantic_buckets = Column(ARRAY(String), index=True)

    deterministic = Column(Boolean, nullable=False, index=True)
    replay_level = Column(String(1), nullable=False, index=True)
    determinism_score = Column(Float)

    created_at = Column(DateTime, nullable=False, index=True)
    created_by = Column(String(255))

    duration_ms = Column(Integer)
    cost_usd = Column(Float)
    error_message = Column(String)

    # Model info
    model_name = Column(String(255), index=True)
    model_provider = Column(String(50))
    temperature = Column(Float)

    # Storage reference
    object_storage_uri = Column(String, nullable=True)

    # Metadata
    tags = Column(JSON)
    extra_metadata = Column(JSON)

    # Indexes
    __table_args__ = (
        Index("idx_tenant_env", "tenant_id", "environment"),
        Index("idx_created_desc", "created_at"),
        Index("idx_deterministic_level", "deterministic", "replay_level"),
        Index("idx_semantic_buckets", "semantic_buckets", postgresql_using="gin"),
    )


class PostgresStorage:
    """
    PostgreSQL storage for Kurral metadata

    This stores searchable metadata while full artifacts live in Cloudflare R2
    """

    def __init__(self, database_url: str):
        """
        Initialize PostgreSQL connection

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create database tables"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables (USE WITH CAUTION)"""
        Base.metadata.drop_all(self.engine)

    def save_metadata(
        self,
        kurral_id: UUID,
        run_id: str,
        tenant_id: str,
        environment: str,
        semantic_buckets: list[str],
        deterministic: bool,
        replay_level: str,
        determinism_score: float,
        created_at: datetime,
        created_by: Optional[str] = None,
        duration_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        temperature: Optional[float] = None,
        object_storage_uri: Optional[str] = None,
        tags: Optional[dict] = None,
        extra_metadata: Optional[dict] = None,
    ) -> None:
        """Save artifact metadata to PostgreSQL"""
        with self.SessionLocal() as session:
            run = KurralRunModel(
                kurral_id=kurral_id,
                run_id=run_id,
                tenant_id=tenant_id,
                environment=environment,
                semantic_buckets=semantic_buckets,
                deterministic=deterministic,
                replay_level=replay_level,
                determinism_score=determinism_score,
                created_at=created_at,
                created_by=created_by,
                duration_ms=duration_ms,
                cost_usd=cost_usd,
                error_message=error_message,
                model_name=model_name,
                model_provider=model_provider,
                temperature=temperature,
                object_storage_uri=object_storage_uri,
                tags=tags or {},
                extra_metadata=extra_metadata or {},
            )
            session.merge(run)  # Upsert
            session.commit()

    def get_by_id(self, kurral_id: UUID) -> Optional[dict[str, Any]]:
        """Get metadata by kurral_id"""
        with self.SessionLocal() as session:
            run = session.query(KurralRunModel).filter_by(kurral_id=kurral_id).first()
            if not run:
                return None

            return self._model_to_dict(run)

    def query(
        self,
        tenant_id: Optional[str] = None,
        environment: Optional[str] = None,
        semantic_bucket: Optional[str] = None,
        deterministic: Optional[bool] = None,
        replay_level: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query artifacts with filters

        Returns list of metadata dicts
        """
        with self.SessionLocal() as session:
            query = session.query(KurralRunModel)

            # Apply filters
            if tenant_id:
                query = query.filter(KurralRunModel.tenant_id == tenant_id)
            if environment:
                query = query.filter(KurralRunModel.environment == environment)
            if semantic_bucket:
                query = query.filter(KurralRunModel.semantic_buckets.contains([semantic_bucket]))
            if deterministic is not None:
                query = query.filter(KurralRunModel.deterministic == deterministic)
            if replay_level:
                query = query.filter(KurralRunModel.replay_level == replay_level)
            if start_date:
                query = query.filter(KurralRunModel.created_at >= start_date)
            if end_date:
                query = query.filter(KurralRunModel.created_at <= end_date)
            if model_name:
                query = query.filter(KurralRunModel.model_name == model_name)

            # Order and limit
            query = query.order_by(KurralRunModel.created_at.desc())
            query = query.limit(limit).offset(offset)

            runs = query.all()
            return [self._model_to_dict(run) for run in runs]

    def list_semantic_buckets(self, tenant_id: Optional[str] = None) -> list[str]:
        """
        List all unique semantic buckets

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of semantic bucket names
        """
        with self.SessionLocal() as session:
            query = session.query(KurralRunModel.semantic_buckets)

            if tenant_id:
                query = query.filter(KurralRunModel.tenant_id == tenant_id)

            results = query.distinct().all()

            # Flatten array results
            buckets = set()
            for (bucket_list,) in results:
                if bucket_list:
                    buckets.update(bucket_list)

            return sorted(buckets)

    def get_stats(self, tenant_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get statistics about stored artifacts

        Returns dict with counts, averages, etc.
        """
        with self.SessionLocal() as session:
            query = session.query(KurralRunModel)

            if tenant_id:
                query = query.filter(KurralRunModel.tenant_id == tenant_id)

            total = query.count()
            deterministic = query.filter(KurralRunModel.deterministic == True).count()

            # Level counts
            level_a = query.filter(KurralRunModel.replay_level == "A").count()
            level_b = query.filter(KurralRunModel.replay_level == "B").count()
            level_c = query.filter(KurralRunModel.replay_level == "C").count()

            return {
                "total": total,
                "deterministic": deterministic,
                "non_deterministic": total - deterministic,
                "level_a": level_a,
                "level_b": level_b,
                "level_c": level_c,
            }

    def delete(self, kurral_id: UUID) -> None:
        """Delete metadata by kurral_id"""
        with self.SessionLocal() as session:
            session.query(KurralRunModel).filter_by(kurral_id=kurral_id).delete()
            session.commit()

    @staticmethod
    def _model_to_dict(model: KurralRunModel) -> dict[str, Any]:
        """Convert SQLAlchemy model to dict"""
        return {
            "kurral_id": model.kurral_id,
            "run_id": model.run_id,
            "tenant_id": model.tenant_id,
            "environment": model.environment,
            "semantic_buckets": model.semantic_buckets,
            "deterministic": model.deterministic,
            "replay_level": model.replay_level,
            "determinism_score": model.determinism_score,
            "created_at": model.created_at,
            "created_by": model.created_by,
            "duration_ms": model.duration_ms,
            "cost_usd": model.cost_usd,
            "error_message": model.error_message,
            "model_name": model.model_name,
            "model_provider": model.model_provider,
            "temperature": model.temperature,
            "object_storage_uri": model.object_storage_uri,
            "tags": model.tags,
            "extra_metadata": model.extra_metadata,
        }

