from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Attachment(BaseModel):
    type: str
    url: str
    text: Optional[str] = None

class MessageBase(BaseModel):
    content: str
    category: Optional[str] = None
    attachments: Optional[List[Attachment]] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True