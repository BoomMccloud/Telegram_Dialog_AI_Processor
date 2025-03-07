"""
Pydantic models for message data.
These models replace the deprecated SQLAlchemy Message model.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Message(BaseModel):
    """Schema for message data"""
    id: Optional[str] = None
    telegram_message_id: Optional[str] = None
    dialog_id: Optional[str] = None
    text: str
    sender_id: str
    sender_name: str
    date: datetime
    is_outgoing: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True 