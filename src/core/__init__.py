"""
Core module

Provides basic functionality used throughout the application
"""

from src.core.config import Settings, get_settings, settings
from src.core.database import DatabaseManager, db_manager, get_db, session_scope
from src.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    DataImportError,
    DuplicateError,
    ExternalServiceError,
    JRAVANError,
    KeibaAIException,
    ModelNotFoundError,
    NotFoundError,
    PredictionError,
    ValidationError,
    register_exception_handlers,
)
from src.core.logging import (
    BoundLogger,
    log,
    log_async_execution_time,
    log_execution_time,
    logger,
    logger_manager,
    setup_logging,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Database
    "DatabaseManager",
    "db_manager",
    "get_db",
    "session_scope",
    # Exceptions
    "KeibaAIException",
    "ValidationError",
    "NotFoundError",
    "DuplicateError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "DataImportError",
    "ModelNotFoundError",
    "PredictionError",
    "ExternalServiceError",
    "JRAVANError",
    "register_exception_handlers",
    # Logging
    "logger",
    "log",
    "logger_manager",
    "setup_logging",
    "log_execution_time",
    "log_async_execution_time",
    "BoundLogger",
]
