from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field
from .base import PyObjectId, MongoBaseModel, BaseDBModel

class UserBase(MongoBaseModel):
    """Base user model"""
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(default=None)
    disabled: bool = Field(default=False)
    is_active: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "disabled": False,
                "is_active": True
            }
        }

class UserCreate(UserBase):
    """Model for user registration"""
    password: str = Field(..., min_length=8)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "password": "strongpassword123",
                "disabled": False,
                "is_active": True
            }
        }

class UserUpdate(BaseModel):
    """Model for updating user information"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    disabled: Optional[bool] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "username": "newusername",
                "full_name": "New Name",
                "password": "newpassword123"
            }
        }

class UserResponse(BaseModel):
    """Model for user response data"""
    id: str = Field(..., alias="_id")
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    disabled: bool = False
    is_active: bool = True
    created_at: datetime
    role: str = Field(default="user")
    preferences: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False,
                "is_active": True,
                "created_at": "2024-02-20T12:00:00Z",
                "role": "user",
                "preferences": {}
            }
        }

class UserInDB(BaseDBModel):
    """Internal user model with hashed password"""
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    disabled: bool = False
    is_active: bool = True
    hashed_password: str
    role: str = Field(default="user")
    preferences: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False,
                "is_active": True,
                "hashed_password": "hashedpassword123",
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z",
                "role": "user",
                "preferences": {}
            }
        }
