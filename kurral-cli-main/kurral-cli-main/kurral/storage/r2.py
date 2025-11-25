"""
Cloudflare R2 storage backend for .kurral artifacts
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from kurral.models.kurral import KurralArtifact


class R2Storage:
    """
    Cloudflare R2-based storage for Kurral artifacts

    Artifacts are stored with key pattern:
    {tenant_id}/{year}/{month}/{kurral_id}.kurral
    """

    def __init__(
        self,
        bucket: str,
        account_id: str,
        r2_access_key_id: str,
        r2_secret_access_key: str,
        prefix: str = "",
        endpoint_url: Optional[str] = None,
        region: str = "auto",
    ):
        """
        Initialize Cloudflare R2 or S3-compatible storage

        Args:
            bucket: R2/S3 bucket name
            account_id: Cloudflare account ID (for R2) or AWS account (for S3)
            r2_access_key_id: R2/S3 access key ID
            r2_secret_access_key: R2/S3 secret access key
            prefix: Optional prefix for all keys
            endpoint_url: Custom endpoint URL (for S3-compatible services)
            region: Region name (default: "auto" for R2, or specify AWS region)
        """
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.account_id = account_id

        # Determine endpoint URL
        if endpoint_url:
            # Custom endpoint (e.g., for S3-compatible services)
            self.endpoint_url = endpoint_url
        elif region == "auto":
            # Cloudflare R2 endpoint
            self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        else:
            # AWS S3 endpoint (or None for default)
            self.endpoint_url = None

        # Initialize S3-compatible client
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=r2_access_key_id,
            aws_secret_access_key=r2_secret_access_key,
            region_name=region,
        )

    def _get_key(self, artifact: KurralArtifact) -> str:
        """
        Generate R2 key for artifact

        Format: {prefix}/{tenant_id}/{year}/{month}/{kurral_id}.kurral
        """
        timestamp = artifact.created_at
        parts = [
            self.prefix,
            artifact.tenant_id,
            str(timestamp.year),
            f"{timestamp.month:02d}",
            f"{artifact.kurral_id}.kurral",
        ]
        # Filter out empty strings
        parts = [p for p in parts if p]
        return "/".join(parts)

    def _get_key_by_id(
        self, kurral_id: UUID, tenant_id: str, created_at: datetime
    ) -> str:
        """Generate R2 key from ID and metadata"""
        parts = [
            self.prefix,
            tenant_id,
            str(created_at.year),
            f"{created_at.month:02d}",
            f"{kurral_id}.kurral",
        ]
        parts = [p for p in parts if p]
        return "/".join(parts)

    def save(self, artifact: KurralArtifact) -> str:
        """
        Save artifact to R2

        Args:
            artifact: KurralArtifact to save

        Returns:
            R2 URI (r2://bucket/key)
        """
        key = self._get_key(artifact)

        # Serialize artifact
        content = artifact.to_json(pretty=True)

        # Upload to R2
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "kurral-id": str(artifact.kurral_id),
                "tenant-id": artifact.tenant_id,
                "replay-level": artifact.replay_level.value,
                "deterministic": str(artifact.deterministic),
            },
        )

        uri = f"r2://{self.bucket}/{key}"

        # Update artifact with storage URI
        artifact.object_storage_uri = uri

        return uri

    def load(self, kurral_id: UUID, tenant_id: str, created_at: datetime) -> KurralArtifact:
        """
        Load artifact from R2

        Args:
            kurral_id: Artifact UUID
            tenant_id: Tenant ID
            created_at: Creation timestamp (for key generation)

        Returns:
            KurralArtifact
        """
        key = self._get_key_by_id(kurral_id, tenant_id, created_at)

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return KurralArtifact.from_json(content)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Artifact {kurral_id} not found in R2")
            raise

    def load_by_uri(self, uri: str) -> KurralArtifact:
        """
        Load artifact by R2 URI

        Args:
            uri: R2 URI (r2://bucket/key) or S3 URI (s3://bucket/key for compatibility)

        Returns:
            KurralArtifact
        """
        # Parse URI - support both r2:// and s3:// for compatibility
        if uri.startswith("r2://"):
            parts = uri[5:].split("/", 1)
        elif uri.startswith("s3://"):
            parts = uri[5:].split("/", 1)
        else:
            raise ValueError(f"Invalid URI: {uri} (expected r2:// or s3://)")

        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""

        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return KurralArtifact.from_json(content)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Artifact not found at {uri}")
            raise

    def list_artifacts(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[str]:
        """
        List artifact URIs

        Args:
            tenant_id: Filter by tenant
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            List of R2 URIs
        """
        # Build prefix for filtering
        prefix_parts = [self.prefix]
        if tenant_id:
            prefix_parts.append(tenant_id)

        prefix = "/".join([p for p in prefix_parts if p])
        if prefix:
            prefix += "/"

        # List objects
        paginator = self.s3.get_paginator("list_objects_v2")
        uris = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if "Contents" not in page:
                break

            for obj in page["Contents"]:
                key = obj["Key"]

                # Date filtering (basic - could be improved)
                if start_date or end_date:
                    # Extract date from key path
                    # This is a simplified version
                    pass

                uri = f"r2://{self.bucket}/{key}"
                uris.append(uri)

                if len(uris) >= limit:
                    return uris

        return uris

    def delete(self, kurral_id: UUID, tenant_id: str, created_at: datetime) -> None:
        """
        Delete artifact from R2

        Args:
            kurral_id: Artifact UUID
            tenant_id: Tenant ID
            created_at: Creation timestamp
        """
        key = self._get_key_by_id(kurral_id, tenant_id, created_at)

        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise

    def exists(self, kurral_id: UUID, tenant_id: str, created_at: datetime) -> bool:
        """
        Check if artifact exists in R2

        Args:
            kurral_id: Artifact UUID
            tenant_id: Tenant ID
            created_at: Creation timestamp

        Returns:
            True if exists
        """
        key = self._get_key_by_id(kurral_id, tenant_id, created_at)

        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

