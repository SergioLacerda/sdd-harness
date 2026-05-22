# 🎯 DECISIONS APRIL 2026 — Consolidated & Optimized

**Status:** ✅ FINAL (8 functional decisions, all ADRs mapped, ready for Phase 1)

**Source Consolidation:**
- DECISIONS_EXPLAINED_PRACTICAL.md
- DECISIONS_REFACTORED_FUNCTIONAL.md
- DECISION_POINTS_CONSOLIDATED.md
- CONSOLIDATION_QUALITY_AUDIT.md
- SEMANTIC_MEMORY_VISION.md

**Optimization:** Removed redundancy, kept decision essentials only

---

## 📊 QUICK REFERENCE: 8 DECISIONS

| # | Decision | Pattern | Rationale | ADR Alignment |
|---|---|---|---|---|
| 1 | Campaign isolation | Thread-local + simple lock | Prevents context contamination | ADR-005 (Level 2) |
| 2 | Resource lifecycle | RAII + finalizer + async cleanup | Exception-safe, no leaks | ADR-002, ADR-006 |
| 3 | Concurrency safety | Double-checked locking | Fast, scalable, no deadlock | ADR-005 |
| 4 | Memory hierarchy | World/Genre/Campaign/Global + cascade | Clear priority, echo system | ADR-001, ADR-006 |
| 5 | Cache invalidation | Event-driven (not TTL) | Reactive, precise, no stale data | ADR-002, ADR-006 |
| 6 | Memory versioning | Event sourcing (full history) | Temporal queries, audit trail | ADR-006 |
| 7 | Canonical immutability | Strict (error on modify) | Baseline integrity, echo safety | ADR-006 |
| 8 | Port isolation | Keep separate (ExecutorPort ≠ EventBusPort) | SRP, testability, flexibility | ADR-003 |

---

## 🔬 DETAILED SPECS (Short Form)

### DECISION #1: Campaign Isolation

**Functional Requirement:**
- Multiple campaigns (Thread A + Thread B) must NOT contaminate each other
- Context must be isolated at thread level
- Cleanup must be automatic

**Pattern:** Thread-local storage + Simple lock (threading.Lock)

**Why Simple Lock?**
- 5-10 concurrent campaigns typical (Discord RPG)
- Lock only held during creation (~10ms)
- Can upgrade to RWLock if benchmarks show bottleneck
- Single lock = no deadlock risk

**ADR Mapping:**
- ✅ ADR-005 (Thread isolation Level 2: Campaign runtime)
- ✅ ADR-001 (Layer 5: Application Composition - DI container)

---

### DECISION #2: Resource Lifecycle

**Functional Requirement:**
- All campaign resources must be cleaned up (connections, cache, memory)
- Cleanup must happen even on exception
- Async cleanup (no blocking I/O during shutdown)

**Pattern:** RAII (Resource Acquisition Is Initialization) + Finalizer + Async

**Async Cleanup Sequence (Order Critical - ADR-006):**
1. Stop accepting new events (pause event bus)
2. Wait for in-flight operations (executor.wait_all())
3. Persist accumulated events (append-only commit)
4. Close vector connections
5. Close LLM connections
6. Flush caches
7. Update campaign state
8. Release container reference

**ADR Mapping:**
- ✅ ADR-002 (Async-first, no blocking I/O)
- ✅ ADR-006 (Event sourcing - persist before cleanup)

---

### DECISION #3: Concurrency Safety

**Functional Requirement:**
- No race conditions on shared _containers dict
- Fast path (read) should not use lock
- Slow path (write) protected by lock
- No deadlock between campaigns

**Pattern:** Double-checked locking

```
1. Fast path: if campaign exists → return (no lock)
2. Slow path: need to create → acquire lock
3. Double-check after lock acquired (another thread might have created it)
4. Create and store
```

**ADR Mapping:**
- ✅ ADR-005 (Thread isolation safe)
- ✅ ADR-002 (Lock held minimal time, no blocking)

---

### DECISION #4: Memory Hierarchy

**Functional Requirement:**
- Echo system: Campaign 2 can access Campaign 1 memories
- World baseline is immutable source of truth
- Genre cache is shared between similar campaigns
- Clear priority: Campaign > Genre > World > Global

**Storage Structure:**
```
data/world_id/
├── canonical/              (World baseline - immutable)
├── genre_id/
│   ├── shared_cache/       (90-day TTL + event invalidation)
│   ├── campaign_1/         (isolated, dynamic)
│   ├── campaign_2/         (isolated, dynamic)
│   └── campaign_3/         (can access campaign_1/2 echoes)
└── global/
    └── templates/          (semantic reusable)
```

**Retrieval Cascade:**
1. Check campaign-specific memory
2. Check genre shared cache
3. Check world canonical facts
4. Check global templates

**ADR Mapping:**
- ✅ ADR-001 (Layer 2 Domain models - hierarchy concept)
- ✅ ADR-006 (Event sourcing - versioned retrieval)
- ✅ ADR-003 (VectorReaderPort - cascading search)

---

### DECISION #5: Cache Invalidation

**Functional Requirement:**
- Genre cache must stay fresh when world changes
- No stale cache (if data changed → cache invalid)
- No false invalidations (if nothing changed → cache valid)
- Event-driven (not time-based)

**Pattern:** Event-driven invalidation (not TTL)

**How it works:**
1. When world changes → emit WorldChangedEvent
2. Genre cache listens
3. If event affects this genre → invalidate cache
4. Next access rebuilds from fresh data

**vs TTL-based:**
- ❌ TTL: 90 days is arbitrary, stale data after 1 day if changed
- ✅ Event: Only invalidates when it SHOULD

**ADR Mapping:**
- ✅ ADR-006 (Changes are events)
- ✅ ADR-002 (Async event listeners)
- ✅ ADR-003 (EventBusPort)

---

### DECISION #6: Memory Versioning

**Functional Requirement:**
- Echo system needs temporal queries ("what was state at time T?")
- Full audit trail (who changed, when, why)
- Can reconstruct narrative exactly as it was

**Pattern:** Event sourcing (full history, immutable events)

**Version Structure:**
```json
{
  "id": "memory_001",
  "versions": {
    "1": {
      "timestamp": "2026-03-15T10:00:00Z",
      "type": "CREATED",
      "actor": "game_engine",
      "content": "Hero discovers prophecy",
      "metadata": {}
    },
    "2": {
      "timestamp": "2026-03-22T15:30:00Z",
      "type": "UPDATED",
      "actor": "player",
      "previous_version": 1,
      "changes": {"interpretation": "Prophecy misunderstood"},
      "metadata": {"reason": "Found hidden scroll"}
    }
  },
  "current_version": 2
}
```

**Enables:**
- ✅ `get_state_at_timestamp(T)` → Reconstruct as it was at time T
- ✅ `get_history_since(T)` → All changes since T (for echo system)
- ✅ Full audit trail → Verify AI decisions against history

**ADR Mapping:**
- ✅ ADR-006 (Event sourcing mandate)
- ✅ ADR-003 (NarrativeGraphPort versioned queries)

---

### DECISION #7: Canonical Immutability

**Functional Requirement:**
- World baseline (canonical) NEVER changes after creation
- Ensures echo system consistency
- Prevents accidental corruption
- If correction needed → create new fact, deprecate old

**Pattern:** Write-once immutable (strict enforcement)

**How it works:**
```python
if memory.level == CANONICAL:
    raise ImmutableCanonicalError(
        "Cannot modify canonical. Instead:\n"
        "1. Create new canonical fact\n"
        "2. Deprecate old\n"
        "3. Invalidate genre cache\n"
        "4. Future campaigns see corrected version"
    )
```

**Why strict?**
- ✅ Prevents silent corruption
- ✅ Thread-safe (immutable = no sync)
- ✅ Distributed-safe (no conflict resolution)
- ✅ Echo system safe (echoes point to stable facts)

**ADR Mapping:**
- ✅ ADR-006 (Immutable events)
- ✅ ADR-001 (Domain rule Layer 2)

---

### DECISION #8: Port Isolation

**Functional Requirement:**
- Must swap LLM provider without affecting rest of system
- Must swap vector DB without affecting rest of system
- Different setups need different port combinations

**Question:** ExecutorPort + EventBusPort = ONE port or SEPARATE?

**Decision:** KEEP SEPARATE (Interface Segregation Principle)

**ExecutorPort (CPU-bound task execution):**
```python
async def run_sync(func: Callable) -> Any
async def run_async(coro: Coroutine) -> Any
async def start() -> None
async def shutdown() -> None
```

**EventBusPort (Event dispatch + messaging):**
```python
async def publish(event: object) -> None
async def subscribe(event_type: type, handler) -> None
async def start() -> None
async def shutdown() -> None
```

**Why Separate?**
- ✅ Single responsibility (each does one thing)
- ✅ Testability (mock each independently)
- ✅ Flexibility (mix and match for setups)
- ✅ Easy to evolve (one doesn't affect other)

**Setup Examples:**
- Local: BlinkerEventBus + ThreadPoolExecutor
- Hybrid: BlinkerWithWebhook + ThreadPoolExecutor
- Remote: RabbitMQEventBus + RemoteExecutor

**ADR Mapping:**
- ✅ ADR-003 (Ports & Adapters - 18 independent ports)
- ✅ ADR-001 (SOLID principles)

---

## 🔗 ADR MAPPING TABLE

| ADR | Decisions Using It | Coverage |
|---|---|---|
| ADR-001: Clean Architecture 8-layer | #1, #4, #7, #8 | ✅ Complete |
| ADR-002: Async-first, no blocking | #2, #3, #5 | ✅ Complete |
| ADR-003: Ports & Adapters (18 ports) | #4, #5, #8 | ✅ Complete |
| ADR-004: Vector black-box factory | #4 (via VectorReaderPort) | ✅ Covered |
| ADR-005: Thread isolation (2 levels) | #1, #3 | ✅ Level 2 complete |
| ADR-006: Event sourcing append-only | #2, #5, #6, #7 | ✅ Complete |

**Status:** ✅ All 6 ADRs respected, no conflicts

---

## ✅ VALIDATION CHECKLIST

**Functional Requirements Met:**
- [x] Campaign isolation (no contamination)
- [x] Resource cleanup (no leaks)
- [x] Echo system (temporal queries)
- [x] Immutable baseline (integrity)
- [x] Cache correctness (event-driven)
- [x] Audit trail (full history)
- [x] Flexible deployments (port separation)

**SPEC Mandates Met:**
- [x] All 6 ADRs respected
- [x] No mandate violations
- [x] Setup-agnostic (works local/hybrid/remote)
- [x] World-class patterns used

**Ready for Implementation:**
- ✅ 8 decisions are final
- ✅ All ADRs mapped
- ✅ No ambiguities remain
- ✅ Ready for Phase 1 coding

---

## 📍 REFERENCES

**Original Analysis Files (Now Archived):**
- DECISIONS_EXPLAINED_PRACTICAL.md (context, problem scenarios)
- DECISIONS_REFACTORED_FUNCTIONAL.md (functional specs)
- DECISION_POINTS_CONSOLIDATED.md (decision matrix)
- CONSOLIDATION_QUALITY_AUDIT.md (validation)
- SEMANTIC_MEMORY_VISION.md (business rules alignment)

**These are consolidated into this file. Original files archived in /docs/ia/ARCHIVE/ for reference.**

**Detailed Specs:**
- For full context, see: `/docs/ia/specs/_shared/business-rules.md`
- For architecture details: `/docs/ia/specs/_shared/architecture.md`
- For contracts: `/docs/ia/specs/_shared/contracts.md`

---

**Status:** ✅ CONSOLIDATED & OPTIMIZED (Ready for Phase 1)

**Next:** Execute Phase 1 implementation using these 8 decisions as blueprint.
