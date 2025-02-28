"""
Data models for dialogs and messages.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Sender(BaseModel):
    """A message sender"""
    id: str
    name: str

class Message(BaseModel):
    """A message in a dialog/chat"""
    id: str
    dialog_id: str
    dialog_name: Optional[str] = None
    dialog_type: Optional[str] = None
    text: str
    sender: Sender
    date: str
    is_outgoing: bool = False

class Dialog(BaseModel):
    """A Telegram dialog (chat)"""
    id: str
    name: str
    type: str  # "private", "group", "channel"
    unread_count: int = 0
    last_message: Optional[Dict[str, Any]] = None 