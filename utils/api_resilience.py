"""
API Resilience Utilities

Provides retry with exponential backoff and fallback chain mechanisms
for robust external API calls.
"""

import time
import functools
from typing import TypeVar, Callable, Optional, Tuple, Any
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,)
):
    """
    Decorator for retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay cap in seconds
        exponential_base: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry on
    
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(RequestException, Timeout))
        def call_external_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[Retry] {func.__name__} attempt {attempt + 1}/{max_retries} "
                            f"failed: {e}. Retrying in {delay:.1f}s..."
                        )
                        print(f"⚠️ [Retry] Attempt {attempt + 1}/{max_retries} failed: {e}")
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
            
            logger.error(f"[Retry] {func.__name__} failed after {max_retries} retries")
            raise last_exception
        return wrapper
    return decorator


class FallbackChain:
    """
    Execute functions in sequence until one succeeds.
    
    Useful for trying multiple API providers or fallback data sources.
    
    Example:
        chain = FallbackChain(
            primary_api_call,
            backup_api_call,
            get_cached_data
        )
        result = chain.execute(destination="Paris", date="2025-01-01")
    """
    
    def __init__(self, *functions: Callable[..., T]):
        """
        Initialize with ordered list of fallback functions.
        
        Args:
            *functions: Callable functions to try in order
        """
        self.functions = functions
    
    def execute(self, *args, **kwargs) -> Optional[T]:
        """
        Execute functions in order until one succeeds.
        
        Returns:
            Result from first successful function, or None if all fail
        """
        for i, func in enumerate(self.functions):
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    if i > 0:
                        print(f"✅ [Fallback] Provider {i + 1} succeeded")
                    return result
            except Exception as e:
                logger.warning(f"[Fallback] Provider {i + 1} ({func.__name__}) failed: {e}")
                print(f"⚠️ [Fallback] Provider {i + 1} failed: {e}")
                continue
        
        logger.error("[Fallback] All providers failed")
        return None


def with_timeout(timeout_seconds: float):
    """
    Decorator to add a timeout to a function (works on Windows via threading).
    
    Note: This uses threading and may not interrupt I/O-bound operations cleanly.
    For production, consider using asyncio with proper timeout handling.
    
    Args:
        timeout_seconds: Maximum time to wait for function completion
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    raise TimeoutError(
                        f"{func.__name__} timed out after {timeout_seconds}s"
                    )
        return wrapper
    return decorator


def safe_api_call(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    error_message: str = "API call failed",
    **kwargs
) -> Tuple[Optional[T], Optional[str]]:
    """
    Wrapper for safe API calls with error handling.
    
    Returns:
        Tuple of (result, error_message). If successful, error_message is None.
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        return default, str(e)
