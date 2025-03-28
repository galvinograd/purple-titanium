# RFC: Task Signatures

## Summary

A deterministic task signature system that uniquely identifies task instances based on their name, parameters, and version. Task signatures are calculated at task creation time and can be accessed through the context.

## Motivation

Task signatures are needed to:
- Uniquely identify task instances for caching and memoization
- Track changes in task implementations through versioning
- Enable deterministic task identification across runs
- Allow manual version control of tasks when their logic changes
- Provide a way to invalidate cached results when task logic changes

## Detailed Design

### Core Components

1. **Task Signature Generation**
The signature is a hash generated from:
- Task name
- Task parameters (values for regular params, type info for injectable params)
- Manual version number (if specified)

```python
@pt.task()
def add(x: int, y: int) -> int:
    return x + y

# Signature depends on parameters
task1 = add(1, 2)  # sig: "add-v1-1-2"
task2 = add(2, 3)  # sig: "add-v1-2-3"

# Manual versioning changes signature
@pt.task(task_version=2)
def add_v2(x: int, y: int) -> int:
    return x + y  # Same logic, different version

task3 = add_v2(1, 2)  # sig: "add_v2-v2-1-2"
```

2. **Injectable Parameter Handling**
For injectable parameters, only the type information is used in the signature since the actual values come from context:

```python
@pt.task()
def process(data: list, timeout: pt.Injectable[int]) -> list:
    return data[:timeout]

with pt.Context(timeout=30):
    # Signature uses parameter types for injectables
    task = process([1,2,3])  # sig: "process-v1-[1,2,3]-Injectable[int]"
```

3. **Signature Access**
Task signatures are accessible through both the task instance and context:

```python
@pt.task()
def example(x: int) -> int:
    return x * 2

task = example(42)
print(task.signature)  # Access directly from task

# Access from context
with pt.Context() as ctx:
    task = example(42)
    print(ctx.get_task_signature(task))
```

4. **Signature Format**
The signature format is: `{task_name}-v{version}-{param_hash}`
where:
- `task_name` is the function name
- `version` is the manual version or 1 by default
- `param_hash` is a deterministic hash of parameters

### Implementation Details

1. **Task Class Enhancement**
```python
from inspect import signature
from typing import Any, Dict, Optional

class Task:
    def __init__(self, func, args, kwargs, task_version: Optional[int] = None):
        self.func = func
        self.task_version = task_version or 1
        # Convert args/kwargs to a unified parameter dict
        self.parameters = self._build_parameter_dict(args, kwargs)
        # Calculate signature during task initialization
        self.signature = self._calculate_signature()

    def _build_parameter_dict(self, args, kwargs):
        """Convert args and kwargs into a single parameter dictionary using parameter names."""
        func_sig = signature(self.func)
        bound_args = func_sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return dict(bound_args.arguments)

    def _calculate_signature(self):
        hasher = xxhash.xxh64()
        
        # Add task name
        hasher.update(self.func.__name__.encode())
        
        # Add version
        hasher.update(str(self.task_version).encode())
        
        # Hash parameters by name (order-invariant)
        self._hash_parameters(hasher, self.parameters)
        
        return hasher.intdigest()

    def _hash_parameters(self, hasher, parameters):
        # Sort by parameter name for deterministic ordering
        for param_name in sorted(parameters.keys()):
            value = parameters[param_name]
            # Hash parameter name
            hasher.update(param_name.encode())
            # Hash parameter value
            self._hash_value(hasher, value)

    def _hash_value(self, hasher, value):
        if isinstance(value, LazyOutput):
            # For nested tasks, use their signature
            dep_sig = value.owner.signature
            hasher.update(dep_sig.to_bytes(8, 'big'))
        elif isinstance(value, (list, tuple)):
            # Hash sequence type
            hasher.update(type(value).__name__.encode())
            # Hash length for additional safety
            hasher.update(len(value).to_bytes(8, 'big'))
            # Hash items
            for item in value:
                self._hash_value(hasher, item)
        elif isinstance(value, dict):
            hasher.update(b'dict')
            # Sort by key for deterministic ordering
            for key in sorted(value.keys()):
                hasher.update(str(key).encode())
                self._hash_value(hasher, value[key])
        else:
            # For basic types, hash type and value
            hasher.update(type(value).__name__.encode())
            hasher.update(str(value).encode())

2. **Signature Cascading Example**
```python
@pt.task()
def add(x: int, y: int) -> int:
    return x + y

@pt.task()
def multiply(x: int, y: int) -> int:
    return x * y

# Define task composition at the top level
sum_ab = add(1, 2)      # Task 1
sum_bc = add(2, 3)      # Task 2
result = multiply(sum_ab, sum_bc)  # Task 3

# The signatures cascade naturally:
# - sum_ab signature depends on add function name, version, and parameters {x: 1, y: 2}
# - sum_bc signature depends on add function name, version, and parameters {x: 2, y: 3}
# - result signature depends on multiply function name, version, and the signatures of sum_ab and sum_bc

# Example with injectable parameters
@pt.task()
def process_data(
    data: list,
    config: pt.Injectable[Dict[str, Any]]
) -> list:
    return [x * config['multiplier'] for x in data]

# The injectable parameter is unwrapped and hashed recursively
with pt.Context(config={'multiplier': 2, 'options': {'normalize': True}}):
    task1 = process_data([1, 2, 3])
    # Signature includes:
    # - function name
    # - version
    # - data parameter ([1, 2, 3])
    # - unwrapped and recursively hashed config dictionary
```

3. **Parameter Order Invariance Example**
```python
@pt.task()
def process(x: int, y: int, z: int = 0) -> int:
    return x + y + z

# All these calls produce the same signature
t1 = process(1, 2)
t2 = process(y=2, x=1)
t3 = process(x=1, y=2, z=0)

assert t1.owner.signature == t2.owner.signature == t3.owner.signature

# Different parameter values produce different signatures
t4 = process(y=2, x=2)
assert t1.owner.signature != t4.owner.signature
```

Key corrections:
1. Removed task creation within tasks as it's not allowed per the pipeline framework
2. Changed Injectable handling to recursively hash the wrapped value instead of just the type info
3. Showed proper task composition at the top level
4. Demonstrated how injectable parameters are unwrapped and hashed recursively like other container types

## Implementation Plan

1. Core Signature Implementation
- [X] Implement signature calculation logic
- [X] Add version support to task decorator
- [X] Create parameter stringification utilities
- [X] Add signature storage to Task class

2. Testing
- [X] Test signature determinism
- [X] Test version changes
- [X] Test injectable parameter handling
- [X] Test context integration
- [X] Test edge cases (empty params, special characters, unhashable objs)

3. Documentation
- [X] Document signature format
- [X] Provide versioning guidelines
- [X] Create usage examples
- [X] Document context integration

## Code References

- [Pipeline Framework RFC](rfcs/01-pipeline-framework.md)
- [Context RFC](rfcs/02-context.md)
