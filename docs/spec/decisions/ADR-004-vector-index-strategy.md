# ADR-004: Vector Index Strategy (ChromaDB with IVF)

## Status
- **Accepted** ✅
- Proposed: 2025-09-01
- Accepted: 2025-09-10
- Review Date: 2027-09-01

---

## Context

**Problem**:
System needs semantic search over narrative documents.
- 10-50 documents per campaign
- 50-200 campaigns active
- Sub-second query latency required
- In-memory is acceptable for now
- Future: May need distributed search

**Scale constraints**:
- ~5,000-10,000 total vectors across all campaigns
- Queries per second: 10-50 peak
- Accuracy: Better than keyword search

---

## Decision

**Use ChromaDB with IVF (Inverted File) for in-memory vector indexing**:

- **Store**: ChromaDB (in-memory)
- **Index type**: IVF (Inverted File, ~1000-5000 clusters)
- **Embedding model**: OpenAI (text-embedding-3-small)
- **Similarity metric**: Cosine distance
- **Persistence**: Campaign-specific (recreate on startup)

**Why ChromaDB?**
- Python-native, easy integration
- Multiple index types available
- Built-in support for metadata filtering
- Good performance for our scale

**Why IVF?**
- Better than flat indexing at 5K+ vectors
- Configurable accuracy/speed trade-off
- Good for our scale (10-50 docs per campaign)

---

## Consequences

### Positive ✅
- Sub-100ms query latency
- Easy to deploy (in-memory)
- No external service dependency
- Good enough for current scale

### Negative ⚠️
- Index rebuilt on startup (~5-10s)
- Can't share index across instances
- In-memory only (limited to available RAM)
- IVF has approximate results (can miss documents)

### Risk 🚨
- Index rebuild is slow at scale (> 1000 docs per campaign)
- IVF sometimes returns wrong results (false negatives)
- Concurrency issues with index updates
- No persistence (loss on crash)

---

## Alternatives Considered

### 1. Elasticsearch
**Rejected because**: Overkill for current scale, additional deployment complexity, cost.

### 2. Pinecone
**Rejected because**: External dependency, monthly cost, adds network latency.

### 3. FAISS
**Rejected because**: Lower-level, more setup required, ChromaDB wraps it anyway.

### 4. Flat Indexing (no IVF)
**Rejected because**: Linear search too slow at 5K vectors, latency > 500ms.

---

## Current Implementation Status

**Status**: ✅ In Production (local deployments), 🟡 Monitoring (scale 5k-50k)

### Implementation Checklist
- [x] ChromaDB 0.4.24+ integrated with IVF + HNSW fallback
- [x] JSON persistence layer (vector_index/persistence/json_adapter.py)
- [x] Pydantic-compatible serialization (NDArray → List[float])
- [x] Async query interface (non-blocking I/O)
- [x] Local deployment tested up to 50k vectors
- [ ] PostgreSQL migration path (blocked on >50k threshold)
- [ ] Sharding strategy for horizontal scaling
- [ ] Distributed index coordination (Ray/Celery consideration)

### Known Limitations
- IVF degradation observed at 40k+ vectors (requires nprobe tuning)
- No distributed lock mechanism (single-writer assumption)
- Memory usage: ~2.5GB per 50k vectors (+ embedding model)

### Next Checkpoint
- Evaluate at 50k events (Q3 2026)
- Benchmark against Pinecone cost/performance
- Prototype PostgreSQL adapter

---

## Related ADRs
- ADR-003: Ports & Adapters (VectorStorePort)
- ADR-002: Async-First (queries must be async)

---

## Known Issues

See: [current-system-state/known_issues.md](../current-system-state/known_issues.md)

- 🔴 CRITICAL: IVF lazy initialization race condition
- 🟡 MEDIUM: Sometimes returns incomplete results
- 🟢 LOW: Vector cleanup exceptions swallowed

---

## Scaling Path

**Current tier** (5-10K vectors):
- ChromaDB IVF = sufficient

**Next tier** (100K vectors):
- Shard by campaign
- OR migrate to Pinecone
- OR Elasticsearch + fallback search

**Enterprise tier** (1M+ vectors):
- Distributed Pinecone/Qdrant
- Metadata-based pre-filtering
- Caching layer

---

## Implementation Notes

See: [current-system-state/rag_pipeline.md](../current-system-state/rag_pipeline.md)

8-component RAG pipeline:
1. Query expansion
2. Embedding stage
3. ANN pre-filter
4. Candidate retrieval
5. Narrative expansion
6. Candidate control
7. Context prioritization
8. Ranking pipeline

---

## ✅ Validation

**How to verify this decision is working:**

### Metrics to Monitor

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Query latency P99 | < 100ms | Benchmark tests |
| Index rebuild time | < 10s | Startup timing |
| False negative rate | < 1% | Accuracy tests |
| Memory per 1k vectors | ~2.5MB | Memory profiling |
| Concurrent queries | 50+ RPS | Load testing |

### Automated Validation

```bash
# Benchmark vector search performance
pytest tests/quality/test_performance_slos.py -k "vector" -v

# Test accuracy (recall/precision)
pytest tests/integration/test_vector_accuracy.py -v

# Memory profiling
python -m memory_profiler scripts/profile_vector_index.py

# Index rebuild timing
time python scripts/rebuild_vector_index.py
```

### Manual Validation

1. **Performance Benchmarks**
   - Query 1k vectors with random queries
   - Measure P50, P95, P99 latencies
   - Verify all < SLO
   - Check consistency

2. **Accuracy Testing**
   - Create known dataset
   - Query for specific documents
   - Measure recall (found/total)
   - Measure precision (correct/found)

3. **Scaling Tests**
   - Add vectors incrementally (1k, 5k, 10k, 50k)
   - Measure latency at each step
   - Verify index rebuild time < 10s
   - Check memory usage linear

### Success Criteria

✅ Performance targets met:
- Query latency P99 < 100ms
- Index rebuild < 10s
- Supports 50k+ vectors
- 50+ concurrent queries/sec

✅ Accuracy targets met:
- Recall > 95% (finds 95% of relevant docs)
- Precision > 90% (90% of results relevant)
- False negatives < 1%

✅ Scaling plan in place:
- Current tier (5-10k): ChromaDB IVF ✅
- Next tier (50-100k): Evaluate Pinecone/Qdrant
- Enterprise tier (1M+): Distributed solution

---

## Next Review: September 1, 2027

Consider:
- How many vectors in largest campaign?
- Query latency? (< 100ms desired)
- Any false negative issues?
- Time to migrate to distributed vector DB?
