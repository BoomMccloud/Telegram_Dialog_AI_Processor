"""
SQLAlchemy Enum Types for the application
"""

import enum
from sqlalchemy import Enum

class SessionStatus(str, enum.Enum):
    """Session status enum"""
    PENDING = "PENDING"
    AUTHENTICATED = "AUTHENTICATED"
    ERROR = "ERROR"
    EXPIRED = 'EXPIRED'

    # Add PostgreSQL enum name
    __enum_name__ = 'session_status'

class TokenType(str, enum.Enum):
    """Token type enum"""
    ACCESS = "access"
    REFRESH = "refresh"

class DialogType(str, enum.Enum):
    PRIVATE = 'PRIVATE'
    GROUP = 'GROUP'
    CHANNEL = 'CHANNEL'

class ProcessingStatus(str, enum.Enum):
    """Status of a processed response
    
    PENDING_APPROVAL: Ready state - user can input their own reply or generate AI response
    GENERATING: AI is currently generating a response
    FAILED: Generation failed and can be retried
    """
    PENDING_APPROVAL = 'pending_approval'  # Used as our "ready" state
    GENERATING = 'generating'
    FAILED = 'failed'

class AuthMethod(str, enum.Enum):
    """Authentication method enum"""
    UNKNOWN = "unknown"
    PHONE = "phone"
    QR = "qr"
    TELEGRAM = "telegram"
    PASSWORD = "password"  # For future use
    
    @classmethod
    def requires_temp_user(cls, method: str) -> bool:
        """Check if auth method requires a temporary user"""
        return method == cls.QR
        
    @classmethod
    def requires_metadata(cls, method: str) -> set[str]:
        """Get required metadata fields for auth method"""
        if method == cls.PHONE:
            # Only require phone_number initially, as phone_code_hash is added later
            return {"phone_number"}
        elif method == cls.QR:
            return {"qr_login_token"}
        elif method == cls.PASSWORD:
            return {"password_hash"}
        return set() 