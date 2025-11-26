"""API route definitions"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import health_check as db_health_check
from app.models.schemas import (
    GenerateIDRequest, GenerateIDResponse, PrefixConfigResponse,
    HealthResponse, ErrorResponse, ScrapeResult
)
from app.models.enums import OperationStatus, PrefixStatus
from app.services import IDGeneratorService, SPDCLScraperService, GoogleSheetsService

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency injection
def get_id_generator() -> IDGeneratorService:
    return IDGeneratorService()

def get_scraper() -> SPDCLScraperService:
    return SPDCLScraperService()

def get_sheets() -> GoogleSheetsService:
    return GoogleSheetsService()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    
    services = {}
    
    # Check database
    services["database"] = db_health_check()
    
    # Check scraper
    try:
        scraper = SPDCLScraperService()
        services["scraper"] = scraper.health_check()
    except Exception:
        services["scraper"] = False
    
    # Check Google Sheets
    try:
        sheets = GoogleSheetsService()
        services["sheets"] = sheets.health_check()
    except Exception:
        services["sheets"] = False
    
    # Overall status
    overall_healthy = all(services.values())
    
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        services=services
    )


@router.post("/prefixes/{prefix}/generate", response_model=GenerateIDResponse)
async def generate_id(
    prefix: str,
    request: GenerateIDRequest,
    background_tasks: BackgroundTasks,
    id_generator: IDGeneratorService = Depends(get_id_generator),
    scraper: SPDCLScraperService = Depends(get_scraper),
    sheets: GoogleSheetsService = Depends(get_sheets),
    settings = Depends(get_settings)
):
    """Generate next ID for a prefix with scraping and logging"""
    
    prefix = prefix.strip().upper()
    logger.info(f"Generating ID for prefix: {prefix}, dry_run: {request.dry_run}")
    
    try:
        # Generate ID
        id_result = id_generator.generate_next_id(
            prefix=prefix,
            digits=request.digits,
            has_space=request.has_space
        )
        
        timestamp = datetime.now(timezone.utc)
        mobile_number = None
        metadata = {}
        status = OperationStatus.SUCCESS
        sheet_range = None
        
        # Scraping (if not dry run)
        if not request.dry_run:
            try:
                scrape_result = scraper.scrape_mobile_number(id_result.generated_id)
                mobile_number = scrape_result.mobile_number
                
                metadata["scraper"] = {
                    "success": scrape_result.success,
                    "attempts": scrape_result.attempts,
                    "response_time": scrape_result.response_time,
                    "error_message": scrape_result.error_message
                }
                
                if not scrape_result.success:
                    status = OperationStatus.PARTIAL
                    
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                metadata["scraper"] = {"error": str(e)}
                status = OperationStatus.PARTIAL
        else:
            metadata["scraper"] = {"skipped": "dry_run"}
        
        # Google Sheets logging (if not dry run)
        if not request.dry_run:
            try:
                sheet_range = sheets.log_result(
                    prefix=prefix,
                    serial_number=id_result.serial_number,
                    generated_id=id_result.generated_id,
                    mobile_number=mobile_number,
                    timestamp=timestamp,
                    sheet_id=request.sheet_id
                )
                metadata["sheets"] = {"range": sheet_range}
                
            except Exception as e:
                logger.error(f"Sheets logging failed: {e}")
                metadata["sheets"] = {"error": str(e)}
                if status == OperationStatus.SUCCESS:
                    status = OperationStatus.PARTIAL
        else:
            metadata["sheets"] = {"skipped": "dry_run"}
        
        # Background task: Log to serial_log table
        if not request.dry_run:
            background_tasks.add_task(
                log_serial_event,
                id_generator,
                prefix,
                id_result.generated_id,
                mobile_number,
                status.value,
                metadata
            )
        
        # Update prefix status
        if status == OperationStatus.FAILED:
            id_generator.update_prefix_status(
                prefix, 
                PrefixStatus.ERROR, 
                "Generation failed"
            )
        elif mobile_number:
            id_generator.update_prefix_status(
                prefix, 
                PrefixStatus.COMPLETED, 
                "Mobile number found"
            )
        
        return GenerateIDResponse(
            generated_id=id_result.generated_id,
            prefix=prefix,
            serial_number=id_result.serial_number,
            mobile_number=mobile_number,
            timestamp=timestamp,
            status=status,
            sheet_range=sheet_range,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"ID generation failed: {e}")
        
        # Update prefix status to error
        try:
            id_generator.update_prefix_status(
                prefix, 
                PrefixStatus.ERROR, 
                str(e)
            )
        except Exception:
            pass  # Don't fail if status update fails
        
        raise HTTPException(
            status_code=500,
            detail=f"ID generation failed: {str(e)}"
        )


@router.get("/prefixes/{prefix}/status", response_model=PrefixConfigResponse)
async def get_prefix_status(
    prefix: str,
    id_generator: IDGeneratorService = Depends(get_id_generator)
):
    """Get current status of a prefix"""
    
    prefix = prefix.strip().upper()
    config = id_generator.get_prefix_status(prefix)
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Prefix '{prefix}' not found"
        )
    
    return PrefixConfigResponse(
        prefix=config.prefix,
        digits=config.digits,
        last_number=config.last_number,
        has_space=config.has_space,
        status=config.status,
        remarks=config.remarks,
        created_at=config.created_at or datetime.now(timezone.utc),
        updated_at=config.updated_at or datetime.now(timezone.utc)
    )


@router.post("/prefixes/{prefix}/reset")
async def reset_prefix(
    prefix: str,
    starting_number: int = 0,
    id_generator: IDGeneratorService = Depends(get_id_generator)
):
    """Reset a prefix to a specific starting number"""
    
    prefix = prefix.strip().upper()
    
    try:
        # Update the prefix configuration
        config = id_generator.get_prefix_status(prefix)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Prefix '{prefix}' not found"
            )
        
        # Update last_number to starting_number - 1 so next generation gives starting_number
        updated_config = id_generator.client.table("prefix_metadata").update({
            "last_number": starting_number,
            "status": PrefixStatus.PENDING.value,
            "remarks": f"Reset to {starting_number}",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("prefix", prefix).execute()
        
        return {
            "message": f"Prefix '{prefix}' reset to start from {starting_number + 1}",
            "prefix": prefix,
            "next_number": starting_number + 1
        }
        
    except Exception as e:
        logger.error(f"Prefix reset failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset prefix: {str(e)}"
        )


async def log_serial_event(
    id_generator: IDGeneratorService,
    prefix: str,
    generated_id: str,
    mobile_number: Optional[str],
    status: str,
    metadata: dict
):
    """Background task to log serial event"""
    try:
        id_generator.log_serial_event(
            prefix=prefix,
            generated_id=generated_id,
            mobile_number=mobile_number,
            status=status,
            metadata=metadata
        )
    except Exception as e:
        logger.error(f"Failed to log serial event: {e}")


# Note: Exception handlers are added at the app level in main.py
