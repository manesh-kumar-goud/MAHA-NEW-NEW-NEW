"""Application enums"""

from enum import Enum


class PrefixStatus(str, Enum):
    """Status of a prefix configuration - Only 3 statuses"""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    COMPLETED = "completed"


class OperationStatus(str, Enum):
    """Status of an operation"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
