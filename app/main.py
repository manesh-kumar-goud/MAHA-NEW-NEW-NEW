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
    """Application lifespan events - starts automation in background"""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Start automation service in background
    import asyncio
    from app.services.startup import StartupService
    
    startup_service = StartupService()
    automation_task = None
    
    try:
        # Start automation
        resume_summary = await startup_service.check_and_resume_automation()
        if resume_summary['total_prefixes_to_automate'] > 0:
            logger.info(f"Starting automation for {resume_summary['total_prefixes_to_automate']} prefixes")
            automation_task = asyncio.create_task(
                startup_service.automation_service.start_sequential_processing(generation_interval=5)
            )
            # Store reference to prevent garbage collection
            app.state.automation_task = automation_task
            app.state.startup_service = startup_service
        else:
            logger.info("No prefixes to automate at startup")
            app.state.startup_service = startup_service
    except Exception as e:
        logger.error(f"Failed to start automation: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down application")
    if automation_task:
        logger.info("Stopping automation...")
        startup_service.automation_service.stop()
        automation_task.cancel()
        try:
            await automation_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Create FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Robust SPDCL ID Generator with scraping and Google Sheets integration",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix=settings.api_prefix)
    app.include_router(automation_router, prefix=settings.api_prefix)
    app.include_router(startup_router, prefix=settings.api_prefix)
    
    # Health check endpoint (for Render free tier - keeps service alive)
    @app.get("/")
    async def health_check():
        """Health check endpoint - keeps service alive on Render free tier"""
        stats = {}
        if hasattr(app.state, 'startup_service'):
            try:
                stats = app.state.startup_service.automation_service.get_stats()
            except:
                pass
        return {
            "status": "running",
            "service": settings.app_name,
            "version": settings.app_version,
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