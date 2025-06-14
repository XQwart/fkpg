"""Centralized cache management system for the game."""
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple, List, Set
from collections import OrderedDict
from weakref import WeakValueDictionary
import time
import gc
import pygame as pg


class CachePolicy:
    """Cache eviction policies."""
    
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


class CacheEntry:
    """Single cache entry with metadata."""
    
    def __init__(self, key: Any, value: Any, ttl: Optional[float] = None):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl = ttl
        self.size = self._estimate_size(value)
    
    def access(self) -> Any:
        """Access the cached value and update metadata."""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.value
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value in bytes."""
        if isinstance(value, pg.Surface):
            return value.get_width() * value.get_height() * 4  # RGBA
        elif isinstance(value, pg.sprite.Group):
            return len(value) * 64  # Rough estimate per sprite
        elif isinstance(value, (list, tuple)):
            return sum(self._estimate_size(item) for item in value)
        elif isinstance(value, dict):
            return sum(self._estimate_size(k) + self._estimate_size(v) 
                      for k, v in value.items())
        else:
            return 64  # Default size estimate


class Cache:
    """Generic cache with configurable policy and limits."""
    
    def __init__(
        self,
        name: str,
        max_size: int = 100,
        max_memory: int = 100 * 1024 * 1024,  # 100MB default
        policy: str = CachePolicy.LRU,
        ttl: Optional[float] = None
    ):
        self.name = name
        self.max_size = max_size
        self.max_memory = max_memory
        self.policy = policy
        self.default_ttl = ttl
        
        self._entries: OrderedDict[Any, CacheEntry] = OrderedDict()
        self._total_memory = 0
        self._hits = 0
        self._misses = 0
    
    def get(self, key: Any, default: Any = None) -> Any:
        """Get value from cache."""
        entry = self._entries.get(key)
        
        if entry is None:
            self._misses += 1
            return default
        
        if entry.is_expired():
            self.remove(key)
            self._misses += 1
            return default
        
        self._hits += 1
        value = entry.access()
        
        # Move to end for LRU
        if self.policy == CachePolicy.LRU:
            self._entries.move_to_end(key)
        
        return value
    
    def put(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in cache."""
        # Remove old entry if exists
        if key in self._entries:
            self.remove(key)
        
        # Create new entry
        entry = CacheEntry(key, value, ttl or self.default_ttl)
        
        # Check if we need to evict
        self._evict_if_needed(entry.size)
        
        # Add entry
        self._entries[key] = entry
        self._total_memory += entry.size
    
    def remove(self, key: Any) -> bool:
        """Remove entry from cache."""
        entry = self._entries.pop(key, None)
        if entry:
            self._total_memory -= entry.size
            return True
        return False
    
    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._total_memory = 0
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "name": self.name,
            "size": len(self._entries),
            "memory": self._total_memory,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "policy": self.policy
        }
    
    def _evict_if_needed(self, new_size: int) -> None:
        """Evict entries if cache limits exceeded."""
        # Evict expired entries first
        self._evict_expired()
        
        # Evict by size limit
        while len(self._entries) >= self.max_size:
            self._evict_one()
        
        # Evict by memory limit
        while self._total_memory + new_size > self.max_memory:
            if not self._evict_one():
                break
    
    def _evict_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._entries.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            self.remove(key)
    
    def _evict_one(self) -> bool:
        """Evict one entry based on policy."""
        if not self._entries:
            return False
        
        if self.policy == CachePolicy.LRU:
            # Remove least recently used (first item)
            key = next(iter(self._entries))
        elif self.policy == CachePolicy.LFU:
            # Remove least frequently used
            key = min(self._entries.keys(), 
                     key=lambda k: self._entries[k].access_count)
        elif self.policy == CachePolicy.FIFO:
            # Remove oldest (first item)
            key = next(iter(self._entries))
        else:  # TTL or default
            # Remove oldest
            key = next(iter(self._entries))
        
        return self.remove(key)


class CacheManager:
    """Centralized cache manager for the entire game."""
    
    _instance: Optional[CacheManager] = None
    
    def __new__(cls) -> CacheManager:
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize cache manager."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._caches: Dict[str, Cache] = {}
        
        # Create default caches
        self._create_default_caches()
        
        # Memory monitoring
        self._last_gc_time = time.time()
        self._gc_interval = 60.0  # Run GC every minute
    
    def _create_default_caches(self) -> None:
        """Create default game caches."""
        # Tile rendering cache
        self.create_cache(
            "tile_surfaces",
            max_size=200,
            max_memory=50 * 1024 * 1024,  # 50MB
            policy=CachePolicy.LRU
        )
        
        # Animation frame cache
        self.create_cache(
            "animation_frames",
            max_size=100,
            max_memory=30 * 1024 * 1024,  # 30MB
            policy=CachePolicy.LFU
        )
        
        # Collision groups cache
        self.create_cache(
            "collision_groups",
            max_size=10,
            max_memory=10 * 1024 * 1024,  # 10MB
            policy=CachePolicy.LRU,
            ttl=5.0  # Expire after 5 seconds
        )
        
        # Level data cache
        self.create_cache(
            "level_data",
            max_size=5,
            max_memory=20 * 1024 * 1024,  # 20MB
            policy=CachePolicy.LRU
        )
        
        # Sound effects cache
        self.create_cache(
            "sounds",
            max_size=50,
            max_memory=20 * 1024 * 1024,  # 20MB
            policy=CachePolicy.LFU
        )
    
    def create_cache(
        self,
        name: str,
        max_size: int = 100,
        max_memory: int = 100 * 1024 * 1024,
        policy: str = CachePolicy.LRU,
        ttl: Optional[float] = None
    ) -> Cache:
        """Create a new cache."""
        cache = Cache(name, max_size, max_memory, policy, ttl)
        self._caches[name] = cache
        return cache
    
    def get_cache(self, name: str) -> Optional[Cache]:
        """Get cache by name."""
        return self._caches.get(name)
    
    def get(self, cache_name: str, key: Any, default: Any = None) -> Any:
        """Get value from named cache."""
        cache = self._caches.get(cache_name)
        if cache:
            return cache.get(key, default)
        return default
    
    def put(self, cache_name: str, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in named cache."""
        cache = self._caches.get(cache_name)
        if cache:
            cache.put(key, value, ttl)
    
    def clear_cache(self, name: str) -> None:
        """Clear specific cache."""
        cache = self._caches.get(name)
        if cache:
            cache.clear()
    
    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self._caches.values():
            cache.clear()
    
    def get_total_memory(self) -> int:
        """Get total memory used by all caches."""
        return sum(cache._total_memory for cache in self._caches.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        return {
            "total_memory": self.get_total_memory(),
            "cache_count": len(self._caches),
            "caches": {
                name: cache.get_stats() 
                for name, cache in self._caches.items()
            }
        }
    
    def update(self) -> None:
        """Update cache manager (garbage collection, etc)."""
        current_time = time.time()
        
        # Periodic garbage collection
        if current_time - self._last_gc_time > self._gc_interval:
            self._run_garbage_collection()
            self._last_gc_time = current_time
    
    def _run_garbage_collection(self) -> None:
        """Run garbage collection and cache cleanup."""
        # Clean up expired entries in all caches
        for cache in self._caches.values():
            cache._evict_expired()
        
        # Force Python garbage collection if memory usage is high
        total_memory = self.get_total_memory()
        if total_memory > 200 * 1024 * 1024:  # 200MB threshold
            gc.collect()
    
    def shutdown(self) -> None:
        """Shutdown cache manager and free resources."""
        self.clear_all()
        self._caches.clear()


# Global instance getter
def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return CacheManager()