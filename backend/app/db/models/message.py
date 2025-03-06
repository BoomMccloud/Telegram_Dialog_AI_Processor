from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel

class Message(BaseModel):
    """Model for a message"""
    id: int
    dialog_id: int
    text: str
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    date: str
    is_outgoing: bool = False

class MessageSend(BaseModel):
    """Model for sending a message"""
    dialog_id: int
    text: str

class MessageResponse(BaseModel):
    """Model for message send response"""
    message_id: int
    dialog_id: int
    status: str = "sent" 