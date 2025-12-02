"""
Service layer for R2 storage operations
"""

import json
from typing import Optional
from datetime import datetime
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class R2Service:
    """Service for interacting with Cloudflare R2 storage"""
    
    def __init__(self):
        """Initialize R2 client"""
        endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        
        self.bucket_name = settings.R2_BUCKET_NAME
    
    def _get_key(self, tenant_id: str, kurral_id: UUID, created_at: datetime) -> str:
        """
        Generate R2 key for artifact
        
        Format: {tenant_id}/{year}/{month}/{kurral_id}.kurral
        """
        return (
            f"{tenant_id}/"
            f"{created_at.year}/"
            f"{created_at.month:02d}/"
            f"{kurral_id}.kurral"
        )
    
    def upload_artifact(
        self,
        artifact_data: dict,
        tenant_id: str,
        kurral_id: UUID,
        created_at: datetime
    ) -> str:
        """
        Upload artifact to R2
        
        Args:
            artifact_data: Full artifact JSON
            tenant_id: Tenant ID
            kurral_id: Artifact UUID
            created_at: Creation timestamp
            
        Returns:
            R2 URI (r2://bucket/key)
        """
        key = self._get_key(tenant_id, kurral_id, created_at)
        
        # Serialize artifact
        content = json.dumps(artifact_data, indent=2, default=str)
        
        # Metadata
        metadata = {
            "kurral-id": str(kurral_id),
            "tenant-id": tenant_id,
            "created-at": created_at.isoformat(),
        }
        
        # Upload to R2
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
            Metadata=metadata,
        )
        
        uri = f"r2://{self.bucket_name}/{key}"
        return uri
    
    def download_artifact(self, uri: str) -> dict:
        """
        Download artifact from R2
        
        Args:
            uri: R2 URI (r2://bucket/key)
            
        Returns:
            Artifact data as dict
        """
        # Parse URI
        if not uri.startswith("r2://"):
            raise ValueError(f"Invalid R2 URI: {uri}")
        
        parts = uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Artifact not found at {uri}")
            raise
    
    def delete_artifact(self, uri: str) -> None:
        """
        Delete artifact from R2
        
        Args:
            uri: R2 URI (r2://bucket/key)
        """
        # Parse URI
        if not uri.startswith("r2://"):
            raise ValueError(f"Invalid R2 URI: {uri}")
        
        parts = uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise
    
    def artifact_exists(self, uri: str) -> bool:
        """
        Check if artifact exists in R2
        
        Args:
            uri: R2 URI (r2://bucket/key)
            
        Returns:
            True if exists, False otherwise
        """
        # Parse URI
        if not uri.startswith("r2://"):
            return False
        
        parts = uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
    
    def get_artifact_size(self, uri: str) -> int:
        """
        Get artifact size in bytes
        
        Args:
            uri: R2 URI (r2://bucket/key)
            
        Returns:
            Size in bytes
        """
        # Parse URI
        if not uri.startswith("r2://"):
            raise ValueError(f"Invalid R2 URI: {uri}")
        
        parts = uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            return response["ContentLength"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"Artifact not found at {uri}")
            raise


# Singleton instance
r2_service = R2Service()

