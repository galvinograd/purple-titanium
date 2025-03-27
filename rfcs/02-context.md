# RFC: Context

## Summary
# RFC: Context

## Summary

A Context system that provides hierarchical, thread-safe parameter injection through an immutable context stack. This enables predictable dependency injection and scoped parameter management across the application.

## Motivation

Managing dependencies and injecting parameters across different parts of an application can be challenging and error-prone. We need a system that:
- Provides predictable parameter injection
- Ensures thread-safety for concurrent operations
- Allows temporary parameter overrides without side effects
- Makes dependency injection state explicit and traceable

## Detailed Design

### Core Components

1. **Context**
   - Immutable class that contains global settings
   - Contexts have hierarchy and kept in a global stack
   - Context scope is managed with context manager

2. **Context Stack**
   - A global thread-safe stack of contexts wth a default context
   - A task's context is determined at creation, not runtime

3. **Parameter Injection**
   - A task's arguments can be type hinted as injectables
   - If the injectable argument's name is in the context settings, it is injected at runtime
   - If the injectable argument's name is not in the context settings, exception is raised in intialization

### Example Usage

```python
# Basic context usage
@pt.task()
def foo(debug: pt.Injectable[bool]):  # Explicitly marked as injectable
   print(f"Debug mode: {debug}")

with pt.Context(debug=True):
    # Operations in this block use debug=True
    bar = foo()  # Task inherits debug=True
    
# Nested contexts
with pt.Context(debug=True):
    with pt.Context(timeout=30):
        # Inherits debug=True from parent, adds timeout=30
        baz = foo()

# Parameter injection with multiple arguments
@pt.task()
def process_data(
    data: list,  # Regular parameter, not injected
    timeout: pt.Injectable[int],  # Will be injected from context
    retries: pt.Injectable[int]  # Will be injected from context
):
    for attempt in range(retries):
        try:
            process_with_timeout(data, timeout)
            break
        except TimeoutError:
            continue

# Will raise an exception because 'retries' is not in context
with pt.Context(timeout=30):
    task = process_data([1, 2, 3])  # Fails at creation time

# Correct usage with all required injectable parameters in context
with pt.Context(timeout=30, retries=3):
    task = process_data([1, 2, 3])  # Works: timeout=30, retries=3 injected
```

The key points demonstrated:
1. Parameters must be explicitly marked with `Injectable[T]` to be injected
2. Regular parameters (like `data`) are passed normally
3. Injectable parameters must be present in the context
4. Missing injectable parameters raise exceptions at task creation
5. Injectable parameters can be inherited from parent contexts

This better aligns with the Core Components description by making it explicit which parameters are injectables through the type hint system.

## Implementation Plan

1. ✅ Implement base Context class
   - Use `@dataclass(frozen=True)` for immutability
   - Add context inheritance logic
   - Add `replace()` method
   - Add context manager support
   - Add proper equality and hash implementations

2. ✅ Implement ContextStack
   - Use `threading.Lock` for thread-safe operations
   - Initialize default context
   - Add context manager support
   - Add push/pop operations

3. ✅ Add context-aware task creation
   - Add `Injectable` type for parameter injection
   - Update task decorator to handle injectable parameters
   - Add error handling for missing injectable parameters
   - Add tests for parameter injection

4. ✅ Create testing suite
   - Add unit tests for Context class
   - Add unit tests for ContextStack
   - Add integration tests for task creation
   - Add thread safety tests

## Code References

- `src/purple_titanium/context.py` - Context and ContextStack implementation
- `src/purple_titanium/decorators.py` - Task decorator with parameter injection
- `src/purple_titanium/types.py` - Injectable type definition
- `tests/test_context.py` - Context and ContextStack tests
- `tests/test_task_injection.py` - Parameter injection tests