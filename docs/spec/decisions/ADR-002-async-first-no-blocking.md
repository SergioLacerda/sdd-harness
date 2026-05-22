# ADR-002: Async-First, No Blocking Operations

## Status
- **Accepted** ✅
- Proposed: 2025-07-01
- Accepted: 2025-07-05
- Review Date: 2027-07-01

---

## Context

**Problem**:
System needs to handle 50-200 concurrent users, each with their own campaign state. A traditional threaded approach would require 50-200 threads, each blocking.

**Scale Requirements**:
- 50-200 campaigns running simultaneously
- 10-50 requests/second during peak
- Sub-second response times required
- Limited CPU/memory (single machine initially)

---

## Decision

**All I/O must be async (asyncio). No blocking operations.**

Rules:
- ✅ Use `async def`, `await`
- ✅ Use asyncio primitives (locks, queues, events)
- ✅ Delegate CPU-bound work to ExecutorPort (thread pool)
- ❌ No `time.sleep()`, use `asyncio.sleep()`
- ❌ No synchronous file I/O
- ❌ No blocking calls from libraries

**Why async-first?**
- Single event loop can handle 100+ concurrent tasks
- Memory usage is lower (tasks, not threads)
- Context switching is faster (no OS scheduler)
- Scales better with I/O-heavy operations

---

## Consequences

### Positive ✅
- Can handle 50-200 concurrent campaigns on single machine
- Low memory footprint
- Fast context switching between tasks
- Easier to reason about (single-threaded event loop)

### Negative ⚠️
- Learning curve (async/await is different mental model)
- Blocking calls can crash entire system (one blocked task blocks all)
- Debugging is harder (stack traces less clear)
- Libraries must support async (or we wrap them)

### Risk 🚨
- One blocking call kills performance for all users
- No true parallelism (CPU-bound tasks will be slow)
- Race conditions from shared state
- Forget to await and code silently fails

---

## Alternatives Considered

### 1. Threaded (Thread Pool + Locks)
**Rejected because**: 50-200 threads would use too much memory, context switching overhead, GIL limits Python parallelism.

### 2. ProcessPool (Multi-processing)
**Rejected because**: Inter-process communication is complex, state sharing is hard, startup time is slow.

### 3. Hybrid (Async + Threads for CPU work)
**Chosen partly**: We do use ThreadPoolExecutor for CPU-bound work via ExecutorPort, but I/O stays async.

### 4. Sync with Queue (Old approach)
**Rejected because**: Queue-based sync is slower than async events, hard to scale.

---

## Related ADRs
- ADR-001: Clean Architecture (affects all layers)
- ADR-003: Ports & Adapters (ExecutorPort for CPU work)

---

## Rules for Implementation

When implementing:
- **I/O**: Always async/await
- **Waiting**: Use asyncio primitives (Event, Lock, Queue)
- **CPU-bound**: Delegate to ExecutorPort
- **Sleep**: Never use time.sleep(), use asyncio.sleep()
- **File I/O**: Never use open(), use aiofiles or similar

See: [threading_concurrency.md](../current-system-state/threading_concurrency.md)

---

## Current Implementation Status

- ✅ Main event loop is async
- ✅ NarrativeUseCase is async
- ✅ MemoryService is async
- ✅ VectorReaderService is async
- ⚠️ Some adapters have sync I/O (technical debt)
- 🚨 Signal handlers not tested with async (bug)

See: [known_issues.md](../current-system-state/known_issues.md)

---

## ✅ Validation

**How to verify this decision is working:**

### Metrics to Monitor

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Async operations | 100% of I/O | Code coverage analysis |
| Blocking calls found | 0 | Linting + runtime detection |
| Event loop responsiveness | < 10ms | Trace analysis |
| Concurrent campaigns supported | 200+ | Load testing |
| CPU utilization | < 80% | Monitoring dashboard |

### Automated Validation

```bash
# Check for blocking calls
pytest tests/quality/test_no_blocking_calls.py -v

# Run with blocking call detection
python -X dev app.py  # Python dev mode detects blocking

# Check for sync imports of async libraries
grep -r "^import asyncio" src/ | wc -l  # Should be low
grep -r "time.sleep" src/ | wc -l  # Should be 0
```

### Manual Validation

1. **Code Review Checklist**
   - [ ] All I/O operations are `async`
   - [ ] No `time.sleep()` calls (use `asyncio.sleep()`)
   - [ ] No synchronous file operations
   - [ ] No blocking imports
   - [ ] CPU work delegated to ExecutorPort
   - [ ] No database blocking calls

2. **Performance Testing**
   - Run with 200 concurrent campaigns
   - Measure response time for each
   - Verify no degradation as concurrency increases
   - Check one slow campaign doesn't block others

3. **Trace Analysis**
   - Start application with asyncio tracing
   - Monitor event loop tasks
   - Verify no single task blocks > 1ms
   - Check task switch frequency

### Success Criteria

✅ Code passes automated checks:
- No `time.sleep()` found
- No sync I/O found
- All `await` keywords where needed

✅ Performance targets met:
- 200+ concurrent campaigns
- < 10ms event loop lag
- Response times < 1s at 200 concurrency

✅ Runtime behavior:
- Each campaign responsive independently
- No task starvation detected
- CPU < 80% at max concurrency

---

## Next Review: July 1, 2027

Consider:
- Are new features consistently async?
- Have we found any blocking calls that hurt performance?
- Should we enforce with linting?
- Time to migrate to async database driver?
