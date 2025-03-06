from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timedelta

from .base import Base
from .types import SessionStatus, TokenType

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=True)
    token_type = Column(SQLEnum(TokenType), nullable=False, default=TokenType.ACCESS)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session_metadata = Column(JSONB, server_default='{}', nullable=False)
    device_info = Column(JSONB, server_default='{}', nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if the session is expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if the session is active"""
        return (
            self.status == SessionStatus.AUTHENTICATED
            and not self.is_expired
            and (datetime.utcnow() - self.last_activity) < timedelta(days=7)
        )

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>" 