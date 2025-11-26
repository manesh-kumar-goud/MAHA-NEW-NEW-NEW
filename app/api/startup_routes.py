"""Startup and database management API endpoints"""

import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.startup import StartupService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/startup", tags=["startup"])


class DatabaseSummaryResponse(BaseModel):
    """Database summary response"""
    total_prefixes: int
    by_status: Dict[str, int]
    prefixes: List[Dict]


class ResumeResponse(BaseModel):
    """Resume automation response"""
    running_resumed: List[str]
    pending_started: List[str]
    completed_marked: List[str]
    errors_reset: List[str]
    total_prefixes_to_automate: int
    message: str


@router.get("/database-summary", response_model=DatabaseSummaryResponse)
async def get_database_summary():
    """Get current database state summary"""
    
    startup_service = StartupService()
    summary = startup_service.get_database_summary()
    
    return DatabaseSummaryResponse(**summary)


@router.post("/check-and-resume", response_model=ResumeResponse)
async def check_and_resume_automation():
    """Check database and automatically resume/start automation"""
    
    startup_service = StartupService()
    
    try:
        resume_summary = await startup_service.check_and_resume_automation()
        
        # Create response message
        messages = []
        if resume_summary["running_resumed"]:
            messages.append(f"Resumed {len(resume_summary['running_resumed'])} running prefixes")
        if resume_summary["pending_started"]:
            messages.append(f"Started {len(resume_summary['pending_started'])} pending prefixes")
        if resume_summary["errors_reset"]:
            messages.append(f"Reset {len(resume_summary['errors_reset'])} error prefixes")
        
        if resume_summary["total_prefixes_to_automate"] > 0:
            messages.append(f"Automation started for {resume_summary['total_prefixes_to_automate']} prefixes")
        else:
            messages.append("No prefixes require automation")
        
        return ResumeResponse(
            **resume_summary,
            message="; ".join(messages)
        )
        
    except Exception as e:
        logger.error(f"Failed to check and resume: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check and resume automation: {str(e)}"
        )


@router.post("/reset-completed-to-pending")
async def reset_completed_to_pending():
    """Reset all COMPLETED prefixes to PENDING for a new cycle"""
    
    startup_service = StartupService()
    
    try:
        reset_prefixes = await startup_service.mark_all_completed_as_pending()
        
        return {
            "message": f"Reset {len(reset_prefixes)} completed prefixes to pending",
            "reset_prefixes": reset_prefixes
        }
        
    except Exception as e:
        logger.error(f"Failed to reset completed prefixes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset prefixes: {str(e)}"
        )


@router.post("/force-start-automation")
async def force_start_automation(prefixes: List[str]):
    """Force start automation for specific prefixes (regardless of status)"""
    
    from app.services.automation import AutomationService
    import asyncio
    
    try:
        automation_service = AutomationService()
        
        if automation_service.running:
            raise HTTPException(
                status_code=400,
                detail="Automation is already running. Stop it first."
            )
        
        # Start automation
        asyncio.create_task(
            automation_service.start_continuous_generation(
                prefixes=prefixes,
                generation_interval=5,
                batch_size=1
            )
        )
        
        return {
            "message": f"Force started automation for {len(prefixes)} prefixes",
            "prefixes": prefixes
        }
        
    except Exception as e:
        logger.error(f"Failed to force start automation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start automation: {str(e)}"
        )
