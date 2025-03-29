"""Persistence backend implementations for Purple Titanium.

This module provides different persistence backends for storing task outputs,
including local filesystem, memory, and custom implementations.
"""

import json
from pathlib import Path
from typing import Any, Dict, Protocol, Union, runtime_checkable

JSONValue = Union[bool, int, float, str, list, dict, tuple, set, None]


@runtime_checkable
class PersistenceBackend(Protocol):
    """Protocol defining the interface for persistence backends."""
    
    def save(self, key: str, data: bytes) -> None:
        """Save data to persistence.
        
        Args:
            key: Unique identifier for the data.
            data: The data to save as bytes.
            
        Raises:
            RuntimeError: If saving fails.
        """
        ...
    
    def load(self, key: str) -> bytes:
        """Load data from persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Returns:
            The loaded data as bytes.
            
        Raises:
            FileNotFoundError: If the data doesn't exist.
            RuntimeError: If loading fails.
        """
        ...
    
    def exists(self, key: str) -> bool:
        """Check if data exists in persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Returns:
            True if the data exists, False otherwise.
        """
        ...
    
    def delete(self, key: str) -> None:
        """Delete data from persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Raises:
            RuntimeError: If deletion fails.
        """
        ...
    
    def list_keys(self) -> list[str]:
        """List all keys in persistence.
        
        Returns:
            List of all keys in persistence.
        """
        ...


class FileSystemPersistence:
    """Local filesystem persistence backend."""
    
    def __init__(self, base_dir: str):
        """Initialize the persistence backend.
        
        Args:
            base_dir: Base directory for persistence.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, key: str) -> Path:
        """Get the file path for a key.
        
        Args:
            key: Unique identifier for the data.
            
        Returns:
            Path object pointing to the persistence file.
        """
        return self.base_dir / f"{key}.bin"
    
    def _validate_data(self, data: Any) -> None:
        """Validate that data is JSON-serializable.
        
        Args:
            data: Data to validate.
            
        Raises:
            RuntimeError: If data is not JSON-serializable.
        """
        try:
            # Try to serialize to validate
            json.dumps(data)
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"Data is not JSON-serializable: {e}")
    
    def save(self, key: str, data: bytes) -> None:
        """Save data to persistence.
        
        Args:
            key: Unique identifier for the data.
            data: The data to save as bytes.
            
        Raises:
            RuntimeError: If saving fails.
        """
        path = self._get_path(key)
        try:
            with open(path, 'wb') as f:
                f.write(data)
        except OSError as e:
            raise RuntimeError(f"Failed to save data to {path}: {e}")
    
    def load(self, key: str) -> bytes:
        """Load data from persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Returns:
            The loaded data as bytes.
            
        Raises:
            FileNotFoundError: If the data doesn't exist.
            RuntimeError: If loading fails.
        """
        path = self._get_path(key)
        try:
            with open(path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"No data found for key: {key}")
        except OSError as e:
            raise RuntimeError(f"Failed to load data from {path}: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if data exists in persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Returns:
            True if the data exists, False otherwise.
        """
        return self._get_path(key).exists()
    
    def delete(self, key: str) -> None:
        """Delete data from persistence.
        
        Args:
            key: Unique identifier for the data.
            
        Raises:
            RuntimeError: If deletion fails.
        """
        path = self._get_path(key)
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            raise RuntimeError(f"Failed to delete data at {path}: {e}")
    
    def list_keys(self) -> list[str]:
        """List all keys in persistence.
        
        Returns:
            List of all keys in persistence.
        """
        return [path.stem for path in self.base_dir.glob("*.bin")]


class InMemoryPersistence:
    """In-memory persistence backend."""

    def __init__(self) -> None:
        """Initialize the in-memory persistence backend."""
        self._data: Dict[str, bytes] = {}

    def save(self, data: bytes, key: str) -> None:
        """Save data to persistence.

        Args:
            data: The data to save as bytes.
            key: Unique identifier for the data.

        Raises:
            RuntimeError: If data is not bytes.
        """
        if not isinstance(data, bytes):
            raise RuntimeError("Data must be bytes")
        self._data[key] = data

    def load(self, key: str) -> bytes:
        """Load data from persistence.

        Args:
            key: Unique identifier for the data.

        Returns:
            The loaded data as bytes.

        Raises:
            FileNotFoundError: If the data doesn't exist.
        """
        if key not in self._data:
            raise FileNotFoundError(f"No data found for key: {key}")
        return self._data[key]

    def exists(self, key: str) -> bool:
        """Check if data exists in persistence.

        Args:
            key: Unique identifier for the data.

        Returns:
            True if the data exists, False otherwise.
        """
        return key in self._data

    def invalidate(self, key: str) -> None:
        """Remove data from persistence.

        Args:
            key: Unique identifier for the data.
        """
        if key in self._data:
            del self._data[key]

    def invalidate_all(self) -> None:
        """Remove all data from persistence."""
        self._data.clear()

    def list_keys(self) -> list[str]:
        """List all keys in persistence.
        
        Returns:
            List of all keys in persistence.
        """
        return list(self._data.keys()) 