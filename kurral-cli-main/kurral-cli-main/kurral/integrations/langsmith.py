"""
LangSmith API integration for trace import
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import httpx
from langsmith import Client

from kurral.core.artifact import ArtifactGenerator
from kurral.models.kurral import KurralArtifact
from kurral.models.langsmith import LangSmithRun, LangSmithTrace


class LangSmithIntegration:
    """
    Integration with LangSmith for trace import and export
    """

    def __init__(self, api_key: str, project: Optional[str] = None):
        """
        Initialize LangSmith client

        Args:
            api_key: LangSmith API key
            project: Default project name
        """
        self.api_key = api_key
        self.project = project
        self.client = Client(api_key=api_key)
        self.http_client = httpx.AsyncClient(
            base_url="https://api.smith.langchain.com",
            headers={"x-api-key": api_key},
            timeout=30.0,
        )

    async def get_run(self, run_id: str) -> dict[str, Any]:
        """
        Fetch a single run from LangSmith

        Args:
            run_id: LangSmith run ID

        Returns:
            Run data as dict
        """
        response = await self.http_client.get(f"/runs/{run_id}")
        response.raise_for_status()
        return response.json()

    async def list_runs(
        self,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        run_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        List runs from LangSmith

        Args:
            project_id: Filter by project
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum runs to return
            offset: Pagination offset
            run_type: Filter by run type (llm, chain, tool, etc.)
            tags: Filter by tags

        Returns:
            List of run data dicts
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if project_id:
            params["project"] = project_id
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        if run_type:
            params["run_type"] = run_type
        if tags:
            params["tag"] = tags

        response = await self.http_client.get("/runs", params=params)
        response.raise_for_status()
        return response.json()

    def normalize_to_kurral(
        self, run: dict[str, Any], tenant_id: str = "default"
    ) -> KurralArtifact:
        """
        Convert LangSmith run to Kurral artifact

        Args:
            run: LangSmith run data
            tenant_id: Tenant ID to assign

        Returns:
            KurralArtifact
        """
        generator = ArtifactGenerator()
        return generator.from_langsmith_run(run, tenant_id)

    async def import_run(self, run_id: str, tenant_id: str = "default") -> KurralArtifact:
        """
        Import a single run and convert to artifact

        Args:
            run_id: LangSmith run ID
            tenant_id: Tenant ID

        Returns:
            KurralArtifact
        """
        run = await self.get_run(run_id)
        return self.normalize_to_kurral(run, tenant_id)

    async def import_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[KurralArtifact]:
        """
        Import all runs from a project

        Args:
            project_id: LangSmith project ID
            tenant_id: Tenant ID
            start_time: Start time filter
            end_time: End time filter
            limit: Max runs to import

        Returns:
            List of KurralArtifacts
        """
        runs = await self.list_runs(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        artifacts = []
        for run in runs:
            try:
                artifact = self.normalize_to_kurral(run, tenant_id)
                artifacts.append(artifact)
            except Exception as e:
                print(f"Warning: Failed to convert run {run.get('id')}: {e}")
                continue

        return artifacts

    async def export_artifact(
        self, artifact: KurralArtifact, project: Optional[str] = None
    ) -> str:
        """
        Export a Kurral artifact back to LangSmith as metadata

        Args:
            artifact: KurralArtifact to export
            project: LangSmith project name

        Returns:
            LangSmith run ID
        """
        project_name = project or self.project

        # Use the LangSmith SDK to create/update a run with metadata
        # This attaches kurral_id and replay_level to the original trace
        try:
            # Update the run with Kurral metadata
            self.client.update_run(
                run_id=artifact.run_id,
                extra={
                    "kurral_id": str(artifact.kurral_id),
                    "replay_level": artifact.replay_level.value,
                    "deterministic": artifact.deterministic,
                    "determinism_score": artifact.determinism_report.overall_score,
                },
            )
            return artifact.run_id
        except Exception as e:
            print(f"Warning: Failed to export to LangSmith: {e}")
            return ""

    async def poll_new_runs(
        self,
        project_id: str,
        tenant_id: str,
        callback: callable,
        poll_interval: int = 300,
        last_timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Poll for new runs and invoke callback

        Args:
            project_id: LangSmith project ID
            tenant_id: Tenant ID
            callback: Async function to call with new artifacts
            poll_interval: Polling interval in seconds
            last_timestamp: Last poll timestamp
        """
        current_timestamp = last_timestamp or datetime.utcnow()

        while True:
            try:
                # Fetch runs since last poll
                runs = await self.list_runs(
                    project_id=project_id,
                    start_time=current_timestamp,
                )

                # Convert to artifacts
                for run in runs:
                    try:
                        artifact = self.normalize_to_kurral(run, tenant_id)
                        await callback(artifact)
                    except Exception as e:
                        print(f"Error processing run {run.get('id')}: {e}")

                # Update timestamp
                current_timestamp = datetime.utcnow()

            except Exception as e:
                print(f"Error polling LangSmith: {e}")

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def close(self) -> None:
        """Close HTTP client"""
        await self.http_client.aclose()

    async def __aenter__(self) -> "LangSmithIntegration":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.close()

