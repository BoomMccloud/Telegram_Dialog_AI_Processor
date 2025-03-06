from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.db.base import Base

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class ProcessingResult(Base):
    """Results from AI processing of messages"""
    __tablename__ = "processing_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id"), nullable=False)
    model_name = Column(String, nullable=False)
    status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING)
    result = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dialog = relationship("Dialog", back_populates="processing_results")

    def __repr__(self):
        return f"<ProcessingResult(id={self.id}, dialog_id={self.dialog_id}, status={self.status})>" 