"""
Simple cache backend for tool call responses
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    def prime(self, cache_key: str, response: dict[str, Any]) -> None:
        """Pre-populate cache with a response"""
        pass

    @abstractmethod
    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached response"""
        pass

    @abstractmethod
    def evict(self, cache_key: str) -> None:
        """Remove cache entry"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""
        pass


class MemoryCache(CacheBackend):
    """Simple in-memory cache for testing"""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize memory cache"""
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, tuple[dict[str, Any], int]] = {}

    def prime(self, cache_key: str, response: dict[str, Any]) -> None:
        """Pre-populate cache"""
        expires_at = int(time.time()) + self.ttl_seconds
        self.cache[cache_key] = (response, expires_at)

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached response"""
        if cache_key not in self.cache:
            return None

        response, expires_at = self.cache[cache_key]

        # Check expiration
        if expires_at < int(time.time()):
            del self.cache[cache_key]
            return None

        return response

    def evict(self, cache_key: str) -> None:
        """Remove cache entry"""
        self.cache.pop(cache_key, None)

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()

