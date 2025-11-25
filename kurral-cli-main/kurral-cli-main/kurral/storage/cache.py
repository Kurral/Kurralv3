"""
Cache backend for storing tool call responses
"""

import json
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
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


class SQLiteCache(CacheBackend):
    """
    SQLite-based cache for local development and testing

    For production, use Redis or DynamoDB
    """

    def __init__(self, db_path: str | Path = ":memory:", ttl_seconds: int = 3600):
        """
        Initialize SQLite cache

        Args:
            db_path: Path to SQLite database file (':memory:' for in-memory)
            ttl_seconds: Time-to-live for cache entries
        """
        self.db_path = str(db_path)
        self.ttl_seconds = ttl_seconds
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self) -> None:
        """Create cache table if not exists"""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
            """
        )
        self.conn.commit()

    def prime(self, cache_key: str, response: dict[str, Any]) -> None:
        """Pre-populate cache with a response"""
        now = int(time.time())
        expires_at = now + self.ttl_seconds

        response_json = json.dumps(response)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO cache (cache_key, response, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (cache_key, response_json, now, expires_at),
        )
        self.conn.commit()

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached response"""
        now = int(time.time())

        cursor = self.conn.execute(
            """
            SELECT response, expires_at FROM cache
            WHERE cache_key = ?
            """,
            (cache_key,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        response_json, expires_at = row

        # Check if expired
        if expires_at < now:
            self.evict(cache_key)
            return None

        return json.loads(response_json)

    def evict(self, cache_key: str) -> None:
        """Remove cache entry"""
        self.conn.execute(
            """
            DELETE FROM cache WHERE cache_key = ?
            """,
            (cache_key,),
        )
        self.conn.commit()

    def clear(self) -> None:
        """Clear all cache entries"""
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def cleanup_expired(self) -> int:
        """
        Remove expired entries

        Returns:
            Number of entries removed
        """
        now = int(time.time())

        cursor = self.conn.execute(
            """
            DELETE FROM cache WHERE expires_at < ?
            """,
            (now,),
        )
        self.conn.commit()

        return cursor.rowcount

    def stats(self) -> dict[str, int]:
        """Get cache statistics"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM cache")
        total = cursor.fetchone()[0]

        now = int(time.time())
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM cache WHERE expires_at >= ?", (now,)
        )
        valid = cursor.fetchone()[0]

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
        }

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()

    def __enter__(self) -> "SQLiteCache":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self.close()


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

