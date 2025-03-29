"""Tests for core task functionality."""

import pytest

import purple_titanium as pt
from purple_titanium.task_factory import TaskFactory


def test_lazy_output_creation() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    task = TaskFactory.create(
        name="sample",
        func=sample_func,
        args=(5,),
    )
    output = task.output

    assert isinstance(output, pt.LazyOutput)
    assert output.owner == task
    assert output.value is None
    assert not output.exists()


def test_task_execution() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    task = TaskFactory.create(
        name="sample",
        func=sample_func,
        args=(5,),
    )
    output = task.output

    assert output.resolve() == 10
    assert output.value == 10
    assert output.exists()
    assert task.status == pt.TaskStatus.COMPLETED


def test_task_dependencies() -> None:
    def one() -> int:
        return 1

    def inc(n: int) -> int:
        return n + 1

    task_one = TaskFactory.create(
        name="one",
        func=one,
        args=(),
    )
    task_inc = TaskFactory.create(
        name="inc",
        func=inc,
        args=(task_one.output,),
    )

    assert task_inc.output.resolve() == 2
    assert task_one.status is pt.TaskStatus.COMPLETED
    assert task_inc.status is pt.TaskStatus.COMPLETED


def test_task_error_handling() -> None:
    def failing_func(x: int) -> int:
        raise ValueError("x must be non-negative")

    task = TaskFactory.create(
        name="failing",
        func=failing_func,
        args=(-1,),
    )
    output = task.output

    with pytest.raises(ValueError, match="x must be non-negative"):
        output.resolve()

    assert task.status is pt.TaskStatus.FAILED
    assert isinstance(task.exception, ValueError)
    assert not output.exists()


def test_event_handling() -> None:
    events = []
    
    @pt.listen(pt.EventType.ROOT_STARTED)
    def on_root_started(event: pt.Event) -> None:
        events.append(("root_started", event.task.name))

    @pt.listen(pt.EventType.ROOT_FINISHED)
    def on_root_finished(event: pt.Event) -> None:
        events.append(("root_finished", event.task.name))

    @pt.listen(pt.EventType.ROOT_FAILED)
    def on_root_failed(event: pt.Event) -> None:
        events.append(("root_failed", event.task.name))

    @pt.listen(pt.EventType.TASK_STARTED)
    def on_task_started(event: pt.Event) -> None:
        events.append(("started", event.task.name))

    @pt.listen(pt.EventType.TASK_FINISHED)
    def on_task_finished(event: pt.Event) -> None:
        events.append(("finished", event.task.name))

    def sample_func(x: int) -> int:
        return x * 2

    task = TaskFactory.create(
        name="sample",
        func=sample_func,
        args=(5,),
    )
    output = task.output

    assert output.resolve() == 10
    assert events == [
        ("root_started", "sample"),
        ("started", "sample"),
        ("finished", "sample"),
        ("root_finished", "sample"),
    ]


def test_task_initialization_rules() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    def helper(x: int) -> int:
        # This should raise RuntimeError
        return TaskFactory.create(
            name="nested",
            func=sample_func,
            args=(x,),
        ).output

    def invalid_task(x: int) -> int:
        return helper(x)

    # Test that task initialization can be done at top level
    task = TaskFactory.create(
        name="valid",
        func=sample_func,
        args=(5,),
    )
    assert task.output.resolve() == 10

    # Test that task initialization cannot be done inside a task
    invalid_task = TaskFactory.create(
        name="invalid",
        func=invalid_task,
        args=(5,),
    )
    with pytest.raises(RuntimeError, match="task\\(\\) cannot be called inside a task"):
        invalid_task.output.resolve()


def test_multiple_resolve_calls() -> None:
    def one() -> int:
        return 1

    def two() -> int:
        return 2

    task_one = TaskFactory.create(
        name="one",
        func=one,
        args=(),
    )
    task_two = TaskFactory.create(
        name="two",
        func=two,
        args=(),
    )

    # Test that multiple resolve() calls are allowed at top level
    assert task_one.output.resolve() == 1
    assert task_two.output.resolve() == 2
    assert task_one.status is pt.TaskStatus.COMPLETED
    assert task_two.status is pt.TaskStatus.COMPLETED


def test_dependency_resolution_order() -> None:
    def one() -> int:
        return 1

    def inc(n: int) -> int:
        return n + 1

    def add(a: int, b: int) -> int:
        return a + b

    task_one = TaskFactory.create(
        name="one",
        func=one,
        args=(),
    )
    task_two = TaskFactory.create(
        name="two",
        func=inc,
        args=(task_one.output,),
    )
    task_three = TaskFactory.create(
        name="three",
        func=add,
        args=(task_one.output, task_two.output),
    )

    # Test that dependencies are resolved in correct order
    assert task_three.output.resolve() == 3  # 1 + (1 + 1)
    assert task_one.status is pt.TaskStatus.COMPLETED
    assert task_two.status is pt.TaskStatus.COMPLETED
    assert task_three.status is pt.TaskStatus.COMPLETED


def test_error_propagation() -> None:
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    def dependent_task(x: int) -> int:
        return x * 2

    task_one = TaskFactory.create(
        name="failing",
        func=failing_task,
        args=(42,),
    )
    task_two = TaskFactory.create(
        name="dependent",
        func=dependent_task,
        args=(task_one.output,),
    )

    # Test that errors propagate through the DAG
    with pytest.raises(ValueError, match="Task failed"):
        task_two.output.resolve()

    assert task_one.status is pt.TaskStatus.FAILED
    assert task_two.status is pt.TaskStatus.DEP_FAILED
    assert isinstance(task_one.exception, ValueError)
    assert not task_one.output.exists()
    assert not task_two.output.exists() 

def test_root_task_failure() -> None:
    events = []
    
    @pt.listen(pt.EventType.ROOT_FAILED)
    def on_root_failed(event: pt.Event) -> None:
        events.append(("root_failed", event.task.name))

    def failing_func(x: int) -> int:
        raise ValueError("Task failed")

    task = TaskFactory.create(
        name="failing",
        func=failing_func,
        args=(5,),
    )
    
    with pytest.raises(ValueError):  # noqa: PT011
        task.output.resolve()

    assert events == [("root_failed", "failing")]

def test_dependency_task_events() -> None:
    events = []
    
    @pt.listen(pt.EventType.ROOT_STARTED)
    def on_root_started(event: pt.Event) -> None:
        events.append(("root_started", event.task.name))

    @pt.listen(pt.EventType.TASK_STARTED)
    def on_task_started(event: pt.Event) -> None:
        events.append(("started", event.task.name))

    @pt.listen(pt.EventType.TASK_FINISHED)
    def on_task_finished(event: pt.Event) -> None:
        events.append(("finished", event.task.name))

    def add(a: int, b: int) -> int:
        return a + b

    def multiply(x: int) -> int:
        return x * 2

    # Create tasks
    add_task = TaskFactory.create(
        name="add",
        func=add,
        args=(1, 2),
    )
    
    multiply_task = TaskFactory.create(
        name="multiply",
        func=multiply,
        args=(add_task.output,),
    )

    # Resolve the root task
    multiply_task.output.resolve()

    # Verify events
    assert events == [
        ("root_started", "multiply"),  # Root task starts
        ("started", "multiply"),       # Root task execution starts
        ("started", "add"),           # Dependency task starts
        ("finished", "add"),          # Dependency task completes
        ("finished", "multiply"),     # Root task completes
    ]