# ADR-005: Thread Isolation Mandatory

## Status
- **Accepted** ✅
- Proposed: 2025-10-01
- Accepted: 2025-10-08
- Review Date: 2027-10-01

---

## Context

**Problem**:
System supports parallel agent work (multiple agents implementing features simultaneously).
- Risk: Agents modify global state and break each other
- Need: Clear isolation between work threads
- Need: Prevent "I'll just modify this global thing"

---

## Decision

**Thread Isolation at TWO levels:**

### Level 1: AI Agent Threads (Original - Governance)
Each agent work is isolated in its own thread:

Rules:
- ✅ Each thread has its own scope (execution_state.md)
- ✅ Threads only modify their own checkpoints
- ✅ No shared mutable global state
- ✅ No cross-thread modifications (except via ports)
- ❌ Threads don't touch other threads' work
- ❌ No global architecture changes while threads are active

### Level 2: Campaign Runtime Threads (NEW - April 2026)
Each concurrent campaign has thread-local container isolation:

Rules:
- ✅ Each campaign instance gets CampaignScopedContainer
- ✅ Thread-local storage prevents cross-campaign state leakage
- ✅ No shared mutable campaign state between concurrent executions
- ✅ Campaign cleanup happens via context manager
- ❌ Campaign containers cannot share KV/Vector/Cache directly
- ❌ Must use Ports for inter-campaign communication

**CampaignScopedContainer Pattern:**
```python
# Use context manager for automatic cleanup
with CampaignScopedContainer.instance().campaign_scope("campaign_123"):
    # All container resolves use campaign_123's container
    service = container.resolve(NarrativeServicePort)
    # service uses campaign-specific state (isolated memory, cache, etc.)
    await service.execute(...)
# Automatic cleanup when exiting context
```

**Why mandatory?**
- Prevents accidental breaking of other agents' work (Level 1 - Governance)
- Prevents concurrent campaign state leakage (Level 2 - Runtime)
- Makes it clear who owns what (campaign isolation)
- Enables true parallelization at both agent and campaign levels
- Prevents race conditions on shared resources

---

## Consequences

### Positive ✅
- No accidental conflicts between agents
- Clear ownership (this thread owns this work)
- Can safely run multiple agents in parallel
- Prevents global state corruption

### Negative ⚠️
- Agents need to know their thread boundaries
- Cross-thread communication is harder
- Global changes require coordination
- Adds complexity to task tracking

### Risk 🚨
- Agents can still violate isolation (discipline required)
- No technical enforcement (soft constraint)
- Cross-thread data sharing could be missed
- Architecture changes while threads active = conflict

---

## Alternatives Considered

### 1. No isolation (free-for-all)
**Rejected because**: Too risky, agents would constantly break each other.

### 2. Serialized work (one agent at a time)
**Rejected because**: Slow, defeats purpose of parallel work.

### 3. Lock-based serialization (mutex per resource)
**Rejected because**: Too complex, hard to get right.

### 4. Thread-pool with queues
**Rejected because**: Adds infrastructure, hard to implement for documentation/code work.

---

## Related ADRs
- ADR-002: Async-First (threading model)
- ADR-001: Clean Architecture (isolation at layer level)

---

## Thread Specification

Each thread has its own:
- `docs/ia/specs/runtime/threads/THREAD_NAME.md` (tracking)
- Assigned work scope
- List of files they can modify
- Checkpoint progress
- Status (BLOCKED / IN_PROGRESS / COMPLETE)

See: [/docs/ia/specs/runtime/threads/](../specs/runtime/threads/)

---

## Rules for Threads

When starting a thread:
1. Create `threads/THREAD_NAME.md`
2. Document assigned work
3. Document files you'll modify
4. Document dependencies on other threads
5. Mark as IN_PROGRESS

When modifying global architecture:
1. Check all active threads
2. Flag as breaking change
3. Update execution_state.md
4. Notify all affected threads

When finishing:
1. Update checkpoint
2. Document decisions made
3. Flag any open questions
4. Mark as COMPLETE

---

## Current Implementation Status

### Level 1 (AI Agent Threads - Governance)
- ✅ Thread isolation concept documented
- ✅ execution_state.md tracks active threads
- ⚠️ No technical enforcement (GitHub Actions missing)
- ⚠️ No linting for file ownership

### Level 2 (Campaign Runtime Threads - NEW April 2026)

**[MARKER: CampaignScopedContainer Design]** Thread-local campaign isolation

Planned Implementation:
- Location: `src/rpg_narrative_server/bootstrap/campaign/campaign_scoped_container.py`
- Pattern: Singleton with thread-local storage (threading.local())
- Features:
  - Context manager for automatic cleanup
  - Per-campaign container factory
  - Nested campaign_scope() support (if needed)

**DECISION POINTS to resolve before implementation:**
1. **[DECISION: Lock Strategy]** How to handle concurrent campaign_scope() calls?
   - Option A: Simple threading.Lock() on _containers dict
   - Option B: Per-campaign locks for fine-grained concurrency
   - Status: TBD

2. **[DECISION: Cleanup Timing]** When/how to cleanup campaign containers?
   - Option A: Automatic on context exit (current plan)
   - Option B: Explicit cleanup_campaign() call
   - Option C: TTL-based cleanup (campaign expires after timeout)
   - Status: TBD - Recommend A (context manager)

3. **[DECISION: Error Handling]** What if context manager not closed properly?
   - Option A: Resource leak (bad)
   - Option B: Add finalizer for cleanup
   - Option C: Strict validation (error on scope exit without matching enter)
   - Status: TBD - Recommend B (finalizer)

4. **[DECISION: Nesting Support]** Should campaign_scope() support nesting?
   - Example: campaign_scope("c1") { campaign_scope("c2") { } }
   - Current plan: No nesting, raise error if attempted
   - Status: TBD - Recommend: No nesting (simpler, prevents confusion)

---

---

## ✅ Validation

**How to verify this decision is working:**

### Level 1 Validation: AI Agent Threads

**Metrics to Monitor:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Thread conflicts | 0 | GitHub PR conflicts |
| File ownership violations | 0 | Linting + code review |
| Cross-thread coordination issues | 0 | Incident reports |
| Thread status accuracy | 100% | Checkpoint audit |

**Automated Checks:**

```bash
# Check for file ownership violations
pytest tests/architecture/test_thread_isolation.py -v

# Verify all threads documented
grep -r "# THREAD:" src/ | wc -l  # Should > 0

# Check execution state is up to date
python scripts/audit_execution_state.py
```

**Manual Checks:**

1. For each active thread:
   - [ ] Thread has `/EXECUTION/spec/custom/[PROJECT]/development/execution-state/threads/THREAD_NAME.md`
   - [ ] Assigned work clearly documented
   - [ ] Modified files listed
   - [ ] Status matches reality (IN_PROGRESS vs BLOCKED)
   - [ ] No conflicts with other threads

2. Before global architecture changes:
   - [ ] Check all active threads
   - [ ] Notify affected threads
   - [ ] Update execution-state.md
   - [ ] Mark as breaking change

### Level 2 Validation: Campaign Runtime Threads

**Metrics to Monitor:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Campaign isolation violations | 0 | Runtime errors + logs |
| Cross-campaign state leakage | 0 | Memory analysis |
| Campaign cleanup failures | 0 | Resource monitoring |
| Concurrent campaigns supported | 50+ | Load testing |

**Automated Checks:**

```bash
# Test campaign isolation
pytest tests/integration/test_campaign_isolation.py -v

# Test concurrent access
pytest tests/integration/test_concurrent_campaigns.py -v -n 50

# Memory leak detection
pytest tests/integration/test_campaign_cleanup.py --memray
```

**Manual Tests:**

1. **Concurrent Campaign Test**
   - Create 50 campaigns
   - Execute actions on each simultaneously
   - Verify no interference between campaigns
   - Check memory grows linearly

2. **Cleanup Test**
   - Create/destroy 100 campaigns
   - Monitor memory (should return to baseline)
   - Check no dangling resources

### Success Criteria

✅ Level 1 (AI Agent Threads):
- Zero file ownership conflicts
- Zero cross-thread modifications
- All threads properly documented
- Architecture changes properly coordinated

✅ Level 2 (Campaign Runtime):
- 50+ concurrent campaigns
- No state leakage between campaigns
- Memory returns to baseline on cleanup
- All tests pass

---

## Next Review: October 1, 2027

Consider:
- Have threads helped prevent conflicts?
- Any violations of thread boundaries?
- Should we add technical enforcement?
- Need for cross-thread coordination mechanism?
