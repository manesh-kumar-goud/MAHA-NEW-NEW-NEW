"""Database change monitor - detects Supabase changes and restarts automation"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)


class DatabaseChangeMonitor:
    """Monitor Supabase for changes and trigger automation restart"""
    
    def __init__(self, automation_service, check_interval: int = 30):
        """
        Initialize change monitor
        
        Args:
            automation_service: The automation service to restart
            check_interval: How often to check for changes (seconds)
        """
        self.client = get_supabase_client()
        self.automation_service = automation_service
        self.check_interval = check_interval
        self.running = False
        self.last_check_time = None
        self.last_prefix_count = 0
        self.last_pending_count = 0
        
    async def start_monitoring(self):
        """Start monitoring database for changes"""
        self.running = True
        logger.info(f"🔍 Starting database change monitor (checking every {self.check_interval}s)")
        
        # Get initial state
        await self._get_current_state()
        
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)
                
                if not self.running:
                    break
                
                # Check for changes
                current_state = await self._get_current_state()
                
                # Detect changes
                if self._detect_changes(current_state):
                    logger.info("🔄 Database changes detected - restarting automation...")
                    await self._restart_automation()
                    
            except Exception as e:
                logger.error(f"❌ Error in change monitor: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue monitoring even if there's an error
                await asyncio.sleep(self.check_interval)
    
    async def _get_current_state(self) -> dict:
        """Get current state of prefix_metadata table"""
        try:
            # Get all prefixes
            result = self.client.table("prefix_metadata").select("*").execute()
            all_prefixes = result.data or []
            
            # Count by status
            pending_count = sum(1 for p in all_prefixes if p.get("status") == "pending")
            not_started_count = sum(1 for p in all_prefixes if p.get("status") == "not_started")
            completed_count = sum(1 for p in all_prefixes if p.get("status") == "completed")
            
            # Get last updated timestamp
            last_updated = None
            for prefix in all_prefixes:
                updated_at = prefix.get("updated_at")
                if updated_at:
                    try:
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        if last_updated is None or dt > last_updated:
                            last_updated = dt
                    except:
                        pass
            
            state = {
                "total_count": len(all_prefixes),
                "pending_count": pending_count,
                "not_started_count": not_started_count,
                "completed_count": completed_count,
                "last_updated": last_updated,
                "check_time": datetime.now(timezone.utc)
            }
            
            self.last_check_time = state["check_time"]
            return state
            
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {
                "total_count": 0,
                "pending_count": 0,
                "not_started_count": 0,
                "completed_count": 0,
                "last_updated": None,
                "check_time": datetime.now(timezone.utc)
            }
    
    def _detect_changes(self, current_state: dict) -> bool:
        """Detect if there are meaningful changes"""
        
        # First check - no previous state
        if self.last_prefix_count == 0:
            self.last_prefix_count = current_state["total_count"]
            self.last_pending_count = current_state["pending_count"]
            return False
        
        # Check for changes
        changes_detected = False
        
        # 1. New prefixes added
        if current_state["total_count"] > self.last_prefix_count:
            logger.info(f"📊 New prefixes detected: {current_state['total_count']} (was {self.last_prefix_count})")
            changes_detected = True
        
        # 2. Pending count changed (status changed)
        if current_state["pending_count"] != self.last_pending_count:
            logger.info(f"📊 Pending count changed: {current_state['pending_count']} (was {self.last_pending_count})")
            changes_detected = True
        
        # 3. Recent updates (within last check interval)
        if current_state["last_updated"]:
            if self.last_check_time:
                time_since_update = (self.last_check_time - current_state["last_updated"]).total_seconds()
                # If update happened within last check interval, it's a change
                if abs(time_since_update) < self.check_interval * 2:
                    logger.info(f"📊 Recent database update detected (within last {self.check_interval * 2}s)")
                    changes_detected = True
        
        # Update last known state
        self.last_prefix_count = current_state["total_count"]
        self.last_pending_count = current_state["pending_count"]
        
        return changes_detected
    
    async def _restart_automation(self):
        """Restart the automation service"""
        try:
            # Stop current automation if running
            if self.automation_service.running:
                logger.info("⏸️  Stopping current automation...")
                self.automation_service.stop()
                # Wait a bit for it to stop
                await asyncio.sleep(2)
            
            # Check for new work
            from app.services.startup import StartupService
            startup = StartupService()
            startup.automation_service = self.automation_service
            
            resume_summary = await startup.check_and_resume_automation()
            
            if resume_summary['total_prefixes_to_automate'] > 0:
                logger.info(f"✅ Restarting automation for {resume_summary['total_prefixes_to_automate']} prefixes")
                await self.automation_service.start_sequential_processing(generation_interval=5)
            else:
                logger.info("ℹ️  No prefixes to automate after restart")
                
        except Exception as e:
            logger.error(f"❌ Error restarting automation: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def stop(self):
        """Stop monitoring"""
        logger.info("🛑 Stopping database change monitor...")
        self.running = False

