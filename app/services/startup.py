"""Startup service to check and resume existing automation tasks"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

from app.core.database import get_supabase_client
from app.models.enums import PrefixStatus
from app.models.schemas import PrefixConfig
from app.services.automation_new import SequentialAutomationService

logger = logging.getLogger(__name__)


class StartupService:
    """Service to check database state and resume automation on startup"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.automation_service = SequentialAutomationService()
        self.automation_task = None  # Store task reference
    
    async def check_and_resume_automation(self) -> Dict:
        """Check database for running/pending prefixes and resume automation"""
        
        logger.info("Checking Supabase for existing automation tasks...")
        
        # Get all prefixes from database
        all_prefixes = self._get_all_prefixes()
        
        # Categorize prefixes by status (only 3 statuses: NOT_STARTED, PENDING, COMPLETED)
        not_started_prefixes = []
        pending_prefixes = []
        completed_prefixes = []
        
        for prefix_data in all_prefixes:
            # Convert old statuses before validation
            old_status = prefix_data.get("status", "not_started")
            if old_status in ["running", "error", "paused"]:
                logger.warning(f"Converting old status '{old_status}' for {prefix_data.get('prefix')} to PENDING")
                # Update in database directly
                from app.core.database import get_supabase_client
                client = get_supabase_client()
                client.table("prefix_metadata").update({
                    "status": PrefixStatus.PENDING.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("prefix", prefix_data.get("prefix")).execute()
                # Update in memory for processing
                prefix_data["status"] = "pending"
            
            config = PrefixConfig(**prefix_data)
            
            if config.status == PrefixStatus.NOT_STARTED:
                not_started_prefixes.append(config)
            elif config.status == PrefixStatus.PENDING:
                pending_prefixes.append(config)
            elif config.status == PrefixStatus.COMPLETED:
                completed_prefixes.append(config)
        
        logger.info(f"Database Status:")
        logger.info(f"   NOT_STARTED: {len(not_started_prefixes)}")
        logger.info(f"   PENDING: {len(pending_prefixes)}")
        logger.info(f"   COMPLETED: {len(completed_prefixes)}")
        
        # Process prefixes in priority order: PENDING first, then NOT_STARTED
        resume_summary = {
            "pending_to_process": [],
            "not_started_to_process": [],
            "completed": [],
            "total_prefixes_to_automate": 0
        }
        
        # PRIORITY 1: Process all PENDING prefixes first
        if pending_prefixes:
            logger.info(f"Found {len(pending_prefixes)} PENDING prefixes - will process these first")
            for config in pending_prefixes:
                resume_summary["pending_to_process"].append(config.prefix)
        
        # PRIORITY 2: Then process NOT_STARTED prefixes
        if not_started_prefixes:
            logger.info(f"Found {len(not_started_prefixes)} NOT_STARTED prefixes - will process after PENDING")
            for config in not_started_prefixes:
                resume_summary["not_started_to_process"].append(config.prefix)
        
        # Keep COMPLETED as is
        if completed_prefixes:
            logger.info(f"Found {len(completed_prefixes)} COMPLETED prefixes (keeping as completed)")
            for config in completed_prefixes:
                resume_summary["completed"].append(config.prefix)
        
        # Determine which prefixes to automate (PENDING first, then NOT_STARTED)
        prefixes_to_automate = (
            resume_summary["pending_to_process"] + 
            resume_summary["not_started_to_process"]
        )
        
        resume_summary["total_prefixes_to_automate"] = len(prefixes_to_automate)
        
        # Start automation if we have prefixes to process
        if prefixes_to_automate:
            logger.info(f"Starting automation for {len(prefixes_to_automate)} prefixes")
            logger.info(f"  Priority order: PENDING first ({len(resume_summary['pending_to_process'])}), then NOT_STARTED ({len(resume_summary['not_started_to_process'])})")
            
            # Start sequential automation (will automatically pick up prefixes from database)
            # It will process PENDING first, then NOT_STARTED
            # Only start if not already running
            if not self.automation_service.running:
                import asyncio
                task = asyncio.create_task(
                    self.automation_service.start_sequential_processing(
                        generation_interval=5  # 5 seconds between generations
                        # Max IDs calculated automatically from digit count
                    )
                )
                # Store task reference to prevent garbage collection
                self.automation_task = task
                logger.info("Automation task created and started")
            else:
                logger.info("Automation already running, skipping start")
            
        else:
            logger.info("No prefixes require automation at startup")
        
        return resume_summary
    
    def _get_all_prefixes(self) -> List[Dict]:
        """Get all prefixes from database"""
        try:
            result = self.client.table("prefix_metadata").select("*").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch prefixes: {e}")
            return []
    
    async def _resume_running_prefix(self, config: PrefixConfig):
        """Resume a RUNNING prefix"""
        logger.info(f"Resuming RUNNING prefix: {config.prefix} (last_number: {config.last_number})")
        
        # Update timestamp to show it's being resumed
        try:
            self.client.table("prefix_metadata").update({
                "remarks": f"Resumed at startup - last: {config.last_number}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("prefix", config.prefix).execute()
        except Exception as e:
            logger.error(f"Failed to update running prefix {config.prefix}: {e}")
    
    async def _start_pending_prefix(self, config: PrefixConfig):
        """Start a PENDING prefix"""
        logger.info(f"Starting PENDING prefix: {config.prefix} (will start from: {config.last_number + 1})")
        
        # Update status to RUNNING
        try:
            self.client.table("prefix_metadata").update({
                "status": PrefixStatus.PENDING.value,
                "remarks": f"Auto-started at startup - from: {config.last_number + 1}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("prefix", config.prefix).execute()
        except Exception as e:
            logger.error(f"Failed to start pending prefix {config.prefix}: {e}")
    
    async def _reset_error_prefix(self, config: PrefixConfig):
        """Reset an ERROR prefix to PENDING"""
        logger.info(f"Resetting ERROR prefix: {config.prefix} (remarks: {config.remarks})")
        
        # Reset to PENDING status
        try:
            self.client.table("prefix_metadata").update({
                "status": PrefixStatus.PENDING.value,
                "remarks": f"Auto-reset from ERROR at startup - previous: {config.remarks}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("prefix", config.prefix).execute()
        except Exception as e:
            logger.error(f"Failed to reset error prefix {config.prefix}: {e}")
    
    def get_database_summary(self) -> Dict:
        """Get a summary of current database state"""
        all_prefixes = self._get_all_prefixes()
        
        summary = {
            "total_prefixes": len(all_prefixes),
            "by_status": {},
            "prefixes": []
        }
        
        for prefix_data in all_prefixes:
            # Convert old statuses before validation
            old_status = prefix_data.get("status", "not_started")
            if old_status in ["running", "error", "paused"]:
                prefix_data["status"] = "pending"
            
            config = PrefixConfig(**prefix_data)
            
            # Count by status
            status = config.status.value
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Add prefix info
            summary["prefixes"].append({
                "prefix": config.prefix,
                "status": config.status.value,
                "last_number": config.last_number,
                "digits": config.digits,
                "has_space": config.has_space,
                "remarks": config.remarks,
                "updated_at": config.updated_at
            })
        
        return summary
    
    async def mark_all_completed_as_pending(self) -> List[str]:
        """Mark all COMPLETED prefixes as PENDING for a new cycle"""
        logger.info("Marking all COMPLETED prefixes as PENDING for new cycle...")
        
        try:
            # Get completed prefixes
            result = self.client.table("prefix_metadata").select("prefix").eq("status", PrefixStatus.COMPLETED.value).execute()
            completed_prefixes = [row["prefix"] for row in result.data]
            
            if completed_prefixes:
                # Update all to PENDING
                self.client.table("prefix_metadata").update({
                    "status": PrefixStatus.PENDING.value,
                    "remarks": "Reset to PENDING for new automation cycle",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("status", PrefixStatus.COMPLETED.value).execute()
                
                logger.info(f"Marked {len(completed_prefixes)} prefixes as PENDING: {completed_prefixes}")
            
            return completed_prefixes
            
        except Exception as e:
            logger.error(f"Failed to mark completed as pending: {e}")
            return []
