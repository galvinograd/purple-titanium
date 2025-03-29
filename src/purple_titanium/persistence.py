"""Output persistence module for Purple Titanium.

This module provides functionality for persisting task outputs,
enabling caching across program runs and workflow resumption.
"""

from typing import Any, Optional, Union

from .persistence_backends import PersistenceBackend
from .serializers import SerializationError, Serializer


class OutputPersistence:
    """Handles persistence of task outputs.
    
    This class provides methods to save, load, and manage task outputs
    using a configurable persistence backend.
    """
    
    def __init__(
        self,
        backend: PersistenceBackend,
        serializer: Serializer,
    ):
        """Initialize the persistence system.
        
        Args:
            backend: The persistence backend to use.
            serializer: The serializer to use.
        """
        self._backend = backend
        self._serializer = serializer
    
    def save(self, data: Any, key: Union[str, int]) -> None:
        """Save task output to persistence.
        
        Args:
            data: The data to save.
            key: The unique identifier for the output.
            
        Raises:
            SerializationError: If the output cannot be serialized.
            RuntimeError: If there are file system errors.
        """
        try:
            if isinstance(key, int):
                key = str(key)
            data = self._serializer.serialize(data)
            self._backend.save(
                key=key,
                data=data,
            )
        except (SerializationError, RuntimeError) as e:
            raise RuntimeError(f"Failed to save output: {e}")
    
    def load(self, cache_key: str) -> Any:
        """Load task output from persistence.
        
        Args:
            cache_key: The unique identifier for the output.
            
        Returns:
            The loaded output.
            
        Raises:
            FileNotFoundError: If the output doesn't exist in the cache.
            SerializationError: If the cache file is corrupted.
            RuntimeError: If there are file system errors.
        """
        try:
            if isinstance(cache_key, int):
                cache_key = str(cache_key)
            data = self._backend.load(cache_key)
            return self._serializer.deserialize(data)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"No cached output found for key: {cache_key}")
        except (SerializationError, RuntimeError) as e:
            raise RuntimeError(f"Failed to load output: {e}")
    
    def exists(self, cache_key: Union[str, int]) -> bool:
        """Check if output exists in cache.
        
        Args:
            cache_key: The unique identifier for the output.
            
        Returns:
            True if the output exists in the cache, False otherwise.
        """
        if isinstance(cache_key, int):
            cache_key = str(cache_key)
        return self._backend.exists(cache_key)
    
    def invalidate(self, cache_key: Optional[str] = None) -> None:
        """Invalidate specific or all cached outputs.
        
        Args:
            cache_key: Optional specific cache key to invalidate.
                      If None, invalidates all cached outputs.
        """
        if cache_key is None:
            # Delete all cache entries
            for key in self._backend.list_keys():
                try:
                    self._backend.delete(key)
                except RuntimeError:
                    pass
        else:
            # Delete specific cache entry
            try:
                self._backend.delete(cache_key)
            except RuntimeError:
                pass 