"""
SQLAlchemy Enum Types for the application
"""

import enum
from sqlalchemy import Enum

class SessionStatus(str, enum.Enum):
    PENDING = 'PENDING'
    AUTHENTICATED = 'AUTHENTICATED'
    ERROR = 'ERROR'
    EXPIRED = 'EXPIRED'

class TokenType(str, enum.Enum):
    ACCESS = 'access'
    REFRESH = 'refresh'

class DialogType(str, enum.Enum):
    PRIVATE = 'private'
    GROUP = 'group'
    CHANNEL = 'channel'

class ProcessingStatus(str, enum.Enum):
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SENT = 'sent'
    FAILED = 'failed'

class TaskStatus(str, enum.Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class TaskType(str, enum.Enum):
    MESSAGE = 'message'
    DIALOG = 'dialog'
    BATCH = 'batch' 