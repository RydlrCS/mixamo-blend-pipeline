"""
Advanced retry logic with exponential backoff and jitter.

Provides production-grade retry mechanisms for transient failures with:
- Exponential backoff with jitter (prevents thundering herd)
- Circuit breaker pattern (fails fast when service is down)
- Custom retry conditions and exception handling
- Comprehensive logging of retry attempts

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
Date: January 4, 2026

Usage:
    from src.utils.retry import retry_with_backoff, CircuitBreaker
    
    # Simple retry decorator:
    @retry_with_backoff(max_attempts=5, base_delay=1.0)
    def upload_file(path):
        # ... upload logic that may fail transiently ...
        pass
    
    # Circuit breaker for external services:
    breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    
    @breaker
    def call_external_api():
        # ... API call ...
        pass
"""

import time
import random
import functools
from typing import Callable, Optional, Type, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)


# ============================================================================
# Retry Configuration
# ============================================================================

@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        jitter: Whether to add randomness to delays (prevents thundering herd)
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called before each retry
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable] = None


def calculate_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    multiplier: float,
    jitter: bool,
) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.
    
    Formula:
        delay = min(base_delay * (multiplier ** attempt), max_delay)
        if jitter:
            delay = delay * random.uniform(0.5, 1.5)
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        multiplier: Exponential multiplier
        jitter: Whether to add random jitter
    
    Returns:
        Calculated delay in seconds
    
    Example:
        >>> # Attempt 0: ~1.0s, Attempt 1: ~2.0s, Attempt 2: ~4.0s
        >>> delay = calculate_backoff_delay(2, base_delay=1.0, max_delay=60.0,
        ...                                  multiplier=2.0, jitter=False)
        >>> print(delay)
        4.0
    """
    # Calculate exponential delay
    delay = base_delay * (multiplier ** attempt)
    
    # Cap at maximum delay
    delay = min(delay, max_delay)
    
    # Add jitter if enabled (±50% randomness)
    if jitter:
        jitter_factor = random.uniform(0.5, 1.5)
        delay = delay * jitter_factor
    
    return delay


# ============================================================================
# Retry Decorator
# ============================================================================

def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Automatically retries function on specified exceptions with increasing
    delays between attempts. Logs all retry attempts.
    
    Args:
        max_attempts: Maximum number of attempts (including initial)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        jitter: Add randomness to prevent thundering herd
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @retry_with_backoff(max_attempts=5, base_delay=2.0)
        ... def upload_to_gcs(file_path):
        ...     # May fail transiently due to network issues
        ...     return client.upload(file_path)
        
        >>> @retry_with_backoff(
        ...     max_attempts=3,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
        ... def call_api():
        ...     return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper function with retry logic."""
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_attempts):
                try:
                    # Log attempt (first attempt is not a retry)
                    if attempt == 0:
                        logger.debug(f"Executing {func.__name__}")
                    else:
                        logger.info(
                            f"Retry attempt {attempt}/{max_attempts - 1} "
                            f"for {func.__name__}"
                        )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Success - log if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    
                    return result
                
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we have more attempts
                    if attempt < max_attempts - 1:
                        # Calculate delay
                        delay = calculate_backoff_delay(
                            attempt=attempt,
                            base_delay=base_delay,
                            max_delay=max_delay,
                            multiplier=backoff_multiplier,
                            jitter=jitter,
                        )
                        
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt + 1}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(attempt, e, delay)
                            except Exception as callback_error:
                                logger.error(
                                    f"Retry callback failed: {callback_error}"
                                )
                        
                        # Wait before retrying
                        time.sleep(delay)
                    else:
                        # No more attempts
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts. "
                            f"Last error: {e}"
                        )
            
            # All attempts exhausted - raise last exception
            if last_exception:
                raise last_exception
            
            # Should never reach here, but satisfy type checker
            raise RuntimeError(f"{func.__name__} failed without exception")
        
        return wrapper
    return decorator


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================

class CircuitState(str, Enum):
    """
    Circuit breaker states.
    
    States:
        CLOSED: Normal operation, requests pass through
        OPEN: Circuit is open, requests fail immediately
        HALF_OPEN: Testing if service recovered, limited requests
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    """
    Statistics for circuit breaker.
    
    Attributes:
        total_requests: Total number of requests
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        last_failure_time: Timestamp of last failure
        state_changes: Number of state transitions
    """
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    Prevents repeated calls to a failing service by "opening" the circuit
    after a threshold of failures. After a timeout, allows limited requests
    to test if service has recovered.
    
    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Circuit open, all requests fail immediately
        - HALF_OPEN: Testing recovery, limited requests allowed
    
    Example:
        >>> breaker = CircuitBreaker(
        ...     failure_threshold=5,
        ...     timeout=60,
        ...     expected_exception=ConnectionError
        ... )
        >>> 
        >>> @breaker
        ... def call_external_api():
        ...     return requests.get("https://api.example.com")
        >>> 
        >>> try:
        ...     result = call_external_api()
        ... except CircuitBreakerError:
        ...     print("Service is down, circuit is open")
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        half_open_max_attempts: int = 1,
    ) -> None:
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open)
            expected_exception: Exception type that triggers circuit
            half_open_max_attempts: Max attempts in half-open state
        """
        logger.info(
            f"Initializing CircuitBreaker "
            f"(threshold={failure_threshold}, timeout={timeout}s)"
        )
        
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.half_open_max_attempts = half_open_max_attempts
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_attempts = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        
        # Statistics
        self.stats = CircuitBreakerStats()
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator interface for circuit breaker.
        
        Args:
            func: Function to wrap with circuit breaker
        
        Returns:
            Wrapped function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(func, *args, **kwargs)
        
        return wrapper
    
    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function positional arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception if function fails
        """
        self.stats.total_requests += 1
        
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("Circuit transitioning from OPEN to HALF_OPEN")
                self._transition_to_half_open()
            else:
                # Circuit still open - fail fast
                logger.warning(f"Circuit is OPEN, failing fast for {func.__name__}")
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Success - record and potentially close circuit
            self._on_success()
            
            return result
        
        except self.expected_exception as e:
            # Expected failure - record and potentially open circuit
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.
        
        Returns:
            True if should transition to HALF_OPEN
        """
        if self.opened_at is None:
            return True
        
        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return elapsed >= self.timeout
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit from OPEN to HALF_OPEN."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_attempts = 0
        self.stats.state_changes += 1
        logger.info("Circuit state: HALF_OPEN (testing recovery)")
    
    def _on_success(self) -> None:
        """
        Handle successful request.
        
        In HALF_OPEN state, close circuit if recovery confirmed.
        In CLOSED state, just record success.
        """
        self.stats.successful_requests += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Recovery confirmed - close circuit
            logger.info("Service recovered, closing circuit")
            self._close_circuit()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug(
                    f"Resetting failure count from {self.failure_count} to 0"
                )
                self.failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """
        Handle failed request.
        
        Args:
            exception: Exception that occurred
        """
        self.stats.failed_requests += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.stats.last_failure_time = self.last_failure_time
        
        logger.warning(
            f"Circuit breaker recorded failure "
            f"({self.failure_count}/{self.failure_threshold}): {exception}"
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery - reopen circuit
            logger.warning("Recovery failed, reopening circuit")
            self._open_circuit()
        
        elif self.state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Failure threshold ({self.failure_threshold}) exceeded, "
                    f"opening circuit"
                )
                self._open_circuit()
    
    def _open_circuit(self) -> None:
        """Open circuit breaker (fail fast mode)."""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.now()
        self.stats.state_changes += 1
        logger.error(
            f"Circuit state: OPEN (will retry in {self.timeout}s)"
        )
    
    def _close_circuit(self) -> None:
        """Close circuit breaker (normal operation)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
        self.half_open_attempts = 0
        self.stats.state_changes += 1
        logger.info("Circuit state: CLOSED (normal operation)")
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("Manually resetting circuit breaker")
        self._close_circuit()
    
    def get_stats(self) -> CircuitBreakerStats:
        """
        Get circuit breaker statistics.
        
        Returns:
            CircuitBreakerStats object
        """
        return self.stats


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# ============================================================================
# Utility Functions
# ============================================================================

def is_transient_error(exception: Exception) -> bool:
    """
    Determine if exception is likely transient (retryable).
    
    Args:
        exception: Exception to check
    
    Returns:
        True if exception is likely transient
    
    Note:
        Common transient errors include:
        - Connection errors
        - Timeout errors
        - Rate limit errors (429)
        - Server errors (500, 502, 503, 504)
    """
    # Common transient exception types
    transient_types = (
        ConnectionError,
        TimeoutError,
        OSError,  # Network-related
    )
    
    if isinstance(exception, transient_types):
        return True
    
    # Check for HTTP status codes (if using requests library)
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        status_code = exception.response.status_code
        transient_codes = {429, 500, 502, 503, 504}
        if status_code in transient_codes:
            return True
    
    # Check for GCP-specific transient errors
    exception_str = str(exception).lower()
    transient_keywords = [
        "timeout",
        "connection",
        "temporary",
        "unavailable",
        "rate limit",
        "quota",
    ]
    
    return any(keyword in exception_str for keyword in transient_keywords)


# ============================================================================
# CLI Entry Point (for testing)
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test retry logic and circuit breaker"
    )
    parser.add_argument(
        "--test",
        choices=["retry", "circuit-breaker"],
        required=True,
        help="Test type to run",
    )
    
    args = parser.parse_args()
    
    if args.test == "retry":
        # Test retry logic
        attempt_counter = [0]
        
        @retry_with_backoff(max_attempts=5, base_delay=0.5, jitter=False)
        def flaky_function():
            """Function that fails first 3 times."""
            attempt_counter[0] += 1
            if attempt_counter[0] < 4:
                raise ConnectionError(f"Attempt {attempt_counter[0]} failed")
            return f"Success on attempt {attempt_counter[0]}"
        
        try:
            result = flaky_function()
            print(f"✓ {result}")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    elif args.test == "circuit-breaker":
        # Test circuit breaker
        breaker = CircuitBreaker(failure_threshold=3, timeout=5)
        
        @breaker
        def failing_service():
            """Service that always fails."""
            raise ConnectionError("Service unavailable")
        
        # Trigger circuit breaker
        for i in range(10):
            try:
                failing_service()
            except (ConnectionError, CircuitBreakerError) as e:
                print(f"Attempt {i + 1}: {type(e).__name__}: {e}")
            time.sleep(0.5)
        
        # Show stats
        print(f"\nCircuit Breaker Stats:")
        print(f"  State: {breaker.state.value}")
        print(f"  Total requests: {breaker.stats.total_requests}")
        print(f"  Failed requests: {breaker.stats.failed_requests}")
        print(f"  State changes: {breaker.stats.state_changes}")
