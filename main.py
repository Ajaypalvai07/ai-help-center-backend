import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.database import Database, get_db_dependency
from core.logging_config import configure_logging
from motor.motor_asyncio import AsyncIOMotorDatabase

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI Assistant API with OpenAI integration",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc"
)

# Configure CORS
origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400
)

# Import routers here to avoid circular imports
from routers import chat, admin, categories, auth, feedback

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        logger.info("=== Starting AI Assistant API ===")
        # Initialize database first
        await db.initialize()
        logger.info("✅ Database initialized")
        logger.info(f"✅ CORS enabled for: {', '.join(origins)}")
        logger.info("=== Startup Complete ===")
    except Exception as e:
        logger.error(f"❌ Startup Error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        await db.close()
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error(f"❌ Shutdown Error: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    """Health check endpoint"""
    try:
        # Verify database connection
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e) if settings.ENVIRONMENT == "development" else "Service unavailable"
            }
        )

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 