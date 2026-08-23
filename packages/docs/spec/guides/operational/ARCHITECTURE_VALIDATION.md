# 🏛️ Architecture Validation Guide — Compliance Testing

**Authority:** SPEC v2.1
**Status:** Mandatory reference guide
**Location:** Tests in `tests/unit/specs_ia_units/`
**Templates:** `INTEGRATION/templates/tests/unit/specs_ia_units/`
**Updated:** April 19, 2026

---

## 🎯 Purpose

Quick reference for writing architecture compliance tests that validate:

- ✅ Layer isolation (domain ≠ infrastructure)
- ✅ Port contract compliance
- ✅ Thread isolation
- ✅ Project specializations
- ✅ Domain entity contracts

**Note:** Complete test templates are in `INTEGRATION/templates/tests/unit/specs_ia_units/`. Copy and adapt for your project.

---

## 📋 Five Required Test Categories

### Category 1: Layer Isolation Tests

**File:** `tests/unit/specs_ia_units/test_layer_isolation.py`
**Template:** `INTEGRATION/templates/tests/unit/specs_ia_units/test_layer_isolation_template.py`

**What:** Verify domain layer never directly imports infrastructure

**Why:** Domain must stay pure (fundamental clean architecture principle)

**Tests Included:**

- ✅ Domain never imports infrastructure
- ✅ Domain never imports frameworks (FastAPI, Django, Flask, etc)
- ✅ Application uses ports (abstract), not direct infrastructure
- ✅ Interfaces layer imports domain only
- ✅ Frameworks layer only wires adapters

**Setup:**

```bash
cp INTEGRATION/templates/tests/unit/specs_ia_units/test_layer_isolation_template.py \
   tests/unit/specs_ia_units/test_layer_isolation.py

# Edit file: replace [project_name] with your package name
# Run test
pytest tests/unit/specs_ia_units/test_layer_isolation.py -v
```

**Success Criteria:**

- No domain imports to infrastructure/ ✅
- No framework imports in domain/ ✅
- All infrastructure access via ports ✅

---

### Category 2: Port Contract Tests

**File:** `tests/unit/specs_ia_units/test_port_contracts.py`
**Template:** `INTEGRATION/templates/tests/unit/specs_ia_units/test_port_contracts_template.py`

**What:** Verify infrastructure implementations fulfill port contracts

**Why:** Ports define contracts; implementations must satisfy them

**Tests Included:**

- ✅ All adapters implement ports from domain
- ✅ Storage adapter implements StoragePort
- ✅ Port methods are implemented
- ✅ No domain code calls non-port methods

**Setup:**

```bash
cp INTEGRATION/templates/tests/unit/specs_ia_units/test_port_contracts_template.py \
   tests/unit/specs_ia_units/test_port_contracts.py

# Edit: replace [project_name]
# Run
pytest tests/unit/specs_ia_units/test_port_contracts.py -v
```

**Success Criteria:**

- All adapters implement their ports ✅
- All ports have required methods ✅
- No domain code calls non-port methods ✅

---

### Category 3: Thread Isolation Tests

**File:** `tests/unit/specs_ia_units/test_thread_isolation.py`
**Template:** `INTEGRATION/templates/tests/unit/specs_ia_units/test_thread_isolation_template.py`

**What:** Verify thread modifications don't interfere

**Why:** Concurrent development requires thread safety

**Tests Included:**

- ✅ Execution state tracks threads
- ✅ No global mutable state at module level
- ✅ No shared session variables
- ✅ Caches are thread-safe if used
- ✅ Valid concurrency patterns

**Setup:**

```bash
cp INTEGRATION/templates/tests/unit/specs_ia_units/test_thread_isolation_template.py \
   tests/unit/specs_ia_units/test_thread_isolation.py

# Edit: replace [project_name]
# Run
pytest tests/unit/specs_ia_units/test_thread_isolation.py -v
```

**Success Criteria:**

- Execution state documents threads ✅
- No shared mutable module state ✅
- Thread-safe synchronization if needed ✅

---

---

## 🚀 Running Architecture Tests

### Before Commit

```bash
# Run all architecture tests
pytest tests/unit/specs_ia_units/ -v

# Run specific category
pytest tests/unit/specs_ia_units/test_layer_isolation.py -v

# With short output
pytest tests/unit/specs_ia_units/ --tb=short
```

### In CI/CD

```yaml
# .github/workflows/ci.yml
- name: Validate SPEC Architecture Compliance
  run: pytest tests/unit/specs_ia_units/ -v --tb=short

  # If this fails, PR cannot merge
```

---

## 🔧 Creating New Tests

### When to Add Tests

1. **New rule discovered** → Add test to enforce it
2. **New violation pattern** → Add test to catch it
3. **New architecture layer** → Add test for layer isolation
4. **New port type** → Add contract test

### Template Pattern

All templates follow this structure:

```python
def test_rule_X_specific_check(self):
    """RULE X: [Describe what's validated]."""
    files = Path("[search_path]").rglob("*.py")

    for file in files:
        content = file.read_text()
        assert [condition], f"{file}: [violation description]"
```

---

## 🔍 Debugging Failed Tests

### Process

```bash
# 1. Run with verbose output
pytest tests/unit/specs_ia_units/ -vv

# 2. Find specific failure
pytest tests/unit/specs_ia_units/test_layer_isolation.py::test_domain_never_imports_infrastructure -vv

# 3. Inspect file mentioned in error
cat src/[project]/domain/[failing_file].py | grep infrastructure

# 4. Fix violation
# ... edit file ...

# 5. Verify fix
pytest tests/unit/specs_ia_units/ -v
```

### Common Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `domain imports infrastructure` | Layer violation | Move code to application layer |
| `StoragePort not implemented` | Missing adapter | Implement port in adapter |
| `thread_local not found` | Shared state | Use threading.local() |

---

## ✅ Compliance Checklist

Before PR can merge:

- [ ] All tests in `tests/unit/specs_ia_units/` pass
- [ ] No false positives (intentional exceptions documented)
- [ ] Coverage for each category >= 80%
- [ ] No test-specific code in production
- [ ] Tests only use public interfaces

---

## 🔗 Related Documents

- Templates: `INTEGRATION/templates/tests/unit/specs_ia_units/`
- Rules: `CANONICAL/rules/ia-rules.md`
- Architecture: `CANONICAL/specifications/architecture.md`
- Testing: `CANONICAL/specifications/testing.md`
- Enforcement: Test compliance with `tests/unit/specs_ia_units/`

---

**Authority:** SPEC v2.1 Framework
**Status:** Mandatory for all projects
**Effective Date:** April 19, 2026
