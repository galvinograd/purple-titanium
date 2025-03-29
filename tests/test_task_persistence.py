"""Tests for task persistence integration."""

import pytest

import purple_titanium as pt
from purple_titanium.decorators import task
from purple_titanium.persistence import OutputPersistence
from purple_titanium.persistence_backends import FileSystemPersistence, InMemoryPersistence
from purple_titanium.serializers import JSONSerializer
from purple_titanium.task import Task
from purple_titanium.task_state import TaskParameters
from purple_titanium.types import TaskStatus


# Test helper function
def add_numbers(x: int, y: int) -> int:
    """Test function that adds two numbers."""
    return x + y


@pytest.fixture
def persistence() -> OutputPersistence:
    """Create an OutputPersistence instance with InMemoryPersistence."""
    return OutputPersistence(
        backend=InMemoryPersistence(),
        serializer=JSONSerializer(),
    )


def test_task_caching(persistence):
    """Test that task outputs are properly cached."""
    # Create a task with persistence
    with pt.set_persistence(persistence):
        task = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
        )
    
    # First execution should compute the result
    result = task.output.resolve()
    assert result == 3
    assert task.status == TaskStatus.COMPLETED
    
    # Verify the result was cached
    cache_key = str(task.signature)
    assert persistence.exists(cache_key)
    assert persistence.load(cache_key) == 3
    
    # Create a new task with the same signature
    with pt.set_persistence(persistence):
        task2 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
        )
    
    # Second execution should use cached result
    result2 = task2.resolve()
    assert result2 == 3
    assert task2.status == TaskStatus.COMPLETED


def test_task_version_affects_cache(persistence):
    """Test that changing task version invalidates cache."""
    # Create a task with version 1
    with pt.set_persistence(persistence):
        task_v1 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
            task_version=1,
        )
        
        task_v2 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
            task_version=2,
        )
    
    # Execute and cache result
    result_v1 = task_v1.output.resolve()
    assert result_v1 == 3
    
    # Should recompute result due to different version
    result_v2 = task_v2.output.resolve()
    assert result_v2 == 3
    
    # Both results should be cached with different signatures
    assert persistence.exists(task_v1.signature)
    assert persistence.exists(task_v2.signature)
    assert task_v1.signature != task_v2.signature


def test_task_parameters_affect_cache(persistence):
    """Test that different parameters result in different cache entries."""
    # Create tasks with different parameters
    with pt.set_persistence(persistence):
        task1 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
        )
        
        task2 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 2, "y": 3}),
            persist=True,
        )
    
    # Execute both tasks
    result1 = task1.output.resolve()
    result2 = task2.output.resolve()
    
    assert result1 == 3
    assert result2 == 5
    
    # Both results should be cached with different signatures
    assert persistence.exists(str(task1.signature))
    assert persistence.exists(str(task2.signature))
    assert task1.signature != task2.signature


def test_cache_error_handling(tmp_path):
    """Test that cache errors are handled gracefully."""
    # Create a filesystem persistence with a temporary directory
    persistence_backend = FileSystemPersistence(str(tmp_path))
    persistence = OutputPersistence(
        backend=persistence_backend,
        serializer=JSONSerializer(),
    )
    
    # Create a task
    with pt.set_persistence(persistence):
        task = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
        )
    
    # Execute task to cache result
    result = task.output.resolve()
    assert result == 3
    
    # Corrupt the cache file
    cache_key = str(task.signature)
    cache_path = persistence_backend._get_path(cache_key)
    with open(cache_path, 'w') as f:
        f.write("invalid json data")
    
    # Create a new task with same signature
    with pt.set_persistence(persistence):
        task2 = Task(
            name="test_task",
            func=add_numbers,
            parameters=TaskParameters({"x": 1, "y": 2}),
            persist=True,
        )
    
    # Should recompute result due to cache error
    result2 = task2.resolve()
    assert result2 == 3


def test_no_persistence():
    """Test that tasks work correctly without persistence."""
    # Create a task without persistence
    task = Task(
        name="test_task",
        func=add_numbers,
        parameters=TaskParameters({"x": 1, "y": 2}),
    )
    
    # Execute task
    result = task.resolve()
    assert result == 3
    assert task.status == TaskStatus.COMPLETED
    
    # Create another task with same signature
    task2 = Task(
        name="test_task",
        func=add_numbers,
        parameters=TaskParameters({"x": 1, "y": 2}),
    )
    
    # Should recompute result
    result2 = task2.resolve()
    assert result2 == 3
    assert task2.status == TaskStatus.COMPLETED


def test_task_decorator_persist_flag(persistence):
    """Test that the persist flag in task decorator works correctly."""    
    # Define a task with persistence enabled
    @task(persist=True)
    def add(x: int, y: int) -> int:
        return x + y
    
    with pt.set_persistence(persistence):
        # First call should compute and cache
        result1 = add(1, 2).resolve()
        assert result1 == 3
        
        # Second call should use cached result
        result2 = add(1, 2).resolve()
        assert result2 == 3
        
        # Different parameters should compute new result
        result3 = add(2, 3).resolve()
        assert result3 == 5


def test_task_decorator_persist_no_backend():
    """Test that persist=True fails when no backend is configured."""
    # Define a task with persistence enabled
    @task(persist=True)
    def add(x: int, y: int) -> int:
        return x + y
    
    # Should raise RuntimeError when called without backend
    with pytest.raises(RuntimeError) as exc_info:
        add(1, 2).resolve()
    assert "requires persistence but no backend is configured" in str(exc_info.value)


def test_task_decorator_persist_version(persistence):
    """Test that version works with persist flag in decorator."""
    @task(persist=True, task_version=1)
    def add_v1(x: int, y: int) -> int:
        return x + y
    
    @task(persist=True, task_version=2)
    def add_v2(x: int, y: int) -> int:
        return x + y
    
    with pt.set_persistence(persistence):
        # Create task instances
        output1 = add_v1(1, 2)
        output2 = add_v2(1, 2)
        
        # Verify different signatures
        assert output1.owner.signature != output2.owner.signature
        
        # Execute tasks
        result1 = output1.resolve()
        result2 = output2.resolve()
        
        assert result1 == result2 == 3
        
        # Verify both results are cached
        assert persistence.exists(str(output1.owner.signature))
        assert persistence.exists(str(output2.owner.signature))
