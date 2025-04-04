from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import List
from models.multimedia import VoiceInput, ImageAnalysis, MediaAnalysisResponse
from models.user import UserInDB
from middleware.auth import get_current_active_user
from core.database import get_database
import logging
import aiofiles
import os
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/media", tags=["multimedia"])

UPLOAD_DIR = "uploads"
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mp3", "audio/mpeg"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_file(file: UploadFile, file_type: str) -> str:
    """Save uploaded file and return the file path"""
    ext = file.filename.split(".")[-1]
    filename = f"{file_type}_{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    async with aiofiles.open(filepath, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)
    
    return filepath

@router.post("/voice", response_model=MediaAnalysisResponse)
async def process_voice(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Process voice input"""
    try:
        if file.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail="Invalid audio format")
            
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
            
        filepath = await save_file(file, "voice")
        session_id = str(uuid.uuid4())
        
        voice_input = {
            "user_id": str(current_user.id),
            "session_id": session_id,
            "audio_file": {
                "path": filepath,
                "format": file.content_type,
                "size": file.size
            },
            "created_at": datetime.utcnow()
        }
        
        result = await db.voice_inputs.insert_one(voice_input)
        
        # Here you would typically start an async task for transcription
        # For now, we'll return the ID for status checking
        return MediaAnalysisResponse(
            id=str(result.inserted_id),
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process voice input")

@router.post("/image", response_model=MediaAnalysisResponse)
async def process_image(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Process image input"""
    try:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid image format")
            
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
            
        filepath = await save_file(file, "image")
        session_id = str(uuid.uuid4())
        
        image_analysis = {
            "user_id": str(current_user.id),
            "session_id": session_id,
            "image": {
                "path": filepath,
                "type": file.content_type,
                "size": file.size
            },
            "created_at": datetime.utcnow()
        }
        
        result = await db.image_analysis.insert_one(image_analysis)
        
        # Here you would typically start an async task for image analysis
        # For now, we'll return the ID for status checking
        return MediaAnalysisResponse(
            id=str(result.inserted_id),
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process image")

@router.get("/analysis/{analysis_id}", response_model=MediaAnalysisResponse)
async def get_analysis_result(
    analysis_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get the status/result of a media analysis"""
    try:
        # Check both collections
        result = await db.voice_inputs.find_one({"_id": analysis_id}) or \
                await db.image_analysis.find_one({"_id": analysis_id})
                
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        if result["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized")
            
        status = "completed" if result.get("analysis") else "processing"
        
        return MediaAnalysisResponse(
            id=str(result["_id"]),
            status=status,
            result=result.get("analysis")
        )
        
    except Exception as e:
        logger.error(f"Error getting analysis result: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get analysis result") 