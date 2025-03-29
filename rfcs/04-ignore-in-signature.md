# RFC 04: Parameter Annotations in Task Signatures

## Summary
Leverage Python's `Annotated` type (PEP 593) to provide parameter metadata for tasks, including signature ignoring and dependency injection.

## Motivation
Currently, every parameter in a task's function signature contributes to the task's cache signature. However, certain parameters like device selection (cuda/cpu), debug flags, or logging configurations don't affect the actual output of the task. When these parameters change, they trigger unnecessary cache invalidation and task re-execution.

Use cases include:
- Training device selection (cuda vs cpu)
- Debug printing flags
- Logging verbosity levels
- Progress bar configurations
- Random seeds when deterministic execution is not required
- Monitoring callbacks that don't affect the output

Additionally, we want to provide a consistent API for all parameter-level metadata in tasks, including:
- Parameters that should be ignored in signature calculation
- Injectable parameters that are resolved from context
- Future parameter metadata needs

## Detailed Design

### 1. Using Annotated Type for All Parameter Metadata

```python
from typing import Annotated
from purple_titanium.signatures import IgnoreInSignature, Injectable

# Ignore in signature example
@task
def train_model(
    model: nn.Module,
    device: Annotated[str, IgnoreInSignature] = "cuda",
    batch_size: int = 32
):
    pass

# Injectable parameter example
@task
def process_data(
    data: list[str],
    logger: Annotated[Logger, Injectable] = Injectable.required(),
    batch_size: int = 32
):
    pass

# Combined usage example
@task
def train_with_logging(
    model: nn.Module,
    device: Annotated[str, IgnoreInSignature] = "cuda",
    logger: Annotated[Logger, Injectable] = Injectable.required()
):
    pass
```

### 2. Marker Classes

```python
class Ignorable:
    """Marks a parameter to be ignored in signature calculation."""
    pass

class Injectable:
    """Marks a parameter as injectable from context."""
    pass
```

### 3. Type Aliases
To improve readability, we'll provide convenient type aliases:

```python
from typing import TypeVar, Annotated

T = TypeVar('T')
Ignored = Annotated[T, Ignorable()]
Injected = Annotated[T, Injectable()]

# Usage example
@task
def train_model(
    model: nn.Module,
    device: Ignored[str] = "cuda",
    logger: Injected[Logger] = None
):
    pass
```

### 4. Implementation Details

```python
def resolve_parameters(func, args, kwargs, context):
    params = get_parameters(func, args, kwargs)
    type_hints = get_type_hints(func, include_extras=True)
    
    for name, hint in type_hints.items():
        if hasattr(hint, "__metadata__"):
            for meta in hint.__metadata__:
                if isinstance(meta, Injectable):
                    params[name] = resolve_injectable(name, meta, context)
    
    return params

def resolve_injectable(name: str, injectable: Injectable, context: Context) -> Any:
    """Resolve an injectable parameter from context."""
    if name in context:
        return context[name]
    if not injectable.required:
        return injectable.default
    raise ValueError(f"Required injectable parameter '{name}' not found in context")
```

### 5. Error Handling
- Invalid nested paths will raise `InvalidNestedPathError`
- Type mismatches will raise `TypeAnnotationError`
- Circular references in nested parameters will raise `CircularReferenceError`
- Missing required injectable parameters will raise `MissingInjectableError`
- Invalid injectable types will raise `InvalidInjectableError`

## Implementation Plan

- [X] Core Implementation
  - [X] Add `Ignored` and `Injected` marker classes
  - [X] Modify parameter resolution to handle `Annotated` types
  - [X] Implement context-based injection
  - [X] Add type aliases for improved ergonomics

- [X] Testing
  - [X] Unit tests for parameter ignoring
  - [X] Tests for dependency injection
  - [X] Tests for combined usage
  - [X] Edge case tests

- [X] Documentation
  - [X] API documentation for new features
  - [X] Usage examples and type hints

## Migration Guide
For users of the existing `Injectable` type:

```python
# Old style
@task
def my_task(x: Injectable[int]) -> int:
    return x * 2

# New style
@task
def my_task(x: Annotated[int, Injectable()]) -> int:
    return x * 2

# Or using type alias
@task
def my_task(x: Injected[int]) -> int:
    return x * 2
```

## Backwards Compatibility
This change will break existing code that uses the current `Injectable` type directly. Users will need to:

1. Update their imports to use the new type aliases:
   ```python
   from purple_titanium import Injected, Ignored
   ```

2. Update their type annotations to use either:
   - The new type aliases: `Injected[T]` or `Ignored[T]`
   - The explicit `Annotated` syntax: `Annotated[T, Injectable()]` or `Annotated[T, Ignorable()]`

3. Update any code that relies on the old `Injectable` class implementation

## Limitations and Considerations
- Ignored parameters won't contribute to cache invalidation, which could lead to stale results if used incorrectly
- Type checkers must support PEP 593 to provide proper type checking
- Users should document ignored parameters clearly to maintain code clarity
- Runtime performance impact of checking annotations should be monitored
