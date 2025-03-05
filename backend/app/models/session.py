from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base

class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    EXPIRED = "expired"

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)
    status = Column(String, nullable=False, default=SessionStatus.PENDING.value)
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    session_metadata = Column("metadata", JSON, default=dict)

    # Relationships
    user = relationship("User", foreign_keys=[telegram_id], primaryjoin="Session.telegram_id == User.telegram_id")

    def __repr__(self):
        return f"<Session(id={self.id}, telegram_id={self.telegram_id}, status={self.status})>" 