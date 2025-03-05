"""
Data models for dialogs and messages.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class Dialog(Base):
    """A Telegram dialog (chat)"""
    __tablename__ = "dialogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_dialog_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "private", "group", "channel"
    unread_count = Column(Integer, default=0)
    last_message = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="dialog", cascade="all, delete-orphan")

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