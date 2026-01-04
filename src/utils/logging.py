"""
Logging utilities for the Mixamo Blend Pipeline.

Provides structured logging with entry/exit decorators, JSON formatting,
correlation IDs, and consistent formatting across all pipeline stages.

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
Date: January 4, 2026

Features:
    - Structured JSON logging for production environments
    - Correlation ID tracking across requests
    - Entry/exit decorators with timing
    - Colorized console output for development
    - Context-aware logging with metadata

Example usage:
    >>> from src.utils.logging import get_logger, log_function_call, set_correlation_id
    >>>
    >>> logger = get_logger(__name__)
    >>> set_correlation_id("req-12345")
    >>>
    >>> @log_function_call
    >>> def process_animation(file_path: str) -> bool:
    >>>     logger.info("Processing animation", extra={"file": file_path})
    >>>     return True
"""

import logging
import functools
import json
import os
import uuid
from typing import Any, Callable, TypeVar, cast, Optional, Dict
from datetime import datetime
from contextvars import ContextVar

try:
    import coloredlogs
    HAS_COLOREDLOGS = True
except ImportError:
    HAS_COLOREDLOGS = False

# Type variable for generic decorator typing
F = TypeVar("F", bound=Callable[..., Any])

# Context variable for correlation ID (thread-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Global logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
JSON_LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower() == "json"


# ============================================================================
# Correlation ID Management
# ============================================================================

def get_correlation_id() -> str:
    """
    Get current correlation ID or generate new one.
    
    Returns:
        Current correlation ID (generates UUID if not set)
    
    Example:
        >>> corr_id = get_correlation_id()
        >>> logger.info("Processing request", extra={"correlation_id": corr_id})
    """
    corr_id = _correlation_id.get()
    if corr_id is None:
        corr_id = str(uuid.uuid4())
        _correlation_id.set(corr_id)
    return corr_id


def set_correlation_id(corr_id: str) -> None:
    """
    Set correlation ID for current context.
    
    Args:
        corr_id: Correlation ID to set
    
    Example:
        >>> set_correlation_id("req-12345")
        >>> # All subsequent logs will include this correlation ID
    """
    _correlation_id.set(corr_id)


def clear_correlation_id() -> None:
    """Clear correlation ID for current context."""
    _correlation_id.set(None)


# ============================================================================
# JSON Formatter
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Outputs logs in JSON format with standard fields and custom metadata.
    Includes correlation ID, timestamp, level, message, and extra fields.
    
    Example output:
        {
            "timestamp": "2026-01-04T10:30:15.123456Z",
            "level": "INFO",
            "logger": "src.uploader",
            "message": "Uploading file",
            "correlation_id": "req-12345",
            "extra": {"file_size": 1024, "destination": "seed/"}
        }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON-formatted log string
        """
        # Build base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        
        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # Add extra fields from record
        # Filter out standard logging attributes
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }
        
        # Add environment metadata
        log_data["environment"] = {
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "pod_name": os.getenv("POD_NAME", ""),
            "node_name": os.getenv("NODE_NAME", ""),
        }
        
        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO", enable_colors: bool = True) -> None:
    """
    Configure global logging settings for the application.

    Sets up structured JSON logging for production or colorized text for development.
    Automatically detects environment from LOG_FORMAT environment variable.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_colors: Whether to enable colorized console output (default: True)

    Returns:
        None

    Raises:
        ValueError: If invalid logging level is provided

    Example:
        >>> # Production (JSON):
        >>> os.environ["LOG_FORMAT"] = "json"
        >>> setup_logging(level="INFO")
        >>>
        >>> # Development (colorized text):
        >>> setup_logging(level="DEBUG", enable_colors=True)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Use JSON formatter for production, text for development
    if JSON_LOG_FORMAT:
        # Production: JSON structured logging
        formatter = JSONFormatter()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    elif enable_colors and HAS_COLOREDLOGS:
        # Development: Colorized text logging
        coloredlogs.install(
            level=log_level, 
            fmt=LOG_FORMAT, 
            datefmt=LOG_DATE_FORMAT, 
            logger=root_logger
        )
    else:
        # Fallback: Plain text logging
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


def log_function_call(func: F) -> F:
    """
    Decorator that logs function entry and exit with parameters and return values.

    This decorator provides verbose logging for debugging and monitoring:
    - Logs function entry with all parameter values
    - Logs function exit with return value and execution time
    - Logs exceptions with full traceback
    - Includes correlation ID in all log entries
    - Adds structured metadata (function name, duration, status)

    Args:
        func: Function to be decorated

    Returns:
        Wrapped function with logging

    Example:
        >>> @log_function_call
        >>> def download_animation(url: str, output_path: str) -> bool:
        >>>     # Download logic here
        >>>     return True
        >>>
        >>> # Text output:
        >>> # 2026-01-04 10:30:15 - module - INFO - ENTER download_animation(...)
        >>> # 2026-01-04 10:30:16 - module - INFO - EXIT download_animation -> True (1.23s)
        >>>
        >>> # JSON output:
        >>> # {"timestamp": "...", "level": "INFO", "message": "ENTER download_animation",
        >>> #  "correlation_id": "...", "extra": {"function": "download_animation", ...}}
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Ensure correlation ID is set
        correlation_id = get_correlation_id()
        
        # Format function arguments for logging
        arg_names = func.__code__.co_varnames[: func.__code__.co_argcount]
        args_repr = [f"{name}={repr(value)}" for name, value in zip(arg_names, args)]
        kwargs_repr = [f"{key}={repr(value)}" for key, value in kwargs.items()]
        all_args = ", ".join(args_repr + kwargs_repr)

        # Log function entry with structured metadata
        logger.info(
            f"ENTER {func.__name__}",
            extra={
                "function": func.__name__,
                "module": func.__module__,
                "arguments": all_args,
                "correlation_id": correlation_id,
                "event": "function_entry",
            }
        )

        start_time = datetime.now()

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log function exit with return value
            logger.info(
                f"EXIT {func.__name__} -> {repr(result)}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": execution_time,
                    "return_value": repr(result),
                    "correlation_id": correlation_id,
                    "event": "function_exit",
                    "status": "success",
                }
            )

            return result

        except Exception as error:
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log exception with structured metadata
            logger.error(
                f"ERROR {func.__name__} raised {type(error).__name__}: {str(error)}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": execution_time,
                    "correlation_id": correlation_id,
                    "event": "function_error",
                    "status": "error",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                },
                exc_info=True,
            )

            # Re-raise exception to preserve original behavior
            raise

    return cast(F, wrapper)
