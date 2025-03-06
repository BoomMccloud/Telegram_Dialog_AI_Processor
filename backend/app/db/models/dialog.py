"""
Data models for dialogs and messages.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import List, Dict, Optional
from pydantic import BaseModel

from .base import Base
from .types import DialogType

class Dialog(BaseModel):
    """Model for a dialog/chat"""
    id: int
    name: str
    type: str
    unread_count: Optional[int] = 0
    last_message: Optional[Dict] = None

class DialogListResponse(BaseModel):
    """Response model for list of dialogs"""
    dialogs: List[Dialog]

class Dialog(Base):
    """A Telegram dialog (chat)"""
    __tablename__ = "dialogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_dialog_id = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(DialogType), nullable=False)
    unread_count = Column(Integer, default=0)
    last_message = Column(JSONB, server_default='{}')
    is_processing_enabled = Column(Boolean, nullable=False, default=False)
    auto_send_enabled = Column(Boolean, nullable=False, default=False)
    last_processed_message_id = Column(String(255))
    last_processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="dialogs")
    processed_responses = relationship("ProcessedResponse", back_populates="dialog", cascade="all, delete-orphan")

    __table_args__ = (
        # Unique constraint on user_id and telegram_dialog_id
        {'unique_together': ('user_id', 'telegram_dialog_id')}
    )

    def __repr__(self):
        return f"<Dialog(id={self.id}, name={self.name}, type={self.type})>"

class Message(Base):
    """A message in a dialog/chat"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_message_id = Column(String, nullable=False)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id"), nullable=False)
    text = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    is_outgoing = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    dialog = relationship("Dialog", back_populates="messages")
    processing_results = relationship("ProcessingResult", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message(id={self.id}, dialog_id={self.dialog_id}, sender={self.sender_name})>" 