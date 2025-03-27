"""Tests for the context management system."""

import threading
from dataclasses import FrozenInstanceError

import pytest

from purple_titanium.context import Context, get_current_context


def test_basic_context() -> None:
    """Test basic context creation and attribute access."""
    ctx = Context(debug=True, timeout=30)
    assert ctx.debug is True
    assert ctx.timeout == 30
    
    # Test missing attribute
    with pytest.raises(AttributeError):
        _ = ctx.missing_attr


def test_context_inheritance() -> None:
    """Test context inheritance through replace()."""
    base = Context(debug=True, timeout=30)
    child = base.replace(timeout=60)
    
    assert child.debug is True  # Inherited from parent
    assert child.timeout == 60  # Overridden in child
    
    # Parent should be unchanged
    assert base.timeout == 30


def test_context_manager() -> None:
    """Test context manager functionality."""
    ctx0 = Context(
        debug=False,
        timeout=60,
    )
    ctx1 = Context(debug=True)
    ctx2 = Context(timeout=30)
    
    # Test entering and exiting contexts
    with ctx0:
        with ctx1:
            assert get_current_context().debug is True
            with ctx2:
                assert get_current_context().timeout == 30
                assert get_current_context().debug is True  # Inherited from parent
            assert get_current_context().debug is True  # Back to ctx1
        assert get_current_context().debug is False  # Back to default
    assert not hasattr(get_current_context(), 'debug')  # Back to default
    assert not hasattr(get_current_context(), 'timeout')  # Back to default

def test_thread_safety() -> None:
    """Test thread safety of context stack."""
    def worker() -> None:
        ctx = Context(thread_id=threading.get_ident())
        with ctx:
            assert get_current_context().thread_id == threading.get_ident()
    
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # Main thread context should be restored
    assert not hasattr(get_current_context(), 'thread_id')


def test_context_immutability() -> None:
    """Test that contexts are truly immutable."""
    ctx = Context(debug=True)
    
    # Attempting to modify settings should raise TypeError
    with pytest.raises(TypeError):
        ctx._settings['debug'] = False
    
    # Attempting to modify parent should raise FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        ctx._parent = None


def test_context_equality() -> None:
    """Test context equality comparison."""
    ctx1 = Context(debug=True)
    ctx2 = Context(debug=True)
    ctx3 = Context(debug=False)
    
    assert ctx1 == ctx2
    assert ctx1 != ctx3
    
    # Contexts with different parents should not be equal
    child1 = ctx1.replace(timeout=30)
    child2 = ctx2.replace(timeout=30)
    assert child1 != child2  # Different parents (identity comparison)


def test_context_hash() -> None:
    """Test that contexts can be hashed."""
    ctx1 = Context(debug=True)
    ctx2 = Context(debug=True)
    ctx3 = Context(debug=False)
    
    # Equal contexts should have equal hashes
    assert hash(ctx1) == hash(ctx2)
    assert hash(ctx1) != hash(ctx3)
    
    # Contexts with different parents should have different hashes
    child1 = ctx1.replace(timeout=30)
    child2 = ctx2.replace(timeout=30)
    assert hash(child1) != hash(child2)  # Different parents (identity comparison)


def test_default_context() -> None:
    """Test default context behavior."""
    # Default context should have default settings
    default = get_current_context()
    assert len(default) == 0
    
    # Default context should be immutable
    with pytest.raises(TypeError):
        default._settings['debug'] = True 