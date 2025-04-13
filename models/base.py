from datetime import datetime
from typing import Optional, Any, Dict, Generator
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

class PyObjectId(str):
    """Custom type for handling MongoDB ObjectId with improved validation"""
    @classmethod
    def __get_validators__(cls) -> Generator:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(str(v)):
            raise ValueError(f"Invalid ObjectId: {v}")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema: Dict[str, Any]) -> Dict[str, Any]:
        field_schema.update(type="string", format="objectid")
        return field_schema

class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents with modern Pydantic configuration"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }
    )

class DateTimeModelMixin(BaseModel):
    """Mixin for models that need created_at and updated_at fields with validation"""
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current UTC time"""
        self.updated_at = datetime.utcnow()

class DBModelMixin(MongoBaseModel):
    """Mixin for database models with ID field and validation"""
    id: PyObjectId = Field(
        default_factory=lambda: str(ObjectId()), 
        alias="_id",
        description="MongoDB ObjectId"
    )

class BaseDBModel(DBModelMixin, DateTimeModelMixin):
    """Complete base model for database documents with comprehensive configuration"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        },
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "created_at": "2024-02-20T12:00:00",
                "updated_at": "2024-02-20T12:00:00"
            }
        }
    )