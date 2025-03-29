"""API for configuring and managing persistence in Purple Titanium.

This module provides functions for setting up and interacting with
the persistence system, allowing tasks to cache their outputs across runs.
"""

import os
from pathlib import Path
from typing import Optional, Union

from purple_titanium.serializers import JSONSerializer, Serializer

from .context import Context, get_current_context
from .persistence import OutputPersistence
from .persistence_backends import FileSystemPersistence, InMemoryPersistence, PersistenceBackend

DEFAULT_FILESYSTEM_DIR = os.path.join(os.getcwd(), '.cache', 'purple_titanium')


def set_persistence(
    backend_or_output: Union[OutputPersistence, PersistenceBackend, str] = None,
    serializer: Optional[Serializer] = None,
) -> Context:
    """Configure the persistence backend for the current context.
    
    This function sets up the persistence system that will be used by tasks
    with persist=True to cache their outputs.
    
    Args:
        backend: The persistence backend to use. Can be:
                - A PersistenceBackend instance
                - "memory" for in-memory persistence (not persistent across runs)
                - "filesystem" for file-based persistence (default if None)
                - None to use the default filesystem backend
    
    Examples:
        # Use default filesystem persistence
        set_persistence()
        
        # Specify a custom cache directory
        set_persistence(cache_dir="/path/to/cache")
        
        # Use in-memory persistence (for testing)
        set_persistence("memory")
        
        # Use a custom persistence backend
        set_persistence(MyCustomPersistenceBackend())
    """
    context = get_current_context()
    
    if isinstance(backend_or_output, OutputPersistence):
        return context.replace(_pt_persistence=backend_or_output)
    
    # Handle string backend specifications
    if isinstance(backend_or_output, str):
        if backend_or_output == "memory":
            backend_or_output = InMemoryPersistence()
        elif backend_or_output == "filesystem":
            backend_or_output = FileSystemPersistence(DEFAULT_FILESYSTEM_DIR)
        else:
            raise ValueError(f"Unknown persistence backend type: {backend_or_output}")
    
    if serializer is None:
        serializer = JSONSerializer()
    
    persistence = OutputPersistence(backend=backend_or_output, serializer=serializer)
    
    return context.replace(_pt_persistence=persistence)
