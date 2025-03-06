"""
Model for processed responses from AI
"""

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from .base import Base
from .types import ProcessingStatus

class ProcessedResponse(Base):
    __tablename__ = "processed_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False)
    last_message_id = Column(String(255), nullable=False)
    last_message_timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    suggested_response = Column(Text, nullable=False)
    edited_response = Column(Text)
    status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING_APPROVAL)
    model_name = Column(String(255), nullable=False)
    processed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(TIMESTAMP(timezone=True))
    sent_at = Column(TIMESTAMP(timezone=True))
    error = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    dialog = relationship("Dialog", back_populates="processed_responses")

    __table_args__ = (
        UniqueConstraint('dialog_id', name='uq_dialog_response'),
    )

    def __repr__(self):
        return f"<ProcessedResponse(id={self.id}, dialog_id={self.dialog_id}, status={self.status})>" 