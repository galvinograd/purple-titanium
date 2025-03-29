"""Tests for the serializers module."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pytest

from purple_titanium.serializers import (JSONSerializer, PickleSerializer,
                                         SerializationError)


@dataclass
class TestDataClass:
    """Test dataclass for serialization testing."""
    name: str
    value: int
    optional: Optional[str] = None


def test_json_serializer_basic_types():
    """Test JSON serializer with basic Python types."""
    serializer = JSONSerializer()
    
    # Test with various basic types
    test_data = {
        'int': 42,
        'float': 3.14,
        'str': 'hello',
        'bool': True,
        'none': None,
        'list': [1, 2, 3],
        'tuple': (1, 2),
        'set': {1, 2, 3},
        'dict': {'a': 1, 'b': 2}
    }
    
    # Serialize and deserialize
    serialized = serializer.serialize(test_data)
    deserialized = serializer.deserialize(serialized)
    
    # Verify the data
    assert deserialized['int'] == test_data['int']
    assert deserialized['float'] == test_data['float']
    assert deserialized['str'] == test_data['str']
    assert deserialized['bool'] == test_data['bool']
    assert deserialized['none'] == test_data['none']
    assert deserialized['list'] == test_data['list']
    assert tuple(deserialized['tuple']) == test_data['tuple']
    assert set(deserialized['set']) == test_data['set']
    assert deserialized['dict'] == test_data['dict']


def test_json_serializer_complex_types():
    """Test JSON serializer with complex Python types."""
    serializer = JSONSerializer()
    
    # Test with complex nested structures
    test_data = {
        'nested_dict': {
            'list_of_dicts': [
                {'a': 1, 'b': 2},
                {'c': 3, 'd': 4}
            ],
            'tuple_of_lists': (
                [1, 2, 3],
                [4, 5, 6]
            )
        },
        'mixed_types': [
            {'int': 1, 'str': 'hello'},
            {'float': 3.14, 'bool': True},
            {'none': None, 'list': [1, 2, 3]}
        ]
    }
    
    # Serialize and deserialize
    serialized = serializer.serialize(test_data)
    deserialized = serializer.deserialize(serialized)
    
    # Verify the data
    assert deserialized['nested_dict']['list_of_dicts'] == test_data['nested_dict']['list_of_dicts']
    assert tuple(deserialized['nested_dict']['tuple_of_lists']) == test_data['nested_dict']['tuple_of_lists']
    assert deserialized['mixed_types'] == test_data['mixed_types']


def test_json_serializer_errors():
    """Test JSON serializer error handling."""
    serializer = JSONSerializer()
    
    # Test with non-serializable object
    class NonSerializable:
        pass
    
    with pytest.raises(SerializationError):
        serializer.serialize(NonSerializable())
    
    # Test with invalid JSON bytes
    with pytest.raises(SerializationError):
        serializer.deserialize(b'invalid json')


def test_pickle_serializer_basic_types():
    """Test pickle serializer with basic Python types."""
    serializer = PickleSerializer()
    
    # Test with various basic types
    test_data = {
        'int': 42,
        'float': 3.14,
        'str': 'hello',
        'bool': True,
        'none': None,
        'list': [1, 2, 3],
        'tuple': (1, 2),
        'set': {1, 2, 3},
        'dict': {'a': 1, 'b': 2}
    }
    
    # Serialize and deserialize
    serialized = serializer.serialize(test_data)
    deserialized = serializer.deserialize(serialized)
    
    # Verify the data
    assert deserialized == test_data


def test_pickle_serializer_complex_types():
    """Test pickle serializer with complex Python types."""
    serializer = PickleSerializer()
    
    # Test with complex nested structures
    test_data = {
        'nested_dict': {
            'list_of_dicts': [
                {'a': 1, 'b': 2},
                {'c': 3, 'd': 4}
            ],
            'tuple_of_lists': (
                [1, 2, 3],
                [4, 5, 6]
            )
        },
        'mixed_types': [
            {'int': 1, 'str': 'hello'},
            {'float': 3.14, 'bool': True},
            {'none': None, 'list': [1, 2, 3]}
        ]
    }
    
    # Serialize and deserialize
    serialized = serializer.serialize(test_data)
    deserialized = serializer.deserialize(serialized)
    
    # Verify the data
    assert deserialized == test_data


def test_pickle_serializer_custom_types():
    """Test pickle serializer with custom types."""
    serializer = PickleSerializer()
    
    # Test with dataclass
    test_data = TestDataClass(name='test', value=42, optional='optional')
    
    # Serialize and deserialize
    serialized = serializer.serialize(test_data)
    deserialized = serializer.deserialize(serialized)
    
    # Verify the data
    assert isinstance(deserialized, TestDataClass)
    assert deserialized.name == test_data.name
    assert deserialized.value == test_data.value
    assert deserialized.optional == test_data.optional


def test_pickle_serializer_errors():
    """Test pickle serializer error handling."""
    serializer = PickleSerializer()
    
    # Test with invalid pickle bytes
    with pytest.raises(SerializationError):
        serializer.deserialize(b'invalid pickle data') 