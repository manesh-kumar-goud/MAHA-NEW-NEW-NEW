"""Automation API endpoints"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field

from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/automation", tags=["automation"])

# Try to import automation service - use the actual service that exists
try:
    from app.services.automation_new import SequentialAutomationService
    automation_service = SequentialAutomationService()
except ImportError:
    # Fallback if import fails
    logger.warning("Could not import SequentialAutomationService - automation routes may not work")
    automation_service = None


class AutomationStartRequest(BaseModel):
    """Request to start automation"""
    prefixes: List[str] = Field(..., description="List of prefixes to process")
    generation_interval: int = Field(default=5, ge=1, le=300, description="Seconds between generations")
    batch_size: int = Field(default=1, ge=1, le=10, description="Number of IDs to generate per batch")


class AutomationRunRequest(BaseModel):
    """Request to run automation for duration"""
    prefixes: List[str] = Field(..., description="List of prefixes to process")
    duration_minutes: int = Field(..., ge=1, le=1440, description="Duration in minutes")
    generation_interval: int = Field(default=5, ge=1, le=300, description="Seconds between generations")


class AutomationStatsResponse(BaseModel):
    """Automation statistics response"""
    running: bool
    total_generated: int
    mobile_numbers_found: int
    errors: int
    runtime_seconds: Optional[float]
    success_rate: float


@router.post("/start")
async def start_automation(
    request: AutomationStartRequest,
    background_tasks: BackgroundTasks
):
    """Start continuous automation (runs indefinitely until stopped)"""
    
    if automation_service is None:
        raise HTTPException(
            status_code=503,
            detail="Automation service is not available"
        )
    
    if automation_service.running:
        raise HTTPException(
            status_code=400,
            detail="Automation is already running. Stop it first."
        )
    
    logger.info(f"Starting automation for prefixes: {request.prefixes}")
    
    # Start automation in background - SequentialAutomationService uses start_sequential_processing
    # Note: SequentialAutomationService doesn't support batch_size or specific prefixes in the same way
    background_tasks.add_task(
        automation_service.start_sequential_processing,
        request.generation_interval
    )
    
    return {
        "message": "Automation started successfully",
        "prefixes": request.prefixes,
        "generation_interval": request.generation_interval,
        "note": "Sequential automation processes prefixes from database, not from request"
    }


@router.post("/run")
async def run_automation(
    request: AutomationRunRequest,
    background_tasks: BackgroundTasks
):
    """Run automation for a specific duration"""
    
    if automation_service is None:
        raise HTTPException(
            status_code=503,
            detail="Automation service is not available"
        )
    
    if automation_service.running:
        raise HTTPException(
            status_code=400,
            detail="Automation is already running. Stop it first."
        )
    
    logger.info(f"Running automation for {request.duration_minutes} minutes")
    
    # SequentialAutomationService doesn't have run_for_duration, use start_sequential_processing
    # Duration control would need to be implemented separately
    background_tasks.add_task(
        automation_service.start_sequential_processing,
        request.generation_interval
    )
    
    return {
        "message": f"Automation started (duration control not implemented for sequential service)",
        "prefixes": request.prefixes,
        "duration_minutes": request.duration_minutes,
        "generation_interval": request.generation_interval,
        "note": "Sequential automation will run until stopped manually"
    }


@router.post("/stop")
async def stop_automation():
    """Stop running automation"""
    
    if automation_service is None:
        raise HTTPException(
            status_code=503,
            detail="Automation service is not available"
        )
    
    if not automation_service.running:
        raise HTTPException(
            status_code=400,
            detail="Automation is not currently running"
        )
    
    automation_service.stop()
    
    return {
        "message": "Automation stopped successfully",
        "final_stats": automation_service.get_stats()
    }


@router.get("/status", response_model=AutomationStatsResponse)
async def get_automation_status():
    """Get current automation status and statistics"""
    
    if automation_service is None:
        return AutomationStatsResponse(
            running=False,
            total_generated=0,
            mobile_numbers_found=0,
            errors=0,
            runtime_seconds=None,
            success_rate=0.0
        )
    
    stats = automation_service.get_stats()
    
    return AutomationStatsResponse(
        running=stats.get("running", automation_service.running),
        total_generated=stats.get("total_generated", 0),
        mobile_numbers_found=stats.get("mobile_numbers_found", 0),
        errors=stats.get("errors", 0),
        runtime_seconds=stats.get("runtime_seconds"),
        success_rate=stats.get("success_rate", 0.0)
    )


@router.get("/health")
async def automation_health():
    """Check automation service health"""
    
    if automation_service is None:
        return {
            "status": "unavailable",
            "automation_running": False,
            "stats": {}
        }
    
    return {
        "status": "healthy",
        "automation_running": automation_service.running,
        "stats": automation_service.get_stats()
    }
