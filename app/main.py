"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Configure logging FIRST before any imports that might log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import with error handling to prevent crashes during module load
try:
    from app.core.config import get_settings
except Exception as e:
    logger.error(f"Failed to import settings: {e}")
    get_settings = None

try:
    from app.api.routes import router
except Exception as e:
    logger.error(f"Failed to import routes: {e}")
    router = None

try:
    from app.api.automation_routes import router as automation_router
except Exception as e:
    logger.error(f"Failed to import automation_routes: {e}")
    automation_router = None

try:
    from app.api.startup_routes import router as startup_router
except Exception as e:
    logger.error(f"Failed to import startup_routes: {e}")
    startup_router = None

try:
    from app.models.schemas import ErrorResponse
except Exception as e:
    logger.error(f"Failed to import ErrorResponse: {e}")
    ErrorResponse = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - starts automation in background thread"""
    import os
    import threading
    import asyncio
    import time
    
    # Define automation function BEFORE yield (but don't start it yet)
    def run_automation():
        """Run automation in background thread - completely non-blocking"""
        try:
            # Wait to ensure web server is fully started and port is bound
            logger.info("⏳ Waiting 10 seconds for web server to fully bind to port...")
            time.sleep(10)
            
            logger.info("🔄 Starting background automation...")
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start automation
            async def start():
                try:
                    from app.services.startup import StartupService
                    from app.services.db_change_monitor import DatabaseChangeMonitor
                    
                    startup = StartupService()
                    app.state.startup_service = startup
                    automation_service = startup.automation_service
                    
                    # Start database change monitor
                    change_monitor = DatabaseChangeMonitor(automation_service, check_interval=30)
                    app.state.change_monitor = change_monitor
                    
                    # Start monitoring in background
                    monitor_task = asyncio.create_task(change_monitor.start_monitoring())
                    logger.info("🔍 Database change monitor started (will detect Supabase changes)")
                    
                    logger.info("📊 Checking database for prefixes to automate...")
                    resume_summary = await startup.check_and_resume_automation()
                    
                    if resume_summary['total_prefixes_to_automate'] > 0:
                        logger.info(f"✅ Starting automation for {resume_summary['total_prefixes_to_automate']} prefixes")
                        await automation_service.start_sequential_processing(generation_interval=5)
                    else:
                        logger.info("ℹ️  No prefixes to automate - monitoring for changes...")
                        # Keep running - change monitor will restart automation when changes detected
                        while True:
                            await asyncio.sleep(300)  # Check every 5 minutes as backup
                            if not automation_service.running:
                                resume_summary = await startup.check_and_resume_automation()
                                if resume_summary['total_prefixes_to_automate'] > 0:
                                    logger.info(f"✅ Found {resume_summary['total_prefixes_to_automate']} prefixes - starting automation")
                                    await automation_service.start_sequential_processing(generation_interval=5)
                except Exception as e:
                    logger.error(f"❌ Automation error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            loop.run_until_complete(start())
        except Exception as e:
            logger.error(f"❌ Failed to start automation thread: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Start automation thread BEFORE yield (non-blocking, daemon thread)
    # This schedules it to start, but doesn't block server startup
    try:
        port = os.getenv("PORT")
        if port is None:
            logger.info("ℹ️  Running in build/test mode - skipping automation startup")
        else:
            logger.info("🔧 Server mode detected - scheduling background automation...")
            automation_thread = threading.Thread(target=run_automation, daemon=True, name="AutomationThread")
            automation_thread.start()
            logger.info("✅ Background automation thread started (will begin in 10 seconds)")
    except Exception as e:
        logger.warning(f"⚠️  Could not start automation thread (web server will continue): {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    # CRITICAL: Yield NOW - this allows the web server to start immediately
    # Render will detect this and mark the service as "live"
    logger.info("🚀 FastAPI web server starting - binding to port...")
    yield
    
    # Cleanup on shutdown (after yield completes)
    logger.info("🛑 Shutting down application...")
    if hasattr(app.state, 'change_monitor'):
        try:
            app.state.change_monitor.stop()
            logger.info("✅ Change monitor stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping change monitor: {e}")
    if hasattr(app.state, 'startup_service'):
        try:
            app.state.startup_service.automation_service.stop()
            logger.info("✅ Automation service stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping automation: {e}")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    import os
    
    # Log port binding info for Render
    port = os.getenv("PORT", "8000")
    logger.info("=" * 60)
    logger.info(f"Creating FastAPI app")
    logger.info(f"Will bind to: 0.0.0.0:{port}")
    logger.info("=" * 60)
    
    # Get settings with error handling
    app_name = "SPDCL ID Generator"
    app_version = "2.0.0"
    api_prefix = "/api/v1"
    cors_origins = ["*"]
    
    try:
        if get_settings:
            settings = get_settings()
            app_name = settings.app_name or app_name
            app_version = settings.app_version or app_version
            api_prefix = settings.api_prefix or api_prefix
            cors_origins = settings.cors_origins or cors_origins
    except Exception as e:
        logger.warning(f"⚠️  Could not load all settings (using defaults): {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    app = FastAPI(
        title=app_name,
        version=app_version,
        description="Robust SPDCL ID Generator with scraping and Google Sheets integration",
        lifespan=lifespan
    )
    
    logger.info("✅ FastAPI app created - ready to start server")
    
    # CORS middleware
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception as e:
        logger.warning(f"⚠️  Could not add CORS middleware: {e}")
    
    # Include API routes (only if they imported successfully)
    routes_registered = 0
    if router:
        try:
            app.include_router(router, prefix=api_prefix)
            routes_registered += 1
            logger.info(f"✅ Main routes registered at {api_prefix}")
        except Exception as e:
            logger.warning(f"⚠️  Could not register main routes: {e}")
    
    if automation_router:
        try:
            app.include_router(automation_router, prefix=api_prefix)
            routes_registered += 1
            logger.info(f"✅ Automation routes registered at {api_prefix}")
        except Exception as e:
            logger.warning(f"⚠️  Could not register automation routes: {e}")
    
    if startup_router:
        try:
            app.include_router(startup_router, prefix=api_prefix)
            routes_registered += 1
            logger.info(f"✅ Startup routes registered at {api_prefix}")
        except Exception as e:
            logger.warning(f"⚠️  Could not register startup routes: {e}")
    
    logger.info(f"✅ Total routes registered: {routes_registered}/3")
    
    # Health check endpoint (for Render free tier - keeps service alive)
    @app.get("/")
    async def health_check():
        """Health check endpoint - keeps service alive on Render free tier"""
        # Ultra-simple response - no imports, no settings access, instant response
        return {
            "status": "live",
            "service": "SPDCL ID Generator",
            "version": "2.0.0"
        }
    
    @app.get("/health")
    async def detailed_health():
        """Detailed health check with automation stats"""
        try:
            settings = get_settings()
            service_name = settings.app_name
            service_version = settings.app_version
        except:
            service_name = "SPDCL ID Generator"
            service_version = "2.0.0"
        
        stats = {}
        try:
            # Try to get automation stats if available
            if hasattr(app.state, 'startup_service'):
                stats = app.state.startup_service.automation_service.get_stats()
        except:
            pass
        return {
            "status": "running",
            "service": service_name,
            "version": service_version,
            "automation": {
                "running": stats.get("current_prefix") is not None,
                "generated": stats.get("total_generated", 0),
                "found": stats.get("mobile_numbers_found", 0)
            }
        }
    
    # Exception handlers (only if ErrorResponse imported successfully)
    if ErrorResponse:
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error=exc.detail
                ).dict()
            )
    else:
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail}
            )
    
    return app


# Create app instance with error handling
try:
    app = create_app()
    logger.info("✅ App instance created successfully")
except Exception as e:
    logger.error(f"❌ CRITICAL: Failed to create app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Create minimal app that will at least start
    import os
    app = FastAPI(title="SPDCL ID Generator", version="2.0.0")
    
    @app.get("/")
    async def minimal_health():
        return {
            "status": "degraded",
            "message": "App started but some services failed to initialize",
            "error": str(e),
            "port": os.getenv("PORT", "8000")
        }
    
    logger.warning("⚠️  Created minimal app - some features may not work")