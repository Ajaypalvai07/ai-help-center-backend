from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from core.database import get_database, get_db_dependency
from bson import ObjectId
import logging
from models.category import CategoryResponse, CategoryInDB, CategoryStats
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
router = APIRouter(tags=["categories"])

@router.get("", response_model=List[CategoryResponse])
async def get_categories(
    active_only: bool = True,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
) -> List[CategoryResponse]:
    """Get all categories"""
    try:
        query = {"active": True} if active_only else {}
        cursor = db.categories.find(query).sort("name", 1)
        categories = await cursor.to_list(length=None)
        return [CategoryResponse(**category) for category in categories]
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch categories"
        )

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str) -> CategoryResponse:
    """Get a specific category by ID"""
    try:
        if not ObjectId.is_valid(category_id):
            raise HTTPException(status_code=400, detail="Invalid category ID format")
        
        db = await get_database()
        category = await db.find_one("categories", {"_id": ObjectId(category_id)})
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return CategoryResponse(**category)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category {category_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category_id}/stats", response_model=CategoryStats)
async def get_category_stats(category_id: str) -> CategoryStats:
    """Get statistics for a specific category"""
    try:
        if not ObjectId.is_valid(category_id):
            raise HTTPException(status_code=400, detail="Invalid category ID format")
        
        db = await get_database()
        category = await db.find_one("categories", {"_id": ObjectId(category_id)})
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Get messages for this category
        messages = await db.find_many("messages", {"category_id": ObjectId(category_id)})
        total_messages = len(messages)
        
        if total_messages == 0:
            return CategoryStats(
                category_id=category_id,
                total_messages=0,
                resolved_messages=0,
                resolution_rate=0.0,
                avg_confidence=0.0
            )
        
        resolved_messages = sum(1 for msg in messages if msg.get("resolved", False))
        resolution_rate = (resolved_messages / total_messages) * 100 if total_messages > 0 else 0
        
        confidences = [msg.get("confidence", 0) for msg in messages if msg.get("confidence") is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return CategoryStats(
            category_id=category_id,
            total_messages=total_messages,
            resolved_messages=resolved_messages,
            resolution_rate=resolution_rate,
            avg_confidence=avg_confidence
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category stats for {category_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 