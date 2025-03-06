"""
Model for user's selected AI model preferences
"""

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from .base import Base

class UserSelectedModel(Base):
    __tablename__ = "user_selected_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(255), nullable=False)
    system_prompt = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="selected_models")

    def __repr__(self):
        return f"<UserSelectedModel(id={self.id}, user_id={self.user_id}, model_name={self.model_name})>" 