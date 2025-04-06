import logging
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.database import Database, init_db, close_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.logging_config import configure_logging
from routers import auth, chat, admin, categories, feedback
from datetime import datetime
import sys
import asyncio
from typing import Dict, Any

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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

async def initialize_database(max_retries: int = 5, retry_delay: int = 2) -> None:
    """Initialize database with retries"""
    last_error = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Database initialization attempt {attempt + 1}/{max_retries}")
            await init_db()
            logger.info("✅ Database initialized successfully")
            return
        except Exception as e:
            last_error = e
            logger.error(f"Database initialization attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
    
    logger.error(f"❌ All database initialization attempts failed. Last error: {str(last_error)}")
    raise RuntimeError(f"Failed to initialize database after {max_retries} attempts: {str(last_error)}")

@app.on_event("startup")
async def startup_event():
    """Application startup: initialize database connection"""
    try:
        logger.info("Starting up application...")
        await initialize_database()
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: cleanup"""
    try:
        logger.info("Shutting down application...")
        await close_db()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    response = {
        "status": "unhealthy",
        "database": "disconnected",
        "version": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        if not Database.initialized or Database.db is None:
            # Try to initialize the database
            try:
                await initialize_database(max_retries=1, retry_delay=1)
            except Exception as init_error:
                logger.error(f"Database initialization failed during health check: {str(init_error)}")
                response["error"] = f"Database initialization failed: {str(init_error)}"
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=response
                )
        
        # Test database connection
        await Database.db.command("ping")
        
        response.update({
            "status": "healthy",
            "database": "connected",
            "database_name": settings.MONGODB_DB_NAME
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        response["error"] = str(e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to AI Help Center API", "version": "1.0.0"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global error handler caught: {str(exc)}", exc_info=True)
    return {
        "detail": "An unexpected error occurred. Please try again later."
    }

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 