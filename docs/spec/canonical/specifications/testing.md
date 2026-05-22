# 🧪 TESTING BEST PRACTICES

Version: 1.0
Status: ACTIVE

---

# 🎯 PURPOSE

Define testing strategies that validate behavior without compromising production code integrity.

---

# 🚫 GOLDEN RULE: Never Alter Production Code to Satisfy Tests

> Tests must validate behavior, not vice versa.

**FORBIDDEN:**
```python
# ❌ NEVER: Add flags/modes for testing
class ProductionService:
    def __init__(self, is_test: bool = False):
        self.is_test = is_test

    def execute(self):
        if self.is_test:
            # Test-specific behavior
            return mock_data()
        # Production behavior
        return real_data()

# ❌ NEVER: Skip validations in test mode
def validate(data):
    if os.getenv('TEST_MODE'):
        return True  # Skip validation
    return check_integrity(data)
```

**IMPACT IF VIOLATED:**
- Tests become unreliable (don't catch regressions)
- Prod code grows complexity
- Hidden dependencies between test and prod

---

# 📋 TESTING STRATEGY BY LAYER

## Domain Layer

**Test Type:** Unit (No Mocks)
**Strategy:** Pure function testing

```python
# ✅ Domain entity - testable in isolation
def test_campaign_add_event():
    campaign = Campaign(id="c1", name="Test")
    event = NarrativeEvent(id="e1", content="Something happened")

    campaign.add_event(event)

    assert event in campaign.events
    # No mocks, no fixtures, no setup
```

**Checklist:**
- [ ] No external dependencies
- [ ] No mocking required
- [ ] Tests focus on business rules
- [ ] No production code modifications needed

---

## Application Layer (UseCases)

**Test Type:** Integration with Mocked Ports
**Strategy:** Mock ONLY ports (adapters), never prod behavior

```python
# ✅ UseCase test with port mocks
from unittest.mock import AsyncMock

async def test_retrieve_narrative_usecase():
    # Mock PORTS (abstract interfaces)
    mock_repository = AsyncMock(spec=NarrativeRepositoryPort)
    mock_repository.get.return_value = Campaign(id="c1")

    usecase = RetrieveNarrativeUseCase(
        repository_port=mock_repository
    )

    result = await usecase.execute("c1")

    assert result.id == "c1"
    mock_repository.get.assert_called_once_with("c1")
```

**Checklist:**
- [ ] Mock Ports (interfaces), NOT adapters
- [ ] Assert both return value AND port calls
- [ ] No production adapters instantiated
- [ ] No database/file access
- [ ] Production UseCase logic unchanged

**FORBIDDEN:**
```python
# ❌ NEVER: Mock adapters directly
mock_adapter = AsyncMock(spec=JsonNarrativeAdapter)  # Wrong!

# ❌ NEVER: Use real infrastructure
def test_something():
    adapter = JsonNarrativeAdapter("/real/file.json")  # Wrong!
    usecase = SomeUseCase(repository_port=adapter)

# ❌ NEVER: Add test fixtures to production code
class NarrativeRepositoryPort:
    async def get_test_data(self):  # Wrong!
        pass
```

---

## Infrastructure Layer (Adapters)

**Test Type:** Integration or Contract Testing
**Strategy:** Test real backends in isolation (or use test containers)

```python
# ✅ Test adapter with real backend (in isolation)
async def test_json_narrative_adapter(tmp_path):
    # Use temp file for isolation
    test_file = tmp_path / "test_campaigns.json"
    test_file.write_text('{}')

    adapter = JsonNarrativeAdapter(str(test_file))
    campaign = Campaign(id="c1", name="Test")

    await adapter.save(campaign)

    loaded = await adapter.get("c1")
    assert loaded.id == "c1"
    # Real file I/O, no mocks
```

**Checklist:**
- [ ] Uses real backend (or test container)
- [ ] Isolated (temp files, test DB, etc.)
- [ ] Tests port contract compliance
- [ ] No production code modifications
- [ ] Validates serialization/deserialization

---

## Interface Layer (Routes, Handlers)

**Test Type:** Integration with Mocked UseCases
**Strategy:** Mock UseCases (application layer), NOT production logic

```python
# ✅ Route test with mocked usecase
async def test_create_narrative_route():
    # Mock the UseCase (not the whole app)
    mock_usecase = AsyncMock(spec=CreateNarrativeUseCase)
    mock_usecase.execute.return_value = Campaign(id="c1")

    # Inject mocked usecase
    app.dependency_overrides[CreateNarrativeUseCase] = lambda: mock_usecase

    response = await client.post("/narratives", json={...})

    assert response.status_code == 201
    mock_usecase.execute.assert_called_once()

    # Clean up
    app.dependency_overrides.clear()
```

**Checklist:**
- [ ] Mock only UseCases/Services
- [ ] Assert HTTP contract (status, schema)
- [ ] No production logic modified
- [ ] No real database access

---

# 🔐 VECTOR INDEX TESTING

## Rule: Treat as Black Box

**DO NOT:**
- Mock internal implementation
- Test retrieval algorithm
- Assume ranking behavior
- Couple tests to index state

**DO:**
- Mock the VectorIndexPort in UseCases
- Test that port is called correctly
- Validate error handling
- Test timeout/fallback logic

```python
# ✅ Test VectorIndexPort usage
async def test_usecase_calls_vector_index():
    mock_index = AsyncMock(spec=VectorIndexPort)
    mock_index.retrieve.return_value = [
        RetrievalResult(id="doc1", score=0.95),
    ]

    usecase = RetrieveContextUseCase(
        vector_port=mock_index
    )

    results = await usecase.execute("query")

    assert len(results) == 1
    mock_index.retrieve.assert_called_once_with("query")
    # Do NOT test how ranking was done!
```

---

# 🎯 TESTING PATTERNS

## Pattern 1: Fake Adapters (vs. Mocks)

```python
# ✅ Better than mocking for complex behavior
class FakeNarrativeRepository(NarrativeRepositoryPort):
    """In-memory implementation for testing."""

    def __init__(self):
        self.store: dict[str, Campaign] = {}

    async def get(self, id: str) -> Campaign:
        if id not in self.store:
            raise NotFoundError(f"Campaign {id} not found")
        return self.store[id]

    async def save(self, campaign: Campaign) -> None:
        self.store[campaign.id] = campaign

# Use it:
async def test_something():
    fake_repo = FakeNarrativeRepository()
    usecase = SomeUseCase(repository_port=fake_repo)
    # Test against real implementation logic (not mocked calls)
```

**Advantages over AsyncMock:**
- Tests actual port behavior
- More realistic scenarios
- Easier to maintain
- Better for discovery of bugs

---

## Pattern 2: Fixture Factory

```python
# ✅ Reusable test data creation
@pytest.fixture
def campaign_factory():
    """Factory for creating test campaigns."""
    def _create(id: str = "c1", name: str = "Test") -> Campaign:
        return Campaign(id=id, name=name)
    return _create

async def test_retrieve(campaign_factory):
    campaign = campaign_factory(id="my-id")
    # Use factory, not hardcoded data
```

---

## Pattern 3: Parametrized Tests

```python
# ✅ Test multiple scenarios efficiently
@pytest.mark.parametrize("campaign_id,expected", [
    ("c1", Campaign(id="c1")),
    ("c2", Campaign(id="c2")),
])
async def test_retrieve_campaigns(campaign_id, expected):
    usecase = RetrieveUseCase(repository_port=...)
    result = await usecase.execute(campaign_id)
    assert result.id == expected.id
```

---

# 🎯 CLARIFICATION: Ports vs Adapters vs Fakes

**Purpose:** Define the clear distinctions to prevent confusion on what to mock

## Port (Abstract Interface)

```python
# Location: application/ports/<entity>_<operation>_port.py
# Example: application/ports/memory_service_port.py

from typing import Protocol, Async

class MemoryServicePort(Protocol):
    """Abstract interface for memory retrieval."""

    async def load_context(self, campaign_id: str) -> str:
        """Load memory context. MUST be async."""
        ...

    async def store_event(self, campaign_id: str, event: str) -> None:
        """Store event. MUST be async."""
        ...
```

**Key:** Abstract (Protocol/ABC), NO implementation, ALWAYS async

## Adapter (Concrete Implementation)

```python
# Location: infrastructure/adapters/<technology>_<entity>_adapter.py
# Example: infrastructure/adapters/json_memory_adapter.py

class JsonMemoryAdapter(MemoryServicePort):
    """Implements MemoryServicePort using JSON files."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    async def load_context(self, campaign_id: str) -> str:
        # Real implementation using JSON I/O
        file_path = f"{self.base_path}/{campaign_id}/context.json"
        with open(file_path) as f:
            return json.load(f).get("context", "")

    async def store_event(self, campaign_id: str, event: str) -> None:
        # Real implementation
        pass
```

**Key:** Concrete implementation, extends Port, does real I/O

## Fake (Test Implementation)

```python
# Location: tests/config/fakes/<layer>/<entity>_fake.py
# Example: tests/config/fakes/infrastructure/memory/fake_memory_service.py

class FakeMemoryService(MemoryServicePort):
    """Fake implementation for testing (in-memory, no I/O)."""

    def __init__(self):
        self._context: dict[str, str] = {}
        self._events: list[str] = []

    async def load_context(self, campaign_id: str) -> str:
        return self._context.get(campaign_id, "")

    async def store_event(self, campaign_id: str, event: str) -> None:
        self._events.append(f"{campaign_id}:{event}")
        self._context[campaign_id] = event
```

**Key:** Implements Port fully, used in tests, NO real I/O

## Mocking Rules Clarified

| Test Type | Use Mock? | Use Fake? | Use Real Adapter? | Decision Rule |
|-----------|----------|----------|-------------------|---------------|
| **Unit (Domain)** | ❌ No | ❌ No | ❌ No | No external deps |
| **Unit (UseCase)** | ✅ Yes | ✅ Yes* | ❌ No | Only Port-level mocks |
| **Integration** | ❌ No | ✅ Yes | ✅ OK (test containers) | Real behavior |
| **Contracts** | ⚠️ Maybe | ✅ Yes | ✅ Yes | Validate port contract |
| **E2E (Golden)** | ❌ Rarely | ✅ Mostly | ✅ Sometimes | Real scenarios |

*Fake is preferred over Mock for complex behavior

### When to Use Each

```python
# ✅ USE MOCK for UseCase tests
async def test_usecase():
    mock_repo = AsyncMock(spec=MemoryServicePort)
    mock_repo.load_context.return_value = "context"

    usecase = MyUseCase(memory=mock_repo)
    result = await usecase.execute()

    mock_repo.load_context.assert_called()

# ✅ USE FAKE for Integration tests
async def test_integration():
    fake_repo = FakeMemoryService()
    fake_repo.store("c1", "event1")

    service = MemoryOrchestrator(memory=fake_repo)
    result = await service.get_full_context("c1")

    assert "event1" in result  # Tests actual behavior, not mocked

# ✅ USE REAL ADAPTER for Adapter tests (with temp files)
async def test_adapter(tmp_path):
    adapter = JsonMemoryAdapter(str(tmp_path))

    await adapter.store_event("c1", "test_event")
    context = await adapter.load_context("c1")

    assert "test_event" in context
```

---

# 🏗️ CLARIFICATION: Test Layers & Mocking Requirements

**Purpose:** Clarify what mocking level is allowed for each test type

## Testing Hierarchy

```
tests/
├─ unit/
│  ├─ domain/          → ZERO mocks (pure logic)
│  ├─ application/
│  │  ├─ usecases/     → Mock PORTS ONLY
│  │  ├─ services/     → Mock PORTS ONLY
│  │  └─ queries/      → ZERO mocks (stateless)
│  └─ (never: infrastructure/)
│
├─ integration/        → Use FAKES (not mocks)
│  ├─ bootstrap/
│  ├─ runtime/
│  └─ scenarios/
│
├─ contracts/         → Use FAKES or REAL adapters
│  ├─ ports/
│  ├─ architecture/
│  └─ framework/
│
└─ golden/            → Mix of FAKES + setattr()
```

## Rule by Layer

| Layer | Must Have | Can Have | Cannot Have |
|-------|-----------|----------|------------|
| **Domain** | ✅ Pure entities | ❌ Nothing | ❌ Mocks |
| **UseCase** | ✅ Port deps | ✅ Mock ports | ❌ Real adapters |
| **Service** | ✅ Port deps | ✅ Mock ports | ❌ Real adapters |
| **Query** | ✅ Nothing | ✅ Parsing | ❌ I/O |
| **Adapter** | ✅ Real backend | ✅ Test container | ❌ Real prod |
| **Route** | ✅ UseCase deps | ✅ Mock usecases | ❌ Real I/O |

## Quick Decision: Can I Mock This?

```
Am I in tests/unit/?
├─ YES → am in domain/?
│  ├─ YES → NO MOCKS allowed
│  ├─ NO → in application/?
│  │  ├─ YES → Can mock PORTS ONLY (not adapters)
│  │  └─ NO → NO MOCKS (wrong layer)
│
├─ NO → am in tests/integration/?
│  ├─ YES → Use FAKES (not mocks)
│  └─ NO → am in tests/contracts/?
│     ├─ YES → Use FAKES or REAL
│     └─ NO → Different test type
```

---

# ✅ CLARIFICATION: Port Mock Validation Pattern

**Purpose:** Ensure mocks actually validate the Port contract

## Using spec= Parameter (REQUIRED)

```python
# ✅ CORRECT: Use spec= to enforce Port contract
from unittest.mock import AsyncMock
from application.ports.memory_port import MemoryServicePort

async def test_usecase_with_memory():
    # spec= ensures mock ONLY has MemoryServicePort methods
    mock_memory = AsyncMock(spec=MemoryServicePort)

    usecase = NarrativeUseCase(memory_service=mock_memory)
    result = await usecase.execute()

    # Can only call methods that exist on Port
    mock_memory.load_context.assert_called()
```

## Validation Checklist

Before committing UseCase tests:

- [ ] All mocks use `spec=Port` (not `spec="SomeAdapter"`)
- [ ] Port is from `application/ports/` (not infrastructure)
- [ ] All Port methods are async
- [ ] No extra methods added to mock beyond Port
- [ ] Mock behavior reflects Port contract (not guessed)

## Bad Patterns to Avoid

```python
# ❌ WRONG: No spec= (can mock anything)
mock_service = AsyncMock()

# ❌ WRONG: spec points to adapter (not port)
mock_service = AsyncMock(spec=JsonMemoryAdapter)

# ❌ WRONG: Mocking internal methods
mock_service = AsyncMock(spec=MemoryServicePort)
mock_service._internal_method = AsyncMock()

# ❌ WRONG: Setting behavior that Port doesn't define
mock_service.extra_behavior = AsyncMock()

# ✅ CORRECT: Explicit Port spec, well-defined behavior
mock_service = AsyncMock(spec=MemoryServicePort)
mock_service.load_context.return_value = "known_context"
```

## Testing the Test (Meta-validation)

```python
import inspect

# Validate your mock matches the Port
from application.ports.memory_port import MemoryServicePort

mock_memory = AsyncMock(spec=MemoryServicePort)

# Extract Port methods
port_methods = {
    m for m in dir(MemoryServicePort)
    if not m.startswith('_')
}

# Extract mock methods
mock_methods = {
    m for m in dir(mock_memory)
    if not m.startswith('_')
}

# They should match
assert port_methods == mock_methods, (
    f"Mismatch: {port_methods ^ mock_methods}"
)

print("✅ Mock correctly implements Port contract")
```

---

# ❌ ANTI-PATTERNS (FORBIDDEN)

| ❌ DON'T | ✅ DO INSTEAD | Why? |
|----------|-------------|------|
| Add test flags to production code | Use dependency injection + mocks | Tests shouldn't modify prod code |
| Mock everything (including domain) | Only mock external boundaries (ports) | Domain should be pure, testable |
| Skip validation in test mode | Use fake adapters that validate | Tests should catch regressions |
| Access real DB in tests | Use test containers or temp files | Tests must be isolated |
| Assume vector index behavior | Mock port, test port calls | Vector is black box |
| Hardcode test data in prod code | Use fixtures/factories | Separation of concerns |
| Test implementation details | Test contracts (input → output) | Implementation can change |
| Modify usecase for testing | Use ports for abstraction | Prevents behavior drift |

---

# 📊 TESTING CHECKLIST

Before merging:

- [ ] **Domain tests:** Pure functions, no mocks
- [ ] **UseCase tests:** Port mocks only, no adapters
- [ ] **Adapter tests:** Real backends or containers
- [ ] **Route tests:** UseCase mocks only
- [ ] **No production code flags:** No `if TEST_MODE`
- [ ] **Behavior validated:** Tests fail when logic breaks
- [ ] **Isolation verified:** Tests don't affect each other
- [ ] **All tests pass:** Both unit and integration
- [ ] **Coverage reasonable:** Focus on critical paths, not 100%

---

# 🔍 TEST VALIDATION RULES

## Rule 1: Production Code Never Adapts for Tests

**REQUIRED REVIEW:**
```bash
# Before merging, verify:
grep -r "TEST_MODE\|is_test\|test_flag" src/
# Should return: 0 results
```

## Rule 2: Tests Access Only Ports (Not Adapters)

**REQUIRED REVIEW:**
```bash
# Before merging, verify no test imports concrete adapters:
grep -r "from.*adapters.*import\|from.*adapter import" tests/
# Should reference ONLY ports and fakes
```

## Rule 3: No Backdoors to Production

**REQUIRED REVIEW:**
```python
# ❌ NEVER allow this:
class SomeService:
    @classmethod
    def _set_test_mode(cls):
        pass  # Hidden test interface

# ✅ Use ports instead:
class SomeService:
    def __init__(self, port: SomePort):
        self.port = port  # Explicit dependency
```

---

# 🚀 TESTING EXECUTION

## Test Categories

```bash
# Unit tests (domain) - MUST pass before commit
pytest tests/unit/domain/

# Integration tests (usecases + mocked ports) - MUST pass before commit
pytest tests/integration/usecases/

# Adapter tests (real backends) - Optional but recommended
pytest tests/integration/adapters/

# E2E tests (full stack) - Optional, catches regressions
pytest tests/golden/
```

## CI/CD Requirements

- ✅ Unit tests MUST pass
- ✅ Integration tests MUST pass
- ✅ No production code modifications allowed
- ✅ Coverage threshold respected
- ✅ No test-specific flags in code

---

# 📚 RELATED SPECS

- [architecture.md](./architecture.md) — Layer responsibilities
- [feature-checklist.md](./feature-checklist.md) — Testing per layer
- [contracts.md](./contracts.md) — Port definitions (what to mock)
