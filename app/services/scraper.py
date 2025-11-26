"""SPDCL web scraping service with robust error handling"""

import asyncio
import logging
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.models.schemas import ScrapeResult

logger = logging.getLogger(__name__)


class SPDCLScraperService:
    """Service for scraping SPDCL website"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://tgsouthernpower.org"
        self.form_url = f"{self.base_url}/knowyourusn"
        self.data_url = f"{self.base_url}/getUkscno"
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def scrape_mobile_number(self, service_number: str) -> ScrapeResult:
        """Scrape mobile number for a service number"""
        
        if not self.settings.scraper_enabled:
            return ScrapeResult(
                success=False,
                attempts=0,
                error_message="Scraping disabled",
                response_time=0.0
            )
        
        service_number = service_number.strip()
        logger.info(f"Scraping mobile number for: {service_number}")
        
        start_time = time.time()
        attempts = 0
        
        try:
            attempts += 1
            
            # Make request
            response = self.session.post(
                self.data_url,
                data={"ukscno": service_number},
                headers={"Referer": self.form_url},
                timeout=self.settings.scraper_timeout
            )
            response.raise_for_status()
            
            response_time = time.time() - start_time
            
            # Parse response
            mobile_number = self._extract_mobile_number(response.text, service_number)
            
            result = ScrapeResult(
                mobile_number=mobile_number,
                success=mobile_number is not None,
                attempts=attempts,
                response_time=response_time,
                raw_data={"status_code": response.status_code, "content_length": len(response.text)}
            )
            
            if mobile_number:
                logger.info(f"Found mobile number: {mobile_number}")
            else:
                logger.warning(f"No mobile number found for: {service_number}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            
            return ScrapeResult(
                success=False,
                attempts=attempts,
                error_message=error_msg,
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            
            return ScrapeResult(
                success=False,
                attempts=attempts,
                error_message=error_msg,
                response_time=response_time
            )
    
    def _extract_mobile_number(self, html: str, service_number: str) -> Optional[str]:
        """Extract mobile number from HTML response"""
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Check for error message
        error_tag = soup.find("p", style="color:red", align="center")
        if error_tag and "doesn't matched" in error_tag.text:
            return None
        
        # Look for main content section
        main_section = soup.find("section", id="main-container")
        if not main_section:
            return None
        
        # Find table
        table = main_section.find("table", class_="table")
        if not table:
            return None
        
        # Get headers
        header_row = table.find("tr")
        if not header_row:
            return None
        
        headers = [th.text.strip() for th in header_row.find_all("th")]
        
        # Find mobile column index
        mobile_index = -1
        try:
            mobile_index = headers.index("Mobile")
        except ValueError:
            return None
        
        # Search data rows
        data_rows = table.find_all("tr")[1:]  # Skip header
        for row in data_rows:
            cols = [td.text.strip() for td in row.find_all("td")]
            
            # Check if this row matches our service number
            if cols and service_number in cols[0]:
                if mobile_index < len(cols):
                    mobile = cols[mobile_index].strip()
                    # Clean and validate mobile number
                    mobile = ''.join(filter(str.isdigit, mobile))
                    if len(mobile) == 10:
                        return mobile
        
        return None
    
    def health_check(self) -> bool:
        """Check if scraping service is healthy"""
        try:
            response = self.session.get(self.form_url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False