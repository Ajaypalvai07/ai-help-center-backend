from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(str):
    """Custom type for handling MongoDB ObjectId"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(str(v)):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema: Dict[str, Any]) -> Dict[str, Any]:
        field_schema.update(type="string")
        return field_schema

class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents"""
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }

class DateTimeModelMixin(BaseModel):
    """Mixin for models that need created_at and updated_at fields"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()

class DBModelMixin(MongoBaseModel):
    """Mixin for database models with ID field"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

class BaseDBModel(DBModelMixin, DateTimeModelMixin):
    """Complete base model for database documents"""
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }