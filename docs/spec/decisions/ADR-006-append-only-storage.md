# ADR-006: Append-Only JSON Storage

## Status
- **Accepted** ✅
- Proposed: 2025-11-01
- Accepted: 2025-11-08
- Review Date: 2027-11-01

---

## Context

**Problem**:
Need persistent storage for campaigns. Options:
- Relational database (overkill for MVP)
- Document database (external dependency)
- Simple JSON files (low deployment complexity)

**Scale constraints**:
- 50-200 campaigns concurrent
- ~20-100 events per campaign per day
- MVP phase (rapid iteration > perfect storage)
- Single machine deployment

---

## Decision

**Use append-only JSON file storage:**

- **Format**: One campaign = one JSON file per data type
- **Strategy**: Append-only (never update, only add)
- **Files per campaign**:
  - `campaigns/{id}/events.json` - Event log (append-only)
  - `campaigns/{id}/kv/*.json` - Key-value pairs
  - `campaigns/{id}/memory/narrative.json` - Computed memory
- **Persistence**: No transaction support
- **Atomicity**: No distributed transactions
- **Consistency**: Eventually consistent

**Why append-only?**
- No corruption risk from partial writes
- Easy recovery (replay events)
- No locking needed (concurrent writes append)
- Simple to implement

**Why JSON files?**
- No external dependencies
- Easy to inspect (git-friendly)
- Python dict ↔ JSON trivial
- Easy to export/migrate

---

## Consequences

### Positive ✅
- Simple, works out of the box
- Easy to backup (copy files)
- Easy to inspect (JSON text format)
- Fast reads for small datasets
- No database administration

### Negative ⚠️
- Full read on every query (O(n))
- File size grows continuously
- Concurrent writes can lose data
- No query optimization
- No indexing support

### Risk 🚨
- Race conditions: Multiple writes = data loss
- Performance degrades at scale (> 50k events per campaign)
- Corrupted JSON breaks everything
- Migration to DB will be hard

---

## Alternatives Considered

### 1. PostgreSQL/SQLite
**Rejected because**: Overkill for MVP, adds deployment complexity.

### 2. MongoDB
**Rejected because**: External dependency, higher operational cost.

### 3. In-memory only
**Rejected because**: Loss on restart, not practical.

### 4. Event sourcing (proper)
**Rejected because**: Too much complexity for MVP, append-only is good enough.

---

## Related ADRs
- ADR-002: Async-First (all I/O must be async)
- ADR-003: Ports & Adapters (DocumentStorePort abstraction)

---

## Known Limitations

See: [current-system-state/storage_limitations.md](../current-system-state/storage_limitations.md)

- Single-file JSON (no DB structure)
- No transactions (race conditions possible)
- No encryption
- In-memory by default (data loss on crash)
- Campaign isolation (no cross-campaign queries)

**Performance**:
- Read: O(n) - full scan needed
- Append: O(1) - just add to file
- Search: O(n) - linear search

**Migration checkpoint**: > 50k events per campaign = time to migrate to database

---

## Migration Path

**Phase 1** (now): Append-only JSON (MVP)
- Works for 50-200 campaigns
- Single machine deployment

**Phase 2** (2027): PostgreSQL migration
- Replace DocumentStorePort adapter
- Batch migration of JSON → DB
- Add indexing

**Phase 3** (future): Distributed storage
- Sharding by campaign
- Read replicas
- Multi-region support

---

## Implementation Notes

See: [current-system-state/data_models.md](../current-system-state/data_models.md)

Storage format per campaign:
```
campaigns/{id}/
  ├─ events.json (array of PlayerActionEvent)
  ├─ memory/
  │   ├─ narrative.json (NarrativeMemory)
  │   ├─ events.json (cached event list)
  │   └─ response_cache.json (LLM responses)
  └─ kv/
      ├─ {key1}.json
      ├─ {key2}.json
      └─ ...
```

---

## Current Implementation Status

- ✅ Append-only events.json working
- ✅ KV storage working (per-file)
- ✅ Memory JSON working
- ⚠️ No transaction support (data loss possible on crash)
- ⚠️ No concurrent write protection
- 🚨 Performance degrading at scale

---

## ✅ Validation

**How to verify this decision is working:**

### Metrics to Monitor

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Data consistency | 100% | Integrity checks |
| Append-only property | 100% | Audit log verification |
| Read latency | < 500ms | Benchmark tests |
| File size growth | Linear | Storage monitoring |
| Recovery success rate | 100% | Backup restoration test |

### Automated Validation

```bash
# Check append-only property
pytest tests/quality/test_append_only.py -v

# Verify data consistency
python scripts/verify_storage_consistency.py

# Benchmark read performance
pytest tests/quality/test_storage_performance.py -v

# Test recovery from backup
pytest tests/integration/test_backup_restore.py -v
```

### Manual Validation

1. **Append-Only Verification**
   - [ ] No UPDATE operations in code
   - [ ] No DELETE operations (soft delete only)
   - [ ] Event files only have appends
   - [ ] Timestamps always increasing

2. **Data Integrity Checks**
   ```python
   # Verify events can be replayed
   events = load_events(campaign_id)
   final_state = replay_events(events)
   current_state = load_state(campaign_id)
   assert final_state == current_state
   ```

3. **Performance Tests**
   - Load campaign with 10k events
   - Measure read latency
   - Verify < 500ms
   - Check linear growth with event count

4. **Recovery Procedure**
   - Create backup
   - Corrupt campaign file
   - Restore from backup
   - Verify data intact

### Success Criteria

✅ Consistency validation:
- All events append-only
- No data corruption
- Replay produces same state
- Timestamps monotonically increasing

✅ Performance targets:
- Campaign read < 500ms for 10k events
- File size < 100MB for reasonable history
- Startup time < 5s (including index rebuild)

✅ Backup/Recovery:
- Weekly backups automated
- Recovery tested monthly
- 0% data loss on restore
- RTO < 1 hour

**Migration Checkpoint:**
- At 50k+ events per campaign → Evaluate PostgreSQL
- Current (5-10k): JSON sufficient ✅
- Future: Plan migration path

---

## Next Review: November 1, 2027

Consider:
- Largest campaign now has how many events?
- Query performance acceptable?
- Any data loss incidents?
- Time to migrate to PostgreSQL?
