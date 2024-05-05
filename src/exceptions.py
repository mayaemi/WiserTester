from asyncio import iscoroutinefunction
from functools import wraps
from typing import Any, Callable, Union
from src.configure import LOGGER


def handle_exceptions(log_message: str, should_raise: bool = True, log_level: str = "error") -> Callable:
    """
    A decorator that handles exceptions by logging and optionally re-raising them.
    Supports both synchronous and asynchronous functions.

    Args:
    log_message (str): Message to log on exception.
    should_raise (bool): If True, re-raises the exception after logging.
    log_level (str): Logging level ('info', 'warning', 'error').

    Returns:
    Callable: A wrapped function that handles exceptions as described.
    """

    def decorator(func: Callable) -> Callable:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    getattr(LOGGER, log_level)(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    getattr(LOGGER, log_level)(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return sync_wrapper

    return decorator
