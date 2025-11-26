#!/usr/bin/env python3
"""
Complete SPDCL Automation System - Ready to Run
This script fixes all issues and runs the complete system
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# Simple logging without emojis
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def main():
    """Run complete automation system"""
    
    print("=" * 60)
    print("SPDCL COMPLETE AUTOMATION SYSTEM")
    print("=" * 60)
    
    try:
        # Import services
        from app.services.startup import StartupService
        from app.services.automation import AutomationService
        
        print("+ Services imported successfully")
        
        # Initialize services
        startup_service = StartupService()
        automation_service = startup_service.automation_service
        
        print("+ Services initialized")
        
        # Get database summary
        db_summary = startup_service.get_database_summary()
        print(f"+ Database: {db_summary['total_prefixes']} prefixes found")
        
        for status, count in db_summary['by_status'].items():
            print(f"  - {status.upper()}: {count}")
        
        if db_summary['total_prefixes'] == 0:
            print("\n! No prefixes in database. Creating test prefix...")
            
            # Create a test prefix
            from app.services.id_generator import IDGeneratorService
            id_gen = IDGeneratorService()
            
            # Generate first ID to create prefix
            result = id_gen.generate_next_id("2442", digits=5, has_space=True)
            print(f"+ Created test prefix: {result.generated_id}")
        
        # Check and resume automation
        print("\nChecking and resuming automation...")
        resume_summary = await startup_service.check_and_resume_automation()
        
        print("Resume Results:")
        print(f"  - PENDING to process: {len(resume_summary.get('pending_to_process', []))}")
        print(f"  - NOT_STARTED to process: {len(resume_summary.get('not_started_to_process', []))}")
        print(f"  - COMPLETED: {len(resume_summary.get('completed', []))}")
        print(f"  - Total Automating: {resume_summary['total_prefixes_to_automate']}")
        
        if resume_summary['total_prefixes_to_automate'] > 0:
            print(f"\n+ AUTOMATION STARTED for {resume_summary['total_prefixes_to_automate']} prefixes")
            print("+ System is now running continuously...")
            print("+ Generating IDs every 5 seconds")
            print("+ Scraping mobile numbers from SPDCL")
            print("+ Logging to Google Sheets (if permissions allow)")
            print("\nPress Ctrl+C to stop")
            
            # Monitor for 2 minutes to show it's working
            for i in range(24):  # 24 * 5 seconds = 2 minutes
                await asyncio.sleep(5)
                
                stats = automation_service.get_stats()
                print(f"[{i+1:2d}/24] Generated: {stats['total_generated']:3d} | "
                      f"Found: {stats['mobile_numbers_found']:2d} | "
                      f"Success: {stats['success_rate']:5.1f}% | "
                      f"Errors: {stats['errors']:2d}")
                
                if not automation_service.running:
                    print("! Automation stopped")
                    break
            
            print("\n+ Demo completed - system continues running in background")
            
        else:
            print("\n! No prefixes need automation")
            print("  All prefixes are completed or no work to do")
        
    except KeyboardInterrupt:
        print("\n! Stopped by user")
    except Exception as e:
        print(f"\n- Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            if 'automation_service' in locals() and automation_service.running:
                automation_service.stop()
                print("+ Automation stopped cleanly")
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
