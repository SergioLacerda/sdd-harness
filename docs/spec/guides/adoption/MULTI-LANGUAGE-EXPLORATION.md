# 🌍 Multi-Language Exploration — Roadmap for v3.0

**Status:** Planning Phase
**Target:** SDD v3.0 (2026 Q4)
**Current:** Python + FastAPI only

---

## Vision

**Phase 1 (Current v2.1):** Build robust patterns in Python + FastAPI
**Phase 2 (v2.2):** Gather real metrics, validate framework
**Phase 3 (v3.0):** Expand to Node.js, Go, Rust with same principles

---

## Why Multi-Language?

### Adoption Barriers We're Fixing
- ❌ "I love Go but SDD is Python-only" → Will support Go
- ❌ "We're a Node shop" → Will support Node.js
- ❌ "Rust for systems work" → Will support Rust
- ✅ Now: "SDD principles apply to my stack"

### Economics
- More users = more feedback
- More languages = more battle-testing
- Principles validated across ecosystems
- Network effects (interop between microservices)

### Timeline Reasoning
- v2.1 (now): Python solid, metrics gathering
- v2.2 (Q2): Real data on success, decide expansion
- v3.0 (Q4): Launch Node.js + Go + Rust versions

---

## The Plan: v3.0 Architecture

### Core: Language-Agnostic Principles

```
SDD v3.0 Core (Language Agnostic)
├── Clean Architecture (8 layers)
├── Async-First Mindset
├── Ports & Adapters Pattern
├── Immutable Decisions (ADRs)
├── Explicit Governance Rules
└── [15 total principles]

    ↓ Each language implements above ↓

    ├── sdd-python/ (v2.1, proven)
    ├── sdd-nodejs/ (v3.0, new)
    ├── sdd-go/ (v3.0, new)
    └── sdd-rust/ (v3.0, new)
```

### Each Language Has

```
sdd-{language}/
├── README.md → Language-specific setup
├── core/
│   ├── templates/ → Boilerplate for 8 layers
│   ├── linting/ → Language-specific rules
│   ├── testing/ → Best practices for language
│   └── ci-cd/ → Language-specific pipeline
├── examples/
│   ├── simple/ → Hello world + tests
│   ├── microservice/ → Full 8-layer example
│   └── integration/ → Multi-service example
└── docs/
    ├── PRINCIPLES.md → How v3.0 manifests in this language
    ├── SETUP.md → Language-specific setup
    └── MIGRATION.md → How to bring existing project
```

---

## sdd-nodejs/ — Node.js Implementation (v3.0)

### Technology Stack
- **Runtime:** Node.js 18+
- **Framework:** Express or Fastify (team choice)
- **Validation:** Zod or Joi
- **Async:** Native Promises/async-await
- **Package Manager:** npm or pnpm
- **Type System:** TypeScript (recommended)

### What's Different from Python
- No decorators (use middleware instead)
- Express routing vs FastAPI path operations
- Zod schemas vs Pydantic models
- npm ecosystem vs pip
- Jest vs pytest (testing)

### Core Differences Map

| Concept | Python | Node.js |
|---------|--------|---------|
| Validation | Pydantic | Zod |
| Framework | FastAPI | Express/Fastify |
| Async | asyncio | Promise/async-await |
| Type hints | Type annotations | TypeScript |
| Package mgmt | pip | npm |
| Testing | pytest | Jest |
| Linting | pylint + flake8 | ESLint |

### Example: Domain Layer (Node.js)

```typescript
// No framework imports (same principle as Python)
// src/domain/campaign/campaign.ts

export class Campaign {
  constructor(
    public id: string,
    public name: string,
    public createdAt: Date
  ) {}

  rename(newName: string): void {
    if (newName.length < 3) {
      throw new Error("Campaign name must be at least 3 characters");
    }
    this.name = newName;
  }
}
```

### Example: Port (Node.js)

```typescript
// src/ports/campaign-repository.ts
// Abstract interface (same pattern as Python)

export interface CampaignRepositoryPort {
  save(campaign: Campaign): Promise<void>;
  get(id: string): Promise<Campaign | null>;
}
```

### Example: Adapter (Node.js)

```typescript
// src/adapters/campaign-repository-postgres.ts
// Concrete implementation

export class PostgresCampaignRepository implements CampaignRepositoryPort {
  constructor(private db: Pool) {}

  async save(campaign: Campaign): Promise<void> {
    await this.db.query(
      "INSERT INTO campaigns (id, name, created_at) VALUES ($1, $2, $3)",
      [campaign.id, campaign.name, campaign.createdAt]
    );
  }

  async get(id: string): Promise<Campaign | null> {
    const result = await this.db.query(
      "SELECT * FROM campaigns WHERE id = $1",
      [id]
    );
    return result.rows[0] ? new Campaign(...) : null;
  }
}
```

---

## sdd-go/ — Go Implementation (v3.0)

### Technology Stack
- **Language:** Go 1.21+
- **Framework:** Gin or Echo (team choice)
- **Validation:** go-playground/validator or ozzo-validation
- **Async:** Goroutines + channels
- **Package Manager:** go mod
- **Type System:** Static typing built-in

### Core Differences Map

| Concept | Python | Go |
|---------|--------|-----|
| Validation | Pydantic | struct tags + validator |
| Framework | FastAPI | Gin/Echo |
| Async | asyncio | Goroutines/channels |
| Type hints | Optional annotations | Required, static |
| Error handling | try/except | if err != nil |
| Interfaces | Protocol | interface{} / concrete |
| Testing | pytest | testing.T |

### Example: Domain Layer (Go)

```go
// domain/campaign/campaign.go
// Pure business logic, no framework

package campaign

type Campaign struct {
    ID        string
    Name      string
    CreatedAt time.Time
}

func (c *Campaign) Rename(newName string) error {
    if len(newName) < 3 {
        return errors.New("Campaign name must be at least 3 characters")
    }
    c.Name = newName
    return nil
}
```

### Example: Port (Go)

```go
// ports/campaign_repository.go
// Abstract interface

package ports

import "context"

type CampaignRepository interface {
    Save(ctx context.Context, campaign *campaign.Campaign) error
    Get(ctx context.Context, id string) (*campaign.Campaign, error)
}
```

---

## sdd-rust/ — Rust Implementation (v3.0)

### Technology Stack
- **Language:** Rust 1.70+
- **Framework:** Actix-web or Axum
- **Validation:** serde + custom validators
- **Async:** Tokio runtime
- **Package Manager:** Cargo
- **Type System:** Strong, static, very strict

### Core Differences Map

| Concept | Python | Rust |
|---------|--------|------|
| Validation | Pydantic | serde + validators |
| Framework | FastAPI | Actix-web/Axum |
| Async | asyncio | Tokio |
| Type hints | Annotations | Required, inferred |
| Error handling | Exception | Result<T, E> |
| Borrowing | Automatic GC | Explicit ownership |
| Memory | Managed | Manual (compiler enforces) |

### Example: Domain Layer (Rust)

```rust
// domain/campaign.rs
// Pure business logic, no framework

#[derive(Clone, Debug)]
pub struct Campaign {
    pub id: String,
    pub name: String,
    pub created_at: DateTime<Utc>,
}

impl Campaign {
    pub fn rename(&mut self, new_name: String) -> Result<(), String> {
        if new_name.len() < 3 {
            return Err("Campaign name must be at least 3 characters".to_string());
        }
        self.name = new_name;
        Ok(())
    }
}
```

---

## Implementation Strategy

### 2026 Q2: Preparation
- [ ] Finalize v2.1 metrics
- [ ] Community feedback on SDD approach
- [ ] Design Node.js skeleton
- [ ] Design Go skeleton
- [ ] Design Rust skeleton

### 2026 Q3: Alpha Implementations
- [ ] sdd-nodejs/ alpha
- [ ] sdd-go/ alpha
- [ ] sdd-rust/ alpha
- [ ] Community testing
- [ ] Iterate on design

### 2026 Q4: v3.0 Launch
- [ ] Release sdd-nodejs/ v1.0
- [ ] Release sdd-go/ v1.0
- [ ] Release sdd-rust/ v1.0
- [ ] Update main SDD docs
- [ ] Unified governance framework
- [ ] Cross-language examples

---

## Shared Infrastructure (v3.0)

### Unified Documentation
```
sdd/
├── core/
│   ├── PRINCIPLES.md (15 principles, language-agnostic)
│   ├── ARCHITECTURE.md (8-layer pattern)
│   └── GOVERNANCE.md (constitutional rules)
├── python/
├── nodejs/
├── go/
└── rust/
```

### Interoperability
- Services in different languages can coexist
- Shared ADR format (architecture decisions)
- Unified governance rules
- Cross-language test suites (contract tests)

### CI/CD Federation
```yaml
# .github/workflows/sdd-compliance.yml
# Unified pipeline for multi-language projects

jobs:
  python:
    runs-on: ubuntu-latest
    steps: [run Python compliance]

  nodejs:
    runs-on: ubuntu-latest
    steps: [run Node.js compliance]

  go:
    runs-on: ubuntu-latest
    steps: [run Go compliance]

  integration:
    needs: [python, nodejs, go]
    steps: [contract tests between languages]
```

---

## Success Metrics (v3.0)

- ✅ Each language repo has 100+ GitHub stars
- ✅ Real projects use each version in production
- ✅ Community contributions on each
- ✅ Unified governance working across 4 languages
- ✅ Framework recognized as language-agnostic standard

---

## Known Challenges

### Per-Language
- Different idioms (Go vs Python very different)
- Different testing approaches
- Different packaging ecosystems
- Different performance characteristics

### Cross-Language
- Keeping principles consistent
- Documentation across 4 languages
- Community management (4x communities)
- Performance parity (Go faster than Python? That's OK)

---

## Why This Approach?

### NOT: "One SDD for all languages"
❌ Unrealistic — Go ≠ Python ≠ Rust
❌ Would satisfy nobody

### YES: "Same principles, different implementation"
✅ Clean Architecture works in all 4
✅ Async-first works in all 4
✅ Ports & Adapters works in all 4
✅ Explicit rules work in all 4

---

## Get Involved

### Today (v2.1)
- Use SDD Python + FastAPI
- Provide feedback
- Report pain points

### Soon (v2.2)
- Help gather metrics
- Suggest improvements
- Shape v3.0 priorities

### Future (v3.0)
- Contribute to language repos
- Build examples
- Become a maintainer

---

## Questions?

**What about PHP/Java/C#?**
→ v3.0 focuses on 4. Others can contribute.

**Can I use SDD with my language now?**
→ Yes! Adapt the principles. Full support in v3.0.

**What if my language isn't listed?**
→ Community contribution welcome! Start a discussion.

**When exactly is v3.0?**
→ Q4 2026 (flexible based on v2.2 feedback).

---

## Next Steps

1. **v2.1 (now):** Build solid Python version ✅
2. **v2.2 (Q2):** Gather real metrics, validate
3. **v3.0 (Q4):** Launch multi-language

Your feedback shapes all of it.

---

**SDD is collaborative. Your input matters.**

*Framework under active development.*
