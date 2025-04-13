import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import init_db, close_db
from routers import chat, admin, categories, auth, feedback
from core.logging_config import configure_logging

# Configure logging
configure_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI Assistant API with OpenAI integration"
)

# Configure CORS - More permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Exposes all headers
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        print("\n=== Starting AI Assistant API ===")
        await init_db()
        print("✅ CORS enabled for all origins (development mode)")
        print("=== Startup Complete ===\n")
    except Exception as e:
        print(f"❌ Startup Error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await close_db()
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
    return {
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# Entry point for running the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload for development
    ) 