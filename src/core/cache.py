import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class QueryCache:
    def __init__(self, cache_dir: str = ".cache", ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl_seconds
        self._memory_cache: Dict[str, Any] = {}
    
    def _get_key(self, query_type: str, params: dict) -> str:
        normalized = json.dumps(params, sort_keys=True, default=str)
        hash_val = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"{query_type}_{hash_val}"
    
    def get(self, query_type: str, params: dict) -> Optional[Any]:
        key = self._get_key(query_type, params)
        
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                logger.debug(f"[Cache] Memory hit for {key}")
                return entry["data"]
            else:
                del self._memory_cache[key]
        
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[Cache] Failed to read cache file {key}: {e}")
            return None
        
        if time.time() - cached["timestamp"] > self.ttl:
            logger.debug(f"[Cache] Expired entry for {key}")
            try:
                cache_file.unlink()
            except IOError:
                pass
            return None
        
        self._memory_cache[key] = cached
        logger.debug(f"[Cache] File hit for {key}")
        print(f"💾 [Cache] Using cached {query_type} results")
        
        return cached["data"]
    
    def set(self, query_type: str, params: dict, data: Any) -> None:
        key = self._get_key(query_type, params)
        cache_file = self.cache_dir / f"{key}.json"
        
        entry = {
            "timestamp": time.time(),
            "query_type": query_type,
            "params": params,
            "data": data
        }
        
        self._memory_cache[key] = entry
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, default=str)
            logger.debug(f"[Cache] Stored {key}")
        except IOError as e:
            logger.warning(f"[Cache] Failed to write cache file {key}: {e}")
    
    def invalidate(self, query_type: Optional[str] = None) -> int:
        count = 0
        
        if query_type:
            keys_to_remove = [k for k in self._memory_cache if k.startswith(query_type)]
            for k in keys_to_remove:
                del self._memory_cache[k]
                count += 1
        else:
            count += len(self._memory_cache)
            self._memory_cache.clear()
        
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
                try:
                    cache_file.unlink()
                    count += 1
                except IOError:
                    pass
        
        logger.info(f"[Cache] Cleaned up {count} expired entries")
        return count


_cache: Optional[QueryCache] = None


def get_cache(ttl_seconds: int = 3600) -> QueryCache:
    global _cache
    if _cache is None:
        _cache = QueryCache(ttl_seconds=ttl_seconds)
    return _cache
