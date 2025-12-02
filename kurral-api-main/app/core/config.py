"""
Application configuration using Pydantic settings
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Project
    PROJECT_NAME: str = "Kurral API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    API_KEY_HEADER: str = "X-API-Key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Cloudflare R2
    R2_ACCOUNT_ID: str = Field(..., env="R2_ACCOUNT_ID")
    R2_ACCESS_KEY_ID: str = Field(..., env="R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str = Field(..., env="R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME: str = Field(..., env="R2_BUCKET_NAME")
    R2_PUBLIC_URL: Optional[str] = Field(None, env="R2_PUBLIC_URL")
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default="http://localhost:3000,http://localhost:8000"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    
    # Artifacts
    MAX_ARTIFACT_SIZE_MB: int = Field(default=10, env="MAX_ARTIFACT_SIZE_MB")
    ARTIFACT_RETENTION_DAYS: int = Field(default=90, env="ARTIFACT_RETENTION_DAYS")
    
    # Admin
    ADMIN_EMAIL: Optional[str] = Field(None, env="ADMIN_EMAIL")
    ADMIN_PASSWORD: Optional[str] = Field(None, env="ADMIN_PASSWORD")
    
    @model_validator(mode='after')
    def parse_cors_origins(self):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(self.CORS_ORIGINS, str):
            self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()

