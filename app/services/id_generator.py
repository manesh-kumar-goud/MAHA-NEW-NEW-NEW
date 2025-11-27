"""ID generation service with robust error handling"""

import logging
from datetime import datetime, timezone
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.database import get_supabase_client
from app.models.schemas import PrefixConfig, IDGenerationResult
from app.models.enums import PrefixStatus

logger = logging.getLogger(__name__)


class IDGeneratorService:
    """Service for generating sequential IDs with Supabase backend"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.table_name = "prefix_metadata"
        self.log_table = "serial_log"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def generate_next_id(
        self, 
        prefix: str, 
        digits: Optional[int] = None,
        has_space: Optional[bool] = None
    ) -> IDGenerationResult:
        """Generate the next sequential ID for a prefix"""
        
        prefix = prefix.strip().upper()
        logger.info(f"Generating next ID for prefix: {prefix}")
        
        try:
            # Try to use RPC function for atomic increment
            config = self._increment_via_rpc(prefix, digits, has_space)
        except Exception as e:
            logger.warning(f"RPC increment failed, using fallback: {e}")
            config = self._increment_via_update(prefix, digits, has_space)
        
        # Format the ID
        formatted_id = self._format_id(config)
        
        result = IDGenerationResult(
            prefix_config=config,
            generated_id=formatted_id,
            serial_number=config.last_number,
            formatted_id=formatted_id
        )
        
        logger.info(f"Generated ID: {formatted_id}")
        return result
    
    def _increment_via_rpc(
        self, 
        prefix: str, 
        digits: Optional[int], 
        has_space: Optional[bool]
    ) -> PrefixConfig:
        """Use Supabase RPC function for atomic increment"""
        
        payload = {
            "p_prefix": prefix,
            "p_digits": digits or 5,
            "p_has_space": has_space if has_space is not None else True
        }
        
        result = self.client.rpc("next_prefix_number", payload).execute()
        
        if not result.data:
            raise ValueError(f"RPC returned no data for prefix: {prefix}")
        
        # Handle both dict and list responses
        data = result.data
        if isinstance(data, list):
            data = data[0]
        
        # Convert old statuses before validation
        if isinstance(data, dict) and data.get("status") in ["running", "error", "paused"]:
            data["status"] = "pending"
        
        return PrefixConfig(**data)
    
    def _increment_via_update(
        self, 
        prefix: str, 
        digits: Optional[int], 
        has_space: Optional[bool]
    ) -> PrefixConfig:
        """Fallback method using direct table operations"""
        
        # Get current config
        existing = self.client.table(self.table_name).select("*").eq("prefix", prefix).execute()
        
        if existing.data:
            # Update existing
            current = existing.data[0]
            new_number = current["last_number"] + 1
            
            updated = self.client.table(self.table_name).update({
                "last_number": new_number,
                "digits": digits or current["digits"],
                "has_space": has_space if has_space is not None else current["has_space"],
                "status": PrefixStatus.PENDING.value
            }).eq("prefix", prefix).execute()
            
            return PrefixConfig(**updated.data[0])
        else:
            # Create new
            new_config = {
                "prefix": prefix,
                "digits": digits or 5,
                "last_number": 1,
                "has_space": has_space if has_space is not None else True,
                "status": PrefixStatus.PENDING.value
            }
            
            created = self.client.table(self.table_name).insert(new_config).execute()
            return PrefixConfig(**created.data[0])
    
    def _format_id(self, config: PrefixConfig) -> str:
        """Format the ID according to configuration"""
        padded_number = str(config.last_number).zfill(config.digits)
        separator = " " if config.has_space else ""
        return f"{config.prefix}{separator}{padded_number}"
    
    def get_prefix_status(self, prefix: str) -> Optional[PrefixConfig]:
        """Get current status of a prefix"""
        prefix = prefix.strip().upper()
        
        result = self.client.table(self.table_name).select("*").eq("prefix", prefix).execute()
        
        if result.data:
            return PrefixConfig(**result.data[0])
        return None
    
    def update_prefix_status(
        self, 
        prefix: str, 
        status: PrefixStatus
    ) -> PrefixConfig:
        """Update prefix status"""
        prefix = prefix.strip().upper()
        
        updated = self.client.table(self.table_name).update({
            "status": status.value
        }).eq("prefix", prefix).execute()
        
        if not updated.data:
            raise ValueError(f"Prefix not found: {prefix}")
        
        return PrefixConfig(**updated.data[0])
    
    def log_serial_event(
        self,
        prefix: str,
        generated_id: str,
        mobile_number: Optional[str],
        status: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Log a serial generation event"""
        
        log_entry = {
            "prefix": prefix.strip().upper(),
            "generated_id": generated_id,
            "mobile": mobile_number,
            "status": status,
            "extra": metadata or {}
        }
        
        result = self.client.table(self.log_table).insert(log_entry).execute()
        return result.data[0]["id"]