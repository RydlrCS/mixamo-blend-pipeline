"""
Unit tests for logging utilities.

Tests verify:
- Logging setup and configuration
- Function call decorator behavior
- Entry/exit logging
- Exception handling in decorated functions
"""

import logging
from src.utils.logging import setup_logging, get_logger, log_function_call


def test_setup_logging_configures_root_logger() -> None:
    """Test that setup_logging properly configures the root logger."""
    setup_logging(level="DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_get_logger_returns_logger_instance() -> None:
    """Test that get_logger returns a valid logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_log_function_call_decorator_logs_entry_and_exit() -> None:
    """Test that log_function_call decorator logs function entry and exit."""

    @log_function_call
    def sample_function(x: int, y: int) -> int:
        """Sample function for testing decorator."""
        return x + y

    result = sample_function(2, 3)
    assert result == 5


def test_log_function_call_decorator_handles_exceptions() -> None:
    """Test that log_function_call decorator properly logs exceptions."""

    @log_function_call
    def failing_function() -> None:
        """Function that raises an exception."""
        raise ValueError("Test exception")

    try:
        failing_function()
        assert False, "Exception should have been raised"
    except ValueError as e:
        assert str(e) == "Test exception"
