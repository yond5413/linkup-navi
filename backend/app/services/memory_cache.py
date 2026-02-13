"""Memory query caching service for vector retrieval optimization."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import asyncio
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """Cache entry with TTL and metadata."""

    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # 5 minutes default

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry


class MemoryQueryCache:
    """
    Tiered caching for vector memory queries.

    Features:
    - In-memory caching with configurable TTL
    - Query normalization for cache keys
    - Cache statistics tracking
    - Optional bypass for critical queries
    """

    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl_seconds
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "bypasses": 0}
        self._lock = asyncio.Lock()

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for consistent cache keys.

        - Lowercase
        - Remove extra whitespace
        - Trim to first 200 chars for fuzzy matching
        """
        normalized = query.lower().strip()
        normalized = " ".join(normalized.split())  # Remove extra whitespace
        return normalized[:200]

    def _generate_cache_key(self, query: str, top_k: int) -> str:
        """Generate cache key from query and parameters."""
        normalized = self._normalize_query(query)
        key_data = f"{normalized}:{top_k}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, query: str, top_k: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.

        Args:
            query: The search query
            top_k: Number of results requested

        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._generate_cache_key(query, top_k)

        async with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                del self._cache[cache_key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return {
                **entry.data,
                "_cache_hit": True,
                "_cached_at": entry.created_at.isoformat(),
            }

    async def set(
        self, query: str, data: Dict[str, Any], top_k: int = 5, ttl_seconds: int = None
    ):
        """
        Cache query results.

        Args:
            query: The search query
            data: Results to cache
            top_k: Number of results
            ttl_seconds: Custom TTL (uses default if None)
        """
        cache_key = self._generate_cache_key(query, top_k)
        ttl = ttl_seconds or self._default_ttl

        # Remove cache metadata before storing
        clean_data = {k: v for k, v in data.items() if not k.startswith("_cache")}

        async with self._lock:
            self._cache[cache_key] = CacheEntry(data=clean_data, ttl_seconds=ttl)

    async def get_or_query(
        self,
        query: str,
        query_func,
        top_k: int = 5,
        use_cache: bool = True,
        ttl_seconds: int = None,
    ) -> Dict[str, Any]:
        """
        Get from cache or execute query function.

        This is the main interface for cached queries.

        Args:
            query: The search query
            query_func: Async function to call if cache miss
            top_k: Number of results
            use_cache: Whether to use caching (default True)
            ttl_seconds: Custom TTL

        Returns:
            Query results with cache metadata
        """
        if not use_cache:
            self._stats["bypasses"] += 1
            results = await query_func(query, top_k)
            return {**results, "_cache_hit": False, "_source": "query"}

        # Try cache first
        cached = await self.get(query, top_k)
        if cached:
            return {**cached, "_source": "cache"}

        # Cache miss - execute query
        results = await query_func(query, top_k)

        # Store in cache
        await self.set(query, results, top_k, ttl_seconds)

        return {**results, "_cache_hit": False, "_source": "query"}

    async def invalidate(self, query_pattern: str = None):
        """
        Invalidate cache entries.

        Args:
            query_pattern: If provided, only invalidate matching queries
        """
        async with self._lock:
            if query_pattern is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._stats["evictions"] += count
            else:
                # Clear matching queries
                pattern = query_pattern.lower()
                to_remove = [
                    key
                    for key in self._cache.keys()
                    if pattern in self._cache[key].data.get("query", "").lower()
                ]
                for key in to_remove:
                    del self._cache[key]
                self._stats["evictions"] += len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 4),
            "total_entries": len(self._cache),
            "hit_rate_percent": round(hit_rate * 100, 2),
        }

    def clear_stats(self):
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "bypasses": 0}


# Singleton instance
_cache_instance: Optional[MemoryQueryCache] = None


def get_memory_query_cache() -> MemoryQueryCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryQueryCache()
    return _cache_instance


def reset_cache():
    """Reset the global cache (useful for testing)."""
    global _cache_instance
    _cache_instance = None
