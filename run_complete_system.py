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
    
    startup_service = None
    automation_service = None
    
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
            print("\nSystem will run indefinitely. Press Ctrl+C to stop")
            
            # Monitor and keep running indefinitely (automation already started by check_and_resume_automation)
            iteration = 0
            while True:
                await asyncio.sleep(30)  # Print stats every 30 seconds
                iteration += 1
                
                if automation_service.running:
                    stats = automation_service.get_stats()
                    print(f"[{iteration:4d}] Generated: {stats['total_generated']:5d} | "
                          f"Found: {stats['mobile_numbers_found']:4d} | "
                          f"Success: {stats['success_rate']:5.1f}% | "
                          f"Errors: {stats['errors']:3d}")
                else:
                    print(f"[{iteration:4d}] Automation stopped - checking for new work...")
                    # Check for new prefixes and restart if needed
                    await asyncio.sleep(60)
                    resume_summary = await startup_service.check_and_resume_automation()
                    if resume_summary['total_prefixes_to_automate'] > 0:
                        print(f"Found {resume_summary['total_prefixes_to_automate']} new prefixes - automation will restart automatically")
            
        else:
            print("\n! No prefixes need automation")
            print("  All prefixes are completed or no work to do")
            print("  System will keep running and check for new work every 5 minutes...")
            # Keep running and check periodically for new prefixes
            while True:
                await asyncio.sleep(300)  # Check every 5 minutes for new prefixes
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for new prefixes...")
                resume_summary = await startup_service.check_and_resume_automation()
                if resume_summary['total_prefixes_to_automate'] > 0:
                    print(f"Found {resume_summary['total_prefixes_to_automate']} new prefixes - starting automation...")
                    # Start automation
                    automation_task = asyncio.create_task(
                        automation_service.start_sequential_processing(generation_interval=5)
                    )
                    # Monitor while running
                    while automation_service.running:
                        await asyncio.sleep(30)
                        stats = automation_service.get_stats()
                        print(f"Generated: {stats['total_generated']:5d} | "
                              f"Found: {stats['mobile_numbers_found']:4d} | "
                              f"Success: {stats['success_rate']:5.1f}%")
        
    except KeyboardInterrupt:
        print("\n! Stopped by user")
        if automation_service and automation_service.running:
            automation_service.stop()
    except Exception as e:
        print(f"\n- Error in main loop: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit - keep running and retry
        print("+ Error handled - continuing to run...")
        await asyncio.sleep(10)
        # Restart automation if it stopped
        if automation_service and not automation_service.running:
            print("+ Attempting to restart automation...")
            try:
                if startup_service:
                    resume_summary = await startup_service.check_and_resume_automation()
                    if resume_summary['total_prefixes_to_automate'] > 0:
                        print(f"+ Restarted automation for {resume_summary['total_prefixes_to_automate']} prefixes")
            except Exception as restart_error:
                print(f"- Failed to restart: {restart_error}")
        
        # Continue running
        while True:
            await asyncio.sleep(60)
            if automation_service and automation_service.running:
                stats = automation_service.get_stats()
                print(f"Running: Generated={stats['total_generated']}, Found={stats['mobile_numbers_found']}")
            else:
                print("Waiting for work...")
                try:
                    if startup_service:
                        resume_summary = await startup_service.check_and_resume_automation()
                        if resume_summary['total_prefixes_to_automate'] > 0:
                            print(f"Found {resume_summary['total_prefixes_to_automate']} prefixes - restarting...")
                except Exception as e:
                    print(f"Error checking for work: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
