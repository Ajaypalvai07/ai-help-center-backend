from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import PyObjectId

class FeedbackCreate(BaseModel):
    message_id: str = Field(..., description="ID of the message being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_type: str = Field(..., description="Type of feedback (thumbs_up/thumbs_down)")
    comment: Optional[str] = Field(None, description="Optional detailed feedback")
    improvement_suggestions: Optional[str] = Field(None, description="Suggestions for improvement")

class Feedback(FeedbackCreate):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="ID of the user providing feedback")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_name = True
        arbitrary_types_allowed = True 