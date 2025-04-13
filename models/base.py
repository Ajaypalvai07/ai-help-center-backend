from datetime import datetime
from typing import Optional, Any, Dict, Generator
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(str):
    """Custom type for handling MongoDB ObjectId"""
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
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type="string", format="objectid")

class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents"""
    class Config:
        allow_population_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

class DateTimeModelMixin(BaseModel):
    """Mixin for models that need created_at and updated_at fields"""
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = None

    def update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt else None
        }

class DBModelMixin(MongoBaseModel):
    """Mixin for database models with ID field"""
    id: PyObjectId = Field(
        default_factory=lambda: str(ObjectId()),
        alias="_id",
        description="MongoDB ObjectId"
    )

class BaseDBModel(DBModelMixin, DateTimeModelMixin):
    """Complete base model for database documents"""
    class Config:
        allow_population_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "created_at": "2024-02-20T12:00:00",
                "updated_at": "2024-02-20T12:00:00"
            }
        }