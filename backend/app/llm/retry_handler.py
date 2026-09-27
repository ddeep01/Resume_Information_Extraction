import time
import logging
from typing import Callable, TypeVar, Any, Optional
from backend.app.config import settings

logger = logging.getLogger("RetryHandler")

T = TypeVar('T')

class RetryHandler:
    """
    Retry logic for transient LLM calls, JSON parsing failures, and timeouts.
    """
    def __init__(self, max_retries: Optional[int] = None, delay: Optional[float] = None):
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        self.delay = delay if delay is not None else settings.LLM_RETRY_DELAY

    def execute_with_retry(
        self,
        func: Callable[[], T],
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        on_timeout: Optional[Callable[[Exception, int], Optional[T]]] = None
    ) -> T:
        """
        Execute function func with retries.
        """
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                err_msg = str(e).lower()
                is_timeout = "timeout" in err_msg or "timed out" in err_msg or "readtimeout" in err_msg
                
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed: {e}")
                
                if is_timeout and on_timeout:
                    try:
                        timeout_result = on_timeout(e, attempt)
                        if timeout_result is not None:
                            return timeout_result
                    except Exception as sub_e:
                        logger.error(f"Timeout handler error: {sub_e}")
                        last_exception = sub_e

                if on_retry:
                    on_retry(e, attempt)

                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)

        raise RuntimeError(f"Operation failed after {self.max_retries} attempts: {last_exception}")
