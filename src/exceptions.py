import asyncio
from functools import wraps
from src.configure import LOGGER


def handle_exceptions(log_message, should_raise=True):
    # Error Handling Decorator
    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    LOGGER.error(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    LOGGER.error(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return sync_wrapper

    return decorator
