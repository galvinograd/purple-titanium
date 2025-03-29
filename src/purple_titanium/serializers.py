"""Serializers for Purple Titanium.

This module provides serializers that convert Python objects to and from bytes,
independent of the persistence backend.
"""

import json
import pickle
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Serializer(Protocol):
    """Protocol defining the interface for serializers."""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes.
        
        Args:
            data: The data to serialize.
            
        Returns:
            The serialized data as bytes.
            
        Raises:
            SerializationError: If serialization fails.
        """
        ...
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from bytes.
        
        Args:
            data: The bytes to deserialize.
            
        Returns:
            The deserialized data.
            
        Raises:
            SerializationError: If deserialization fails.
        """
        ...


class SerializationError(Exception):
    """Raised when serialization or deserialization fails."""
    pass


class JSONSerializer:
    """JSON serializer for task outputs."""

    def _default(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects to JSON-serializable ones.

        Args:
            obj: The object to convert.

        Returns:
            A JSON-serializable object.

        Raises:
            TypeError: If the object cannot be converted.
        """
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes.
        
        Args:
            data: The data to serialize.
            
        Returns:
            The serialized data as bytes.
            
        Raises:
            SerializationError: If data is not JSON-serializable.
        """
        try:
            return json.dumps(data, default=self._default).encode('utf-8')
        except (TypeError, ValueError) as e:
            raise SerializationError(f"Failed to serialize to JSON: {e}")
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from JSON bytes.
        
        Args:
            data: The bytes to deserialize.
            
        Returns:
            The deserialized data.
            
        Raises:
            SerializationError: If data is not valid JSON.
        """
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SerializationError(f"Failed to deserialize from JSON: {e}")


class PickleSerializer:
    """Pickle serializer that converts to/from bytes."""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to pickle bytes.
        
        Args:
            data: The data to serialize.
            
        Returns:
            The serialized data as bytes.
            
        Raises:
            SerializationError: If data cannot be pickled.
        """
        try:
            return pickle.dumps(data)
        except pickle.PickleError as e:
            raise SerializationError(f"Failed to serialize to pickle: {e}")
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from pickle bytes.
        
        Args:
            data: The bytes to deserialize.
            
        Returns:
            The deserialized data.
            
        Raises:
            SerializationError: If data is not valid pickle.
        """
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError as e:
            raise SerializationError(f"Failed to deserialize from pickle: {e}") 