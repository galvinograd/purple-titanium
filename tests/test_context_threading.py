"""Tests for thread safety and integration of the context system."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import purple_titanium as pt


def test_concurrent_context_access() -> None:
    """Test concurrent access to context stack from multiple threads."""
    def worker(thread_num: int) -> None:
        ctx = pt.Context(thread_num=thread_num)
        with ctx:
            # Simulate some work
            time.sleep(0.1)
            # Verify we're in the correct context
            assert pt.get_current_context().thread_num == thread_num
    
    # Create and run threads
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # Main thread context should be restored
    assert not hasattr(pt.get_current_context(), 'thread_num')


def test_nested_contexts_in_threads() -> None:
    """Test nested context management in multiple threads."""
    def worker(thread_id: int) -> None:
        ctx1 = pt.Context(thread_id=thread_id, value=1)
        ctx2 = pt.Context(thread_id=thread_id, value=2)
        
        with ctx1:
            assert pt.get_current_context().value == 1
            with ctx2:
                assert pt.get_current_context().value == 2
                assert pt.get_current_context().thread_id == thread_id
            assert pt.get_current_context().value == 1
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_context_stack_cleanup() -> None:
    """Test that context stack is properly cleaned up after thread termination."""
    def worker() -> None:
        ctx = pt.Context(thread_id=threading.get_ident())
        with ctx:
            time.sleep(0.1)
    
    # Create and start threads
    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify that no contexts are left in the stack
    with pytest.raises(AttributeError):
        _ = pt.get_current_context().thread_id


def test_context_inheritance_across_threads() -> None:
    """Test that context inheritance works correctly across threads."""
    def worker(parent_value: int) -> None:
        parent = pt.Context(value=parent_value)
        child = parent.replace(thread_id=threading.get_ident())
        
        with parent, child:
            assert pt.get_current_context().value == parent_value
            assert pt.get_current_context().thread_id == threading.get_ident()
    
    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_concurrent_context_modification() -> None:
    """Test concurrent modification of context values."""
    def worker(thread_id: int) -> list[int]:
        values = []
        ctx = pt.Context(thread_id=thread_id)
        
        with ctx:
            for i in range(5):
                new_ctx = pt.get_current_context().replace(value=i)
                with new_ctx:
                    values.append(pt.get_current_context().value)
                    time.sleep(0.01)  # Simulate work
        
        return values
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(worker, i) for i in range(3)]
        results = [future.result() for future in futures]
    
    # Each thread should have its own sequence of values
    for values in results:
        assert values == [0, 1, 2, 3, 4]


def test_context_cleanup_on_exception() -> None:
    """Test that context stack is cleaned up properly when exceptions occur."""
    def worker() -> None:
        ctx = pt.Context(thread_id=threading.get_ident())
        try:
            with ctx:
                raise ValueError("Test exception")
        except ValueError:
            pass
    
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    
    # Context should be cleaned up even after exception
    with pytest.raises(AttributeError):
        _ = pt.get_current_context().thread_id 