"""Tests for task parameter injection."""

import pytest

import purple_titanium as pt


def test_task_with_injectable_parameter() -> None:
    """Test that a task can receive an injectable parameter from context."""
    
    @pt.task()
    def my_task(x: pt.Injected[int]) -> int:
        return x * 2
    
    with pt.Context(x=5):
        task_obj = my_task()
        assert task_obj.resolve() == 10


def test_missing_injectable_parameter() -> None:
    """Test that a missing injectable parameter raises an error."""
    
    @pt.task()
    def my_task(x: pt.Injected[int]) -> int:
        return x * 2
    
    with pytest.raises(ValueError, match="Required injectable parameter 'x' not found in context"):
        my_task()


def test_mixed_parameters() -> None:
    """Test that a task can have both injectable and regular parameters."""
    
    @pt.task()
    def my_task(x: pt.Injected[int], y: int) -> int:
        return x * y
    
    with pt.Context(x=5):
        task_obj = my_task(y=3)
        assert task_obj.resolve() == 15


def test_optional_injectable_parameter() -> None:
    """Test that an optional injectable parameter works correctly."""
    
    @pt.task()
    def my_task(x: pt.Injected[int] = 10) -> int:
        return x * 2
    
    # Test with default value
    task_obj = my_task()
    assert task_obj.resolve() == 20
    
    # Test with context value
    with pt.Context(x=5):
        task_obj = my_task()
        assert task_obj.resolve() == 10


def test_using_type_alias() -> None:
    """Test using the Injected type alias."""
    
    @pt.task()
    def my_task(x: pt.Injected[int]) -> int:
        return x * 2
    
    with pt.Context(x=5):
        task_obj = my_task()
        assert task_obj.resolve() == 10