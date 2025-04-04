from typing import Optional
from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    is_admin: bool

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None