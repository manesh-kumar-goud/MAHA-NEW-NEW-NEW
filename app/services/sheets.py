"""Google Sheets service with robust error handling"""

import logging
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
                # Support Railway/env var JSON (preferred) or file path
                if self.settings.google_service_account_json:
                    import json
                    import io
                    service_account_info = json.loads(self.settings.google_service_account_json)
                    self._client = gspread.service_account_from_dict(service_account_info)
                    logger.info("Google Sheets client initialized from JSON env var")
                elif self.settings.google_service_account_file:
                    self._client = gspread.service_account(
                        filename=self.settings.google_service_account_file
                    )
                    logger.info("Google Sheets client initialized from file")
                else:
                    raise ValueError("Either google_service_account_json or google_service_account_file must be provided")
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
        timestamp: datetime,
        sheet_id: Optional[str] = None
    ) -> str:
        """Log result to Google Sheets - ONLY if mobile number is found"""
        
        # Only log if mobile number was found
        if not mobile_number or mobile_number.strip() == "" or mobile_number == "N/A":
            logger.info(f"Skipping Google Sheets logging for {generated_id} - no mobile number found")
            return f"SKIPPED_{prefix}_{serial_number}"  # Return indicator that it was skipped
        
        logger.info(f"Logging result for {generated_id} with mobile {mobile_number} to Google Sheets")
        
        try:
            # Use override sheet if provided
            if sheet_id:
                spreadsheet = self.client.open_by_key(sheet_id)
            else:
                spreadsheet = self.spreadsheet
            
            # Get or create worksheet for this prefix
            worksheet = self._get_or_create_worksheet(spreadsheet, prefix)
            
            # Prepare row data - only for valid results with mobile numbers
            row_data = [
                serial_number,
                generated_id,
                timestamp.isoformat(),
                mobile_number  # We know this is valid at this point
            ]
            
            # Append row
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            
            # Calculate range
            row_count = len(worksheet.get_all_values())
            range_notation = f"{prefix}!A{row_count}:D{row_count}"
            
            logger.info(f"Successfully logged to range: {range_notation}")
            return range_notation
            
        except Exception as e:
            logger.error(f"Failed to log to Google Sheets: {e}")
            raise
    
    def _get_or_create_worksheet(self, spreadsheet, prefix: str):
        """Get existing worksheet or create new one"""
        
        # Sanitize worksheet name
        worksheet_name = prefix[:100]  # Google Sheets limit
        
        try:
            # Try to get existing worksheet
            worksheet = spreadsheet.worksheet(worksheet_name)
            logger.debug(f"Found existing worksheet: {worksheet_name}")
            return worksheet
            
        except WorksheetNotFound:
            # Create new worksheet
            logger.info(f"Creating new worksheet: {worksheet_name}")
            
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=10
            )
            
            # Add headers
            headers = ["Serial", "Generated ID", "Timestamp", "Mobile Number"]
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
            
            # Format headers (make bold)
            worksheet.format("A1:D1", {"textFormat": {"bold": True}})
            
            logger.info(f"Created worksheet with headers: {worksheet_name}")
            return worksheet
    
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
