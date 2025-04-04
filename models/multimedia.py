from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .user import PyObjectId

class VoiceInput(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="ID of the user")
    session_id: str = Field(..., description="Session ID")
    audio_file: dict = Field(..., description="Audio file details")
    transcription: dict = Field(None, description="Transcription results")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_name = True
        arbitrary_types_allowed = True

class ImageAnalysis(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="ID of the user")
    session_id: str = Field(..., description="Session ID")
    image: dict = Field(..., description="Image file details")
    analysis: dict = Field(None, description="Analysis results")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_name = True
        arbitrary_types_allowed = True

class MediaAnalysisResponse(BaseModel):
    id: str = Field(..., description="Analysis ID")
    status: str = Field(..., description="Analysis status")
    result: Optional[dict] = Field(None, description="Analysis results")
    error: Optional[str] = Field(None, description="Error message if any") 