# Example: Dependency Direction — Go (adapts M001)

**Guideline ID:** G02 (sequential; see `guidelines.dsl`)
**Canonical mandate:** M001 — Clean Architecture
**Language:** Go

---

## DSL Entry

```
guideline G02 {
  type: HARD
  title: "Dependency Direction — Go"
  description: "Domain and application packages must not import infrastructure adapters or external clients. Use golangci-lint with depguard to enforce boundaries."
  category: architecture
  mandate_ref: M001
  tags: ["go", "golangci-lint", "go-vet"]
  enforcement: {
    gate: ci
    severity: block
    tools: ["go vet ./...", "go test -race ./...", "golangci-lint run"]
  }
  violations: ["domain_imports_infrastructure", "indirect_architectural_cycle", "app_imports_concrete_adapter"]
  exception_policy: {
    requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
    ttl: sprint
  }
  maturity_level: 3
  examples: ["import internal/adapters/postgres in internal/domain → VIOLATION", "import internal/ports in internal/domain → OK"]
}
```

---

## Package Structure

```
cmd/
  main.go            ← composition root, wires concrete adapters

internal/
  domain/            ← business rules, zero external imports
  app/               ← use cases, imports domain + ports only
  ports/             ← interfaces (contracts), no implementations
  adapters/
    postgres/        ← implements ports.UserRepository
    http/            ← implements ports.Notifier
  infrastructure/    ← DB connections, env config, external SDKs
```

---

## Violation Patterns

### `domain_imports_infrastructure`

```go
// internal/domain/user.go — VIOLATION
import (
    "internal/adapters/postgres"  // ← breaks direction
    "database/sql"                // ← infrastructure in domain
)
```

**Why it matters:** Go's compiler blocks circular imports but allows
domain→adapter imports. These still represent architectural violations
that golangci-lint/depguard can detect.

**Correct pattern:**
```go
// internal/domain/user.go — OK
// No imports from internal/adapters or internal/infrastructure
type UserRepository interface {
    FindByID(ctx context.Context, id string) (*User, error)
}
```

### `indirect_architectural_cycle`

Go's compiler blocks direct cycles but allows indirect ones:

```
strategist → runtime → governance → strategist (indirect)
```

golangci-lint with `cyclop` or manual architecture checks detect this.

---

## Exception Example (M016 compliant)

```go
// internal/domain/legacy.go
import (
    // nolint:depguard // diagnosis: legacy SDK predates ports layer
    // evidence: https://github.com/org/repo/issues/892
    // follow_up: issue #892 — extract to adapter before v2.0
    "github.com/org/legacy-sdk"
)
```

---

## Tooling Setup

**`golangci-lint` config (`.golangci.yml`):**
```yaml
linters:
  enable:
    - depguard
    - cyclop

linters-settings:
  depguard:
    rules:
      domain-no-infra:
        files:
          - "internal/domain/**/*.go"
          - "internal/app/**/*.go"
        deny:
          - pkg: "internal/adapters"
            desc: "domain/app must not import adapters directly"
          - pkg: "internal/infrastructure"
            desc: "domain/app must not import infrastructure directly"
          - pkg: "database/sql"
            desc: "database drivers belong in adapters layer"
```

**CI check:**
```bash
go vet ./...
go test -race ./...
golangci-lint run
```
