from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import json

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, values=None, config=None, field=None):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict[str, Any]:
        return {"type": "string"}

class UserBase(BaseModel):
    """Base user model with common fields"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
    
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=2, max_length=50, description="User's full name")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    role: str = Field(default="user", description="User's role (e.g., user, admin)")

class UserCreate(UserBase):
    """Model for creating a new user"""
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (min 8 characters)",
        examples=["StrongP@ssw0rd"]
    )

class UserLogin(BaseModel):
    """Model for user login"""
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class UserUpdate(BaseModel):
    """Model for updating user information"""
    model_config = ConfigDict(from_attributes=True)
    
    email: Optional[EmailStr] = Field(None, description="New email address")
    name: Optional[str] = Field(None, min_length=2, description="New full name")
    is_active: Optional[bool] = Field(None, description="Update active status")
    role: Optional[str] = Field(None, description="Update user role")

class User(UserBase):
    """User model for general use"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    preferences: Dict = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True
    )

class UserInDB(User):
    """Internal user model with password"""
    password: str = Field(..., description="Hashed password")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True
    )

class UserResponse(BaseModel):
    """Model for user data in responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="User's unique identifier")
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., description="User's full name")
    role: str = Field(..., description="User's role")
    is_active: bool = Field(..., description="Account status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    preferences: Dict = Field(default_factory=dict, description="User preferences")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AuthResponse(BaseModel):
    """Authentication response model"""
    model_config = ConfigDict(from_attributes=True)
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type (bearer)")
    user: UserResponse = Field(..., description="User information")