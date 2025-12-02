"""
Cloudflare R2 storage backend
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from kurral.models.kurral import KurralArtifact
from kurral.storage.storage_backend import StorageBackend, StorageResult


class R2Storage(StorageBackend):
    """Cloudflare R2 storage backend using S3-compatible API"""
    
    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        tenant_id: str = "default",
        agent_name: Optional[str] = None,
        path_prefix: str = "artifacts",
        local_backup_path: Optional[Path] = None
    ):
        """
        Initialize R2 storage
        
        Args:
            account_id: Cloudflare R2 account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
            tenant_id: Tenant ID for organizing artifacts
            agent_name: Agent name for organizing artifacts (e.g., "level3agentK")
            path_prefix: Path prefix for artifact type ("artifacts" or "replay_runs")
            local_backup_path: Optional local path for backup storage (not used in R2-only mode)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for R2 storage. Install it with: pip install boto3"
            )
        
        self.account_id = account_id
        self.bucket_name = bucket_name
        self.tenant_id = tenant_id
        self.agent_name = agent_name
        self.path_prefix = path_prefix
        self.local_backup_path = local_backup_path
        
        # Initialize S3 client for R2
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )
    
    def _get_key(self, kurral_id: UUID, created_at: datetime) -> str:
        """
        Generate R2 key for artifact
        
        Format: {tenant_id}/{agent_name}/{path_prefix}/{year}/{month}/{kurral_id}.kurral
        If agent_name is None, uses: {tenant_id}/{path_prefix}/{year}/{month}/{kurral_id}.kurral
        """
        parts = [self.tenant_id]
        
        # Add agent name if provided
        if self.agent_name:
            parts.append(self.agent_name)
        
        # Add path prefix (artifacts or replay_runs)
        parts.append(self.path_prefix)
        
        # Add date-based organization
        parts.extend([
            str(created_at.year),
            f"{created_at.month:02d}",
            f"{kurral_id}.kurral"
        ])
        
        return "/".join(parts)
    
    def save(self, artifact: KurralArtifact) -> StorageResult:
        """Save artifact to R2"""
        key = self._get_key(artifact.kurral_id, artifact.created_at)
        
        try:
            # Serialize artifact
            content = artifact.to_json(pretty=True)
            
            # Metadata
            metadata = {
                "kurral-id": str(artifact.kurral_id),
                "tenant-id": artifact.tenant_id,
                "created-at": artifact.created_at.isoformat(),
            }
            
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
                Metadata=metadata,
            )
            
            # Create R2 URI
            storage_uri = f"r2://{self.bucket_name}/{key}"
            
            # R2-only mode: no local backup
            return StorageResult(
                success=True,
                storage_uri=storage_uri,
                local_path=None  # R2-only, no local backup
            )
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Failed to upload artifact to R2: {e}"
            )
    
    def load(self, kurral_id: UUID) -> Optional[KurralArtifact]:
        """
        Load artifact by ID from R2
        
        Searches through all artifacts in the agent's path prefix to find by kurral_id
        """
        # Build search prefix
        if self.agent_name:
            prefix = f"{self.tenant_id}/{self.agent_name}/{self.path_prefix}/"
        else:
            prefix = f"{self.tenant_id}/{self.path_prefix}/"
        
        # Search through all artifacts in the prefix
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".kurral"):
                        continue
                    
                    # Quick check: if filename matches kurral_id, try loading it
                    if str(kurral_id) not in key:
                        continue
                    
                    try:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        content = response["Body"].read().decode("utf-8")
                        artifact_data = json.loads(content)
                        
                        # Verify it's the right artifact
                        if UUID(artifact_data["kurral_id"]) == kurral_id:
                            return KurralArtifact(**artifact_data)
                    except Exception:
                        continue
        except Exception:
            pass
        
        return None
    
    def load_by_run_id(self, run_id: str) -> Optional[KurralArtifact]:
        """
        Load artifact by run_id from R2
        
        Note: This requires listing objects, which can be slow.
        Consider using metadata indexing for better performance.
        """
        # List objects in tenant/agent/path_prefix folder
        if self.agent_name:
            prefix = f"{self.tenant_id}/{self.agent_name}/{self.path_prefix}/"
        else:
            prefix = f"{self.tenant_id}/{self.path_prefix}/"
        
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".kurral"):
                        continue
                    
                    try:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        content = response["Body"].read().decode("utf-8")
                        artifact_data = json.loads(content)
                        
                        if artifact_data.get("run_id") == run_id:
                            return KurralArtifact(**artifact_data)
                    except Exception:
                        continue
        except Exception:
            pass
        
        return None
    
    def exists(self, kurral_id: UUID) -> bool:
        """Check if artifact exists in R2"""
        return self.load(kurral_id) is not None
    
    def list_artifacts(self, limit: Optional[int] = None) -> list[KurralArtifact]:
        """
        List all artifacts from R2
        
        Note: This can be slow for large buckets.
        Consider using metadata indexing for better performance.
        """
        artifacts = []
        # List objects in tenant/agent/path_prefix folder
        if self.agent_name:
            prefix = f"{self.tenant_id}/{self.agent_name}/{self.path_prefix}/"
        else:
            prefix = f"{self.tenant_id}/{self.path_prefix}/"
        
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".kurral"):
                        continue
                    
                    try:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        content = response["Body"].read().decode("utf-8")
                        artifact_data = json.loads(content)
                        artifact = KurralArtifact(**artifact_data)
                        artifacts.append(artifact)
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Sort by created_at, most recent first
        artifacts.sort(key=lambda x: x.created_at, reverse=True)
        
        if limit:
            artifacts = artifacts[:limit]
        
        return artifacts

