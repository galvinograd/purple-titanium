"""Tests for the decorator API."""
import pytest

from purple_titanium import Event, EventType, LazyOutput, listen, task


def test_task_decorator() -> None:
    @task()
    def add(a: int, b: int) -> int:
        return a + b

    result = add(1, 2)
    assert isinstance(result, LazyOutput)
    assert result.resolve() == 3
    assert result.exists()


def test_task_decorator_with_dependencies() -> None:
    @task()
    def one() -> int:
        return 1

    @task()
    def inc(n: int) -> int:
        return n + 1

    o_one = one()
    o_two = inc(o_one)

    assert o_two.resolve() == 2
    assert o_one.exists()
    assert o_two.exists()


def test_task_decorator_with_error() -> None:
    @task()
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    result = failing_task(42)
    with pytest.raises(ValueError, match="Task failed"):
        result.resolve()

    assert not result.exists()


def test_task_decorator_with_error_propagation() -> None:
    @task()
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    @task()
    def dependent_task(x: int) -> int:
        return x * 2

    o_one = failing_task(42)
    o_two = dependent_task(o_one)

    with pytest.raises(ValueError, match="Task failed"):
        o_two.resolve()

    assert not o_one.exists()
    assert not o_two.exists()


def test_listen_decorator() -> None:
    events = []

    @listen(EventType.TASK_STARTED)
    def on_task_started(event: Event) -> None:
        events.append(("started", event.task.name))

    @listen(EventType.TASK_FINISHED)
    def on_task_finished(event: Event) -> None:
        events.append(("finished", event.task.name))

    @task()
    def sample_task(x: int) -> int:
        return x * 2

    result = sample_task(5)
    result.resolve()

    assert events == [
        ("started", "sample_task"),
        ("finished", "sample_task")
    ]


def test_complex_dag_execution() -> None:
    """Test execution of a complex DAG with multiple dependencies."""
    @task()
    def source() -> int:
        return 1

    @task()
    def double(x: int) -> int:
        return x * 2

    @task()
    def triple(x: int) -> int:
        return x * 3

    @task()
    def sum_values(a: int, b: int) -> int:
        return a + b

    # Create a diamond-shaped DAG
    s = source()
    d = double(s)
    t = triple(s)
    result = sum_values(d, t)

    assert result.resolve() == 5  # (1 * 2) + (1 * 3)
    assert s.exists()
    assert d.exists()
    assert t.exists()
    assert result.exists()


def test_task_decorator_type_hints() -> None:
    """Test that type hints are preserved through the task decorator."""
    @task()
    def typed_task(x: int, y: str) -> str:
        return y * x

    result = typed_task(3, "a")
    assert result.resolve() == "aaa"
    assert isinstance(result.value, str)


def test_task_decorator_kwargs() -> None:
    """Test that keyword arguments work correctly with tasks."""
    @task()
    def task_with_kwargs(*, x: int = 1, y: int = 2) -> int:
        return x + y

    result1 = task_with_kwargs()
    assert result1.resolve() == 3

    result2 = task_with_kwargs(x=5, y=7)
    assert result2.resolve() == 12


def test_task_decorator_nested_dependencies() -> None:
    """Test that nested dependencies are handled correctly."""
    @task()
    def level1() -> int:
        return 1

    @task()
    def level2(x: int) -> int:
        return x + 1

    @task()
    def level3(x: int) -> int:
        return x + 1

    l1 = level1()
    l2 = level2(l1)
    l3 = level3(l2)

    assert l3.resolve() == 3
    assert l1.exists()
    assert l2.exists()
    assert l3.exists()


def test_listen_decorator_multiple_events() -> None:
    """Test that multiple event listeners can be registered for the same event."""
    events = []

    @listen(EventType.TASK_STARTED)
    def listener1(event: Event) -> None:
        events.append(("listener1", event.task.name))

    @listen(EventType.TASK_STARTED)
    def listener2(event: Event) -> None:
        events.append(("listener2", event.task.name))

    @task()
    def sample_task() -> int:
        return 42

    result = sample_task()
    result.resolve()

    assert ("listener1", "sample_task") in events
    assert ("listener2", "sample_task") in events


def test_task_decorator_error_handling_with_try_except() -> None:
    """Test that tasks can handle errors internally."""
    events = []

    @listen(EventType.TASK_FAILED)
    def on_task_failed(event: Event) -> None:
        events.append(("failed", event.task.name))

    @task()
    def might_fail(x: int) -> int:
        if x < 0:
            raise ValueError("x must be non-negative")
        return x * 2

    @task()
    def safe_task(x: int) -> int:
        try:
            if x < 0:
                raise ValueError("x must be non-negative")
            return x * 2
        except ValueError:
            return 0

    # Test error case
    result1 = safe_task(-1)
    assert result1.resolve() == 0
    assert result1.exists()
    assert not events  # No task failed since we handled the error

    # Test success case
    result2 = safe_task(2)
    assert result2.resolve() == 4
    assert result2.exists()
    assert not events  # No task failed


def test_task_decorator_with_all_event_types() -> None:
    """Test that all event types are emitted correctly."""
    events = []

    for event_type in EventType:
        @listen(event_type)
        def listener(event: Event, event_type: EventType = event_type) -> None:
            events.append((event_type, event.task.name))

    @task()
    def failing_task() -> int:
        raise ValueError("Task failed")

    @task()
    def dependent_task(x: int) -> int:
        return x * 2

    result = dependent_task(failing_task())
    
    with pytest.raises(ValueError, match="Task failed"):
        result.resolve()

    # Verify that we received TASK_STARTED, TASK_FAILED, and TASK_DEP_FAILED events
    event_types = [e[0] for e in events]
    assert EventType.TASK_STARTED in event_types
    assert EventType.TASK_FAILED in event_types
    assert EventType.TASK_DEP_FAILED in event_types 