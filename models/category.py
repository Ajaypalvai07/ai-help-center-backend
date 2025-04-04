from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Category(BaseModel):
    name: str
    icon: str
    description: str
    order: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class CategoryCreate(BaseModel):
    name: str
    icon: str
    description: str
    order: Optional[int] = 1
    is_active: Optional[bool] = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryInDB(Category):
    id: str 