"""
Queue Model

This module defines the database models for the task queue system.
Used by the background worker to manage and track processing tasks.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
import uuid
from datetime import datetime

from .base import Base


class TaskPriority(PyEnum):
    """Priority levels for queue tasks"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    

class TaskStatus(PyEnum):
    """Status values for queue tasks"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(PyEnum):
    """Types of tasks that can be queued"""
    DIALOG = "dialog"
    USER = "user"
    SYSTEM = "system"


class QueueTask(Base):
    """
    Queue task model for background processing
    
    Represents a task in the processing queue, tracking its status,
    priority, and related entities.
    """
    __tablename__ = "queue_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(Enum(TaskType), nullable=False, default=TaskType.DIALOG)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.NORMAL)
    
    # Related entities - one of these will be set based on task_type
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialogs.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # The model to use for processing
    model_name = Column(String, nullable=True)
    
    # Additional task data as JSON
    data = Column(JSON, nullable=True)
    
    # Error information if task failed
    error = Column(String, nullable=True)
    
    # Retry information
    max_retries = Column(Integer, nullable=False, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=True)  # For delayed tasks
    started_at = Column(DateTime, nullable=True)     # When processing began
    completed_at = Column(DateTime, nullable=True)   # When processing finished
    
    # Relationships
    dialog = relationship("Dialog", back_populates="queue_tasks", uselist=False)
    user = relationship("User", back_populates="queue_tasks", uselist=False)
    
    def __repr__(self):
        return f"<QueueTask(id={self.id}, type={self.task_type}, status={self.status})>" 