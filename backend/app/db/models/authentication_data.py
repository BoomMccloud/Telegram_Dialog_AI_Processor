"""
Model for storing user authentication data
"""

from sqlalchemy import Column, TIMESTAMP, ForeignKey, LargeBinary, Boolean, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from .base import Base

class AuthenticationData(Base):
    __tablename__ = "authentication_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    session_data = Column(JSONB, default=dict)
    encrypted_credentials = Column(LargeBinary)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="auth_data")

    def __repr__(self):
        return f"<AuthenticationData(id={self.id}, user_id={self.user_id}, telegram_id={self.telegram_id})>" 