from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from middleware.auth import get_current_admin
from models.user import UserInDB, UserUpdate
from core.database import get_db_dependency
# from ..core.auth import get_current_admin_user
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = logging.getLogger(__name__)

@router.get("/metrics")
async def get_metrics(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency), 
    _: UserInDB = Depends(get_current_admin)
) -> Dict:
    """Get admin metrics"""
    try:
        # Get total users
        total_users = await db.users.count_documents({})
        
        # Get active users (users who logged in within last 30 days)
        active_users = await db.users.count_documents({
            "last_login": {"$gte": datetime.utcnow() - timedelta(days=30)}
        })
        
        # Get total messages
        total_messages = await db.messages.count_documents({})
        
        # Get resolved messages
        resolved_messages = await db.messages.count_documents({"status": "resolved"})
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_messages": total_messages,
            "resolved_messages": resolved_messages
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@router.get("/users", response_model=List[UserInDB])
async def get_users(_: UserInDB = Depends(get_current_admin)):
    """Get all users in the system"""
    try:
        db = await get_db_dependency()
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
                  db: AsyncIOMotorClient = Depends(get_db_dependency),
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
                 db: AsyncIOMotorClient = Depends(get_db_dependency),
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
        db = await get_db_dependency()
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
        db = await get_db_dependency()
        result = await db.users.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")