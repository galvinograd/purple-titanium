"""Context management system for purple-titanium."""

import threading
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Optional

# Default context settings
DEFAULT_CONTEXT_SETTINGS = MappingProxyType({
    '_pt_persistence': None,
})


@dataclass(frozen=True)
class Context:
    """Immutable class that contains global settings."""
    
    _settings: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))
    _parent: Optional['Context'] = None
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize a new context with the given settings."""
        # Use object.__setattr__ to set attributes in frozen dataclass
        object.__setattr__(self, '_settings', MappingProxyType(kwargs))
        object.__setattr__(self, '_parent', None)
    
    def __len__(self) -> int:
        """Get the number of settings in the context."""
        return len([s for s in self._settings if not s.startswith('_pt_')])
    
    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Get a setting value, falling back to parent context if not found."""
        if name in self._settings:
            return self._settings[name]
        if self._parent is not None:
            return getattr(self._parent, name)
        raise AttributeError(f"Setting '{name}' not found in context or parent contexts")
    
    def replace(self, **kwargs: Any) -> 'Context':
        """Create a new context with updated settings."""
        # Create new settings dict with updated values
        new_settings = dict(self._settings)
        new_settings.update(kwargs)
        
        # Create new context with updated settings
        new_ctx = Context(**new_settings)
        # Set parent to current context
        object.__setattr__(new_ctx, '_parent', self)
        return new_ctx
    
    def __enter__(self) -> 'Context':
        """Push this context onto the stack."""
        _context_stack.push(self)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # noqa: ANN401
        """Pop this context from the stack."""
        _context_stack.pop()
    
    def __eq__(self, other: object) -> bool:
        """Compare contexts based on their settings and parent."""
        if not isinstance(other, Context):
            return NotImplemented
        return (self._settings == other._settings and 
                self._parent is other._parent)  # Compare parent identity
    
    def __hash__(self) -> int:
        """Hash based on settings and parent identity."""
        return hash((frozenset(self._settings.items()), id(self._parent)))


@dataclass
class ContextStack:
    """Thread-safe stack of contexts with a default context."""
    
    _local: threading.local = field(default_factory=threading.local)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _default_context: Context = field(default_factory=lambda: Context(**dict(DEFAULT_CONTEXT_SETTINGS)))
    
    def __post_init__(self) -> None:
        """Initialize thread-local storage."""
        self._local.stack = []
    
    def push(self, context: Context) -> 'ContextStack':
        """Push a context onto the stack."""
        with self._lock:
            if not hasattr(self._local, 'stack'):
                self._local.stack = []
            if self._local.stack:
                # Set parent to current top context
                object.__setattr__(context, '_parent', self._local.stack[-1])
            self._local.stack.append(context)
            return self
    
    def pop(self) -> Context:
        """Pop the top context from the stack."""
        with self._lock:
            if not hasattr(self._local, 'stack') or not self._local.stack:
                raise RuntimeError("Cannot pop from empty context stack")
            return self._local.stack.pop()
    
    def get_current(self) -> Context:
        """Get the current context, falling back to default if stack is empty."""
        with self._lock:
            if not hasattr(self._local, 'stack') or not self._local.stack:
                return self._default_context
            return self._local.stack[-1]

    def __enter__(self) -> 'ContextStack':
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # noqa: ANN401
        """Exit the context manager."""
        if hasattr(self._local, 'stack') and self._local.stack:
            self.pop()

# Global context stack instance
_context_stack = ContextStack()

def get_current_context() -> Context:
    """Get the current context."""
    return _context_stack.get_current() 