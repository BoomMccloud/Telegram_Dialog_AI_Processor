"""
Model for processed responses from AI
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base
from .types import ProcessingStatus

class ProcessedResponse(Base):
    __tablename__ = "processed_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=False)
    last_message_id = Column(String(255), nullable=False)
    last_message_timestamp = Column(DateTime(timezone=True), nullable=False)
    suggested_response = Column(Text, nullable=False)
    edited_response = Column(Text)
    status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING_APPROVAL)
    model_name = Column(String(255), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    dialog = relationship("Dialog", back_populates="processed_responses")

    __table_args__ = (
        # Unique constraint on dialog_id
        {'unique_together': ('dialog_id',)}
    )

    def __repr__(self):
        return f"<ProcessedResponse(id={self.id}, dialog_id={self.dialog_id}, status={self.status})>" 