"""
Logging utilities for the Mixamo Blend Pipeline.

Provides structured logging with entry/exit decorators, colorized output,
and consistent formatting across all pipeline stages.

Example usage:
    >>> from src.utils.logging import get_logger, log_function_call
    >>>
    >>> logger = get_logger(__name__)
    >>>
    >>> @log_function_call
    >>> def process_animation(file_path: str) -> bool:
    >>>     logger.info(f"Processing animation from {file_path}")
    >>>     return True
"""

import logging
import functools
from typing import Any, Callable, TypeVar, cast
from datetime import datetime

try:
    import coloredlogs

    HAS_COLOREDLOGS = True
except ImportError:
    HAS_COLOREDLOGS = False

# Type variable for generic decorator typing
F = TypeVar("F", bound=Callable[..., Any])

# Global logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO", enable_colors: bool = True) -> None:
    """
    Configure global logging settings for the application.

    This function should be called once at application startup to initialize
    the logging system with consistent formatting and output configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_colors: Whether to enable colorized console output (default: True)

    Returns:
        None

    Raises:
        ValueError: If invalid logging level is provided

    Example:
        >>> setup_logging(level="DEBUG", enable_colors=True)
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message with colors")
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    if enable_colors and HAS_COLOREDLOGS:
        # Use coloredlogs for better readability
        coloredlogs.install(
            level=log_level, fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, logger=root_logger
        )
    else:
        # Fallback to standard logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
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
    - Logs function exit with return value
    - Logs execution time
    - Logs exceptions if they occur

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
        >>> # Output:
        >>> # 2026-01-04 10:30:15 - module - INFO - ENTER download_animation(...)
        >>> # 2026-01-04 10:30:16 - module - INFO - EXIT download_animation -> True
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Format function arguments for logging
        arg_names = func.__code__.co_varnames[: func.__code__.co_argcount]
        args_repr = [f"{name}={repr(value)}" for name, value in zip(arg_names, args)]
        kwargs_repr = [f"{key}={repr(value)}" for key, value in kwargs.items()]
        all_args = ", ".join(args_repr + kwargs_repr)

        # Log function entry
        logger.info(f"ENTER {func.__name__}({all_args})")

        start_time = datetime.now()

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log function exit with return value
            logger.info(f"EXIT {func.__name__} -> {repr(result)} ({execution_time:.2f}s)")

            return result

        except Exception as error:
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log exception
            logger.error(
                f"ERROR {func.__name__} raised {type(error).__name__}: {str(error)} "
                f"({execution_time:.2f}s)"
            )

            # Re-raise exception to preserve original behavior
            raise

    return cast(F, wrapper)
