import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import get_settings
from core.database import Database
from routers import chat, admin, categories, auth, feedback
from core.logging_config import configure_logging

# Configure logging
configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI Assistant API with OpenAI integration",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        print("\n=== Starting AI Assistant API ===")
        await Database.initialize()
        print(f"✅ CORS enabled for origins: {settings.CORS_ORIGINS}")
        print("=== Startup Complete ===\n")
    except Exception as e:
        print(f"❌ Startup Error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await Database.close()
    print("✅ Application shutdown complete")

# Include routers with explicit prefixes
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["auth"]
)
app.include_router(
    categories.router,
    prefix="/api/v1/categories",
    tags=["categories"]
)
app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["chat"]
)
app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["admin"]
)
app.include_router(
    feedback.router,
    prefix="/api/v1/feedback",
    tags=["feedback"]
)

@app.get("/")
async def root():
    """Root endpoint returning API status"""
    return {
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/api/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 