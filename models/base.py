from datetime import datetime
from typing import Optional, Any, Dict, Generator, Annotated
from pydantic import BaseModel, Field, ConfigDict, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
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
    def __get_pydantic_json_schema__(
        cls, field_schema: JsonSchemaValue, field: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema.update(type="string", format="objectid")
        return field_schema

class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {}
        }
    )

class DateTimeModelMixin(BaseModel):
    """Mixin for models that need created_at and updated_at fields"""
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = None

    def update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()

    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat() if dt else None}
    )

class DBModelMixin(MongoBaseModel):
    """Mixin for database models with ID field"""
    id: Annotated[str, Field(
        default_factory=lambda: str(ObjectId()),
        alias="_id",
        description="MongoDB ObjectId"
    )]

class BaseDBModel(DBModelMixin, DateTimeModelMixin):
    """Complete base model for database documents"""
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