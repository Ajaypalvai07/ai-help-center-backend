from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from middleware.auth import get_current_admin
from models.user import UserInDB, UserUpdate
from core.database import get_database
# from ..core.auth import get_current_admin_user
from motor.motor_asyncio import AsyncIOMotorClient
import logging

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = logging.getLogger(__name__)

@router.get("/metrics")
async def get_metrics(db: AsyncIOMotorClient = Depends(get_database), 
                     _: UserInDB = Depends(get_current_admin)) -> Dict:
    """Get system-wide metrics and statistics"""
    try:
        # Initialize default response
        metrics = {
            "total_users": 0,
            "total_messages": 0,
            "resolved_messages": 0,
            "resolution_rate": 0.0,
            "messages_last_24h": 0,
            "category_distribution": {},
            "success": True,
            "error": None
        }
        
        # Get collection names
        collections = await db.list_collection_names()
        
        # Calculate user metrics if collection exists
        if "users" in collections:
            try:
                metrics["total_users"] = await db.users.count_documents({})
            except Exception as e:
                logger.error(f"Error counting users: {e}")
                metrics["total_users"] = "Error"
        
        # Calculate message metrics if collection exists
        if "messages" in collections:
            try:
                # Total messages
                metrics["total_messages"] = await db.messages.count_documents({})
                
                # Resolved messages
                metrics["resolved_messages"] = await db.messages.count_documents({"status": "resolved"})
                
                # Resolution rate
                if metrics["total_messages"] > 0:
                    metrics["resolution_rate"] = round(metrics["resolved_messages"] / metrics["total_messages"] * 100, 2)
                
                # Messages in last 24h
                yesterday = datetime.utcnow() - timedelta(days=1)
                metrics["messages_last_24h"] = await db.messages.count_documents({
                    "created_at": {"$gte": yesterday}
                })
                
                # Category distribution
                categories = await db.messages.distinct("category")
                category_counts = {}
                for category in categories:
                    count = await db.messages.count_documents({"category": category})
                    category_counts[category] = count
                metrics["category_distribution"] = category_counts
                
            except Exception as e:
                logger.error(f"Error calculating message metrics: {e}")
                metrics.update({
                    "total_messages": "Error",
                    "resolved_messages": "Error",
                    "resolution_rate": "Error",
                    "messages_last_24h": "Error",
                    "category_distribution": {}
                })
        
        return metrics
        
    except Exception as e:
        logger.error(f"Critical error in get_metrics: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_users": 0,
            "total_messages": 0,
            "resolved_messages": 0,
            "resolution_rate": 0.0,
            "messages_last_24h": 0,
            "category_distribution": {}
        }

@router.get("/users", response_model=List[UserInDB])
async def get_users(_: UserInDB = Depends(get_current_admin)):
    """Get all users in the system"""
    try:
        db = await get_database()
        users = await db.users.find({}).to_list(None)
        return users
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@router.get("/roles")
async def get_roles(_: UserInDB = Depends(get_current_admin)):
    """Get available user roles"""
    try:
        return [
            {"id": "admin", "name": "Administrator", "permissions": ["all"]},
            {"id": "support", "name": "Support Agent", "permissions": ["read", "respond"]},
            {"id": "user", "name": "Regular User", "permissions": ["read", "write"]}
        ]
    except Exception as e:
        logging.error(f"Error fetching roles: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching roles: {str(e)}")

@router.get("/logs")
async def get_logs(limit: int = 100, 
                  db: AsyncIOMotorClient = Depends(get_database),
                  _: UserInDB = Depends(get_current_admin)) -> List[Dict]:
    """Get system logs"""
    try:
        logs = []
        if "system_logs" in await db.list_collection_names():
            cursor = db.system_logs.find().sort("timestamp", -1).limit(limit)
            async for log in cursor:
                logs.append({
                    "timestamp": log["timestamp"],
                    "level": log["level"],
                    "message": log["message"]
                })
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/log")
async def add_log(level: str, message: str,
                 db: AsyncIOMotorClient = Depends(get_database),
                 _: UserInDB = Depends(get_current_admin)):
    try:
        await db.system_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "level": level,
            "message": message
        })
        return {"success": True}
    except Exception as e:
        logger.error(f"Error adding log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Update user details"""
    try:
        db = await get_database()
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": user_update.model_dump(exclude_unset=True)}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User updated successfully"}
    except Exception as e:
        logging.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Delete a user"""
    try:
        db = await get_database()
        result = await db.users.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")