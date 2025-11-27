"""Pydantic schemas for data validation"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .enums import PrefixStatus, OperationStatus


# Request Models
class GenerateIDRequest(BaseModel):
    """Request to generate next ID for a prefix"""
    digits: Optional[int] = Field(default=None, ge=1, le=12, description="Number of digits")
    has_space: Optional[bool] = Field(default=None, description="Include space between prefix and number")
    dry_run: bool = Field(default=False, description="Skip scraping and sheets logging")
    sheet_id: Optional[str] = Field(default=None, description="Override Google Sheet ID")


class PrefixConfigRequest(BaseModel):
    """Request to create/update prefix configuration"""
    digits: int = Field(ge=1, le=12, description="Number of digits")
    has_space: bool = Field(description="Include space between prefix and number")
    starting_number: int = Field(default=0, ge=0, description="Starting number for the prefix")


# Response Models
class PrefixConfigResponse(BaseModel):
    """Prefix configuration response"""
    prefix: str
    digits: int
    last_number: int
    has_space: bool
    status: PrefixStatus


class GenerateIDResponse(BaseModel):
    """Response for ID generation"""
    generated_id: str
    prefix: str
    serial_number: int
    mobile_number: Optional[str] = None
    status: OperationStatus
    sheet_range: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScrapeResult(BaseModel):
    """Result from web scraping"""
    mobile_number: Optional[str] = None
    success: bool
    attempts: int
    error_message: Optional[str] = None
    response_time: float
    raw_data: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = "2.0.0"
    services: Dict[str, bool] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# Internal Models
class PrefixConfig(BaseModel):
    """Internal prefix configuration model"""
    prefix: str
    digits: int
    last_number: int
    has_space: bool
    status: PrefixStatus

    @validator('prefix')
    def validate_prefix(cls, v):
        """Validate prefix format"""
        if not v or not v.strip():
            raise ValueError("Prefix cannot be empty")
        return v.strip().upper()


class SerialLogEntry(BaseModel):
    """Serial number log entry"""
    id: str
    prefix: str
    generated_id: str
    mobile_number: Optional[str]
    status: OperationStatus
    metadata: Optional[Dict[str, Any]] = None


class IDGenerationResult(BaseModel):
    """Result of ID generation process"""
    prefix_config: PrefixConfig
    generated_id: str
    serial_number: int
    formatted_id: str
