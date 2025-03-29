"""Tests for the output persistence module."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from purple_titanium.persistence import OutputPersistence
from purple_titanium.persistence_backends import FileSystemPersistence, InMemoryPersistence
from purple_titanium.serializers import JSONSerializer, PickleSerializer


@dataclass
class CustomClass:
    """Test class for pickle serialization."""
    value: int

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CustomClass):
            return False
        return self.value == other.value


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def filesystem_persistence(temp_cache_dir):
    """Create a FileSystemPersistence instance with a temporary directory."""
    return FileSystemPersistence(temp_cache_dir)


@pytest.fixture
def persistence_with_filesystem(temp_cache_dir):
    """Create an OutputPersistence instance with filesystem backend."""
    return OutputPersistence(
        backend=FileSystemPersistence(temp_cache_dir),
        serializer=JSONSerializer()
    )


@pytest.fixture
def persistence_with_memory():
    """Create an OutputPersistence instance with in-memory backend."""
    return OutputPersistence(
        backend=InMemoryPersistence(),
        serializer=JSONSerializer()
    )


def test_save_and_load_json(persistence_with_filesystem):
    """Test saving and loading task outputs with JSON serializer."""
    test_output = {"result": 42}
    cache_key = "test_task_1"
    
    # Save the output
    persistence_with_filesystem.save(test_output, cache_key)
    
    # Load the output
    loaded_output = persistence_with_filesystem.load(cache_key)
    assert loaded_output == test_output


def test_save_and_load_pickle(persistence_with_filesystem):
    """Test saving and loading task outputs with pickle serializer."""
    # Create persistence with pickle serializer
    persistence = OutputPersistence(
        backend=FileSystemPersistence(persistence_with_filesystem._backend.base_dir),
        serializer=PickleSerializer()
    )
    
    test_output = CustomClass(42)
    cache_key = "test_task_2"
    
    # Save the output
    persistence.save(test_output, cache_key)
    
    # Load the output
    loaded_output = persistence.load(cache_key)
    assert loaded_output == test_output


def test_invalid_data(persistence_with_filesystem):
    """Test handling of invalid data."""
    class NonSerializable:
        pass
    
    cache_key = "test_task"
    test_output = NonSerializable()
    
    # Attempting to save non-serializable data should raise RuntimeError
    with pytest.raises(RuntimeError):
        persistence_with_filesystem.save(test_output, cache_key)
    
    # Verify no file was created
    assert not persistence_with_filesystem.exists(cache_key)


def test_nonexistent_key(persistence_with_filesystem):
    """Test loading from a nonexistent key."""
    cache_key = "nonexistent_key"
    
    # Attempting to load from a nonexistent key should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        persistence_with_filesystem.load(cache_key)


def test_invalidate_specific_key(persistence_with_filesystem):
    """Test invalidating a specific cache key."""
    test_output = {"result": 42}
    cache_key = "test_task"
    
    # Save some data
    persistence_with_filesystem.save(test_output, cache_key)
    assert persistence_with_filesystem.exists(cache_key)
    
    # Invalidate the specific key
    persistence_with_filesystem.invalidate(cache_key)
    assert not persistence_with_filesystem.exists(cache_key)


def test_invalidate_all_keys(persistence_with_filesystem):
    """Test invalidating all cache keys."""
    # Save multiple outputs
    test_outputs = {
        "task1": {"result": 1},
        "task2": {"result": 2},
        "task3": {"result": 3}
    }
    
    for key, output in test_outputs.items():
        persistence_with_filesystem.save(output, key)
        assert persistence_with_filesystem.exists(key)
    
    # Invalidate all keys
    persistence_with_filesystem.invalidate()
    
    # Verify all keys are gone
    for key in test_outputs:
        assert not persistence_with_filesystem.exists(key)


def test_custom_persistence_backend():
    """Test using a custom persistence backend."""
    persistence_backend = InMemoryPersistence()
    persistence = OutputPersistence(
        backend=persistence_backend,
        serializer=JSONSerializer()
    )
    assert persistence._backend is persistence_backend
    
    # Test that it works with the custom persistence
    test_output = {"result": 42}
    cache_key = "test_task"
    
    persistence.save(test_output, cache_key)
    assert persistence.exists(cache_key)
    
    loaded_output = persistence.load(cache_key)
    assert loaded_output == test_output


def test_serializer_switch():
    """Test switching between different serializers."""
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        # First save with JSON serializer
        persistence_json = OutputPersistence(
            backend=FileSystemPersistence(temp_dir),
            serializer=JSONSerializer()
        )
        
        test_data = {"key": "value"}
        cache_key = "test_task"
        persistence_json.save(test_data, cache_key)
        
        # Then load with pickle serializer
        persistence_pickle = OutputPersistence(
            backend=FileSystemPersistence(temp_dir),
            serializer=PickleSerializer()
        )
        
        # Should fail because the data was serialized with JSON
        with pytest.raises(RuntimeError):
            persistence_pickle.load(cache_key) 