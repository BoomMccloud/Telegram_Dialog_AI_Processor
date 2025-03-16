"""
Pydantic models for message data.
These models replace the deprecated SQLAlchemy Message model.
"""

from typing import List, Dict, Optional, Any, ClassVar
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID, uuid4
import json

class Message(BaseModel):
    """Schema for message data with enhanced serialization support"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
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
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    @validator('date', pre=True)
    def parse_datetime(cls, value):
        """Parse datetime from string if needed"""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls(**data) 