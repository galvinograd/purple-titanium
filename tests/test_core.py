import pytest

from purple_titanium import Event, EventType, LazyOutput, Task, TaskStatus, listen


def test_lazy_output_creation() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    task = Task(
        name="sample",
        func=sample_func,
        args=(5,),
        kwargs={},
        dependencies=set()
    )
    output = task.output

    assert isinstance(output, LazyOutput)
    assert output.owner == task
    assert output.value is None
    assert not output.exists()

def test_task_execution() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    task = Task(
        name="sample",
        func=sample_func,
        args=(5,),
        kwargs={},
        dependencies=set()
    )
    output = task.output

    assert output.resolve() == 10
    assert output.value == 10
    assert output.exists()
    assert task.status == TaskStatus.COMPLETED

def test_task_dependencies() -> None:
    def one() -> int:
        return 1

    def inc(n: int) -> int:
        return n + 1

    task_one = Task(
        name="one",
        func=one,
        args=(),
        kwargs={},
        dependencies=set()
    )
    task_inc = Task(
        name="inc",
        func=inc,
        args=(task_one.output,),
        kwargs={},
        dependencies={task_one}
    )

    assert task_inc.output.resolve() == 2
    assert task_one.status is TaskStatus.COMPLETED
    assert task_inc.status is TaskStatus.COMPLETED

def test_task_error_handling() -> None:
    def failing_func(x: int) -> int:
        raise ValueError("x must be non-negative")

    task = Task(
        name="failing",
        func=failing_func,
        args=(-1,),
        kwargs={},
        dependencies=set()
    )
    output = task.output

    with pytest.raises(ValueError, match="x must be non-negative"):
        output.resolve()

    assert task.status is TaskStatus.FAILED
    assert isinstance(task.exception, ValueError)
    assert not output.exists()

def test_event_handling() -> None:
    events = []
    
    @listen(EventType.TASK_STARTED)
    def on_task_started(event: Event) -> None:
        events.append(("started", event.task.name))

    @listen(EventType.TASK_FINISHED)
    def on_task_finished(event: Event) -> None:
        events.append(("finished", event.task.name))

    def sample_func(x: int) -> int:
        return x * 2

    task = Task(
        name="sample",
        func=sample_func,
        args=(5,),
        kwargs={},
        dependencies=set()
    )
    task.output.resolve()

    assert events == [
        ("started", "sample"),
        ("finished", "sample")
    ]

def test_task_initialization_rules() -> None:
    def sample_func(x: int) -> int:
        return x * 2

    def helper(x: int) -> int:
        # This should raise RuntimeError
        return Task(
            name="nested",
            func=sample_func,
            args=(x,),
            kwargs={},
            dependencies=set()
        ).output

    def invalid_task(x: int) -> int:
        return helper(x)

    # Test that task initialization can be done at top level
    task = Task(
        name="valid",
        func=sample_func,
        args=(5,),
        kwargs={},
        dependencies=set()
    )
    assert task.output.resolve() == 10

    # Test that task initialization cannot be done inside a task
    invalid_task = Task(
        name="invalid",
        func=invalid_task,
        args=(5,),
        kwargs={},
        dependencies=set()
    )
    with pytest.raises(RuntimeError, match="task\\(\\) cannot be called inside a task"):
        invalid_task.output.resolve()

def test_multiple_resolve_calls() -> None:
    def one() -> int:
        return 1

    def two() -> int:
        return 2

    task_one = Task(
        name="one",
        func=one,
        args=(),
        kwargs={},
        dependencies=set()
    )
    task_two = Task(
        name="two",
        func=two,
        args=(),
        kwargs={},
        dependencies=set()
    )

    # Test that multiple resolve() calls are allowed at top level
    assert task_one.output.resolve() == 1
    assert task_two.output.resolve() == 2
    assert task_one.status is TaskStatus.COMPLETED
    assert task_two.status is TaskStatus.COMPLETED

def test_dependency_resolution_order() -> None:
    def one() -> int:
        return 1

    def inc(n: int) -> int:
        return n + 1

    def add(a: int, b: int) -> int:
        return a + b

    task_one = Task(
        name="one",
        func=one,
        args=(),
        kwargs={},
        dependencies=set()
    )
    task_two = Task(
        name="two",
        func=inc,
        args=(task_one.output,),
        kwargs={},
        dependencies={task_one}
    )
    task_three = Task(
        name="three",
        func=add,
        args=(task_one.output, task_two.output),
        kwargs={},
        dependencies={task_one, task_two}
    )

    # Test that dependencies are resolved in correct order
    assert task_three.output.resolve() == 3  # 1 + (1 + 1)
    assert task_one.status is TaskStatus.COMPLETED
    assert task_two.status is TaskStatus.COMPLETED
    assert task_three.status is TaskStatus.COMPLETED

def test_error_propagation() -> None:
    def failing_task(x: int) -> int:
        raise ValueError(f"Task failed with input {x}")

    def dependent_task(x: int) -> int:
        return x * 2

    task_one = Task(
        name="failing",
        func=failing_task,
        args=(42,),
        kwargs={},
        dependencies=set()
    )
    task_two = Task(
        name="dependent",
        func=dependent_task,
        args=(task_one.output,),
        kwargs={},
        dependencies={task_one}
    )

    # Test that errors propagate through the DAG
    with pytest.raises(ValueError, match="Task failed"):
        task_two.output.resolve()

    assert task_one.status is TaskStatus.FAILED
    assert task_two.status is TaskStatus.DEP_FAILED
    assert isinstance(task_one.exception, ValueError)
    assert not task_one.output.exists()
    assert not task_two.output.exists() 