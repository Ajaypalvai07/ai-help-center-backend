from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from .base import PyObjectId, MongoBaseModel, BaseDBModel

class UserBase(MongoBaseModel):
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(default=None)
    disabled: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False
            }
        }

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "password": "strongpassword123"
            }
        }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)

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
    id: str = Field(..., alias="_id")
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: datetime

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
                "created_at": "2024-02-20T12:00:00Z"
            }
        }

class UserInDB(BaseDBModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    disabled: bool = False
    hashed_password: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False,
                "hashed_password": "hashedpassword123",
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z"
            }
        }
