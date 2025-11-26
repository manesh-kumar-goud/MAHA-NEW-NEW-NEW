"""Application configuration with robust validation"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from pydantic import Field, validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and defaults"""
    
    # Database
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    
    # Google Sheets
    google_service_account_file: Optional[str] = Field(
        default=None,
        description="Path to Google service account JSON file (optional if GOOGLE_SERVICE_ACCOUNT_JSON is set)"
    )
    google_service_account_json: Optional[str] = Field(
        default=None,
        description="Google service account JSON as string (for Railway/env vars)"
    )
    google_sheet_id: str = Field(..., description="Google Sheet ID")
    
    # Application settings
    app_name: str = Field(default="SPDCL ID Generator", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    cors_origins: list[str] = Field(default=["*"], description="CORS origins")
    
    # ID Generation
    default_digits: int = Field(default=5, ge=1, le=12, description="Default number of digits")
    default_has_space: bool = Field(default=True, description="Default space between prefix and number")
    
    # Scraping settings
    scraper_enabled: bool = Field(default=True, description="Enable web scraping")
    scraper_timeout: int = Field(default=30, ge=5, le=120, description="Scraper timeout in seconds")
    scraper_max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    scraper_retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Retry delay in seconds")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, ge=1, description="Requests per minute")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @model_validator(mode='after')
    def validate_service_account(self):
        """Validate service account - either JSON env var or file must be provided"""
        # Check if JSON env var is set (even if not in values yet)
        json_from_env = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or self.google_service_account_json
        
        # If JSON is provided, file is not needed
        if json_from_env:
            # Clear file path if JSON is provided
            self.google_service_account_file = None
            return self
        
        # If no JSON, file must exist
        if not self.google_service_account_file or not Path(self.google_service_account_file).exists():
            raise ValueError(
                "Either GOOGLE_SERVICE_ACCOUNT_JSON env var or google_service_account_file must be provided. "
                f"File not found: {self.google_service_account_file}"
            )
        
        return self
    
    @validator("supabase_url")
    def validate_supabase_url(cls, v):
        """Validate Supabase URL format"""
        if not v.startswith("https://") or "supabase.co" not in v:
            raise ValueError("Invalid Supabase URL format")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()
