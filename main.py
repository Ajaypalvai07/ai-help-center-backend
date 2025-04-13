import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from core.config import get_settings
from core.database import Database
from core.logging_config import configure_logging
from api.routes import router as api_router

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app with metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    AI Help Center API - A powerful backend service for AI-powered customer support.
    
    Features:
    * User authentication and authorization
    * AI-powered chat assistance
    * Category management
    * User feedback collection
    * Admin dashboard metrics
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("\n=== Starting AI Assistant API ===")
        await Database.initialize()
        logger.info("✅ CORS enabled for origins: %s", settings.CORS_ORIGINS)
        logger.info("=== Startup Complete ===\n")
    except Exception as e:
        logger.error("❌ Startup Error: %s", str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await Database.close()
        logger.info("=== Shutdown Complete ===")
    except Exception as e:
        logger.error("❌ Shutdown Error: %s", str(e))
        raise

@app.get("/")
async def root():
    """Root endpoint returning API status"""
    return {
        "status": "online",
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )