from typing import Optional
from pydantic import BaseModel
from .user import UserResponse

class Token(BaseModel):
    """Token model"""
    access_token: str
    token_type: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }

class TokenData(BaseModel):
    """Token data model"""
    email: Optional[str] = None
    role: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "role": "user"
            }
        }

class AuthResponse(BaseModel):
    """Authentication response model"""
    access_token: str
    token_type: str
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "role": "user",
                    "is_active": True,
                    "created_at": "2024-04-12T10:00:00Z",
                    "last_login": None
                }
            }
        }