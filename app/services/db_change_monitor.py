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
        self.last_pending_count = None  # None means not initialized yet
        
    async def start_monitoring(self):
        """Start monitoring database for changes"""
        self.running = True
        logger.info(f"🔍 Starting database change monitor (checking every {self.check_interval}s)")
        
        # Wait a bit before first check to ensure automation has time to start
        await asyncio.sleep(5)
        
        # Get initial state (but don't act on it immediately - let automation start first)
        initial_state = await self._get_current_state()
        self.last_pending_count = initial_state.get("pending_count", 0)
        logger.info(f"📊 Initial state: {self.last_pending_count} PENDING prefixes (monitoring for changes)")
        
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
        """Get current state of prefix_metadata table - simple check for PENDING"""
        try:
            # Get only PENDING prefixes
            result = self.client.table("prefix_metadata").select("prefix,status").eq("status", "pending").execute()
            pending_prefixes = result.data or []
            
            state = {
                "pending_count": len(pending_prefixes)
            }
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {
                "pending_count": 0
            }
    
    def _detect_changes(self, current_state: dict) -> bool:
        """Detect if there are new PENDING prefixes to process"""
        
        pending_count = current_state.get("pending_count", 0)
        
        # Initialize on first check
        if self.last_pending_count is None:
            self.last_pending_count = pending_count
            # Only restart on initial check if automation is NOT running and there are pending prefixes
            if pending_count > 0 and not self.automation_service.running:
                logger.info(f"📊 Found {pending_count} PENDING prefixes (initial check) - automation not running, will restart")
                return True
            elif pending_count > 0:
                logger.info(f"📊 Found {pending_count} PENDING prefixes (initial check) - automation already running, no restart needed")
            return False
        
        # Only restart if:
        # 1. PENDING count INCREASED (new prefixes added), OR
        # 2. Automation is not running and there are pending prefixes
        if pending_count > self.last_pending_count:
            # New prefixes were added
            logger.info(f"📊 PENDING count increased: {self.last_pending_count} → {pending_count} (new prefixes detected)")
            self.last_pending_count = pending_count
            return True
        
        # If automation stopped but there are still pending prefixes, restart
        if pending_count > 0 and not self.automation_service.running:
            logger.info(f"📊 Automation stopped but {pending_count} PENDING prefixes exist - restarting")
            self.last_pending_count = pending_count
            return True
        
        # Update last known state (even if count decreased or stayed same)
        self.last_pending_count = pending_count
        
        return False
    
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

