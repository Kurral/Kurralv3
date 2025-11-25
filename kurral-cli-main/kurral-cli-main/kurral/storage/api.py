"""
Kurral API client for cloud artifact storage
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

try:
    import httpx
except ImportError:
    httpx = None

from kurral.models.kurral import KurralArtifact


class KurralAPIClient:
    """
    Client for uploading artifacts to Kurral's managed cloud storage
    
    This client handles authentication and artifact uploads to the Kurral API,
    which automatically stores artifacts in Kurral's managed R2 bucket.
    """

    def __init__(self, api_key: str, api_url: str = "https://api.kurral.io"):
        """
        Initialize Kurral API client
        
        Args:
            api_key: Kurral API key (get from https://app.kurral.io/settings/api-keys)
            api_url: Base URL for Kurral API (default: https://api.kurral.io)
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for API storage. Install with: pip install httpx"
            )
        
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        
        # Create HTTP client with authentication
        self.client = httpx.Client(
            base_url=self.api_url,
            headers={
                "kurral": self.api_key,  # Kurral API expects "kurral" header
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    
    def save(self, artifact: KurralArtifact) -> str:
        """
        Upload artifact to Kurral cloud
        
        Args:
            artifact: KurralArtifact to upload
        
        Returns:
            Cloud URI (api://kurral.io/{artifact_id})
        
        Raises:
            httpx.HTTPStatusError: If upload fails
        """
        # Convert artifact to dict (parse the JSON)
        import json
        artifact_dict = json.loads(artifact.to_json(pretty=False))
        
        # Wrap in the expected schema format
        request_body = {
            "artifact_data": artifact_dict
        }
        
        # Upload to API
        try:
            response = self.client.post(
                "/api/v1/artifacts/upload",
                json=request_body,  # Use json parameter instead of content
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Generate URI
            uri = f"api://{self.api_url.replace('https://', '').replace('http://', '')}/{artifact.kurral_id}"
            
            # Update artifact with storage URI
            artifact.object_storage_uri = uri
            
            return uri
            
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = str(e)
            
            raise Exception(f"Failed to upload artifact to Kurral API: {error_detail}") from e
        except Exception as e:
            raise Exception(f"Failed to upload artifact to Kurral API: {str(e)}") from e
    
    def load(self, kurral_id: UUID, tenant_id: str) -> KurralArtifact:
        """
        Download artifact from Kurral cloud
        
        Args:
            kurral_id: Artifact UUID
            tenant_id: Tenant ID
        
        Returns:
            KurralArtifact
        
        Raises:
            httpx.HTTPStatusError: If download fails
        """
        try:
            response = self.client.get(
                f"/api/v1/artifacts/{kurral_id}",
                params={"tenant_id": tenant_id},
            )
            response.raise_for_status()
            
            artifact_json = response.text
            return KurralArtifact.from_json(artifact_json)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"Artifact {kurral_id} not found in Kurral cloud")
            
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = str(e)
            
            raise Exception(f"Failed to download artifact from Kurral API: {error_detail}") from e
    
    def list_artifacts(
        self,
        tenant_id: Optional[str] = None,
        semantic_bucket: Optional[str] = None,
        environment: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List artifacts from Kurral cloud
        
        Args:
            tenant_id: Filter by tenant
            semantic_bucket: Filter by semantic bucket
            environment: Filter by environment
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
        
        Returns:
            List of artifact metadata
        """
        params = {"limit": limit}
        
        if tenant_id:
            params["tenant_id"] = tenant_id
        if semantic_bucket:
            params["semantic_bucket"] = semantic_bucket
        if environment:
            params["environment"] = environment
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        try:
            response = self.client.get("/api/v1/artifacts", params=params)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = str(e)
            
            raise Exception(f"Failed to list artifacts from Kurral API: {error_detail}") from e
    
    def delete(self, kurral_id: UUID, tenant_id: str) -> None:
        """
        Delete artifact from Kurral cloud
        
        Args:
            kurral_id: Artifact UUID
            tenant_id: Tenant ID
        """
        try:
            response = self.client.delete(
                f"/api/v1/artifacts/{kurral_id}",
                params={"tenant_id": tenant_id},
            )
            response.raise_for_status()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Already deleted, silently succeed
                return
            
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = str(e)
            
            raise Exception(f"Failed to delete artifact from Kurral API: {error_detail}") from e
    
    def health_check(self) -> bool:
        """
        Check if API is reachable and credentials are valid
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

