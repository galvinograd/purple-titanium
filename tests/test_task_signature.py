"""Tests for task signature functionality."""

import subprocess
import sys
from typing import Any

import purple_titanium as pt
from purple_titanium.types import Injectable


def test_basic_signature() -> None:
    """Test basic task signature generation."""
    @pt.task()
    def add(x: int, y: int) -> int:
        return x + y

    task1 = add(1, 2)
    task2 = add(2, 3)
    task3 = add(1, 2)

    # Different parameters should have different signatures
    assert task1.owner.signature != task2.owner.signature
    # Same parameters should have same signature
    assert task1.owner.signature == task3.owner.signature

def test_version_signature() -> None:
    """Test that task version affects signature."""
    @pt.task()
    def add(x: int, y: int) -> int:
        return x + y

    @pt.task(task_version=2)
    def add_v2(x: int, y: int) -> int:
        return x + y

    task1 = add(1, 2)
    task2 = add_v2(1, 2)

    # Same parameters but different versions should have different signatures
    assert task1.owner.signature != task2.owner.signature

def test_parameter_order_invariance() -> None:
    """Test that parameter order doesn't affect signature."""
    @pt.task()
    def process(x: int, y: int, z: int = 0) -> int:
        return x + y + z

    task1 = process(1, 2)
    task2 = process(y=2, x=1)
    task3 = process(x=1, y=2, z=0)

    # All these calls should have the same signature
    assert task1.owner.signature == task2.owner.signature
    assert task1.owner.signature == task3.owner.signature

    # Different parameter values should have different signatures
    task4 = process(y=2, x=2)
    assert task1.owner.signature != task4.owner.signature

def test_injectable_signature() -> None:
    """Test signature generation with injectable parameters."""
    @pt.task()
    def process(data: list, config: Injectable[dict[str, Any]]) -> list:
        return [x * config['multiplier'] for x in data]

    with pt.Context(config={'multiplier': 2}):
        task1 = process([1, 2, 3])

    with pt.Context(config={'multiplier': 3}):
        task2 = process([1, 2, 3])

    # Same parameters should have different signature due to different injected values
    assert task1.owner.signature != task2.owner.signature

def test_nested_signature() -> None:
    """Test signature generation with nested tasks."""
    @pt.task()
    def add(x: int, y: int) -> int:
        return x + y

    @pt.task()
    def multiply(x: int, y: int) -> int:
        return x * y

    # Define task composition at the top level
    sum_ab = add(1, 2)
    sum_bc = add(2, 3)
    result = multiply(sum_ab, sum_bc)

    # Verify signatures are different for different parameters
    assert sum_ab.owner.signature != sum_bc.owner.signature
    # Verify result signature depends on both input task signatures
    assert result.owner.signature != sum_ab.owner.signature
    assert result.owner.signature != sum_bc.owner.signature

def test_container_signature() -> None:
    """Test signature generation with container types."""
    @pt.task()
    def process(data: list, options: dict) -> list:
        return data

    task1 = process([1, 2, 3], {'normalize': True})
    task2 = process([1, 2, 3], {'normalize': False})
    task3 = process([1, 2, 3], {'normalize': True})

    # Different container contents should have different signatures
    assert task1.owner.signature != task2.owner.signature
    # Same container contents should have same signature
    assert task1.owner.signature == task3.owner.signature

def test_complex_types_signature() -> None:
    """Test signature generation with complex Python types."""
    @pt.task()
    def process(
        data: list[int],
        options: dict[str, int | str],
        flags: set[bool],
        coords: tuple[float, float],
        nullable: str | None,
        mixed: int | str | list[float]
    ) -> list[int]:
        return data

    # Test with different complex types
    task1 = process(
        data=[1, 2, 3],
        options={'size': 10, 'mode': 'fast'},
        flags={True, False},
        coords=(1.5, 2.5),
        nullable=None,
        mixed=[1.0, 2.0]
    )

    task2 = process(
        data=[1, 2, 3],
        options={'size': 10, 'mode': 'fast'},
        flags={True, False},
        coords=(1.5, 2.5),
        nullable=None,
        mixed=[1.0, 2.0]
    )

    # Same complex parameters should have same signature
    assert task1.owner.signature == task2.owner.signature

    # Different complex parameters should have different signatures
    task3 = process(
        data=[1, 2, 3],
        options={'size': 20, 'mode': 'fast'},  # Different size
        flags={True, False},
        coords=(1.5, 2.5),
        nullable=None,
        mixed=[1.0, 2.0]
    )
    assert task1.owner.signature != task3.owner.signature

def test_edge_cases_signature() -> None:
    """Test signature generation with edge cases."""
    @pt.task()
    def process(
        empty_list: list,
        empty_dict: dict,
        empty_set: set,
        empty_tuple: tuple,
        none_value: None,
        zero: int,
        empty_str: str,
        special_chars: str
    ) -> Any:  # noqa: ANN401
        return empty_list

    # Test with various edge cases
    task1 = process(
        empty_list=[],
        empty_dict={},
        empty_set=set(),
        empty_tuple=(),
        none_value=None,
        zero=0,
        empty_str="",
        special_chars="!@#$%^&*()"
    )

    task2 = process(
        empty_list=[],
        empty_dict={},
        empty_set=set(),
        empty_tuple=(),
        none_value=None,
        zero=0,
        empty_str="",
        special_chars="!@#$%^&*()"
    )

    # Same edge cases should have same signature
    assert task1.owner.signature == task2.owner.signature

    # Different edge cases should have different signatures
    task3 = process(
        empty_list=[],
        empty_dict={},
        empty_set=set(),
        empty_tuple=(),
        none_value=None,
        zero=0,
        empty_str="",
        special_chars="!@#$%^&*()+"  # Different special chars
    )
    assert task1.owner.signature != task3.owner.signature

def test_nested_containers_signature() -> None:
    """Test signature generation with deeply nested containers."""
    @pt.task()
    def process(
        nested_list: list[list[list[int]]],
        nested_dict: dict[str, dict[str, list[float]]],
        mixed_nested: dict[str, list[dict[str, set[int]]]]
    ) -> Any:  # noqa: ANN401
        return nested_list

    # Test with deeply nested containers
    task1 = process(
        nested_list=[[[1, 2], [3]], [[4]]],
        nested_dict={'a': {'b': [1.0, 2.0]}, 'c': {'d': [3.0]}},
        mixed_nested={'x': [{'y': {1, 2}}, {'z': {3}}]}
    )

    task2 = process(
        nested_list=[[[1, 2], [3]], [[4]]],
        nested_dict={'a': {'b': [1.0, 2.0]}, 'c': {'d': [3.0]}},
        mixed_nested={'x': [{'y': {1, 2}}, {'z': {3}}]}
    )

    # Same nested containers should have same signature
    assert task1.owner.signature == task2.owner.signature

    # Different nested containers should have different signatures
    task3 = process(
        nested_list=[[[1, 2], [3]], [[4]]],
        nested_dict={'a': {'b': [1.0, 2.0]}, 'c': {'d': [3.0]}},
        mixed_nested={'x': [{'y': {1, 2}}, {'z': {4}}]}  # Different value in nested set
    )
    assert task1.owner.signature != task3.owner.signature

def test_cross_process_signature() -> None:
    """Test that signatures remain consistent across different Python processes."""
    # Run the task in the current process
    # Run the same task in a different process
    def run_task(test_different_params: bool = False) -> int:
        # Using sys.executable and hardcoded path, so this is safe
        result = subprocess.run(  # noqa: S603
            [sys.executable, 'tests/test_signature_process.py'],
            capture_output=True,
            text=True,
            check=True,
            env={'TEST_DIFFERENT_PARAMS': '1' if test_different_params else '0'}
        )
        return int(result.stdout.strip())

    sig1 = run_task()
    sig2 = run_task()
    
    # Signatures should be identical across processes
    assert sig1 == sig2, (
        f"Signatures differ across processes: {sig1} != {sig2}"
    )

    # Run with different parameters in the other process
    sig3 = run_task(test_different_params=True)

    # Different parameters should have different signatures
    assert sig1 != sig3, (
        "Signatures should differ for different parameters"
    )
