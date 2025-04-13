from fastapi import APIRouter, WebSocket, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from models.message import MessageCreate, Message
from services.ai_service import ai_service
from core.database import get_db_dependency
from middleware.auth import get_current_user, get_current_active_user
from models.user import UserInDB
from core.ml_engine import ml_engine
from bson import ObjectId
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

class ChatAnalyzeRequest(BaseModel):
    """Request model for chat analysis"""
    content: str = Field(..., min_length=1, description="Message content to analyze")
    category: str = Field(default="General", description="Message category")

class ChatAnalyzeResponse(BaseModel):
    """Response model for chat analysis"""
    content: str = Field(..., description="AI generated response")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    created_at: str = Field(..., description="Timestamp of the response")

@router.post("/analyze", response_model=ChatAnalyzeResponse, status_code=200)
async def analyze_chat(
    message: ChatAnalyzeRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db_dependency)
):
    """Analyze a chat message using AI"""
    try:
        # Log the incoming message
        logger.info(f"Analyzing message from user {current_user.email} in category {message.category}")
        
        # Store the user message first
        user_message = {
            "user_id": str(current_user.id),
            "content": message.content,
            "category": message.category,
            "type": "user",
            "created_at": datetime.utcnow(),
            "status": "sent"
        }
        
        await db.messages.insert_one(user_message)
        
        # Get the response from AI service
        try:
            response = await ai_service.generate_solution(message.content, message.category)
        except HTTPException as he:
            logger.error(f"AI service error: {str(he)}")
            raise he
        except Exception as e:
            logger.error(f"AI service error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="AI service temporarily unavailable"
            )
        
        # Store the AI response
        try:
            ai_message = {
                "user_id": str(current_user.id),
                "content": response["content"],
                "category": message.category,
                "type": "assistant",
                "confidence": response["confidence"],
                "created_at": datetime.fromisoformat(response["created_at"]),
                "status": "completed"
            }
            
            result = await db.messages.insert_one(ai_message)
            response["id"] = str(result.inserted_id)  # Add the message ID to the response
            
        except Exception as e:
            logger.error(f"Database error storing AI response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to store message"
            )
        
        return ChatAnalyzeResponse(**response)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in analyze_chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/{message_id}/feedback")
async def submit_feedback(
    message_id: str,
    feedback: Dict[str, Any],
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db_dependency)
):
    """Submit feedback for a chat message"""
    try:
        # Update the message with feedback
        result = await db.messages.update_one(
            {"_id": ObjectId(message_id), "user_id": str(current_user.id)},
            {"$set": {"feedback": feedback}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Message not found or unauthorized"
            )
            
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback"
        )

@router.get("/history/{user_id}", response_model=List[Message])
async def get_user_history(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db_dependency)
) -> List[Message]:
    """Get chat history for a user"""
    try:
        # Only allow users to view their own history unless they're admin
        if current_user.role != "admin" and str(current_user.id) != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this user's history"
            )
            
        cursor = db.messages.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(10)
        
        messages = await cursor.to_list(length=10)
        
        # Convert ObjectIds to strings
        for msg in messages:
            msg["id"] = str(msg.pop("_id"))
            
        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get chat history"
        )

async def get_category_stats(category: Optional[str]) -> dict:
    try:
        if not category:
            return {}

        db = await get_db_dependency()
        stats = await db.category_stats.find_one({"category": category})
        return stats or {}
    except Exception:
        return {}

async def update_message_status(message_id: str, status: str, data: dict):
    try:
        db = await get_db_dependency()
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {
                "status": status,
                "response_data": data
            }}
        )
    except Exception as e:
        print(f"Error updating message status: {e}")