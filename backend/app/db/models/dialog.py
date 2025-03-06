"""
Data models for dialogs.
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Boolean, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from .base import Base
from .types import DialogType

class Dialog(Base):
    """A Telegram dialog (chat)"""
    __tablename__ = "dialogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    telegram_dialog_id = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(DialogType), nullable=False)
    unread_count = Column(Integer, default=0)
    last_message = Column(JSONB, default=dict)
    is_processing_enabled = Column(Boolean, nullable=False, default=False)
    auto_send_enabled = Column(Boolean, nullable=False, default=False)
    last_processed_message_id = Column(String(255))
    last_processed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="dialogs")
    processed_responses = relationship("ProcessedResponse", back_populates="dialog", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('user_id', 'telegram_dialog_id', name='uq_dialog_user_telegram'),
    )

    def __repr__(self):
        return f"<Dialog(id={self.id}, name={self.name}, type={self.type})>" 