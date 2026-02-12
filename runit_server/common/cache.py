"""
Caching utilities for runit-server with TTL support.
"""
import time
import hashlib
import json
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from threading import Lock
from functools import wraps

T = TypeVar('T')


class CacheItem:
    """Represents a cached item with TTL."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class MemoryCache:
    """Thread-safe in-memory cache with TTL support."""
    
    _instance = None
    _lock = Lock()
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, CacheItem] = {}
        self._cache_lock = Lock()
        self._default_ttl = default_ttl
    
    def __new__(cls, default_ttl: int = 300):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._cache = {}
                    instance._cache_lock = Lock()
                    instance._default_ttl = default_ttl
                    cls._instance = instance
        return cls._instance
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a unique cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._cache_lock:
            item = self._cache.get(key)
            if item is None:
                return None
            if item.is_expired():
                del self._cache[key]
                return None
            return item.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl if ttl is not None else self._default_ttl
        with self._cache_lock:
            self._cache[key] = CacheItem(value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._cache_lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove all expired items. Returns count of removed items."""
        count = 0
        with self._cache_lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
                count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total = len(self._cache)
            expired = sum(1 for v in self._cache.values() if v.is_expired())
            return {
                "total_items": total,
                "active_items": total - expired,
                "expired_items": expired
            }


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key
    """
    cache = MemoryCache()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache_key = f"{key_prefix}:{func.__name__}:{cache._generate_key(*args, **kwargs)}"
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        return wrapper
    
    return decorator


def cached_async(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache async function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key
    """
    cache = MemoryCache()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache_key = f"{key_prefix}:{func.__name__}:{cache._generate_key(*args, **kwargs)}"
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        return wrapper
    
    return decorator


cache = MemoryCache()
