# RFC 05: Output Persistence

## Summary

This RFC proposes a mechanism for persisting task outputs, enabling caching across program runs and allowing for the resumption of workflows after interruptions.

## Motivation

Currently, Purple Titanium tasks are executed and their outputs are cached in memory during a single program run. However, this approach has several limitations:

1. Long-running workflows must be restarted from scratch if interrupted
2. Computationally expensive tasks must be re-executed in each program run
3. There's no way to share task results between different program executions

By implementing output persistence, we can address these limitations and provide a more robust workflow execution model.

## Detailed Design

### Task Output Serialization

We will introduce a serialization mechanism for task outputs that will:

1. Serialize task outputs to disk in a configurable location
2. Use the task's signature as a unique identifier for the cached output
3. Support different serialization formats (JSON, pickle, etc.)
4. Support for custom file registry like S3 or Weights & Biases

### Persistence Configuration

Users will be able to configure persistence behavior:

1. Cache location (local directory, S3 bucket, etc.)
2. Serialization format (JSON, pickle, safetensors)
3. Maximum cache slot size

### Cache Key Generation

Cache keys will be generated using the task signature system defined in RFC 03. This provides:

1. Deterministic identification based on task name, parameters, and version
2. Proper handling of parameters marked with `IgnoreInSignature` (RFC 04)
3. Consistent handling of injectable parameters

Example:

### API Design

```python
class OutputPersistence:
    def save(self, task_output, cache_key):
        """Save task output to persistent storage"""
        
    def load(self, cache_key):
        """Load task output from persistent storage"""
        
    def invalidate(self, cache_key=None):
        """Invalidate specific or all cached outputs"""
        
    def exists(self, cache_key):
        """Check if output exists in cache"""
```

### Error Handling

1. Storage errors (disk full, network issues)
2. Serialization errors (unsupported types)
3. Cache corruption
4. Version mismatch

### Implementation Plan

- [ ] Phase 1: Basic local file system persistence
  - [ ] Implement cache key generation
  - [ ] Add JSON serialization support
  - [ ] Add basic file system storage
  - [ ] Add configuration system

- [ ] Phase 2: Advanced features
  - [ ] Add support for custom storage
  - [ ] Implement cache invalidation
  - [ ] Add compression support
  - [ ] Add additional serialization formats

- [ ] Phase 3: Integration and testing
  - [ ] Integration with task execution pipeline
  - [ ] Add unit and integration tests
  - [ ] Performance testing
  - [ ] Documentation

### Backward Compatibility

The persistence system will be opt-in, with tasks running in-memory by default. Existing workflows will continue to work without modification.

### Performance Considerations

1. Cache hit/miss overhead
2. Serialization/deserialization time
3. Storage I/O performance
4. Network latency for remote storage
5. Memory usage during serialization

### Limitations

1. Not all Python objects may be serializable
2. Remote storage may introduce network-related issues
3. Large outputs may impact storage requirements
4. Version control of cached outputs may be complex

## Alternatives Considered

1. Database-based persistence
   - Pros: Structured storage, querying capabilities
   - Cons: Additional dependency, complexity

2. Memory-mapped files
   - Pros: Fast access, direct memory mapping
   - Cons: Limited to local storage, size limitations

3. Distributed cache (Redis, Memcached)
   - Pros: High performance, distributed access
   - Cons: Additional infrastructure, complexity

