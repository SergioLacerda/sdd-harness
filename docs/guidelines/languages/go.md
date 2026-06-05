# Go Engineering Guidelines

**DSL guidelines active when wizard language = Go:** G02, G06, G10, G14, G18
**Universal principles:** see [core-engineering-principles.md](../core-engineering-principles.md) (M018)

---

## 1. Code Style (G06 — SOFT)

**Tools required:**

```bash
gofmt -l .
go vet ./...
golangci-lint run
```

**Rules:**

- All errors must be checked — never use `_ = err` without a documented reason.

- Errors must be wrapped with context using `fmt.Errorf("...: %w", err)`.

- No `panic` for expected application errors — return errors explicitly.

- Every goroutine must have a cancellation path via `context.Context`.

- Package names must be lowercase, single words reflecting cohesive behavior.

**Install:**

```bash
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

---

## 2. Architecture & Dependency Direction (G02 — HARD)

See [go-dependency-direction.md](../architecture/examples/go-dependency-direction.md) for full reference.

**Summary:** `internal/domain/`and`internal/app/`must not import`internal/adapters/`. Use `golangci-lint`with`depguard` to enforce in CI.

---

## 3. Anti-Patterns (G10 — HARD)

### Ignored Error

```go
// VIOLATION
file.Close()
_ = json.Unmarshal(data, &value)

// OK
if err := json.Unmarshal(data, &value); err != nil {
    return fmt.Errorf("decode payload: %w", err)
}
defer func() {
    if err := file.Close(); err != nil {
        log.Printf("close file: %v", err)
    }
}()
```

### Panic as Control Flow

```go
// VIOLATION
func GetUser(id string) *User {
    if id == "" {
        panic("id cannot be empty")
    }
    // ...
}

// OK
func GetUser(id string) (*User, error) {
    if id == "" {
        return nil, fmt.Errorf("GetUser: id cannot be empty")
    }
    // ...
}
```

### Goroutine Leak

```go
// VIOLATION — no cancellation path
go func() {
    for {
        process()
        time.Sleep(time.Second)
    }
}()

// OK
go func(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        default:
            process()
            time.Sleep(time.Second)
        }
    }
}(ctx)
```

### Package Dumping Ground

```
// VIOLATION
internal/common/      # unrelated helpers dumped here
internal/utils/       # no clear ownership

// OK
internal/domain/user.go
internal/ports/user_repository.go
internal/adapters/postgres/user_repo.go
```

---

## 4. Performance (G14 — SOFT)

**Measure first:**

```bash
go test -bench=. -benchmem ./...
go tool pprof cpu.prof
```

**Key rules:**

- Profile with `pprof` before optimizing any hot path.

- Use `sync.Pool` for frequently allocated short-lived objects.

- Avoid goroutine spawning per request without a worker pool.

- Use buffered channels intentionally — document the buffer size rationale.

- Prefer value types over pointers for small structs in hot paths.

---

## 5. Project Structure (G18 — SOFT)

```
cmd/
  server/
    main.go           # entry point
internal/
  domain/             # business rules; no external imports
    model/
    service/
    ports/            # interfaces (output contracts)
  application/        # use cases; imports domain + ports only
  adapters/           # implements domain ports
    postgres/
    http/
    kafka/
  infrastructure/     # DI wiring, config, startup
pkg/                  # public library code (if any)
go.mod
go.sum
```

**Rules:**

- Avoid `internal/common`, `internal/utils` — name packages by behavior.

- No circular imports — enforced by the Go compiler.

- Package boundaries define architecture boundaries.

---

## 6. CI Checklist

```bash
go build ./...                    # compilation
go test ./...                     # tests
go test -race ./...               # race detector
go vet ./...                      # static analysis
golangci-lint run                 # linting
go mod verify                     # dependency integrity
govulncheck ./...                 # vulnerability scan (optional)
```
