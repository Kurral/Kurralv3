"""
Configuration management for Kurral
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from current working directory (where user runs their script)
try:
    from dotenv import load_dotenv
    # This searches for .env starting from cwd and going up parent directories
    load_dotenv(override=False)  # Don't override already-set env vars
except ImportError:
    pass  # python-dotenv not installed, rely on pydantic settings


# Config file locations (in order of priority)
CONFIG_FILE_LOCATIONS = [
    Path.cwd() / ".kurral" / "config.json",  # Project-specific
    Path.home() / ".config" / "kurral" / "config.json",  # User-wide (XDG)
    Path.home() / ".kurral" / "config.json",  # User-wide (legacy)
]


class KurralConfig(BaseSettings):
    """Global Kurral configuration"""

    model_config = SettingsConfigDict(
        env_prefix="KURRAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env that aren't defined in the model
    )

    # Application
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    
    # Debug logging (controlled by KURRAL_DEBUG env var)
    debug: bool = Field(default=False)  # Set KURRAL_DEBUG=true to enable debug output

    # Storage
    storage_backend: str = Field(default="local", description="local, memory, r2, or api")
    local_storage_path: Path = Field(default=Path("./artifacts"))
    
    # Memory storage limits
    memory_max_artifacts: int = Field(default=1000, description="Max artifacts in memory")
    memory_max_size_mb: int = Field(default=500, description="Max memory size in MB")

    # Kurral API (Cloud service with API key)
    kurral_api_key: Optional[str] = None
    kurral_api_url: str = Field(default="https://api.kurral.io")
    tenant_id: Optional[str] = None
    
    # Custom Bucket Mode (User's own R2/S3 bucket)
    custom_bucket_enabled: bool = Field(default=False, description="Use custom bucket instead of Kurral's")
    custom_bucket_name: Optional[str] = None
    custom_bucket_account_id: Optional[str] = None
    custom_bucket_access_key_id: Optional[str] = None
    custom_bucket_secret_access_key: Optional[str] = None
    custom_bucket_endpoint: Optional[str] = None  # For S3-compatible services
    custom_bucket_region: str = Field(default="auto")  # For R2 or S3 region

    # Legacy Cloudflare R2 (Kurral's shared bucket - deprecated, use API key instead)
    r2_bucket: Optional[str] = None
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None

    # PostgreSQL
    database_url: Optional[str] = Field(
        default="postgresql://kurral:kurral@localhost:5432/kurral"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # LangSmith
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None
    langsmith_enabled: bool = Field(default=False)

    # Auto-export
    auto_export: bool = Field(default=True, description="Automatically export traces to artifacts")

    # Replay
    replay_cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    replay_max_retries: int = Field(default=3)

    # Backtest
    backtest_default_threshold: float = Field(default=0.90)
    backtest_max_replays: int = Field(default=100)
    determinism_threshold: float = Field(default=0.90)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    api_key: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Fallback to standard LANGSMITH_ env vars (without KURRAL_ prefix)
        # This ensures compatibility with LangChain's standard env var names
        if not self.langsmith_api_key:
            self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
        if not self.langsmith_project:
            self.langsmith_project = os.getenv("LANGSMITH_PROJECT")
        
        # Ensure local storage path exists
        if self.storage_backend == "local":
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict:
        """Export config as dictionary (for saving to file)"""
        return {
            "storage_backend": self.storage_backend,
            "local_storage_path": str(self.local_storage_path),
            # Kurral API
            "kurral_api_key": self.kurral_api_key,
            "kurral_api_url": self.kurral_api_url,
            "tenant_id": self.tenant_id,
            # Custom bucket
            "custom_bucket_enabled": self.custom_bucket_enabled,
            "custom_bucket_name": self.custom_bucket_name,
            "custom_bucket_account_id": self.custom_bucket_account_id,
            "custom_bucket_access_key_id": self.custom_bucket_access_key_id,
            "custom_bucket_secret_access_key": self.custom_bucket_secret_access_key,
            "custom_bucket_endpoint": self.custom_bucket_endpoint,
            "custom_bucket_region": self.custom_bucket_region,
            # Legacy R2
            "r2_bucket": self.r2_bucket,
            "r2_account_id": self.r2_account_id,
            "r2_access_key_id": self.r2_access_key_id,
            "r2_secret_access_key": self.r2_secret_access_key,
            # LangSmith
            "langsmith_api_key": self.langsmith_api_key,
            "langsmith_project": self.langsmith_project,
            "langsmith_enabled": self.langsmith_enabled,
            # General
            "environment": self.environment,
            "debug": self.debug,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KurralConfig":
        """Load config from dictionary"""
        return cls(**data)


# Global config instance
_config: Optional[KurralConfig] = None


def load_config_file() -> Optional[dict]:
    """Load config from file (tries multiple locations)"""
    for config_path in CONFIG_FILE_LOCATIONS:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass  # Try next location
    return None


def save_config_file(config: KurralConfig, location: str = "user") -> Path:
    """
    Save config to file
    
    Args:
        config: KurralConfig instance
        location: "user" (default, ~/.config/kurral/) or "project" (./.kurral/)
    
    Returns:
        Path where config was saved
    """
    if location == "project":
        config_path = Path.cwd() / ".kurral" / "config.json"
    else:
        config_path = Path.home() / ".config" / "kurral" / "config.json"
    
    # Create directory
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save config (exclude None values for cleaner file)
    config_dict = {k: v for k, v in config.to_dict().items() if v is not None}
    
    with open(config_path, "w") as f:
        json.dump(config_dict, f, indent=2)
    
    return config_path


def get_config() -> KurralConfig:
    """
    Get global config instance
    
    Priority (highest to lowest):
    1. Environment variables (KURRAL_*)
    2. Config file (.kurral/config.json, ~/.config/kurral/config.json, ~/.kurral/config.json)
    3. Defaults
    """
    global _config
    if _config is None:
        # Load from config file first
        file_config = load_config_file()
        if file_config:
            _config = KurralConfig(**file_config)
        else:
            _config = KurralConfig()
    return _config


def set_config(config: KurralConfig) -> None:
    """Set global config instance"""
    global _config
    _config = config

