import functools
import time

# Simple cache storage
_cache = {}


def timed_cache(seconds=600):  # Default 10 minutes (600 seconds)
    """
    Decorator that caches the result of a function call for a specified duration.
    Default cache duration is 10 minutes (600 seconds).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique key based on function name and arguments
            key = str((func.__name__, args, frozenset(kwargs.items())))
            current_time = time.time()

            # Check if result is in cache and still valid
            if key in _cache:
                result, timestamp = _cache[key]
                if current_time - timestamp < seconds:
                    return result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            _cache[key] = (result, current_time)
            return result

        return wrapper

    return decorator


def clear_cache():
    """Clear the entire cache"""
    _cache.clear()
