from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime, timedelta

from app.db.base import Base

class SessionStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTHENTICATED = "AUTHENTICATED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"

class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=True)
    token_type = Column(SQLEnum(TokenType), nullable=False, default=TokenType.ACCESS)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    device_info = Column(JSONB, default=dict, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[telegram_id], primaryjoin="Session.telegram_id == User.telegram_id")

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
        return f"<Session(id={self.id}, telegram_id={self.telegram_id}, status={self.status}, type={self.token_type})>" 