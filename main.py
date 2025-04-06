import logging
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.database import Database, init_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.logging_config import configure_logging
from routers import auth, chat, admin, categories, feedback
from datetime import datetime
import sys
import asyncio

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Import routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(categories.router, prefix=f"{settings.API_V1_STR}/categories", tags=["categories"])
app.include_router(feedback.router, prefix=f"{settings.API_V1_STR}/feedback", tags=["feedback"])

@app.on_event("startup")
async def startup_event():
    """
    Initialize services on startup
    """
    try:
        logger.info("🚀 Starting up application...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.ENVIRONMENT == 'development'}")
        
        # Initialize database
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    try:
        logger.info("Shutting down application...")
        await Database.close()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Check API health and database connection
    """
    try:
        if not Database.initialized:
            await init_db()
        
        # Test database connection
        db = Database.get_db()
        await db.command("ping")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global error handler caught: {str(exc)}")
    return {
        "detail": str(exc),
        "path": request.url.path,
        "method": request.method,
        "timestamp": datetime.utcnow().isoformat()
    }

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 