"""Signature-related functionality for purple-titanium."""

from typing import Annotated, TypeVar

T = TypeVar('T')

class Ignorable:
    """Marks a parameter to be ignored in signature calculation."""
    pass

class Injectable:
    """Marks a parameter as injectable from context."""
    pass


# Type aliases for improved ergonomics
Ignored = Annotated[T, Ignorable()]
Injected = Annotated[T, Injectable()]
