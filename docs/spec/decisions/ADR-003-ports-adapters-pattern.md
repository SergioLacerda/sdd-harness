# ADR-003: Ports & Adapters Pattern (Hexagonal Architecture)

## Status
- **Accepted** ✅
- Proposed: 2025-08-01
- Accepted: 2025-08-08
- Review Date: 2027-08-01

---

## Context

**Problem**:
System needs to support multiple implementations:
- Storage: JSON file today, but need PostgreSQL tomorrow
- Vector index: ChromaDB today, but Pinecone/Qdrant possible
- LLM: OpenAI today, but local LLMs possible tomorrow
- Executor: ThreadPool today, but Ray/Dask possible

Changing implementations shouldn't require rewriting business logic.

---

## Decision

**Implement 10 Ports (abstraction layer)**:

1. **KeyValueStorePort** - Campaign-level key-value store
2. **VectorStorePort** - Vector database operations
3. **DocumentStorePort** - Long-form document storage
4. **VectorReaderPort** - Query vector database (semantic search, read-only)
5. **VectorWriterPort** - Index new vectors (bulk insert operations)
6. **LLMServicePort** - LLM calls (OpenAI, local, etc.)
7. **EmbeddingGateway** - Embedding generation
8. **CampaignRepositoryPort** - Campaign CRUD
9. **ExecutorPort** - CPU-bound work delegation
10. **EventBusPort** - Async event dispatch & lifecycle (NEW - April 2026)

**Why ports?**
- Business logic never knows which implementation is used
- Easy to test (mock implementations)
- Easy to swap implementations
- Clear responsibility boundaries

**Why 10? (Changed from 9)**
- More specific ports = better separation
- Each port has one responsibility
- Future implementations can implement only needed ports
- **[MARKER: Vector Ports]** Separation of VectorReader/VectorWriter allows read-only deployments
- **[MARKER: EventBusPort]** Added for independent lifecycle management from ExecutorPort

**DECISION POINTS DOCUMENTED:**
- See section "Current Implementation Status" below for implementation notes
- See architecture.md "Vector Index" section for factory pattern requirements

---

## Consequences

### Positive ✅
- Easy to test business logic (mock ports)
- Easy to add new implementations (new adapter)
- No infrastructure leakage into business logic
- Multiple adapters can be chained (caching, retrying)

### Negative ⚠️
- More boilerplate (need port + adapter for each operation)
- Learning curve (need to understand abstraction)
- Abstraction can leak (exceptions, timeouts)
- Performance cost if not designed well

### Risk 🚨
- Ports can become too coarse (lose benefits)
- Ports can become too fine (too many ports)
- Breaking port changes affect multiple adapters
- Contracts not validated automatically

---

## Alternatives Considered

### 1. Dependency Injection only (no explicit ports)
**Rejected because**: Unclear what implementations are possible, hard to understand dependencies.

### 2. Single monolithic port
**Rejected because**: Would require all adapters to implement everything, loses separation benefits.

### 3. Mix of ports and direct imports
**Rejected because**: Inconsistent, infrastructure can still leak in some places.

---

## Related ADRs
- ADR-001: Clean Architecture (Layer 3 is ports)
- ADR-002: Async-First (all ports must be async)

---

## Port Specifications

See: [current-system-state/contracts.md](../current-system-state/contracts.md)

Each port has:
- Interface definition
- Guaranteed behavior
- What can change
- What can't change
- Example implementations

---

## Current Implementation Status

- ✅ All 9 ports defined
- ✅ KeyValueStorePort (JSONFileStore adapter)
- ✅ VectorStorePort (ChromaDB adapter)
- ✅ DocumentStorePort (JSONAppendOnly adapter)
- ✅ VectorReaderPort implemented
- ✅ VectorWriterPort implemented
- ✅ LLMServicePort (OpenAI adapter)
- ✅ EmbeddingGateway (hardcoded concurrency)
- ✅ CampaignRepositoryPort (JSONFile adapter)
- ✅ ExecutorPort (ThreadPool adapter)
- ✅ VectorReaderPort (Search operations)
- ✅ VectorWriterPort (Indexing operations)
- ✅ EventBusPort (Event dispatch + async lifecycle) [NEW: April 2026]

**[MARKER: Implementation Gap]** EventBusPort added April 2026:
- Reason: Phase 1 implementation requires async lifecycle methods (start(), shutdown(), run_async())
- Note: Was not in original 9 ports spec
- Consider: ADR may need clarification on whether EventBusPort should be distinct or part of ExecutorPort
- Decision Made: Kept separate for independent lifecycle management

---

## Future Implementations

Possible future adapters:
- PostgreSQL for KeyValueStore
- Qdrant for VectorStore
- S3 for DocumentStore
- Local Ollama for LLMService
- Ray for ExecutorPort

---

## ✅ Validation

**How to verify this decision is working:**

### Metrics to Monitor

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Port usage | 100% for infra | Code analysis |
| Direct adapter access | 0 | Linting rule |
| Port implementations | 1-3 per port | Service test coverage |
| Port contract violations | 0 | Runtime validation |
| Adapter swap success | 100% | Integration tests |

### Automated Validation

```bash
# Check all infrastructure access via ports
pytest tests/contracts/ -v

# Verify no direct adapter instantiation
grep -r "from.*adapters.*import" src/usecases/ | wc -l  # Should be 0

# Check all adapters implement ports
pytest tests/architecture/test_port_compliance.py -v

# Run adapter swap tests
pytest tests/integration/test_adapter_swaps.py -v
```

### Manual Validation

1. **Port Usage Checklist**
   - [ ] All ports defined with clear interface
   - [ ] All adapters implement ports correctly
   - [ ] No bypassing of ports
   - [ ] Port methods async-first
   - [ ] Port error types consistent

2. **Integration Testing**
   - Swap implementations (JSON ↔ DB, ChromaDB ↔ Pinecone)
   - Verify behavior unchanged
   - Check error handling same
   - Measure performance difference

3. **Compliance Testing**
   - Verify each port interface
   - Check method signatures match
   - Validate error contracts
   - Confirm async behavior

### Success Criteria

✅ Architecture compliance:
- All infrastructure access via ports
- Zero direct adapter access in usecases
- All adapters pass contract tests

✅ Integration testing:
- Adapter swaps work seamlessly
- Behavior identical between adapters
- Error handling consistent

✅ Runtime behavior:
- No "adapter not found" errors
- Clean dependency injection
- Fast adapter startup

---

## Next Review: August 1, 2027

Consider:
- Are ports being used correctly?
- Any port being bypassed?
- Any new infrastructure needs that need new port?
- Performance of current adapters sufficient?
