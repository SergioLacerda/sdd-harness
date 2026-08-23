# ADR-001: Clean Architecture 8-Layer Pattern

## Status

- **Accepted** ✅
- Proposed: 2025-06-15 (Retrofit, original decision earlier)
- Accepted: 2025-06-20
- Review Date: 2027-06-15

---

## Context

**Problem**:
The system needed clear separation between business logic, adaptation, and infrastructure to support:

- Multiple storage backends (JSON file, future DB)
- Multiple vector index backends (ChromaDB, future Pinecone)
- Easy testing at each layer
- Prevent infrastructure concerns from leaking into business logic
- Support multiple API versions without core changes

**Scale**: Supporting 50-200 campaigns concurrently, each with isolated state.

---

## Decision

**Implement 8-layer Clean Architecture**:

```
Layer 8: Controllers & Interfaces (HTTP, CLI)
Layer 7: DTOs & Serialization (Pydantic models)
Layer 6: Adapters (Implementation of ports)
Layer 5: Error Mapping (Domain → HTTP)
Layer 4: Use Cases (Orchestration)
Layer 3: Ports (Abstraction, interfaces)
Layer 2: Domain (Business logic)
Layer 1: Entities (Domain models)
```

**Why 8 layers?**

- 4 layers (clean arch classic) wasn't enough for our infrastructure needs
- 8 layers gives us explicit error mapping layer (Layer 5)
- 8 layers gives us explicit DTO layer (Layer 7)
- Prevents mixing of concerns

**Why mandatory?**

- Consistency across all features
- New agents can understand code structure immediately
- Easy to spot violations (code in wrong layer)

---

## Consequences

### Positive ✅

- Infrastructure changes don't affect business logic
- Easy to test each layer independently
- Clear responsibility boundaries
- Multiple implementations of same port possible
- Future database migration only needs new Adapter

### Negative ⚠️

- More boilerplate (need to follow all 8 layers)
- Steeper learning curve for new contributors
- Can feel "over-engineered" for simple features
- Requires discipline to not skip layers

### Risk 🚨

- Teams can skip layers and "just make it work"
- Need linting/validation to enforce
- Refactoring is harder across layers
- Performance can suffer if layers aren't designed for it

---

## Alternatives Considered

### 1. 4-Layer Classic Clean Architecture

**Rejected because**: Doesn't handle infrastructure abstraction cleanly, error mapping gets mixed with adapters.

### 2. Layered Hexagonal (3 layers)

**Rejected because**: Too simple, no clear separation between ports and adapters.

### 3. Vertical Slicing (Feature-based)

**Rejected because**: Makes it hard to share domain logic across features, each slice would duplicate ports/adapters.

### 4. No enforced layers (organic structure)

**Rejected because**: Led to infrastructure leakage, hard for new agents to understand structure.

---

## Related ADRs

- ADR-003: Ports & Adapters Pattern (implements abstraction)
- ADR-002: Async-First (affects each layer)

---

## How to Implement

When adding a feature, follow all 8 layers:

- See: [feature-checklist.md](../canonical/specifications/feature-checklist.md)
- See: [architecture.md](../canonical/specifications/architecture.md)

---

## Current Implementation Status

- ✅ NarrativeUseCase follows all 8 layers
- ✅ VectorReaderService follows all 8 layers
- ✅ MemoryService follows pattern (with minor gaps)
- ⚠️ Some adapters could be cleaner (technical debt)
- ⚠️ Error mapping not always consistent

---

## ✅ Validation

**How to verify this decision is working:**

### Metrics to Monitor

| Metric | Target | How to Measure |
|--------|--------|----------------|
| New features following all 8 layers | 100% | Code review checklist |
| Layer violation attempts blocked | 0 | Linting passes |
| Error mapping consistency | 100% | Exception test coverage |
| Adapter implementations per port | 1-2 | Service test matrix |

### Automated Validation

```bash
# Check for architectural violations
pytest tests/architecture/test_layers.py -v

# Check for cyclic imports between layers
pytest tests/architecture/test_no_cycles.py -v

# Check for infrastructure in domain
pytest tests/architecture/test_no_infra_in_domain.py -v

# Count implementations per port
grep -r "class.*Port" src/ | wc -l
```

### Manual Validation

1. **New Feature Checklist**
   - [ ] Feature has entity (Layer 1)
   - [ ] Feature has port (Layer 3)
   - [ ] Feature has adapter (Layer 6)
   - [ ] Feature has usecase (Layer 4)
   - [ ] Feature has interface (Layer 8)
   - [ ] No framework in domain layers
   - [ ] Error mapping defined (Layer 5)

2. **Code Review Questions**
   - Does domain import any frameworks? (should be no)
   - Does adapter know about business logic? (should be no)
   - Is there a corresponding port? (should be yes)
   - Is error mapping explicit? (should be yes)

3. **Runtime Checks**
   - Start application with linter enabled
   - Verify all layers load correctly
   - Test error propagation through layers
   - Verify no import cycles

### Success Criteria

✅ All tests pass:

- `pytest tests/architecture/` (no violations)
- `pytest tests/unit/` (per-layer unit tests)
- `pytest tests/integration/` (layer interactions)

✅ Code review gates:

- Zero layer violations in PRs
- 100% of new features follow pattern
- All adapters implement ports correctly

✅ Runtime behavior:

- Application loads without import errors
- Errors properly mapped at Layer 5
- Business logic remains testable in isolation

---

## Next Review: June 15, 2027

Consider:

- Are new features easily following all 8 layers?
- Should we enforce with linting?
- Any layers that could be combined/removed?
