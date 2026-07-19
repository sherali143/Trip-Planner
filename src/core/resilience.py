import time
import functools
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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
    def __init__(self, *functions: Callable[..., T]):
        self.functions = functions
    
    def execute(self, *args, **kwargs) -> Optional[T]:
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
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        return default, str(e)
