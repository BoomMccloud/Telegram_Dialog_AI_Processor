"""
Pydantic models for API request/response schemas
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class DialogBase(BaseModel):
    """Base model for a dialog/chat"""
    name: str
    type: str
    unread_count: Optional[int] = 0
    last_message: Optional[Dict] = None

class DialogCreate(DialogBase):
    """Schema for creating a new dialog"""
    telegram_dialog_id: str
    user_id: UUID

class DialogUpdate(DialogBase):
    """Schema for updating a dialog"""
    is_processing_enabled: Optional[bool] = None
    auto_send_enabled: Optional[bool] = None

class DialogResponse(DialogBase):
    """Schema for dialog response"""
    id: UUID
    telegram_dialog_id: str
    user_id: UUID
    is_processing_enabled: bool
    auto_send_enabled: bool
    last_processed_message_id: Optional[str]
    last_processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class DialogListResponse(BaseModel):
    """Response model for list of dialogs"""
    dialogs: List[DialogResponse]

class MessageBase(BaseModel):
    """Base model for a message"""
    text: str
    sender_id: str
    sender_name: str
    date: datetime
    is_outgoing: bool = False

class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    telegram_message_id: str
    dialog_id: UUID

class MessageResponse(MessageBase):
    """Schema for message response"""
    id: UUID
    telegram_message_id: str
    dialog_id: UUID
    created_at: datetime 