# Resolution Bypass — Go
>
> Parent: [`RESOLUTION_BYPASS.md`](../RESOLUTION_BYPASS.md)

---

## ❌ Go-Specific Hacks

### 1. Vendor Folder Abuse (Legacy)```bash

# ❌ Committing the vendor folder and manually editing files inside it# to "fix" a dependency without changing the import path.```

**Why:** Developer wants to customize a library but doesn't want to fork it or use proper overrides.

---

### 2. Global `replace` in `go.mod` for local hacks```go

// ❌ Using replace for non-local development libraries in production
replace github.com/external/lib => ../../hacks/lib

```
**Why:** Bypasses versioning. The build becomes non-deterministic and tied to a specific local directory structure.

---

### 3. Build Tag Hijacking```go
// ❌ Using custom build tags to swap out core resolution logic
// based on environment variables.
// +build custom_hack
```

**Why:** Creates "ghost code" that only resolves when specific, non-standard flags are passed to the compiler.

---

### 4. `GOPATH` Mixing```bash

# ❌ Relying on code sitting in a specific GOPATH/src location# outside of the current go.mod scope.```

**Why:** Legacy mindset. Mixes modern module resolution with old-style path-based resolution.

---

## ✅ Go Cures

### Cure 1: Proper ForkingIf you need to change a library, fork it to your own repository and change the import path in your `go.mod`

```go
require github.com/your-user/forked-lib v1.0.0
```

### Cure 2: Local Modules (Monorepo)Use `go.mod` workspaces if you have multiple local modules

```bash
# go.workgo 1.21

use (
    ./cmd/app
    ./internal/shared
)
```

### Cure 3: Dependency InjectionIf you need different behavior per environment, use Interfaces and Dependency Injection, not build tags or file-swapping

---

## 🔍 Detection```bash

# Check go.mod for suspicious local replacesgrep "=> .." go.mod

# Check for manual vendor edits (if using vendor)go mod verify

```

---

## 📏 Rule> Your code should compile and run successfully with `go build ./...` immediately after a `git clone`, without requiring any environment variables like `GOPATH` or custom build tags to resolve imports.
