"""Automation API endpoints"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.automation import AutomationService
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/automation", tags=["automation"])

# Global automation service instance
automation_service = AutomationService()


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
    
    if automation_service.running:
        raise HTTPException(
            status_code=400,
            detail="Automation is already running. Stop it first."
        )
    
    logger.info(f"Starting automation for prefixes: {request.prefixes}")
    
    # Start automation in background
    background_tasks.add_task(
        automation_service.start_continuous_generation,
        request.prefixes,
        request.generation_interval,
        request.batch_size
    )
    
    return {
        "message": "Automation started successfully",
        "prefixes": request.prefixes,
        "generation_interval": request.generation_interval,
        "batch_size": request.batch_size
    }


@router.post("/run")
async def run_automation(
    request: AutomationRunRequest,
    background_tasks: BackgroundTasks
):
    """Run automation for a specific duration"""
    
    if automation_service.running:
        raise HTTPException(
            status_code=400,
            detail="Automation is already running. Stop it first."
        )
    
    logger.info(f"Running automation for {request.duration_minutes} minutes")
    
    # Run automation in background
    background_tasks.add_task(
        automation_service.run_for_duration,
        request.prefixes,
        request.duration_minutes,
        request.generation_interval
    )
    
    return {
        "message": f"Automation will run for {request.duration_minutes} minutes",
        "prefixes": request.prefixes,
        "duration_minutes": request.duration_minutes,
        "generation_interval": request.generation_interval
    }


@router.post("/stop")
async def stop_automation():
    """Stop running automation"""
    
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
    
    stats = automation_service.get_stats()
    
    return AutomationStatsResponse(
        running=stats["running"],
        total_generated=stats["total_generated"],
        mobile_numbers_found=stats["mobile_numbers_found"],
        errors=stats["errors"],
        runtime_seconds=stats["runtime_seconds"],
        success_rate=stats["success_rate"]
    )


@router.get("/health")
async def automation_health():
    """Check automation service health"""
    
    return {
        "status": "healthy",
        "automation_running": automation_service.running,
        "stats": automation_service.get_stats()
    }
