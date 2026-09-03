# Rules: Code Style

Hard rules for naming, organization, and code formatting. Go-only for now — see
`formatting.md` for the same scope decision.

---

## Naming Conventions

### Exported Types (structs, interfaces)

- **MUST** use PascalCase: `UserRepository`, `CampaignUseCase`
- **MUST** be singular nouns: ❌ `Users` → ✅ `User`
- **MUST** include domain concept in name: `UserEntity`, `CampaignRepository`
- **Port interfaces:** Suffix with `Port`: `RepositoryPort`, `NotificationPort`
- **Adapter structs:** Suffix with `Adapter`: `PostgresAdapter`, `FileSystemAdapter`

### Functions & Methods

- **Exported:** PascalCase verb phrases: `GetUserByID()`, `SaveCampaign()`
- **Unexported:** camelCase verb phrases, no leading underscore (Go uses case, not
  a prefix, to mark visibility): `validateInput()`, `transformData()`
- **MUST NOT** abbreviate: ❌ `GetUsrID()` → ✅ `GetUserByID()`
- **Concurrency:** functions that may block MUST accept a `context.Context` as the
  first parameter, not a bespoke async suffix or wrapper type

### Variables & Constants

- **Variables:** camelCase (unexported), PascalCase (exported): `userID`,
  `campaignData`, `VectorIndex`
- **Constants:** same camelCase/PascalCase convention as variables — Go does not
  use `ALL_CAPS` for constants; group related constants with `iota` when they form
  a sequence
- **MUST** be descriptive: ❌ `x`, `tmp`, `data` → ✅ `vectorEmbedding`, `tempCache`
- **Boolean variables:** Prefix with `is`, `has`, `can`: `isActive`,
  `hasPermissions`, `canMerge`

### Files & Packages

- **Files:** lowercase, words separated by underscore only when it improves
  readability: `campaign_repository.go`, `userservice.go`
- **Tests:** MUST suffix with `_test.go` — this is a Go toolchain requirement, not
  only a convention: `campaign_repository_test.go`
- **Packages:** short, lowercase, single word, no underscores or mixedCaps:
  `repository`, `usecase`, `adapter` — never `repositories` (Go package names are
  typically singular and describe what the package provides, not a collection)

---

## Code Organization

### Import Order

```go
// Order:
// 1. Standard library
// 2. Third-party
// 3. Local/internal packages

import (
    "context"
    "fmt"

    "github.com/some/thirdparty"

    "example.com/project/internal/domain"
    "example.com/project/internal/application/ports"
)
```

`goimports` enforces this grouping automatically — run it, do not hand-order
imports.

### Struct & Interface Organization

```go
// MyType does X.
type MyType struct {
    // 1. Fields
    field1 string
}

// NewMyType constructs a MyType.
func NewMyType(field1 string) *MyType {
    return &MyType{field1: field1}
}

// 2. Exported methods (constructor first, then exported methods)
func (m *MyType) DoSomething() error {
    return m.doInternalStep()
}

// 3. Unexported methods
func (m *MyType) doInternalStep() error {
    return nil
}
```

---

## Formatting

- **Indentation:** tabs, via `gofmt` — never spaces, never hand-formatted
- **Line length:** no hard limit enforced by `gofmt`; keep lines readable, split
  long expressions across multiple lines when they hurt scanability
- **Blank lines:** let `gofmt` normalize spacing — do not hand-tune it
- **Use `gofmt`, `go vet` & `golangci-lint`:** Enforce via CI/CD (see `make lint`)

---

## Documentation

- **Doc comments:** Required for every exported identifier (type, func, const,
  var); MUST start with the identifier's name per Go doc-comment convention:
  `// UserRepository handles persistence for User aggregates.`
- **Comments:** Explain WHY, not WHAT (code already explains what)
- **Type hints:** N/A — Go is statically typed; every signature already carries
  its types

---

## Common Violations

| ❌ Anti-Pattern | ✅ Fix |
|---|---|
| `x`, `tmpVar`, `data` | `userID`, `tempCache`, `campaignData` |
| `Users` (plural exported type) | `User` (singular) |
| `get_user_id()` (snake_case function) | `GetUserID()` / `getUserID()` (Go case convention) |
| Hardcoded values | Use named constants |
| Mixed import order | Run `goimports` (stdlib → 3rd-party → local) |
| Magic numbers | Extract to named constants |
| `_test` prefix instead of suffix | File MUST end in `_test.go` |

---

## Validation

Enforced via:

- ✅ `gofmt -l .` — Formatting violations
- ✅ `go vet ./...` — Suspicious constructs
- ✅ `golangci-lint run` — Linting and style violations combined
- ✅ `make lint` — All style checks combined
- ✅ `make pre-delivery` — P004 Pre-Delivery Quality Gate includes lint
