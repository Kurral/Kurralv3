"""
Default configuration for Kurral replay system
Provides default LLM parameters when not specified in artifact
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from kurral.models.kurral import LLMParameters, ModelConfig


# Default LLM parameters (used when not in artifact)
DEFAULT_LLM_PARAMETERS = LLMParameters(
    temperature=0.0,
    seed=42,
    top_p=None,
    top_k=None,
    max_tokens=None,
    frequency_penalty=None,
    presence_penalty=None,
)


def get_llm_parameters_from_artifact(
    artifact_config: Optional[ModelConfig],
) -> LLMParameters:
    """
    Get LLM parameters from artifact, or use defaults if not present
    
    Args:
        artifact_config: ModelConfig from artifact (may be None)
        
    Returns:
        LLMParameters with values from artifact or defaults
    """
    if artifact_config and artifact_config.parameters:
        params = artifact_config.parameters
        return LLMParameters(
            temperature=params.temperature if params.temperature is not None else DEFAULT_LLM_PARAMETERS.temperature,
            seed=params.seed if params.seed is not None else DEFAULT_LLM_PARAMETERS.seed,
            top_p=params.top_p if params.top_p is not None else DEFAULT_LLM_PARAMETERS.top_p,
            top_k=params.top_k if params.top_k is not None else DEFAULT_LLM_PARAMETERS.top_k,
            max_tokens=params.max_tokens if params.max_tokens is not None else DEFAULT_LLM_PARAMETERS.max_tokens,
            frequency_penalty=params.frequency_penalty if params.frequency_penalty is not None else DEFAULT_LLM_PARAMETERS.frequency_penalty,
            presence_penalty=params.presence_penalty if params.presence_penalty is not None else DEFAULT_LLM_PARAMETERS.presence_penalty,
        )
    else:
        return DEFAULT_LLM_PARAMETERS


@dataclass
class StorageConfig:
    """Storage configuration loaded from environment variables"""
    
    # Storage backend type
    backend: str = "local"  # local, r2, hybrid
    
    # R2 Configuration (optional)
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    
    # Local storage path
    local_storage_path: Optional[Path] = None
    
    # Tenant ID
    tenant_id: str = "default"
    
    # PostgreSQL/Supabase (optional - for future metadata storage)
    database_url: Optional[str] = None
    
    @classmethod
    def from_env(cls, env_file_path: Optional[Path] = None) -> "StorageConfig":
        """
        Load storage configuration from environment variables
        
        Args:
            env_file_path: Optional path to .env file to load (uses dotenv if provided)
            
        Returns:
            StorageConfig instance with values from environment
        """
        # Load .env file if provided
        if env_file_path and env_file_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file_path, override=False)
            except ImportError:
                pass  # dotenv not available, continue with os.getenv
        
        # Get storage backend type
        # Note: "hybrid" mode removed - using R2-only when R2 is configured
        backend = os.getenv("STORAGE_BACKEND", "local").lower()
        if backend not in ["local", "r2"]:
            backend = "local"
        
        # Get R2 credentials (all optional)
        r2_account_id = os.getenv("R2_ACCOUNT_ID") or None
        r2_access_key_id = os.getenv("R2_ACCESS_KEY_ID") or None
        r2_secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY") or None
        r2_bucket_name = os.getenv("R2_BUCKET_NAME") or None
        
        # Get local storage path
        local_path_str = os.getenv("LOCAL_STORAGE_PATH")
        local_storage_path = Path(local_path_str) if local_path_str else None
        
        # Get tenant ID
        tenant_id = os.getenv("TENANT_ID", "default")
        
        # Get database URL (optional)
        database_url = os.getenv("DATABASE_URL") or None
        
        return cls(
            backend=backend,
            r2_account_id=r2_account_id,
            r2_access_key_id=r2_access_key_id,
            r2_secret_access_key=r2_secret_access_key,
            r2_bucket_name=r2_bucket_name,
            local_storage_path=local_storage_path,
            tenant_id=tenant_id,
            database_url=database_url,
        )
    
    def has_r2_credentials(self) -> bool:
        """Check if all required R2 credentials are present"""
        return all([
            self.r2_account_id,
            self.r2_access_key_id,
            self.r2_secret_access_key,
            self.r2_bucket_name,
        ])
    
    def get_storage_backend(self) -> str:
        """
        Determine which storage backend to use based on configuration
        
        Returns:
            "local" or "r2"
        """
        # If R2 credentials are provided, use R2-only mode
        if self.has_r2_credentials():
            return "r2"
        else:
            return "local"


def get_agent_name(agent_dir: Optional[Path] = None) -> str:
    """
    Get agent name from agent directory or environment variable
    
    Args:
        agent_dir: Optional path to agent directory
        
    Returns:
        Agent name (e.g., "level3agentK")
    """
    # Check environment variable first
    agent_name = os.getenv("AGENT_NAME")
    if agent_name:
        return agent_name
    
    # Use directory name as fallback
    if agent_dir:
        return Path(agent_dir).name
    
    # Final fallback
    return "default"


def get_storage_config(agent_dir: Optional[Path] = None) -> StorageConfig:
    """
    Get storage configuration, loading from agent directory .env file if provided
    
    Args:
        agent_dir: Optional path to agent directory containing .env file
        
    Returns:
        StorageConfig instance
    """
    env_file = None
    if agent_dir:
        env_file = Path(agent_dir) / ".env"
        if not env_file.exists():
            env_file = None
    
    return StorageConfig.from_env(env_file)

