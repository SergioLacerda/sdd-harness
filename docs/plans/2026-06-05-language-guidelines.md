# Language Engineering Guidelines — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate raw engineering guidelines from `.analysis/pending/language/` into the SDD governance system across three layers: mandates (universal), guidelines.dsl (language-specific), and /docs (full reference).

**Architecture:** Universal principles become mandates (M018 new + M001/M002/M010/M016 enriched). Language-specific enforcement becomes 16 new DSL entries (G05–G20) filtered by wizard Phase 4. Full reference docs live in `docs/guidelines/languages/{lang}.md` with identical structure across all 4 languages.

**Tech Stack:** Markdown files, `.sdd/source/` DSL format (existing pattern G01–G04), Python Phase 4 filter (`phase_4_filter_guidelines.py`)

**Critical constraint:** Mandates must be language-agnostic. Language content goes exclusively into `guidelines.dsl` with tags, never into mandates.

---

## Task 1: Add M018 to mandates source files

**Files:**
- Modify: `.sdd/source/mandates/mandates.md`
- Modify: `.sdd/source/mandate.md`

**Step 1: Add M018 block to `.sdd/source/mandates/mandates.md`**

Append after the M017 block:

```markdown
## M018: Code Quality Baseline

**Criticality**: high
**Customizable**: No

Every function must have a single responsibility and fit within 20 lines. Files must stay under 500 lines — split by responsibility when exceeded. Names must be specific and unique (target: ≤ 5 grep hits in the codebase). Types must be explicit — no `any`, no untyped `Dict`, no untyped function signatures. Logic must not be duplicated — extract shared logic into named functions or modules. Control flow must use early returns; max 2 levels of indentation. Exception messages must include the offending value and expected shape. Dependencies must be injected via constructor or parameter — never via global state or import-time mutation. Comments document WHY and provenance (bug reference, upstream constraint, design trade-off). Public functions must have a docstring with intent and one usage example.
```

**Step 2: Add M018 to `.sdd/source/mandate.md`**

Append after the M017 line:

```markdown
## M018: Code Quality Baseline
```

**Step 3: Verify both files contain M018**

```bash
grep "M018" .sdd/source/mandates/mandates.md .sdd/source/mandate.md
```

Expected: two matches, one per file.

**Step 4: Commit**

Files to stage:
- `.sdd/source/mandates/mandates.md`
- `.sdd/source/mandate.md`

Message: `feat: add M018 Code Quality Baseline mandate`

---

## Task 2: Enrich M001, M002, M010, M016 descriptions

**Files:**
- Modify: `.sdd/source/mandates/mandates.md`

**Step 1: Replace "No description available" for M001**

Find the M001 block and replace its description line with:

```markdown
Domain and application layers must not depend on infrastructure adapters, frameworks, or persistence providers directly. Business rules must remain independent of transport, database, and external service implementations. Dependency direction flows inward: infrastructure depends on application, application depends on domain, domain depends on nothing external. Architecture bypass (domain importing infrastructure, controllers containing business rules, framework types leaking into domain) is a Critical violation that blocks merge.
```

**Step 2: Replace "No description available" for M002**

```markdown
Every new function requires a test written before or alongside implementation. Bug fixes require a regression test. Tests must be F.I.R.S.T: Fast, Independent, Repeatable, Self-Validating, Timely. Mock only external I/O boundaries using named fake classes. Tests must run with a single command and produce parseable output. Testing anti-patterns that invalidate this mandate: mock everything (replaces behavior with implementation detail), flaky test normalization (reruns instead of fixing), snapshot abuse (hides regressions behind auto-approved diffs), testing implementation instead of behavior (blocks safe refactoring).
```

**Step 3: Replace "No description available" for M010**

```markdown
Every change must have explicit declared scope before execution. AI agents must diagnose root cause before modifying any file. Scope expansion beyond the declared task requires explicit user approval and stops current execution. Generated code must be validated by tests, linting, and type checking before acceptance. AI-specific violations that block delivery: prompt-to-code without diagnosis (fixes symptoms, misses root cause), scope drift (silent expansion of affected area), hallucinated architecture (inventing conventions or commands without evidence), unvalidated generated code (merging without CI gate).
```

**Step 4: Replace "No description available" for M016**

```markdown
Guardrails (tests, linters, type checks, architecture checks) must not be weakened to make a change appear valid. Validation cheating is a Critical violation: deleting failing tests, weakening assertions, disabling lint rules, ignoring type errors, or suppressing warnings without documented evidence and a follow-up task. Every guardrail exception requires: written diagnosis, evidence link (PR or issue), temporary marker with justification, and a follow-up task with TTL (sprint or quarter). CI must enforce all guardrails on every merge — no local-only bypass.
```

**Step 5: Verify descriptions replaced**

```bash
grep -c "No description available" .sdd/source/mandates/mandates.md
```

Expected: output is a number lower than before (M003, M005–M009, M011, M015 still have "No description available" — that is correct, those are out of scope).

**Step 6: Commit**

Files to stage:
- `.sdd/source/mandates/mandates.md`

Message: `docs: enrich M001 M002 M010 M016 mandate descriptions from raw engineering material`

---

## Task 3: Add Code Style guidelines G05–G08 to guidelines.dsl

**Files:**
- Modify: `.sdd/source/guidelines.dsl`
- Modify: `packages/interfaces/sdd_wizard/src/sdd_wizard/orchestration/phase_4_filter_guidelines.py`

**Step 1: Add `gofmt` to LANGUAGE_TAGS for "go" in `phase_4_filter_guidelines.py`**

Find:
```python
"go": {"go", "golang", "golangci-lint", "go-vet"},
```

Replace with:
```python
"go": {"go", "golang", "golangci-lint", "go-vet", "gofmt"},
```

**Step 2: Append G05–G08 to `.sdd/source/guidelines.dsl`**

```
guideline G05 {
  type: SOFT
  title: "Code Style — Python"
  description: "Python projects must use ruff for linting and formatting, mypy for type checking. No bare except, no Any-driven development, no import-time side effects. All public functions must be type-annotated. Use Protocol for contracts, typed models for structured data."
  category: code_quality
  mandate_ref: M018
  tags: ["python", "ruff", "mypy"]
  violations: ["no_type_hints", "bare_except", "any_driven_development", "import_time_side_effects", "monkeypatch_architecture"]
  maturity_level: 2
  examples: ["except: pass → VIOLATION", "except SpecificError as exc: raise ProcessingError(...) from exc → OK"]
}

guideline G06 {
  type: SOFT
  title: "Code Style — Go"
  description: "Go projects must use gofmt for formatting and golangci-lint for static analysis. All errors must be checked and wrapped with context. No panic as control flow for expected errors. No goroutine leaks — every goroutine must have a cancellation path via context.Context."
  category: code_quality
  mandate_ref: M018
  tags: ["go", "golangci-lint", "gofmt"]
  violations: ["ignored_error", "panic_as_control_flow", "goroutine_leak", "package_dumping_ground"]
  maturity_level: 2
  examples: ["_ = json.Unmarshal(data, &v) → VIOLATION", "if err := json.Unmarshal(data, &v); err != nil { return fmt.Errorf(...) } → OK"]
}

guideline G07 {
  type: SOFT
  title: "Code Style — Java"
  description: "Java projects must use Checkstyle and PMD for static analysis. Business logic must not live in controllers. Domain classes must not depend on Spring annotations or JPA in the domain layer. Exceptions must be caught specifically and cause preserved."
  category: code_quality
  mandate_ref: M018
  tags: ["java", "checkstyle", "pmd"]
  violations: ["business_logic_in_controller", "framework_coupled_domain", "exception_swallowing", "over_engineered_inheritance"]
  maturity_level: 2
  examples: ["catch (Exception e) {} → VIOLATION", "catch (SpecificException e) { throw new AppException(cause, e); } → OK"]
}

guideline G08 {
  type: SOFT
  title: "Code Style — TypeScript"
  description: "TypeScript projects must enable strict mode. No any escape hatches. Promises must be awaited or explicitly fire-and-forget with .catch. Business logic must not live in route handlers. External JSON must be validated before casting to domain types."
  category: code_quality
  mandate_ref: M018
  tags: ["typescript", "eslint", "tsc"]
  violations: ["any_escape_hatch", "floating_promises", "business_logic_in_route_handler", "unsafe_type_assertion"]
  maturity_level: 2
  examples: ["const user = payload as User → VIOLATION", "const user = UserSchema.parse(payload) → OK"]
}
```

**Step 3: Verify Phase 4 filters correctly**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/interfaces/sdd_wizard/src')
from sdd_wizard.orchestration.phase_4_filter_guidelines import LANGUAGE_TAGS
print('go tags:', LANGUAGE_TAGS['go'])
assert 'gofmt' in LANGUAGE_TAGS['go'], 'gofmt missing from go tags'
print('OK')
"
```

Expected: prints go tags set including `gofmt`, then `OK`.

**Step 4: Verify DSL parses correctly**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/core/sdd_compiler/src')
from sdd_compiler.dsl_compiler import DSLParser
content = open('.sdd/source/guidelines.dsl').read()
guidelines = DSLParser.parse_guidelines(content)
ids = [g['id'] for g in guidelines]
print('Guidelines:', ids)
assert 'G05' in ids and 'G06' in ids and 'G07' in ids and 'G08' in ids
print('OK')
"
```

Expected: prints list including G01–G08, then `OK`.

**Step 5: Commit**

Files to stage:
- `.sdd/source/guidelines.dsl`
- `packages/interfaces/sdd_wizard/src/sdd_wizard/orchestration/phase_4_filter_guidelines.py`

Message: `feat: add G05-G08 code style guidelines for Python Go Java TypeScript`

---

## Task 4: Add Anti-pattern guidelines G09–G12 to guidelines.dsl

**Files:**
- Modify: `.sdd/source/guidelines.dsl`

**Step 1: Append G09–G12**

```
guideline G09 {
  type: HARD
  title: "Anti-Patterns — Python"
  description: "Python-specific anti-patterns that block merge: bare except, Any-driven development (using Any to bypass type design), monkeypatch architecture (compensating for poor dependency injection with monkeypatching), import-time side effects (I/O or global mutation at import). All errors must be caught specifically and re-raised with context using 'raise ... from exc'."
  category: code_quality
  mandate_ref: M001
  tags: ["python", "ruff", "mypy"]
  violations: ["bare_except", "any_driven_development", "monkeypatch_architecture", "import_time_side_effects"]
  maturity_level: 2
  examples: ["except: pass → VIOLATION", "import db_client at module level executing connection → VIOLATION"]
}

guideline G10 {
  type: HARD
  title: "Anti-Patterns — Go"
  description: "Go-specific anti-patterns that block merge: ignored errors (using _ = err without documented reason), panic as control flow for expected application errors, goroutine leaks (goroutines started without cancellation path), package dumping grounds (internal/common, internal/utils with unrelated responsibilities)."
  category: code_quality
  mandate_ref: M001
  tags: ["go", "golangci-lint"]
  violations: ["ignored_error", "panic_as_control_flow", "goroutine_leak", "package_dumping_ground"]
  maturity_level: 2
  examples: ["file.Close() without err check → VIOLATION", "panic(err) on validation failure → VIOLATION"]
}

guideline G11 {
  type: HARD
  title: "Anti-Patterns — Java"
  description: "Java-specific anti-patterns that block merge: business logic in controllers, framework-coupled domain (Spring/JPA annotations in domain classes), exception swallowing (catch Exception {}), over-engineered inheritance (deep hierarchy where composition would suffice)."
  category: code_quality
  mandate_ref: M001
  tags: ["java", "archunit", "spotbugs"]
  violations: ["business_logic_in_controller", "framework_coupled_domain", "exception_swallowing", "over_engineered_inheritance"]
  maturity_level: 2
  examples: ["catch (Exception e) {} → VIOLATION", "import org.springframework.stereotype in domain class → VIOLATION"]
}

guideline G12 {
  type: HARD
  title: "Anti-Patterns — TypeScript"
  description: "TypeScript-specific anti-patterns that block merge: any escape hatch (using any to silence compiler), floating promises (unhandled async failures), business logic in route handlers, unsafe type assertion (casting external JSON directly to domain types without runtime validation)."
  category: code_quality
  mandate_ref: M001
  tags: ["typescript", "eslint", "tsc"]
  violations: ["any_escape_hatch", "floating_promises", "business_logic_in_route_handler", "unsafe_type_assertion"]
  maturity_level: 2
  examples: ["sendEmail(user) without await or .catch → VIOLATION", "const user = payload as User → VIOLATION"]
}
```

**Step 2: Verify G09–G12 parse**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/core/sdd_compiler/src')
from sdd_compiler.dsl_compiler import DSLParser
content = open('.sdd/source/guidelines.dsl').read()
guidelines = DSLParser.parse_guidelines(content)
ids = [g['id'] for g in guidelines]
assert all(f'G{n:02d}' in ids for n in range(1, 13)), f'Missing IDs: {ids}'
print('All G01-G12 present. OK')
"
```

**Step 3: Commit**

Files to stage:
- `.sdd/source/guidelines.dsl`

Message: `feat: add G09-G12 anti-pattern guidelines for Python Go Java TypeScript`

---

## Task 5: Add Performance guidelines G13–G16 to guidelines.dsl

**Files:**
- Modify: `.sdd/source/guidelines.dsl`

**Step 1: Append G13–G16**

```
guideline G13 {
  type: SOFT
  title: "Performance — Python"
  description: "Python performance must be evidence-based: profile before optimizing. Avoid unnecessary object creation in hot loops. Use generators and lazy evaluation for large sequences. Avoid repeated network or database calls — batch where possible. Cache only when invalidation is explicit. Use async I/O for I/O-bound workloads. Add benchmarks (pytest-benchmark) before and after non-trivial optimizations."
  category: performance
  mandate_ref: M018
  tags: ["python", "pytest"]
  violations: ["premature_optimization", "repeated_io_calls", "cache_without_invalidation", "blocking_io_in_async_context"]
  maturity_level: 1
  examples: ["[str(x) for x in range(1M)] in hot path → VIOLATION", "generator expression with lazy evaluation → OK"]
}

guideline G14 {
  type: SOFT
  title: "Performance — Go"
  description: "Go performance must be measured with pprof before optimizing. Avoid unnecessary allocations in hot paths — prefer value types where appropriate. Use sync.Pool for frequently allocated short-lived objects. Avoid goroutine spawning per request without pool. Use buffered channels intentionally. Benchmark with go test -bench and -benchmem."
  category: performance
  mandate_ref: M018
  tags: ["go", "golangci-lint"]
  violations: ["premature_optimization", "goroutine_per_request_without_pool", "unnecessary_allocation_in_hot_path"]
  maturity_level: 1
  examples: ["spawning goroutine per HTTP request without pool → VIOLATION", "sync.Pool for short-lived objects → OK"]
}

guideline G15 {
  type: SOFT
  title: "Performance — Java"
  description: "Java performance must be measured with JMH or profiler before optimizing. Use StringBuilder for string concatenation in loops. Prefer streams for bulk data operations. Avoid eager loading of large associations — use lazy loading with explicit fetch. Use connection pooling. Avoid String.format in hot paths — use concatenation or MessageFormat."
  category: performance
  mandate_ref: M018
  tags: ["java", "maven", "gradle"]
  violations: ["premature_optimization", "string_concat_in_loop", "eager_loading_large_associations", "missing_connection_pool"]
  maturity_level: 1
  examples: ["String s = '' + item in loop → VIOLATION", "StringBuilder in loop → OK"]
}

guideline G16 {
  type: SOFT
  title: "Performance — Node.js / TypeScript"
  description: "Node.js performance must be measured with Node.js profiler or clinic.js before optimizing. Avoid blocking the event loop with CPU-intensive synchronous work. Use streaming for large data. Batch database queries instead of N+1 patterns. Avoid re-parsing JSON or re-creating regex in hot paths. Use worker threads for CPU-bound tasks."
  category: performance
  mandate_ref: M018
  tags: ["typescript", "nodejs", "npm"]
  violations: ["premature_optimization", "n_plus_one_queries", "blocking_event_loop", "repeated_parsing_in_hot_path"]
  maturity_level: 1
  examples: ["await db.find(id) inside a loop → VIOLATION", "db.findMany({ where: { id: { in: ids } } }) → OK"]
}
```

**Step 2: Verify G13–G16 parse**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/core/sdd_compiler/src')
from sdd_compiler.dsl_compiler import DSLParser
content = open('.sdd/source/guidelines.dsl').read()
guidelines = DSLParser.parse_guidelines(content)
ids = [g['id'] for g in guidelines]
assert all(f'G{n:02d}' in ids for n in range(1, 17)), f'Missing: {[x for x in [f"G{n:02d}" for n in range(1,17)] if x not in ids]}'
print('All G01-G16 present. OK')
"
```

**Step 3: Commit**

Files to stage:
- `.sdd/source/guidelines.dsl`

Message: `feat: add G13-G16 performance guidelines for Python Go Java TypeScript`

---

## Task 6: Add Structure guidelines G17–G20 to guidelines.dsl

**Files:**
- Modify: `.sdd/source/guidelines.dsl`

**Step 1: Append G17–G20**

```
guideline G17 {
  type: SOFT
  title: "Project Structure — Python"
  description: "Python projects must follow src/ layout: src/{package}/ with domain/, application/, adapters/, infrastructure/. Tests mirror src/ under tests/. Use pyproject.toml with poetry or pip-tools. Module names must reflect business capability, not technical role (avoid utils/, helpers/, common/). Maximum one module per responsibility."
  category: architecture
  mandate_ref: M018
  tags: ["python", "poetry", "pip"]
  violations: ["utility_dumping_ground", "flat_module_layout", "tests_not_mirroring_src"]
  maturity_level: 1
  examples: ["src/utils/helpers.py with unrelated functions → VIOLATION", "src/domain/ports/user_repository.py → OK"]
}

guideline G18 {
  type: SOFT
  title: "Project Structure — Go"
  description: "Go projects must use cmd/ for entry points, internal/ for private packages, pkg/ for public library code. Domain logic lives in internal/domain/. Adapters in internal/adapters/. Ports (interfaces) in internal/ports/. Package names reflect cohesive behavior — avoid internal/common, internal/utils. No circular imports."
  category: architecture
  mandate_ref: M018
  tags: ["go", "golang"]
  violations: ["utility_dumping_ground", "circular_imports", "missing_internal_boundary"]
  maturity_level: 1
  examples: ["internal/common/ with unrelated helpers → VIOLATION", "internal/domain/user.go → OK"]
}

guideline G19 {
  type: SOFT
  title: "Project Structure — Java"
  description: "Java projects must follow com.{org}.{app}.{layer} package hierarchy: domain, application, adapters, infrastructure. Domain package must not import any other package except domain itself. Use Maven or Gradle standard layout: src/main/java, src/test/java. Module names reflect business capability."
  category: architecture
  mandate_ref: M018
  tags: ["java", "maven", "gradle"]
  violations: ["utility_dumping_ground", "flat_package_layout", "domain_importing_application"]
  maturity_level: 1
  examples: ["com.example.app.utils.StringHelper with mixed concerns → VIOLATION", "com.example.app.domain.ports.UserRepository → OK"]
}

guideline G20 {
  type: SOFT
  title: "Project Structure — TypeScript"
  description: "TypeScript projects must use src/{domain,application,adapters,infrastructure}/ layout. Path aliases required: @domain/*, @application/*, @adapters/*. tsconfig.json must enable strict mode. Tests in tests/ mirroring src/. No barrel files (index.ts re-exporting everything) — they hide boundaries and slow compilation."
  category: architecture
  mandate_ref: M018
  tags: ["typescript", "nodejs", "npm"]
  violations: ["utility_dumping_ground", "missing_path_aliases", "barrel_file_abuse", "tests_not_mirroring_src"]
  maturity_level: 1
  examples: ["src/utils/index.ts re-exporting 40 symbols → VIOLATION", "import type { UserRepository } from '@domain/ports/UserRepository' → OK"]
}
```

**Step 2: Verify all G01–G20 present**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/core/sdd_compiler/src')
from sdd_compiler.dsl_compiler import DSLParser
content = open('.sdd/source/guidelines.dsl').read()
guidelines = DSLParser.parse_guidelines(content)
ids = [g['id'] for g in guidelines]
missing = [f'G{n:02d}' for n in range(1, 21) if f'G{n:02d}' not in ids]
print('Found:', ids)
print('Missing:', missing)
assert not missing, f'Missing guidelines: {missing}'
print('All G01-G20 present. OK')
"
```

Expected: all 20 IDs listed, `Missing: []`, then `OK`.

**Step 3: Verify Phase 4 filtering works for all 4 languages**

```bash
python3 -c "
import sys; sys.path.insert(0, 'packages/core/sdd_compiler/src')
sys.path.insert(0, 'packages/interfaces/sdd_wizard/src')
from sdd_compiler.dsl_compiler import DSLParser
from sdd_wizard.orchestration.phase_4_filter_guidelines import filter_guidelines_by_language

content = open('.sdd/source/guidelines.dsl').read()
raw = DSLParser.parse_guidelines(content)
guidelines = {g['id']: g for g in raw}

for lang, expected_ids in [
    ('python', ['G01','G05','G09','G13','G17']),
    ('go',     ['G02','G06','G10','G14','G18']),
    ('java',   ['G03','G07','G11','G15','G19']),
    ('js',     ['G04','G08','G12','G16','G20']),
]:
    filtered, removed = filter_guidelines_by_language(guidelines, lang)
    for eid in expected_ids:
        assert eid in filtered, f'{lang}: expected {eid} but got {list(filtered.keys())}'
    print(f'{lang}: {sorted(filtered.keys())} OK')
"
```

Expected: each language receives exactly its 5 guidelines (1 per topic group).

**Step 4: Commit**

Files to stage:
- `.sdd/source/guidelines.dsl`

Message: `feat: add G17-G20 project structure guidelines and verify full Phase 4 filtering`

---

## Task 7: Create core-engineering-principles.md

**Files:**
- Create: `docs/guidelines/core-engineering-principles.md`

**Step 1: Create the file**

```markdown
# Core Engineering Principles (M018)

**Mandate:** M018 — Code Quality Baseline
**Applies to:** All projects, all languages
**Filtered by wizard:** No — these rules are always active

---

## Function and File Size

- Functions: 4–20 lines. One thing, done well. Split when longer.
- Files: under 500 lines. Split by responsibility when exceeded.
- One responsibility per module (SRP). When a file is hard to name, it does too much.

## Naming

- Names must be specific and unique. Target: ≤ 5 grep hits in the codebase.
- Avoid: `data`, `handler`, `Manager`, `Helper`, `Utils`, `Common`.
- Names reveal intention. Grep-friendly names reduce agent context cost.

## Types

- Types must be explicit. No `any`, no untyped `Dict`, no untyped function signatures.
- Typed code is unambiguous for both humans and AI agents.
- Validate external input at system boundaries — never trust raw JSON.

## Duplication

- No code duplication. Extract shared logic into named functions or modules.
- Three similar lines is a pattern. Four is a function.
- DRY applies to logic, not structure — duplication in config is sometimes correct.

## Control Flow

- Early returns over nested ifs. Maximum 2 levels of indentation.
- Guard clauses at the top. Happy path at the bottom.
- Exception messages must include the offending value and expected shape.

## Dependencies

- Inject dependencies via constructor or parameter.
- Never via global state, module-level singletons, or import-time mutation.
- Wrap third-party libraries behind a thin interface owned by the project.

## Comments

- Comments document WHY and provenance: hidden constraints, bug references, upstream limitations.
- Skip `// increment counter` above `i++`. The code explains WHAT.
- Public functions: docstring with intent + one usage example.
- Reference issue numbers or commit SHAs when a line exists because of a specific bug.

## Clean Code for AI Agents

These principles become technical obligations when AI agents work on the codebase:

- **Small functions** = one tool call, full attention, no pagination.
- **Unique names** = ≤ 5 grep hits, agent navigates directly to the right code.
- **Explicit types** = signature answers questions without reading the body.
- **Comments with provenance** = agent knows WHY without reading git log.
- **Tests that run headlessly** = agent writes code, runs tests, adjusts, repeats.

---

## Related

- Language-specific enforcement: [`docs/guidelines/languages/`](languages/)
- DSL guidelines filtered by language: [`.sdd/source/guidelines.dsl`](../../../.sdd/source/guidelines.dsl)
- Mandate source: [`.sdd/source/mandates/mandates.md`](../../../.sdd/source/mandates/mandates.md) — M018
```

**Step 2: Verify file created**

```bash
ls docs/guidelines/core-engineering-principles.md && echo "OK"
```

**Step 3: Commit**

Files to stage:
- `docs/guidelines/core-engineering-principles.md`

Message: `docs: add core-engineering-principles.md as human reference for M018`

---

## Task 8: Create docs/guidelines/languages/python.md

**Files:**
- Create: `docs/guidelines/languages/python.md`

**Step 1: Create the file**

```markdown
# Python Engineering Guidelines

**DSL guidelines active when wizard language = Python:** G01, G05, G09, G13, G17
**Universal principles:** see [core-engineering-principles.md](../core-engineering-principles.md) (M018)

---

## 1. Code Style (G05 — SOFT)

**Tools required:**

```bash
ruff check .
ruff format --check .
mypy .
```

**Rules:**
- All public functions and methods must have type annotations.
- No `bare except` — always catch specific exceptions.
- No `Any` as a default type. Use `Protocol` for structural contracts.
- No import-time side effects (network I/O, global mutation, env reads at import).
- Use typed models (`dataclass`, `TypedDict`, `pydantic.BaseModel`) for structured data.
- Inject dependencies via parameter — never via `import module_with_global_state`.

**Install:**
```bash
pip install ruff mypy
# or with poetry:
poetry add --group dev ruff mypy
```

---

## 2. Architecture & Dependency Direction (G01 — HARD)

See [python-dependency-direction.md](../examples/python-dependency-direction.md) for full reference.

**Summary:** `domain/` and `application/` must not import from `infrastructure/` or `adapters/`. Use `import-linter` to enforce in CI.

---

## 3. Anti-Patterns (G09 — HARD)

### Bare Except

```python
# VIOLATION
try:
    process()
except:
    pass

# OK
try:
    process()
except SpecificError as exc:
    raise ProcessingError("failed to process item") from exc
```

### Any-Driven Development

```python
# VIOLATION
def process(data: Any) -> Any:
    return data["key"]

# OK
def process(data: UserRequest) -> UserResponse:
    return UserResponse(id=data.user_id)
```

### Monkeypatch Architecture

Monkeypatching is for test doubles at real boundaries, not a substitute for dependency injection. If you need to patch 5 internal functions to test one function, the design has a problem.

### Import-Time Side Effects

```python
# VIOLATION — connects to DB at import time
import psycopg2
conn = psycopg2.connect(os.environ["DB_URL"])  # runs on import

# OK — explicit initialization
def create_connection(url: str) -> Connection:
    return psycopg2.connect(url)
```

---

## 4. Performance (G13 — SOFT)

**Measure first:**
```bash
python -m cProfile -o profile.out your_script.py
python -m pstats profile.out
# or with pytest-benchmark:
pytest --benchmark-only
```

**Key rules:**
- Avoid creating large lists when a generator suffices.
- Batch database calls — never N+1.
- Cache only when invalidation strategy is explicit (TTL or event-driven).
- Use `async`/`await` for I/O-bound work; never block the event loop with CPU work.
- Add benchmarks before and after non-trivial performance changes.

---

## 5. Project Structure (G17 — SOFT)

```
src/
  {package}/
    domain/          ← business rules; zero framework imports
      models/
      services/
      ports/         ← interfaces (output contracts)
    application/     ← use cases; imports domain + ports only
      usecases/
    adapters/        ← implements domain ports
      persistence/
      http/
      messaging/
    infrastructure/  ← DI wiring, config, startup
  main.py            ← composition root
tests/               ← mirrors src/{package}/
  domain/
  application/
  adapters/
pyproject.toml
```

**Rules:**
- No `utils/`, `helpers/`, `common/` — name modules by business capability.
- Tests must mirror `src/` structure exactly.
- Use `src/` layout (not flat) to prevent import accidents.

---

## 6. CI Checklist

```bash
ruff check .              # linting
ruff format --check .     # formatting
mypy .                    # type checking
pytest                    # tests
import-linter             # architecture boundary check (optional, see G01)
```

Full CI YAML example: see [python-dependency-direction.md](../examples/python-dependency-direction.md#ci-setup)
```

**Step 2: Verify file created**

```bash
ls docs/guidelines/languages/python.md && wc -l docs/guidelines/languages/python.md
```

**Step 3: Commit**

Files to stage:
- `docs/guidelines/languages/python.md`

Message: `docs: add Python engineering guidelines reference page`

---

## Task 9: Create docs/guidelines/languages/go.md

**Files:**
- Create: `docs/guidelines/languages/go.md`

Content follows the same 6-section structure as python.md — Go-specific:
- Section 1 Code Style (G06): tools = `gofmt`, `golangci-lint`, `go vet`
- Section 2 Architecture (G02): link to `go-dependency-direction.md`
- Section 3 Anti-Patterns (G10): ignored errors, panic as control flow, goroutine leaks, package dumping ground
- Section 4 Performance (G14): pprof, sync.Pool, go test -bench -benchmem
- Section 5 Structure (G18): cmd/, internal/domain/, internal/adapters/, internal/ports/
- Section 6 CI Checklist: `go test ./...`, `go test -race ./...`, `go vet ./...`, `golangci-lint run`

**Step 1: Create `docs/guidelines/languages/go.md` using the structure above with Go-specific content from the raw material in `.analysis/pending/language/antipatterns.md` (sections 6.x) and `.analysis/pending/language/base_2.md` (Go section).**

**Step 2: Verify file created**

```bash
ls docs/guidelines/languages/go.md && wc -l docs/guidelines/languages/go.md
```

**Step 3: Commit**

Files to stage:
- `docs/guidelines/languages/go.md`

Message: `docs: add Go engineering guidelines reference page`

---

## Task 10: Create docs/guidelines/languages/java.md

**Files:**
- Create: `docs/guidelines/languages/java.md`

Content follows the same 6-section structure — Java-specific:
- Section 1 Code Style (G07): tools = `mvn verify`, Checkstyle, PMD, SpotBugs
- Section 2 Architecture (G03): link to `java-dependency-direction.md`
- Section 3 Anti-Patterns (G11): business logic in controller, framework-coupled domain, exception swallowing, over-engineered inheritance
- Section 4 Performance (G15): JMH, StringBuilder in loops, connection pooling, lazy loading
- Section 5 Structure (G19): `com.{org}.{app}.{domain,application,adapters,infrastructure}` packages
- Section 6 CI Checklist: `mvn verify` (includes ArchUnit + Checkstyle + tests)

**Step 1: Create `docs/guidelines/languages/java.md` using the structure above with Java-specific content from `.analysis/pending/language/antipatterns.md` (sections 7.x) and `.analysis/pending/language/performance.md` (section 6) and `.analysis/pending/language/base_2.md` (Java section).**

**Step 2: Verify file created**

```bash
ls docs/guidelines/languages/java.md && wc -l docs/guidelines/languages/java.md
```

**Step 3: Commit**

Files to stage:
- `docs/guidelines/languages/java.md`

Message: `docs: add Java engineering guidelines reference page`

---

## Task 11: Create docs/guidelines/languages/typescript.md

**Files:**
- Create: `docs/guidelines/languages/typescript.md`

Content follows the same 6-section structure — TypeScript-specific:
- Section 1 Code Style (G08): tools = `tsc --noEmit`, `eslint`, `npm test`; strict mode required
- Section 2 Architecture (G04): link to `nodejs-typescript-dependency-direction.md`
- Section 3 Anti-Patterns (G12): any escape hatch, floating promises, business logic in route handlers, unsafe type assertion
- Section 4 Performance (G16): event loop blocking, N+1 queries, streaming, worker threads
- Section 5 Structure (G20): `src/{domain,application,adapters,infrastructure}/`, path aliases, no barrel files
- Section 6 CI Checklist: `tsc --noEmit`, `eslint . --ext .ts --max-warnings 0`, `npm test`

**Step 1: Create `docs/guidelines/languages/typescript.md` using the structure above with TypeScript-specific content from `.analysis/pending/language/antipatterns.md` (sections 9.x) and `.analysis/pending/language/base_2.md` (Node.js/TypeScript section).**

**Step 2: Verify file created**

```bash
ls docs/guidelines/languages/typescript.md && wc -l docs/guidelines/languages/typescript.md
```

**Step 3: Commit**

Files to stage:
- `docs/guidelines/languages/typescript.md`

Message: `docs: add TypeScript engineering guidelines reference page`

---

## Task 12: Update index files

**Files:**
- Modify: `docs/indices/MASTER_INDEX.md`
- Modify: `docs/spec/canonical/INDEX.md`
- Modify: `docs/guides/architecture/language-adapter-guidelines.md`

**Step 1: Update `docs/indices/MASTER_INDEX.md`**

Find the Core Pillars section and replace the `guides/architecture/` entry:

```markdown
- **`guides/architecture/`**: [Language Adapter Guidelines](../guides/architecture/language-adapter-guidelines.md) — Schema for language-specific enforcement (wizard Phase 4)
- **`guides/guidelines/`**: [Core Engineering Principles](../guides/guidelines/core-engineering-principles.md) (M018) | Languages: [Python](../guides/guidelines/languages/python.md) · [Go](../guides/guidelines/languages/go.md) · [Java](../guides/guidelines/languages/java.md) · [TypeScript](../guides/guidelines/languages/typescript.md)
```

**Step 2: Update `docs/spec/canonical/INDEX.md`**

In the Language Adapter Guidelines section, add after the existing content:

```markdown
- **Java example**: [guides/architecture/examples/java-dependency-direction.md](../../../docs/guides/architecture/examples/java-dependency-direction.md)
- **TypeScript example**: [guides/architecture/examples/nodejs-typescript-dependency-direction.md](../../../docs/guides/architecture/examples/nodejs-typescript-dependency-direction.md)
- **DSL source (all G01–G20)**: [.sdd/source/guidelines.dsl](../../../../.sdd/source/guidelines.dsl)

## 📐 Language Engineering Guidelines (M018)

*Full per-language reference. Wizard selects language; compiled output contains relevant guidelines.*

- **Core principles**: [guides/guidelines/core-engineering-principles.md](../../../docs/guides/guidelines/core-engineering-principles.md) — M018 human reference
- **Python**: [guides/guidelines/languages/python.md](../../../docs/guides/guidelines/languages/python.md)
- **Go**: [guides/guidelines/languages/go.md](../../../docs/guides/guidelines/languages/go.md)
- **Java**: [guides/guidelines/languages/java.md](../../../docs/guides/guidelines/languages/java.md)
- **TypeScript**: [guides/guidelines/languages/typescript.md](../../../docs/guides/guidelines/languages/typescript.md)
```

**Step 3: Update `docs/guides/architecture/language-adapter-guidelines.md`**

In the Tags Convention table, update the note at the bottom:

```markdown
See complete DSL: `.sdd/source/guidelines.dsl` — G01–G20 covering architecture, code style, anti-patterns, performance, and project structure for all 4 languages.
```

In the Examples section, replace the existing links block with:

```markdown
### By topic

- [Python — Dependency Direction](examples/python-dependency-direction.md) (G01)
- [Go — Dependency Direction](examples/go-dependency-direction.md) (G02)
- [Java — Dependency Direction](examples/java-dependency-direction.md) (G03)
- [Node.js / TypeScript — Dependency Direction](examples/nodejs-typescript-dependency-direction.md) (G04)

### Full language reference (all topics)

- [Python Engineering Guidelines](../guidelines/languages/python.md)
- [Go Engineering Guidelines](../guidelines/languages/go.md)
- [Java Engineering Guidelines](../guidelines/languages/java.md)
- [TypeScript Engineering Guidelines](../guidelines/languages/typescript.md)
```

**Step 4: Verify all index files updated**

```bash
grep -l "core-engineering-principles\|language.*guidelines" \
  docs/indices/MASTER_INDEX.md \
  docs/spec/canonical/INDEX.md \
  docs/guides/architecture/language-adapter-guidelines.md
```

Expected: all 3 files listed.

**Step 5: Commit**

Files to stage:
- `docs/indices/MASTER_INDEX.md`
- `docs/spec/canonical/INDEX.md`
- `docs/guides/architecture/language-adapter-guidelines.md`

Message: `docs: update index files with M018 and G05-G20 language guidelines`

---

## Task 13: Move raw material to done and run existing tests

**Files:**
- Move: `.analysis/pending/language/` → `.analysis/done/language/`
- No test file changes — DSL parsing tests already cover tag extraction

**Step 1: Move raw material directory**

```bash
mv .analysis/pending/language .analysis/done/language
```

**Step 2: Verify move**

```bash
ls .analysis/done/language/ && echo "OK"
ls .analysis/pending/language/ 2>/dev/null && echo "still exists" || echo "removed OK"
```

Expected: files listed in `done/language/`, "removed OK" for pending.

**Step 3: Run existing DSL compiler tests**

```bash
python -m pytest packages/core/sdd_compiler/tests/ -v
```

Expected: all tests pass. No new tests needed — tag extraction was added in the previous session and covers the new fields used here (`tags`, etc.).

**Step 4: Run Phase 4 filter tests**

```bash
python -m pytest packages/interfaces/sdd_wizard/ -v -k "phase_4 or filter"
```

Expected: all tests pass.

**Step 5: Final verification — all 20 guidelines filter correctly**

```bash
python3 -c "
import sys
sys.path.insert(0, 'packages/core/sdd_compiler/src')
sys.path.insert(0, 'packages/interfaces/sdd_wizard/src')
from sdd_compiler.dsl_compiler import DSLParser
from sdd_wizard.orchestration.phase_4_filter_guidelines import filter_guidelines_by_language

content = open('.sdd/source/guidelines.dsl').read()
raw = DSLParser.parse_guidelines(content)
guidelines = {g['id']: g for g in raw}

print(f'Total guidelines in DSL: {len(guidelines)}')
for lang in ['python', 'go', 'java', 'js']:
    filtered, removed = filter_guidelines_by_language(guidelines, lang)
    print(f'{lang}: {sorted(filtered.keys())} ({len(filtered)} active, {len(removed)} filtered out)')
"
```

Expected output:
```
Total guidelines in DSL: 20
python: ['G01', 'G05', 'G09', 'G13', 'G17'] (5 active, 15 filtered out)
go: ['G02', 'G06', 'G10', 'G14', 'G18'] (5 active, 15 filtered out)
java: ['G03', 'G07', 'G11', 'G15', 'G19'] (5 active, 15 filtered out)
js: ['G04', 'G08', 'G12', 'G16', 'G20'] (5 active, 15 filtered out)
```

**Step 6: Final commit**

Files to stage:
- `.analysis/done/language/` (all files)

Message: `chore: move raw language material to done after integration into governance system`
