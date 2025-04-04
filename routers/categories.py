from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from core.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["categories"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_categories(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all categories"""
    try:
        db = await get_database()
        query = {"is_active": True} if active_only else {}
        
        # Get categories and sort by order
        cursor = db.categories.find(query).sort("order", 1)
        categories = await cursor.to_list(length=100)
        
        # If no categories exist, create default ones
        if not categories:
            default_categories = [
                {
                    "name": "General",
                    "icon": "chat",
                    "description": "General questions and discussions",
                    "order": 1,
                    "is_active": True
                },
                {
                    "name": "Technical",
                    "icon": "code",
                    "description": "Technical issues and support",
                    "order": 2,
                    "is_active": True
                },
                {
                    "name": "Product",
                    "icon": "box",
                    "description": "Product-related questions",
                    "order": 3,
                    "is_active": True
                },
                {
                    "name": "Account",
                    "icon": "user",
                    "description": "Account-related issues",
                    "order": 4,
                    "is_active": True
                }
            ]
            
            # Insert default categories
            await db.categories.insert_many(default_categories)
            categories = default_categories

        # Convert ObjectId to string for JSON serialization
        for category in categories:
            if "_id" in category:
                category["id"] = str(category["_id"])
                del category["_id"]

        return categories
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category_id}", response_model=Dict[str, Any])
async def get_category(category_id: str) -> Dict[str, Any]:
    """Get a specific category by ID"""
    try:
        db = await get_database()
        
        # Validate and convert category_id to ObjectId
        try:
            obj_id = ObjectId(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID format")
            
        category = await db.categories.find_one({"_id": obj_id})
        
        if not category:
            logger.warning(f"Category not found: {category_id}")
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Convert ObjectId to string for JSON serialization
        category["id"] = str(category["_id"])
        del category["_id"]
        
        return category
    except HTTPException as he:
        logger.error(f"Error getting category: {he.status_code}: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error getting category: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{category_id}/stats", response_model=Dict[str, Any])
async def get_category_stats(category_id: str) -> Dict[str, Any]:
    """Get statistics for a specific category"""
    try:
        db = await get_database()
        
        # Validate category exists
        try:
            obj_id = ObjectId(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID format")
            
        category = await db.categories.find_one({"_id": obj_id})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Get total messages in category
        total_messages = await db.messages.count_documents({"category": category_id})
        
        # Get resolved messages
        resolved_messages = await db.messages.count_documents({
            "category": category_id,
            "status": "completed"
        })
        
        # Get average confidence
        pipeline = [
            {"$match": {"category": category_id}},
            {"$group": {
                "_id": None,
                "avg_confidence": {"$avg": "$confidence"}
            }}
        ]
        confidence_result = await db.messages.aggregate(pipeline).to_list(length=1)
        avg_confidence = confidence_result[0]["avg_confidence"] if confidence_result else 0
        
        return {
            "total_messages": total_messages,
            "resolved_messages": resolved_messages,
            "resolution_rate": resolved_messages / total_messages if total_messages > 0 else 0,
            "average_confidence": avg_confidence
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get category statistics") 