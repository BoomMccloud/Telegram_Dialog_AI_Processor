"""
Metadata models for tracking message processing runs
"""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
import json
from enum import Enum

class ProcessingStatus(str, Enum):
    """Status of a processing run"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingRunMetadata(BaseModel):
    """Metadata for a message processing run"""
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    dialog_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    status: ProcessingStatus = ProcessingStatus.IN_PROGRESS
    error: Optional[str] = None
    additional_info: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert metadata to JSON string"""
        return json.dumps(self.dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessingRunMetadata':
        """Create metadata from JSON string"""
        data = json.loads(json_str)
        return cls(**data)
    
    def mark_completed(self, message_count: int) -> None:
        """Mark the processing run as completed"""
        self.status = ProcessingStatus.COMPLETED
        self.message_count = message_count
    
    def mark_failed(self, error: str) -> None:
        """Mark the processing run as failed"""
        self.status = ProcessingStatus.FAILED
        self.error = error 