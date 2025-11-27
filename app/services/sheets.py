"""Google Sheets service with robust error handling"""

import logging
import os
from datetime import datetime
from typing import Optional

import gspread
from gspread.exceptions import WorksheetNotFound, SpreadsheetNotFound
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for logging data to Google Sheets"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._spreadsheet = None
    
    @property
    def client(self):
        """Lazy-loaded Google Sheets client"""
        if self._client is None:
            try:
                # Check environment variable first (for Render/Railway)
                json_from_env = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
                json_from_settings = self.settings.google_service_account_json
                
                # Support Railway/env var JSON (preferred) or file path
                if json_from_env or json_from_settings:
                    import json
                    service_account_json = json_from_env or json_from_settings
                    try:
                        service_account_info = json.loads(service_account_json)
                        self._client = gspread.service_account_from_dict(service_account_info)
                        logger.info("Google Sheets client initialized from JSON env var")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
                        logger.error(f"JSON length: {len(service_account_json) if service_account_json else 0} characters")
                        raise ValueError(f"Invalid JSON format in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
                elif self.settings.google_service_account_file:
                    from pathlib import Path
                    file_path = Path(self.settings.google_service_account_file)
                    if file_path.exists():
                        self._client = gspread.service_account(
                            filename=str(file_path)
                        )
                        logger.info("Google Sheets client initialized from file")
                    else:
                        raise ValueError(f"Service account file not found: {file_path}")
                else:
                    raise ValueError(
                        "Either GOOGLE_SERVICE_ACCOUNT_JSON env var or google_service_account_file must be provided"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets client: {e}")
                raise
        return self._client
    
    @property 
    def spreadsheet(self):
        """Lazy-loaded spreadsheet"""
        if self._spreadsheet is None:
            try:
                self._spreadsheet = self.client.open_by_key(self.settings.google_sheet_id)
                logger.info(f"Opened spreadsheet: {self._spreadsheet.title}")
            except SpreadsheetNotFound:
                logger.error(f"Spreadsheet not found: {self.settings.google_sheet_id}")
                raise
            except Exception as e:
                logger.error(f"Failed to open spreadsheet: {e}")
                raise
        return self._spreadsheet
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def log_result(
        self,
        prefix: str,
        serial_number: int,
        generated_id: str,
        mobile_number: Optional[str],
        sheet_id: Optional[str] = None
    ) -> str:
        """Log result to Google Sheets - ONLY if mobile number is found"""
        
        # Only log if mobile number was found
        if not mobile_number or mobile_number.strip() == "" or mobile_number == "N/A":
            logger.info(f"📝 Skipping Google Sheets logging for {generated_id} - no mobile number found")
            return f"SKIPPED_{prefix}_{serial_number}"  # Return indicator that it was skipped
        
        logger.info(f"📊 Logging result for {generated_id} with mobile {mobile_number} to Google Sheets")
        
        try:
            # Use override sheet if provided
            if sheet_id:
                spreadsheet = self.client.open_by_key(sheet_id)
                logger.info(f"Using custom sheet ID: {sheet_id}")
            else:
                spreadsheet = self.spreadsheet
                logger.info(f"Using default spreadsheet: {spreadsheet.title}")
            
            # Get or create worksheet for this prefix
            logger.info(f"Getting/creating worksheet for prefix: {prefix}")
            worksheet = self._get_or_create_worksheet(spreadsheet, prefix)
            logger.info(f"✅ Worksheet ready: {worksheet.title}")
            
            # Prepare row data - only for valid results with mobile numbers
            row_data = [
                serial_number,
                generated_id,
                mobile_number  # We know this is valid at this point
            ]
            
            logger.info(f"Appending row to worksheet: {row_data}")
            # Append row
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            
            # Calculate range
            row_count = len(worksheet.get_all_values())
            range_notation = f"{prefix}!A{row_count}:C{row_count}"
            
            logger.info(f"✅ Successfully logged to Google Sheets range: {range_notation}")
            return range_notation
            
        except Exception as e:
            logger.error(f"❌ Failed to log to Google Sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _get_or_create_worksheet(self, spreadsheet, prefix: str):
        """Get existing worksheet or create new one"""
        
        # Sanitize worksheet name
        worksheet_name = prefix[:100]  # Google Sheets limit
        
        try:
            # Try to get existing worksheet
            worksheet = spreadsheet.worksheet(worksheet_name)
            logger.info(f"✅ Found existing worksheet: {worksheet_name} (rows: {worksheet.row_count})")
            return worksheet
            
        except WorksheetNotFound:
            # Create new worksheet
            logger.info(f"📝 Creating new worksheet: {worksheet_name}")
            
            try:
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,
                    cols=10
                )
                logger.info(f"✅ Worksheet created: {worksheet_name}")
                
                # Add headers
                headers = ["Serial", "Generated ID", "Mobile Number"]
                worksheet.append_row(headers, value_input_option="USER_ENTERED")
                logger.info(f"✅ Headers added: {headers}")
                
                # Format headers (make bold)
                try:
                    worksheet.format("A1:C1", {"textFormat": {"bold": True}})
                    logger.info(f"✅ Headers formatted (bold)")
                except Exception as format_error:
                    logger.warning(f"⚠️  Could not format headers: {format_error}")
                
                logger.info(f"✅ Worksheet '{worksheet_name}' ready with headers")
                return worksheet
                
            except Exception as e:
                logger.error(f"❌ Failed to create worksheet '{worksheet_name}': {e}")
                raise
    
    def health_check(self) -> bool:
        """Check if Google Sheets service is healthy"""
        try:
            # Try to access the spreadsheet
            spreadsheet = self.spreadsheet
            return spreadsheet is not None
        except Exception as e:
            logger.error(f"Google Sheets health check failed: {e}")
            return False
    
    def get_worksheet_info(self, prefix: str) -> dict:
        """Get information about a worksheet"""
        try:
            worksheet = self.spreadsheet.worksheet(prefix)
            return {
                "title": worksheet.title,
                "row_count": worksheet.row_count,
                "col_count": worksheet.col_count,
                "data_rows": len(worksheet.get_all_values()) - 1  # Exclude header
            }
        except WorksheetNotFound:
            return {"error": f"Worksheet '{prefix}' not found"}
        except Exception as e:
            return {"error": str(e)}
