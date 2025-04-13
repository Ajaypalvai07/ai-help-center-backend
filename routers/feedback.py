from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from models.feedback import FeedbackCreate, Feedback
from models.user import UserInDB
from middleware.auth import get_current_active_user
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db_dependency
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["feedback"])

@router.post("/submit")
async def submit_feedback(
    feedback: FeedbackCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Submit user feedback for a message"""
    try:
        feedback_doc = feedback.dict()
        feedback_doc["user_id"] = str(current_user.id)
        feedback_doc["timestamp"] = datetime.utcnow()
        
        result = await db.feedback.insert_one(feedback_doc)
        
        # Update message with feedback reference
        await db.messages.update_one(
            {"_id": feedback.message_id},
            {"$set": {"has_feedback": True}}
        )
        
        return {"status": "success", "feedback_id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/stats")
async def get_feedback_stats(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db_dependency)
) -> Dict:
    """Get feedback statistics"""
    try:
        pipeline = [
            {"$group": {
                "_id": "$feedback_type",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$rating"}
            }}
        ]
        
        stats = await db.feedback.aggregate(pipeline).to_list(length=None)
        return {
            "total_feedback": sum(s["count"] for s in stats),
            "by_type": {s["_id"]: {
                "count": s["count"],
                "avg_rating": round(s["avg_rating"], 2)
            } for s in stats}
        }
    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get feedback statistics") 