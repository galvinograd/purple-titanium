"""Tests for the decorator API."""
import pytest

import purple_titanium as pt


def test_task_decorator() -> None:
    @pt.task()
    def add(a: int, b: int) -> int:
        return a + b

    result = add(1, 2)
    assert isinstance(result, pt.LazyOutput)
    assert result.resolve() == 3
    assert result.exists()


def test_task_decorator_with_dependencies() -> None:
    @pt.task()
    def one() -> int:
        return 1

    @pt.task()
    def inc(n: int) -> int:
        return n + 1

    o_one = one()
    o_two = inc(o_one)

    assert o_two.resolve() == 2
    assert o_one.exists()
    assert o_two.exists()


def test_task_decorator_with_error() -> None:
    @pt.task()
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    result = failing_task(42)
    with pytest.raises(ValueError, match="Task failed"):
        result.resolve()

    assert not result.exists()


def test_task_decorator_with_error_propagation() -> None:
    @pt.task()
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    @pt.task()
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

    @pt.listen(pt.EventType.TASK_STARTED)
    def on_task_started(event: pt.Event) -> None:
        events.append(("started", event.task.name))

    @pt.listen(pt.EventType.TASK_FINISHED)
    def on_task_finished(event: pt.Event) -> None:
        events.append(("finished", event.task.name))

    @pt.task()
    def sample_task(x: int) -> int:
        return x * 2

    result = sample_task(5)
    result.resolve()

    assert events == [
        ("started", "tests.test_decorators.sample_task"),
        ("finished", "tests.test_decorators.sample_task")
    ]


def test_complex_dag_execution() -> None:
    """Test execution of a complex DAG with multiple dependencies."""
    @pt.task()
    def source() -> int:
        return 1

    @pt.task()
    def double(x: int) -> int:
        return x * 2

    @pt.task()
    def triple(x: int) -> int:
        return x * 3

    @pt.task()
    def sum_values(a: int, b: int) -> int:
        return a + b

    # Create a diamond-shaped DAG
    s = source()
    d = double(s)
    t = triple(s)
    result = sum_values(d, t)

    assert result.resolve() == 5  # (1 * 2) + (1 * 3)


def test_task_decorator_type_hints() -> None:
    """Test that type hints are preserved through the task decorator."""
    @pt.task()
    def typed_task(x: int, y: str) -> str:
        return y * x

    result = typed_task(3, "a")
    assert result.resolve() == "aaa"


def test_task_decorator_kwargs() -> None:
    """Test that keyword arguments are handled correctly."""
    @pt.task()
    def add(a: int, b: int) -> int:
        return a + b

    result = add(a=1, b=2)
    assert result.resolve() == 3


def test_task_decorator_nested_dependencies() -> None:
    """Test that nested dependencies are handled correctly."""
    @pt.task()
    def level1() -> int:
        return 1

    @pt.task()
    def level2(x: int) -> int:
        return x + 1

    @pt.task()
    def level3(x: int) -> int:
        return x + 1

    l1 = level1()
    l2 = level2(l1)
    l3 = level3(l2)

    assert l3.resolve() == 3


def test_listen_decorator_multiple_events() -> None:
    """Test that multiple event listeners can be registered for the same event."""
    events = []

    @pt.listen(pt.EventType.TASK_STARTED)
    def listener1(event: pt.Event) -> None:
        events.append(("listener1", event.task.name))

    @pt.listen(pt.EventType.TASK_STARTED)
    def listener2(event: pt.Event) -> None:
        events.append(("listener2", event.task.name))

    @pt.task()
    def sample_task() -> int:
        return 42

    result = sample_task()
    result.resolve()

    assert ("listener1", "tests.test_decorators.sample_task") in events
    assert ("listener2", "tests.test_decorators.sample_task") in events


def test_task_decorator_error_handling_with_try_except() -> None:
    """Test that tasks can handle errors internally."""
    events = []

    @pt.listen(pt.EventType.TASK_FAILED)
    def on_task_failed(event: pt.Event) -> None:
        events.append(("failed", event.task.name))

    @pt.task()
    def might_fail(x: int) -> int:
        if x < 0:
            raise ValueError("x must be non-negative")
        return x * 2

    @pt.task()
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

    # Test success case
    result2 = safe_task(2)
    assert result2.resolve() == 4
    assert result2.exists()

    # Test error propagation
    result3 = might_fail(-1)
    with pytest.raises(ValueError, match="x must be non-negative"):
        result3.resolve()
    assert not result3.exists()
    assert ("failed", "tests.test_decorators.might_fail") in events


def test_task_decorator_with_all_event_types() -> None:
    """Test that all event types are emitted correctly."""
    events = []

    for event_type in pt.EventType:
        @pt.listen(event_type)
        def listener(event: pt.Event, event_type: pt.EventType = event_type) -> None:
            events.append((event_type, event.task.name))

    @pt.task()
    def failing_task() -> int:
        raise ValueError("Task failed")

    @pt.task()
    def dependent_task(x: int) -> int:
        return x * 2

    result = dependent_task(failing_task())

    with pytest.raises(ValueError, match="Task failed"):
        result.resolve()

    assert (pt.EventType.TASK_STARTED, "tests.test_decorators.failing_task") in events
    assert (pt.EventType.TASK_FAILED, "tests.test_decorators.failing_task") in events
    assert (pt.EventType.TASK_DEP_FAILED, "tests.test_decorators.dependent_task") in events 