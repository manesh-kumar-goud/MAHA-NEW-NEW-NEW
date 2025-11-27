"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.routes import router
from app.api.automation_routes import router as automation_router
from app.api.startup_routes import router as startup_router
from app.models.schemas import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - starts automation in background thread"""
    import os
    
    # CRITICAL: Yield FIRST to ensure web server starts immediately
    # This is the most important part - Render needs to see the server binding to port
    logger.info("=" * 60)
    logger.info("🚀 Starting FastAPI web server...")
    logger.info("🌐 Web server will bind to 0.0.0.0:$PORT")
    logger.info("=" * 60)
    
    # Yield immediately - this allows the web server to start and bind to port
    # Render will detect this and mark the service as "live"
    yield
    
    # After yield, try to start background automation (non-blocking)
    # This won't prevent the web server from starting if it fails
    try:
        # Only start automation if we're actually running as a server (not during build)
        port = os.getenv("PORT")
        if port is None:
            logger.info("Running in build/test mode - skipping automation startup")
            return
        
        logger.info("Server mode detected - initializing background automation...")
        
        def run_automation():
            """Run automation in background thread - completely non-blocking"""
            import asyncio
            import time
            
            try:
                # Wait to ensure web server is fully started and port is bound
                logger.info("Waiting 15 seconds for web server to fully bind to port...")
                time.sleep(15)
                
                logger.info("Starting background automation...")
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Start automation
                async def start():
                    try:
                        from app.services.startup import StartupService
                        startup = StartupService()
                        app.state.startup_service = startup
                        
                        resume_summary = await startup.check_and_resume_automation()
                        if resume_summary['total_prefixes_to_automate'] > 0:
                            logger.info(f"Starting automation for {resume_summary['total_prefixes_to_automate']} prefixes")
                            await startup.automation_service.start_sequential_processing(generation_interval=5)
                        else:
                            logger.info("No prefixes to automate - will check periodically")
                            while True:
                                await asyncio.sleep(300)
                                resume_summary = await startup.check_and_resume_automation()
                                if resume_summary['total_prefixes_to_automate'] > 0:
                                    logger.info(f"Found {resume_summary['total_prefixes_to_automate']} prefixes - starting automation")
                                    await startup.automation_service.start_sequential_processing(generation_interval=5)
                    except Exception as e:
                        logger.error(f"Automation error: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                loop.run_until_complete(start())
            except Exception as e:
                logger.error(f"Failed to start automation: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Start automation thread (non-blocking, daemon thread)
        import threading
        automation_thread = threading.Thread(target=run_automation, daemon=True, name="AutomationThread")
        automation_thread.start()
        logger.info("✅ Background automation thread scheduled (will wait 15s before starting)")
        
    except Exception as e:
        # If automation setup fails, log but don't crash the web server
        logger.warning(f"⚠️  Could not start automation (web server will continue): {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    # Cleanup on shutdown (after yield completes)
    logger.info("Shutting down application...")
    if hasattr(app.state, 'startup_service'):
        try:
            app.state.startup_service.automation_service.stop()
        except:
            pass


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
    try:
        settings = get_settings()
        app_name = settings.app_name
        app_version = settings.app_version
        api_prefix = settings.api_prefix
        cors_origins = settings.cors_origins
    except Exception as e:
        logger.warning(f"⚠️  Could not load all settings (using defaults): {e}")
        # Use defaults if settings fail to load
        app_name = "SPDCL ID Generator"
        app_version = "2.0.0"
        api_prefix = "/api/v1"
        cors_origins = ["*"]
    
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
    
    # Include API routes
    try:
        app.include_router(router, prefix=api_prefix)
        app.include_router(automation_router, prefix=api_prefix)
        app.include_router(startup_router, prefix=api_prefix)
        logger.info(f"✅ API routes registered at {api_prefix}")
    except Exception as e:
        logger.error(f"❌ Could not register all routes: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Health check endpoint (for Render free tier - keeps service alive)
    @app.get("/")
    async def health_check():
        """Health check endpoint - keeps service alive on Render free tier"""
        # Simple response - don't access automation service to avoid errors
        try:
            settings = get_settings()
            service_name = settings.app_name
            service_version = settings.app_version
        except:
            service_name = "SPDCL ID Generator"
            service_version = "2.0.0"
        
        return {
            "status": "live",
            "service": service_name,
            "version": service_version,
            "message": "Web server is running",
            "port": os.getenv("PORT", "8000")
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
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                timestamp=datetime.now(timezone.utc)
            ).dict()
        )
    
    return app


# Create app instance
app = create_app()