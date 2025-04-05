import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.database import init_db, close_db, get_db
from core.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI Assistant API with OpenAI integration",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# Configure CORS
origins = ["https://ai-help-center-frontend-vkp9.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-CSRF-Token", "X-Requested-With", "Accept", "Accept-Version", 
                  "Content-Length", "Content-MD5", "Content-Type", "Date", 
                  "X-Api-Version", "Authorization"],
    expose_headers=["*"],
    max_age=86400
)

# Import routers here to avoid circular imports
from routers import chat, admin, categories, auth, feedback, multimedia

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        logger.info("=== Starting AI Assistant API ===")
        # Initialize database first
        await init_db()
        logger.info(f"✅ CORS enabled for: https://ai-help-center-frontend-vkp9.vercel.app")
        logger.info("=== Startup Complete ===")
    except Exception as e:
        logger.error(f"❌ Startup Error: {str(e)}")
        # Don't raise the error in production to allow the app to start
        if settings.ENVIRONMENT == "development":
            raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        await close_db()
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
async def health_check():
    """Health check endpoint"""
    try:
        # Verify database connection
        db = get_db()
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.ENVIRONMENT
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
app.include_router(multimedia.router, prefix="/api/v1/multimedia", tags=["multimedia"])

@app.get("/")
async def root():
    """Root endpoint"""
    try:
        return {
            "status": "running",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 