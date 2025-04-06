import logging
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.database import init_db, close_db, get_db_dependency, Database
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.logging_config import configure_logging
from routers import auth, chat, admin, categories, feedback
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
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
        logger.info("🚀 Starting application...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"API Version: {settings.API_V1_STR}")
        
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Log CORS settings
        logger.info(f"CORS Origins: {settings.get_cors_origins()}")
        
        logger.info("✨ API startup complete")
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    try:
        logger.info("Shutting down API...")
        await close_db()
        logger.info("✅ Cleaned up resources")
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Check API health and database connection
    """
    try:
        # Test database connection
        db = Database.get_db()
        await db.command("ping")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "environment": settings.ENVIRONMENT,
            "version": settings.API_V1_STR
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
        "version": settings.API_V1_STR,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "environment": settings.ENVIRONMENT
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    error_msg = str(exc)
    logger.error(f"Global error handler caught: {error_msg}")
    logger.error(f"Request path: {request.url.path}")
    
    if isinstance(exc, HTTPException):
        raise exc
    
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service unavailable"
    )

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 