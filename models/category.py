from typing import Optional
from datetime import datetime
from pydantic import Field, BaseModel
from .base import MongoBaseModel, BaseDBModel

class CategoryBase(MongoBaseModel):
    """Base category model"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    active: bool = Field(default=True)

    @property
    def display_name(self) -> str:
        """Return a formatted display name"""
        return self.name.title()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "General",
                "description": "General category for miscellaneous queries",
                "active": True
            }
        }

class CategoryCreate(CategoryBase):
    """Model for creating a new category"""
    pass

class CategoryUpdate(MongoBaseModel):
    """Model for updating category information"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Category",
                "description": "Updated description",
                "active": True
            }
        }

class CategoryInDB(CategoryBase, BaseDBModel):
    """Internal category model with database fields"""
    pass

class CategoryResponse(BaseModel):
    """API response model for categories"""
    id: str = Field(..., alias="_id")
    name: str
    description: str
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "General",
                "description": "General category for miscellaneous queries",
                "active": True,
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z"
            }
        }

class CategoryStats(BaseModel):
    """Category statistics model"""
    category_id: str = Field(..., description="Category ID")
    total_messages: int = Field(default=0, ge=0)
    resolved_messages: int = Field(default=0, ge=0)
    resolution_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_messages == 0:
            return 0.0
        return round((self.resolved_messages / self.total_messages) * 100, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "category_id": "507f1f77bcf86cd799439011",
                "total_messages": 100,
                "resolved_messages": 95,
                "resolution_rate": 95.0,
                "avg_confidence": 0.85
            }
        }