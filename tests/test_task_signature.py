"""Tests for task signature functionality."""

import logging
import subprocess
import sys
from typing import Any

import purple_titanium as pt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    def process(data: list, config: pt.Injected[dict[str, Any]]) -> list:
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

def test_ignored_signature() -> None:
    """Test that ignored parameters don't affect the task signature."""
    @pt.task()
    def process_with_ignored(
        data: list, 
        multiplier: int, 
        debug_mode: pt.Ignored[bool] = False
    ) -> list:
        if debug_mode:
            logger.info(f"Processing data with multiplier {multiplier}")
        return [x * multiplier for x in data]
    
    # Create tasks with same core parameters but different ignored parameters
    task1 = process_with_ignored([1, 2, 3], 2, debug_mode=False)
    task2 = process_with_ignored([1, 2, 3], 2, debug_mode=True)
    
    # Ignored parameters should not affect the signature
    assert task1.owner.signature == task2.owner.signature
    
    # Different core parameters should still result in different signatures
    task3 = process_with_ignored([1, 2, 3], 3, debug_mode=False)
    assert task1.owner.signature != task3.owner.signature
    
    # Different data should also result in different signatures
    task4 = process_with_ignored([1, 2, 4], 2, debug_mode=True)
    assert task1.owner.signature != task4.owner.signature

def test_mixed_annotations_signature() -> None:
    """Test signature generation with both ignored and injected parameters."""
    @pt.task()
    def complex_process(
        data: list,
        multiplier: int,
        config: pt.Injected[dict[str, Any]] = None,
        verbose: pt.Ignored[bool] = False
    ) -> list:
        if verbose:
            logger.info(f"Using config: {config}")
        return [x * multiplier * config.get('factor', 1) for x in data]
    
    # Create tasks with same core parameters but different ignored parameters
    task1 = complex_process([1, 2, 3], 2, verbose=False)
    task2 = complex_process([1, 2, 3], 2, verbose=True)
    
    # Ignored parameters should not affect the signature
    assert task1.owner.signature == task2.owner.signature
    
    # Different core parameters should result in different signatures
    task3 = complex_process([1, 2, 3], 3, verbose=False)
    assert task1.owner.signature != task3.owner.signature

def test_nested_ignored_in_dataclass() -> None:
    """Test that ignored parameters in nested dataclasses don't affect signatures."""
    from dataclasses import dataclass
    
    @dataclass
    class ProcessingConfig:
        factor: int
        debug_level: pt.Ignored[int] = 0
        verbose_output: pt.Ignored[bool] = False
    
    @pt.task()
    def process_with_config(
        data: list,
        config: ProcessingConfig
    ) -> list:
        if config.verbose_output:
            logger.info(f"Processing with factor {config.factor}, debug level {config.debug_level}")
        return [x * config.factor for x in data]
    
    # Create configs with same core parameters but different ignored parameters
    config1 = ProcessingConfig(factor=2, debug_level=0, verbose_output=False)
    config2 = ProcessingConfig(factor=2, debug_level=3, verbose_output=True)
    
    # Create tasks with these configs
    task1 = process_with_config([1, 2, 3], config1)
    task2 = process_with_config([1, 2, 3], config2)
    
    # Ignored parameters in the dataclass should not affect the signature
    assert task1.owner.signature == task2.owner.signature
    
    # Different core parameters in the dataclass should result in different signatures
    config3 = ProcessingConfig(factor=3, debug_level=0, verbose_output=False)
    task3 = process_with_config([1, 2, 3], config3)
    assert task1.owner.signature != task3.owner.signature
    
    # Different input data should still result in different signatures
    task4 = process_with_config([1, 2, 4], config1)
    assert task1.owner.signature != task4.owner.signature


def test_nested_ignored_in_dataclass_2() -> None:
    """Test that ignored parameters in nested dataclasses don't affect signatures."""
    from dataclasses import dataclass
    
    @dataclass
    class NestedConfig:
        factor: int
        debug_level: pt.Ignored[int] = 0
        verbose_output: pt.Ignored[bool] = False
    
    @dataclass
    class OuterConfig:
        inner: NestedConfig
    
    @pt.task()
    def process_with_outer_config(
        data: list,
        config: OuterConfig
    ) -> list:
        if config.inner.verbose_output:
            logger.info(f"Processing with factor {config.inner.factor}, debug level {config.inner.debug_level}")
        return [x * config.inner.factor for x in data]
    
    # Create configs with same core parameters but different ignored parameters
    config1 = OuterConfig(inner=NestedConfig(factor=2, debug_level=0, verbose_output=False))
    config2 = OuterConfig(inner=NestedConfig(factor=2, debug_level=3, verbose_output=True))

    # Create tasks with these configs
    task1 = process_with_outer_config([1, 2, 3], config1)
    task2 = process_with_outer_config([1, 2, 3], config2)
    
    # Ignored parameters in the nested dataclass should not affect the signature
    assert task1.owner.signature == task2.owner.signature
    
    # Different core parameters in the nested dataclass should result in different signatures
    config3 = OuterConfig(inner=NestedConfig(factor=3, debug_level=0, verbose_output=False))
    task3 = process_with_outer_config([1, 2, 3], config3)
    assert task1.owner.signature != task3.owner.signature