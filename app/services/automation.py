"""Automated continuous data generation service"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.id_generator import IDGeneratorService
from app.services.scraper import SPDCLScraperService
from app.services.sheets import GoogleSheetsService
from app.models.enums import PrefixStatus, OperationStatus

logger = logging.getLogger(__name__)


class AutomationService:
    """Service for continuous automated ID generation and processing"""
    
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
    
    async def start_continuous_generation(
        self, 
        prefixes: List[str] = None,  # Optional - will read from database
        generation_interval: int = 5,  # seconds between generations
        batch_size: int = 1
    ):
        """Start continuous generation - processes ONE prefix at a time based on status"""
        
        self.running = True
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        logger.info("Starting sequential prefix processing based on database status")
        logger.info(f"Generation interval: {generation_interval}s, Batch size: {batch_size}")
        
        try:
            while self.running:
                # Get next prefix to process from database
                current_prefix = await self._get_next_prefix_to_process()
                
                if current_prefix:
                    logger.info(f"Processing prefix: {current_prefix}")
                    
                    # Process this prefix until completion or error
                    await self._process_prefix_until_completion(current_prefix, generation_interval, batch_size)
                    
                else:
                    logger.info("No prefixes to process, waiting...")
                    await asyncio.sleep(generation_interval)
                    
        except Exception as e:
            logger.error(f"Continuous generation error: {e}")
            self.running = False
            raise
    
    async def _process_batch(self, prefix: str, batch_size: int):
        """Process a batch of IDs for a prefix"""
        
        logger.info(f"Processing batch of {batch_size} for prefix: {prefix}")
        
        for i in range(batch_size):
            if not self.running:
                break
            
            try:
                await self._generate_single_id(prefix)
                
                # Small delay between individual generations
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error generating ID for {prefix}: {e}")
                self.stats["errors"] += 1
    
    async def _generate_single_id(self, prefix: str):
        """Generate and process a single ID"""
        
        try:
            # Generate ID
            id_result = self.id_generator.generate_next_id(prefix)
            self.stats["total_generated"] += 1
            
            logger.info(f"Generated: {id_result.generated_id}")
            
            # Scrape mobile number
            mobile_number = None
            scrape_success = False
            
            try:
                scrape_result = self.scraper.scrape_mobile_number(id_result.generated_id)
                mobile_number = scrape_result.mobile_number
                scrape_success = scrape_result.success
                
                if mobile_number:
                    self.stats["mobile_numbers_found"] += 1
                    logger.info(f"Found mobile: {mobile_number} for {id_result.generated_id}")
                
            except Exception as e:
                logger.warning(f"Scraping failed for {id_result.generated_id}: {e}")
            
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
            
            # Update prefix status
            if mobile_number:
                self.id_generator.update_prefix_status(
                    prefix, 
                    PrefixStatus.RUNNING, 
                    f"Last success: {id_result.generated_id}"
                )
            
            # Log to serial_log table
            try:
                # Map to valid status values for serial_log table
                if scrape_success and mobile_number:
                    log_status = "completed"
                elif scrape_success and not mobile_number:
                    log_status = "completed"  # Scraping succeeded but no mobile found
                else:
                    log_status = "error"  # Scraping failed
                
                self.id_generator.log_serial_event(
                    prefix=prefix,
                    generated_id=id_result.generated_id,
                    mobile_number=mobile_number,
                    status=log_status,
                    metadata={
                        "automated": True,
                        "mobile_found": bool(mobile_number),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Serial log failed: {e}")
                
        except Exception as e:
            logger.error(f"Failed to generate ID for {prefix}: {e}")
            
            # Mark prefix as error if too many failures
            try:
                self.id_generator.update_prefix_status(
                    prefix, 
                    PrefixStatus.ERROR, 
                    f"Generation failed: {str(e)}"
                )
            except Exception:
                pass
            
            raise
    
    def stop(self):
        """Stop continuous generation"""
        logger.info("Stopping continuous generation...")
        self.running = False
    
    def get_stats(self) -> Dict:
        """Get automation statistics"""
        runtime = None
        if self.stats["start_time"]:
            runtime = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds()
        
        return {
            **self.stats,
            "running": self.running,
            "runtime_seconds": runtime,
            "success_rate": (
                self.stats["mobile_numbers_found"] / max(self.stats["total_generated"], 1)
            ) * 100
        }
    
    async def run_for_duration(
        self, 
        prefixes: List[str], 
        duration_minutes: int,
        generation_interval: int = 5
    ):
        """Run automation for a specific duration"""
        
        logger.info(f"Running automation for {duration_minutes} minutes")
        
        # Start generation task
        generation_task = asyncio.create_task(
            self.start_continuous_generation(prefixes, generation_interval)
        )
        
        # Wait for duration
        await asyncio.sleep(duration_minutes * 60)
        
        # Stop generation
        self.stop()
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(generation_task, timeout=10)
        except asyncio.TimeoutError:
            generation_task.cancel()
        
        logger.info(f"Automation completed. Stats: {self.get_stats()}")
        return self.get_stats()
