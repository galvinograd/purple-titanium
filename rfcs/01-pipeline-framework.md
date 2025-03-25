# RFC: Pipeline Framework

## Summary

A minimal pipeline framework that provides a structured way to define and execute task-based data processing workflows. The framework connects tasks through targets, forming a directed acyclic graph (DAG) that automatically handles dependencies, execution order, and completion tracking.

## Motivation

Many data processing workflows involve multiple steps that need to be executed in a specific order, with dependencies between them. A pipeline framework provides:

- Clear separation of processing logic into discrete tasks
- Automatic dependency resolution and execution ordering
- Skipping of already completed tasks for efficiency
- Consistent event handling and error reporting
- Configuration management across the entire workflow

This will enable developers to focus on implementation of specific processing steps rather than orchestration logic.

## Detailed Design

### Core Components

1. **Tasks** and **LazyOutput**
A task is a plain function decorated with `@pt.task`, which represents a node in a calculation tree (DAG).
When this decorated function is called, it is added to the calculation tree in the background and returns a single `LazyOutput`.
Each `LazyOutput` has the read-only fields `owner` and `value` and a method `exists()`.

For example, consider the following example

```python
import purple_titanium as pt

@pt.task()
def greet(x: str) -> str:
   return f"Hello {x}!"

text = greet('Gal')

# print the task signature
print(text.owner)

# print None
print(text.value)

# print False
print(text.exists())
```

The `LazyOutput` can be resolved as follows

```python
# print logs about output resolution
res = text.resolve()

# print True
print(res is text.value)
```

It can also resolve though the DAG

```python
@pt.task()
def one() -> int:
   return 1

@pt.task()
def inc(n: int) -> int:
   return n + 1

@pt.task()
def dec(n: int) -> int
   return n - 1

o_one = one()
o_two = inc(o_one)
o_zero = dec(o_one)

# print 2 and resolution logs.
# it first resolve o_one, and then o_two
print(o_two.resolve())

# print True, True, False
print(o_one.exists(), o_two.exists(), o_zero.exists())

# print 0 and resolution logs.
# it resolve o_zero, since o_one was already resolved
print(o_zero.resolve())

# print True, True, True
print(o_one.exists(), o_two.exists(), o_zero.exists())
```

2. **LazyOutput Resolution**

The `resolve()` method is a top-level function that can only be called once in the call stack. This means:

1. `resolve()` cannot be called inside a task:
```python
@pt.task()
def invalid_task(x: int) -> int:
    # This will raise RuntimeError: resolve() cannot be called inside a task
    return x.resolve()  # Error!

@pt.task()
def valid_task(x: int) -> int:
    # This is correct - just use the LazyOutput directly
    return x * 2
```

2. `resolve()` can only be called at the top level:
```python
def helper(x: int) -> int:
    # This will raise RuntimeError: resolve() cannot be called inside a task
    return x.resolve()  # Error!

@pt.task()
def task_with_helper(x: int) -> int:
    return helper(x)  # Error!

# This is correct
result = task_with_helper(42)
value = result.resolve()  # OK - called at top level
```

3. Multiple `resolve()` calls at the top level are allowed:
```python
@pt.task()
def one() -> int:
    return 1

@pt.task()
def two() -> int:
    return 2

o_one = one()
o_two = two()

# Multiple resolve() calls are allowed at the top level
print(o_one.resolve())  # prints 1
print(o_two.resolve())  # prints 2
```

4. Task initialization is also restricted:
```python
@pt.task()
def task(x: int) -> int:
    return x * 2

def helper(x: int) -> int:
    # This will raise RuntimeError: task() cannot be called inside a task
    return task(x)  # Error!

@pt.task()
def invalid_task(x: int) -> int:
    return helper(x)  # Error!

# This is correct
result = task(42)
value = result.resolve()  # OK - called at top level
```

This design ensures that:
- Task execution is deterministic and predictable
- Dependencies are properly tracked and resolved
- The execution graph is well-defined
- Error propagation is consistent
- Task initialization is controlled and happens only at the top level

3. **Error Handling**

Errors during task execution are propagated through the DAG and can be caught at any level. When a task fails, its exception is stored and can be accessed through the `exception` property.

```python
@pt.task()
def might_fail(x: int) -> int:
    if x < 0:
        raise ValueError("x must be non-negative")
    return x * 2

# Create a potentially failing task
result = might_fail(-1)

try:
    result.resolve()
except ValueError as e:
    print(f"Task failed: {e}")
    print(f"Exception stored in task: {result.owner.exception}")

# The failed state persists until the task is successfully resolved
print(result.owner.exception)  # Still contains the ValueError
```

Tasks can also implement custom error handling using try/except blocks:

```python
@pt.task()
def safe_task(x: int) -> int:
    try:
        return might_fail(x)
    except ValueError:
        return 0  # fallback value

result = safe_task(-1)
print(result.resolve())  # prints 0
```

Error propagation in the DAG is handled through a combination of events and exceptions:

1. When a task fails:
   - A `TASK_FAILED` event is emitted with the task and its exception
   - The exception is stored in the task's `exception` property
   - The task's status is set to `FAILED`

2. When a task with dependencies fails:
   - The failure is propagated up the DAG
   - Each dependent task receives a `TASK_DEP_FAILED` event
   - The task's status is set to `DEP_FAILED`
   - The failure can be caught at any level using try/except

3. Root task failures:
   - When a root task fails, a `ROOT_FAILED` event is emitted
   - This allows for global error handling at the pipeline level
   - The exception can be caught using try/except on the root task's output

Example of error propagation:

```python
@pt.task()
def failing_task(x: int) -> int:
    raise ValueError(f"Task failed with input {x}")

@pt.task()
def dependent_task(x: int) -> int:
    return x * 2

@pt.listen(pt.TASK_FAILED)
def on_task_failed(event):
    print(f"Task {event.task.name} failed: {event.task.exception}")

@pt.listen(pt.ROOT_FAILED)
def on_root_failed(event):
    print(f"Pipeline failed: {event.task.exception}")

try:
    result = dependent_task(failing_task(42))
    result.resolve()
except ValueError as e:
    print(f"Caught error at root level: {e}")
```

4. **Event Handling**

One can listen to events emitted while resolving as follows

```python
@pt.listen(pt.ROOT_STARTED)
def on_root_started(task):
   print(f'root task {task.name} is starting')

@pt.listen(pt.ROOT_FINISHED)
def on_root_finished(task):
   print(f'root task {task.name} is finished')

@pt.listen(pt.ROOT_FAILED)
def on_root_failed(task):
   print(f'root task {task.name} is failed with the exception {task.failed}')
```

The possible events are:
 - ROOT_STARTED
 - ROOT_FINISHED
 - ROOT_FAILED
 - TASK_STARTED
 - TASK_FINISHED
 - TASK_FAILED
 - TASK_DEP_FAILED
 - INTERNAL_ERROR

## Implementation Plan

1. Write Acceptance Tests
   - [x] Test basic task creation and execution
   - [x] Test LazyOutput resolution rules (top-level only, no resolve in tasks)
   - [x] Test task initialization rules (top-level only)
   - [x] Test dependency resolution and execution order
   - [x] Test error handling and event propagation
   - [x] Test event system functionality

2. Write Initial Implementation
   - [x] Implement `LazyOutput` class with resolution rules
   - [x] Create base `Task` class with execution and dependency tracking
   - [x] Implement task resolution logic and DAG traversal
   - [x] Develop exception handling and storage mechanism
   - [x] Create event system with standard pipeline events

3. Test, Fix and Iterate
   - [x] Run acceptance tests
   - [x] Fix any issues found
   - [x] Run all tests to ensure no regressions
   - [x] Refine implementation based on test results

4. Write Decorator API Implementation
   - [x] Create `task` decorator for creating tasks from functions
   - [x] Create `listen` decorator for registering event listeners
   - [x] Write tests for decorators
   - [x] Test and fix any issues

5. Write Decorator API Tests
   - [x] Test task decorator functionality
   - [x] Verify event listener registration and triggering
   - [x] Test error handling in decorated tasks
   - [x] Verify that decorated tasks maintain proper execution order
   - [x] Test complex DAG scenarios with multiple dependencies

6. Documentation and Examples
   - [ ] Write comprehensive API documentation
   - [ ] Create getting started guide with simple examples
   - [ ] Document error handling patterns and best practices
   - [ ] Create examples of event handling and custom listeners
   - [ ] Document DAG creation and resolution patterns

## Code References

- [Dagster](https://dagster.io/)
- [scikit-learn Pipeline](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html)
- [Luigi Task-based Pipeline](https://github.com/spotify/luigi)
- [Apache Airflow](https://airflow.apache.org/) 
