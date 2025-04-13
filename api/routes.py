from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

# Create main API router
router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)

@router.get("/status")
async def get_api_status() -> Dict[str, Any]:
    """Get API status"""
    return {
        "status": "operational",
        "version": "1.0.0"
    }

# Import route modules after defining the main router to avoid circular imports
try:
    from routers import auth, chat, admin, categories, feedback
    
    # Include all route modules
    router.include_router(auth.router, prefix="/auth", tags=["auth"])
    router.include_router(chat.router, prefix="/chat", tags=["chat"])
    router.include_router(admin.router, prefix="/admin", tags=["admin"])
    router.include_router(categories.router, prefix="/categories", tags=["categories"])
    router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
    
except ImportError as e:
    logger.error(f"Failed to import route modules: {str(e)}")
    
    @router.get("/error")
    async def get_import_error():
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "API routes not properly configured"}
        ) 