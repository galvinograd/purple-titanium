<p align="center">
  <img src="https://raw.githubusercontent.com/galvinograd/purple-titanium/main/assets/logo.png" alt="Purple Titanium Logo" width="100"/>
</p>

# Purple Titanium

A Python pipeline framework that provides a structured way to define and execute task-based data processing workflows.

## Example

Here's a comprehensive example demonstrating the pipeline framework's features:

```python
import purple_titanium as pt
from typing import List, Dict, Optional

# Define tasks with type hints for better clarity
@pt.task()
def fetch_data() -> List[int]:
    """Simulates fetching data from a source."""
    return [1, 2, 3, 4, 5]

@pt.task()
def validate_data(data: List[int]) -> List[int]:
    """Validates the input data."""
    if not data:
        raise ValueError("Data cannot be empty")
    if not all(isinstance(x, int) for x in data):
        raise TypeError("All elements must be integers")
    return data

@pt.task()
def process_data(data: List[int]) -> List[int]:
    """Processes the data by applying transformations."""
    return [x * 2 for x in data]

@pt.task()
def analyze_data(data: List[int]) -> Dict[str, float]:
    """Analyzes the processed data and returns statistics."""
    return {
        "sum": sum(data),
        "average": sum(data) / len(data),
        "count": len(data)
    }

# Event listeners for monitoring pipeline execution
@pt.listen(pt.TASK_STARTED)
def on_task_started(event):
    print(f"Task {event.task.name} started")

@pt.listen(pt.TASK_FINISHED)
def on_task_finished(event):
    print(f"Task {event.task.name} finished successfully")

@pt.listen(pt.TASK_FAILED)
def on_task_failed(event):
    print(f"Task {event.task.name} failed: {event.task.exception}")

# Create the pipeline with error handling
try:
    # Define the pipeline
    raw_data = fetch_data()
    validated_data = validate_data(raw_data)
    processed_data = process_data(validated_data)
    analysis = analyze_data(processed_data)

    # Execute the pipeline
    result = analysis.resolve()
    print("Pipeline completed successfully!")
    print(f"Analysis results: {result}")
    # Expected output:
    # Analysis results: {'sum': 30, 'average': 6.0, 'count': 5}

except ValueError as e:
    print(f"Validation error: {e}")
except TypeError as e:
    print(f"Type error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Example of checking task existence
print(f"Raw data task exists: {raw_data.exists()}")  # True
print(f"Analysis task exists: {analysis.exists()}")  # True
```

This example demonstrates several key features of the framework:

1. **Task Definition**
   - Tasks are created using the `@pt.task()` decorator
   - Type hints provide clear interface definitions
   - Each task has a single responsibility

2. **Dependency Management**
   - Tasks can depend on other tasks through their parameters
   - Dependencies are automatically resolved
   - The framework ensures correct execution order

3. **Error Handling**
   - Tasks can raise exceptions that propagate through the pipeline
   - Exceptions can be caught at any level
   - Failed tasks maintain their error state

4. **Event System**
   - Event listeners can monitor pipeline execution
   - Events are emitted for task start, completion, and failure
   - Custom event handling enables monitoring and logging

5. **Task State**
   - The `exists()` method checks if a task has been executed
   - Task state persists after execution
   - Failed tasks maintain their error state

6. **Pipeline Execution**
   - The `resolve()` method executes the pipeline
   - Only one `resolve()` call is allowed in the call stack
   - Results are cached for efficiency

## Code Contribution

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/purple-titanium.git
   cd purple-titanium
   ```

2. Install uv if you don't have it already:
   ```bash
   pip install uv
   ```

3. Set up the development environment:
   ```bash
   uv venv
   uv pip install -e ".[dev]"  # Installs package in editable mode with dev dependencies
   ```

### Development Tools

- **Testing**: Run the test suite
  ```bash
  pytest
  ```

- **Code Quality**:
  ```bash
  # Run linting checks
  ruff check .
  
  # Format code
  ruff format .
  ```

### Contributing Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License

Copyright (c) 2024 Purple Titanium Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 