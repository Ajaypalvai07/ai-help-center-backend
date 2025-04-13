from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .base import MongoBaseModel, BaseDBModel

class Attachment(BaseModel):
    type: str
    url: str
    text: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "image",
                "url": "https://example.com/image.jpg",
                "text": "Image description"
            }
        }

class MessageBase(MongoBaseModel):
    content: str = Field(..., min_length=1)
    category: Optional[str] = Field(default="general")
    attachments: Optional[List[Attachment]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello, how can I help you?",
                "category": "general",
                "attachments": []
            }
        }

class MessageCreate(MessageBase):
    """Model for creating a new message"""
    pass

class Message(BaseDBModel):
    content: str = Field(..., min_length=1)
    user_id: str
    category: Optional[str] = Field(default="general")
    status: str = Field(default="active")
    attachments: Optional[List[Attachment]] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "content": "Hello, how can I help you?",
                "user_id": "507f1f77bcf86cd799439012",
                "category": "general",
                "status": "active",
                "attachments": [],
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z"
            }
        }

class MessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    user_id: str
    category: Optional[str] = Field(default="general")
    status: str = Field(default="pending")
    created_at: datetime
    confidence: Optional[float] = Field(default=None)
    type: str = Field(default="text")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "content": "Hello, how can I help you?",
                "user_id": "507f1f77bcf86cd799439012",
                "category": "general",
                "status": "pending",
                "created_at": "2024-02-20T12:00:00Z",
                "confidence": 0.95,
                "type": "text"
            }
        }