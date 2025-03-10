"""
Session model for the application
"""

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .base import Base
from .types import SessionStatus, TokenType, AuthMethod

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=True)
    token_type = Column(SQLEnum(TokenType), nullable=False, default=TokenType.ACCESS)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_activity = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    session_metadata = Column(JSONB, default=dict, nullable=False)
    device_info = Column(JSONB, default=dict, nullable=False)
    auth_method = Column(SQLEnum(AuthMethod), nullable=False, default=AuthMethod.UNKNOWN)

    # Relationships
    user = relationship("User", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if the session is expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if the session is active based on authentication state"""
        if self.status == SessionStatus.AUTHENTICATED:
            # Stricter checks for authenticated sessions
            return (
                not self.is_expired
                and self.user_id is not None
                and (datetime.utcnow() - self.last_activity) < timedelta(days=7)
            )
        else:
            # More lenient checks for pre-auth sessions
            return not self.is_expired

    def validate_pre_auth(self) -> tuple[bool, Optional[str]]:
        """
        Validate pre-authentication session state
        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if self.status != SessionStatus.PENDING:
            return False, "Invalid session status"
        
        if self.is_expired:
            return False, "Session expired"
            
        # Check required metadata based on auth method
        required_metadata = AuthMethod.requires_metadata(self.auth_method)
        missing_fields = required_metadata - set(self.session_metadata.keys())
        if missing_fields:
            return False, f"Missing required metadata: {', '.join(missing_fields)}"
            
        # Check if temporary user is required
        if AuthMethod.requires_temp_user(self.auth_method) and self.user_id is None:
            return False, "Missing temporary user"
            
        return True, None

    def validate_post_auth(self) -> tuple[bool, Optional[str]]:
        """
        Validate post-authentication session state
        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if self.status != SessionStatus.AUTHENTICATED:
            return False, "Session not authenticated"
            
        if self.user_id is None:
            return False, "No user associated with session"
            
        if self.is_expired:
            return False, "Session expired"
            
        if not self.refresh_token:
            return False, "Missing refresh token"
            
        if (datetime.utcnow() - self.last_activity) >= timedelta(days=7):
            return False, "Session inactive"
            
        return True, None

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def update_metadata(self, data: Dict[str, Any]):
        """
        Update session metadata safely
        Args:
            data: New metadata to merge with existing
        """
        current = self.session_metadata or {}
        current.update(data)
        self.session_metadata = current

    def update_device_info(self, info: Dict[str, Any]):
        """
        Update device information safely
        Args:
            info: New device info to merge with existing
        """
        current = self.device_info or {}
        current.update(info)
        self.device_info = current

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status}, auth_method={self.auth_method})>" 