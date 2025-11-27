"""Sequential automation service - processes one prefix at a time"""

import asyncio
import gc
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.id_generator import IDGeneratorService
from app.services.scraper import SPDCLScraperService
from app.services.sheets import GoogleSheetsService
from app.models.enums import PrefixStatus, OperationStatus

logger = logging.getLogger(__name__)


class SequentialAutomationService:
    """Service for sequential automated processing - ONE prefix at a time"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = get_supabase_client()
        self.id_generator = IDGeneratorService()
        self.scraper = SPDCLScraperService()
        self.sheets = GoogleSheetsService()
        self.running = False
        self.current_prefix = None
        self.stats = {
            "total_generated": 0,
            "mobile_numbers_found": 0,
            "errors": 0,
            "start_time": None,
            "current_prefix": None
        }
    
    async def start_sequential_processing(
        self, 
        generation_interval: int = 5  # seconds between generations
    ):
        """Start sequential processing - ONE prefix at a time based on database status"""
        
        self.running = True
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        logger.info("Starting SEQUENTIAL prefix processing")
        logger.info("Rule: Process ONE prefix at a time until completion")
        logger.info("Rule: Complete PENDING first, then NOT_STARTED")
        logger.info(f"Generation interval: {generation_interval}s")
        logger.info("Max IDs: Calculated from digit count (4 digits = 0000-9999, 5 digits = 00000-99999, etc.)")
        
        try:
            while self.running:
                try:
                    # Get the next prefix to process
                    current_prefix = await self._get_next_prefix_to_process()
                    
                    if current_prefix:
                        self.current_prefix = current_prefix
                        self.stats["current_prefix"] = current_prefix
                        
                        logger.info(f"🎯 Processing prefix: {current_prefix}")
                        
                        # Process this prefix until completion
                        await self._process_prefix_until_completion(
                            current_prefix, 
                            generation_interval
                        )
                        
                    else:
                        logger.info("⏸️  No prefixes to process, waiting...")
                        await asyncio.sleep(generation_interval)
                        
                except Exception as e:
                    # Handle individual iteration errors - don't stop the whole service
                    logger.error(f"Error in automation loop iteration: {e}")
                    logger.error(traceback.format_exc())
                    # Wait before retrying
                    await asyncio.sleep(generation_interval)
                    # Continue running - don't break the loop
                    
        except Exception as e:
            # Only log fatal errors - don't raise to keep service running
            logger.error(f"Fatal error in sequential processing: {e}")
            logger.error(traceback.format_exc())
            self.running = False
            # Don't raise - let the service stop gracefully and be restarted
        finally:
            self.current_prefix = None
            self.stats["current_prefix"] = None
            logger.info("Sequential processing loop ended")
    
    async def _get_next_prefix_to_process(self) -> Optional[str]:
        """Get the next prefix to process - PENDING first, then NOT_STARTED"""
        
        try:
            # PRIORITY 1: Process PENDING prefixes first (complete all pending work)
            pending_result = self.client.table("prefix_metadata").select("prefix").eq("status", PrefixStatus.PENDING.value).limit(1).execute()
            
            if pending_result.data:
                prefix = pending_result.data[0]["prefix"]
                logger.info(f"Found PENDING prefix to process: {prefix}")
                return prefix
            
            # PRIORITY 2: If no PENDING, start NOT_STARTED prefixes
            not_started_result = self.client.table("prefix_metadata").select("prefix").eq("status", PrefixStatus.NOT_STARTED.value).limit(1).execute()
            
            if not_started_result.data:
                prefix = not_started_result.data[0]["prefix"]
                logger.info(f"Found NOT_STARTED prefix to start: {prefix}")
                
                # Mark it as PENDING when we start processing
                self.client.table("prefix_metadata").update({
                    "status": PrefixStatus.PENDING.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("prefix", prefix).execute()
                
                logger.info(f"Marked {prefix} as PENDING (started processing)")
                return prefix
            
            # No prefixes to process
            return None
            
        except Exception as e:
            logger.error(f"Error getting next prefix: {e}")
            return None
    
    async def _process_prefix_until_completion(
        self, 
        prefix: str, 
        generation_interval: int
    ):
        """Process a single prefix until completion (reaches max for digit count)"""
        
        # Get prefix config to determine max number based on digits
        prefix_config = self.id_generator.get_prefix_status(prefix)
        if not prefix_config:
            logger.error(f"Prefix {prefix} not found in database")
            return
        
        digits = prefix_config.digits
        max_number = (10 ** digits) - 1  # 4 digits = 9999, 5 digits = 99999, etc.
        current_number = prefix_config.last_number
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        logger.info(f"Starting processing for prefix: {prefix}")
        logger.info(f"  Digits: {digits} (range: 0 to {max_number})")
        logger.info(f"  Current: {current_number}, Remaining: {max_number - current_number}")
        
        try:
            while self.running and current_number < max_number:
                try:
                    # Check current number before generating
                    prefix_config = self.id_generator.get_prefix_status(prefix)
                    if not prefix_config:
                        break
                    
                    current_number = prefix_config.last_number
                    
                    # Check if we've reached the maximum
                    if current_number >= max_number:
                        logger.info(f"Reached maximum for {prefix}: {current_number}/{max_number}")
                        break
                    
                    # Generate and process one ID
                    success = await self._generate_and_process_single_id(prefix)
                    
                    if success:
                        consecutive_errors = 0
                        # Update current number after generation
                        prefix_config = self.id_generator.get_prefix_status(prefix)
                        if prefix_config:
                            current_number = prefix_config.last_number
                            remaining = max_number - current_number
                            logger.info(f"Progress: {current_number}/{max_number} (remaining: {remaining})")
                        
                        # Periodic memory cleanup for free tier (every 50 IDs)
                        if current_number % 50 == 0:
                            gc.collect()
                            logger.debug("Memory cleanup performed")
                    else:
                        consecutive_errors += 1
                        logger.warning(f"Error count: {consecutive_errors}/{max_consecutive_errors}")
                    
                    # Check if too many consecutive errors
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors for {prefix}, keeping as PENDING")
                        # Keep as PENDING so it can be retried later
                        break
                    
                    # Wait before next generation
                    await asyncio.sleep(generation_interval)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {prefix}: {e}")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        # Keep as PENDING so it can be retried later
                        logger.warning(f"Too many errors for {prefix}, keeping as PENDING for retry")
                        break
                    
                    await asyncio.sleep(generation_interval)
            
            # Check final status and mark as completed if reached max
            final_config = self.id_generator.get_prefix_status(prefix)
            if final_config:
                if final_config.last_number >= max_number:
                    logger.info(f"Completed prefix {prefix} - reached maximum: {final_config.last_number}/{max_number}")
                    await self._mark_prefix_status(prefix, PrefixStatus.COMPLETED, f"Completed - reached max for {digits} digits ({max_number})")
                elif not self.running:
                    logger.info(f"Processing stopped for {prefix} at {final_config.last_number}")
            else:
                logger.warning(f"Could not get final status for {prefix}")
            
        except Exception as e:
            logger.error(f"Fatal error processing {prefix}: {e}")
            # Keep as PENDING so it can be retried later
            logger.warning(f"Keeping {prefix} as PENDING for retry after error")
    
    async def _generate_and_process_single_id(self, prefix: str) -> bool:
        """Generate and process a single ID - returns True if successful"""
        
        try:
            # Generate ID
            logger.info(f"Generating next ID for prefix: {prefix}")
            id_result = self.id_generator.generate_next_id(prefix)
            self.stats["total_generated"] += 1
            
            logger.info(f"Generated: {id_result.generated_id}")
            
            # Scrape mobile number
            logger.info(f"Scraping mobile number for: {id_result.generated_id}")
            scrape_result = self.scraper.scrape_mobile_number(id_result.generated_id)
            
            mobile_number = scrape_result.mobile_number if scrape_result.success else None
            
            if mobile_number:
                logger.info(f"Found mobile number: {mobile_number}")
                self.stats["mobile_numbers_found"] += 1
                
                # Log to Google Sheets only if mobile number found
                try:
                    if mobile_number and mobile_number.strip():
                        sheet_range = self.sheets.log_result(
                            prefix=prefix,
                            serial_number=id_result.serial_number,
                            generated_id=id_result.generated_id,
                            mobile_number=mobile_number,
                            timestamp=datetime.now(timezone.utc)
                        )
                        logger.info(f"Logged to sheets: {sheet_range}")
                    else:
                        logger.info(f"Skipping sheets logging for {id_result.generated_id} - no mobile number")
                    
                except Exception as e:
                    logger.warning(f"Sheets logging failed for {id_result.generated_id}: {e}")
            else:
                logger.info(f"No mobile number found for: {id_result.generated_id}")
            
            # Update last_extracted in database
            await self._update_last_extracted(prefix, id_result.serial_number)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating/processing ID for {prefix}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _update_last_extracted(self, prefix: str, serial_number: int):
        """Update the last_extracted field for the prefix"""
        
        try:
            self.client.table("prefix_metadata").update({
                "last_number": serial_number,  # This is already updated by ID generator
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("prefix", prefix).execute()
            
            logger.debug(f"📝 Updated last_extracted for {prefix}: {serial_number}")
            
        except Exception as e:
            logger.error(f"❌ Error updating last_extracted for {prefix}: {e}")
    
    async def _mark_prefix_status(self, prefix: str, status: PrefixStatus, remarks: str = None):
        """Mark prefix with specific status and optional remarks"""
        
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if remarks:
                update_data["remarks"] = remarks
            
            self.client.table("prefix_metadata").update(update_data).eq("prefix", prefix).execute()
            
            logger.info(f"📝 Marked {prefix} as {status.value}" + (f" - {remarks}" if remarks else ""))
            
        except Exception as e:
            logger.error(f"❌ Error marking {prefix} status: {e}")
    
    def stop(self):
        """Stop the automation service"""
        logger.info("🛑 Stopping sequential automation...")
        self.running = False
        
        # Keep current prefix as PENDING if interrupted
        if self.current_prefix:
            try:
                self.client.table("prefix_metadata").update({
                    "status": PrefixStatus.PENDING.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "remarks": "Stopped by user"
                }).eq("prefix", self.current_prefix).execute()
                
                logger.info(f"Marked {self.current_prefix} as PENDING (was interrupted)")
            except Exception as e:
                logger.error(f"Error marking {self.current_prefix} as PENDING: {e}")
    
    def get_stats(self) -> Dict:
        """Get current automation statistics"""
        stats = self.stats.copy()
        
        if stats["start_time"]:
            runtime = datetime.now(timezone.utc) - stats["start_time"]
            stats["runtime_seconds"] = runtime.total_seconds()
            stats["success_rate"] = (
                (stats["total_generated"] - stats["errors"]) / max(stats["total_generated"], 1) * 100
            )
        
        return stats
