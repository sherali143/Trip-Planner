"""
Query Cache Manager

Provides file-based caching for API responses with TTL-based expiration.
Reduces redundant API calls for similar searches.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class QueryCache:
    """
    Simple file-based cache for API responses.
    
    Features:
    - Content-based cache keys (query fingerprinting)
    - TTL-based expiration
    - Automatic cleanup of stale entries
    
    Example:
        cache = QueryCache(ttl_seconds=3600)  # 1 hour cache
        
        # Check cache first
        result = cache.get("flights", {"origin": "NYC", "dest": "LON"})
        if result is None:
            result = call_flight_api(...)
            cache.set("flights", {"origin": "NYC", "dest": "LON"}, result)
    """
    
    def __init__(self, cache_dir: str = ".cache", ttl_seconds: int = 3600):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live for cached entries (default 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl_seconds
        self._memory_cache: Dict[str, Any] = {}  # In-memory cache for speed
    
    def _get_key(self, query_type: str, params: dict) -> str:
        """
        Generate cache key from query parameters.
        
        Uses MD5 hash of normalized JSON for consistent keys.
        """
        # Sort keys for consistent hashing
        normalized = json.dumps(params, sort_keys=True, default=str)
        hash_val = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"{query_type}_{hash_val}"
    
    def get(self, query_type: str, params: dict) -> Optional[Any]:
        """
        Retrieve cached result if valid.
        
        Args:
            query_type: Type of query (e.g., "flights", "hotels")
            params: Query parameters used for cache key
        
        Returns:
            Cached data if valid, None if not found or expired
        """
        key = self._get_key(query_type, params)
        
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                logger.debug(f"[Cache] Memory hit for {key}")
                return entry["data"]
            else:
                del self._memory_cache[key]
        
        # Check file cache
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[Cache] Failed to read cache file {key}: {e}")
            return None
        
        # Check expiration
        if time.time() - cached["timestamp"] > self.ttl:
            logger.debug(f"[Cache] Expired entry for {key}")
            try:
                cache_file.unlink()
            except IOError:
                pass
            return None
        
        # Populate memory cache
        self._memory_cache[key] = cached
        logger.debug(f"[Cache] File hit for {key}")
        print(f"💾 [Cache] Using cached {query_type} results")
        
        return cached["data"]
    
    def set(self, query_type: str, params: dict, data: Any) -> None:
        """
        Store result in cache.
        
        Args:
            query_type: Type of query
            params: Query parameters used for cache key
            data: Data to cache
        """
        key = self._get_key(query_type, params)
        cache_file = self.cache_dir / f"{key}.json"
        
        entry = {
            "timestamp": time.time(),
            "query_type": query_type,
            "params": params,
            "data": data
        }
        
        # Store in memory
        self._memory_cache[key] = entry
        
        # Store to file
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, default=str)
            logger.debug(f"[Cache] Stored {key}")
        except IOError as e:
            logger.warning(f"[Cache] Failed to write cache file {key}: {e}")
    
    def invalidate(self, query_type: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            query_type: If provided, only invalidate entries of this type.
                       If None, invalidate all entries.
        
        Returns:
            Number of entries invalidated
        """
        count = 0
        
        # Clear memory cache
        if query_type:
            keys_to_remove = [k for k in self._memory_cache if k.startswith(query_type)]
            for k in keys_to_remove:
                del self._memory_cache[k]
                count += 1
        else:
            count += len(self._memory_cache)
            self._memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            if query_type is None or cache_file.name.startswith(query_type):
                try:
                    cache_file.unlink()
                    count += 1
                except IOError:
                    pass
        
        logger.info(f"[Cache] Invalidated {count} entries")
        return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries removed
        """
        count = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                
                if current_time - cached["timestamp"] > self.ttl:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, IOError, KeyError):
                # Remove corrupted files
                try:
                    cache_file.unlink()
                    count += 1
                except IOError:
                    pass
        
        logger.info(f"[Cache] Cleaned up {count} expired entries")
        return count


# Global cache instance
_cache: Optional[QueryCache] = None


def get_cache(ttl_seconds: int = 3600) -> QueryCache:
    """
    Get the global cache instance.
    
    Args:
        ttl_seconds: TTL for cache entries (only used on first call)
    
    Returns:
        Global QueryCache instance
    """
    global _cache
    if _cache is None:
        _cache = QueryCache(ttl_seconds=ttl_seconds)
    return _cache
