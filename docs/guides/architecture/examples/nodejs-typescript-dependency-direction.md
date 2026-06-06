# Example: Dependency Direction — Node.js / TypeScript (adapts M001)

**Guideline ID:** G04 (sequential; see `guidelines.dsl`)
**Canonical mandate:** M001 — Clean Architecture
**Language:** Node.js / TypeScript

---

## DSL Entry

```
guideline G04 {
  type: HARD
  title: "Dependency Direction — Node.js / TypeScript"
  description: "Domain and application modules must not import infrastructure adapters, database clients, or framework code directly. Use ESLint import rules and tsc strict mode to enforce boundaries."
  category: architecture
  mandate_ref: M001
  tags: ["typescript", "eslint", "tsc"]
  enforcement: {
    gate: ci
    severity: block
    tools: ["tsc --noEmit", "eslint . --ext .ts", "npm test"]
  }
  violations: ["domain_imports_infrastructure", "app_imports_concrete_adapter", "orm_client_in_domain", "express_req_res_in_domain"]
  exception_policy: {
    requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
    ttl: sprint
  }
  maturity_level: 2
  examples: ["import { PrismaClient } from '@prisma/client' in domain/ -> VIOLATION", "import type { UserRepository } from '../ports/UserRepository' in domain/ -> OK"]
}
```

---

## Directory Structure

```
src/
  domain/
    models/          ← plain TypeScript classes/interfaces; zero framework imports
    services/        ← domain services
    ports/           ← output port interfaces (contracts for adapters)
  application/       ← use cases; imports domain + ports only
    usecases/
  adapters/
    persistence/     ← Prisma/TypeORM/Knex implementations of domain ports
    http/            ← Express/Fastify controllers
    messaging/       ← Kafka, SQS adapters
  infrastructure/    ← DI wiring, env config, database connection setup
  main.ts            ← composition root
```

---

## Violation Patterns

### `orm_client_in_domain`

```typescript
// src/domain/services/UserService.ts — VIOLATION
import { PrismaClient } from '@prisma/client'; // ← ORM in domain
import { DataSource } from 'typeorm';           // ← ORM in domain
```

**Correct pattern:**

```typescript
// src/domain/ports/UserRepository.ts — OK
export interface UserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}

// src/domain/services/UserService.ts — OK
import type { UserRepository } from '../ports/UserRepository';

export class UserService {
  constructor(private readonly userRepo: UserRepository) {}
  // ...
}
```

### `express_req_res_in_domain`

```typescript
// src/domain/services/OrderService.ts — VIOLATION
import { Request, Response } from 'express'; // ← HTTP framework in domain
```

HTTP types belong exclusively in `adapters/http/`. Domain services receive
plain objects, not framework-specific request/response types.

### `app_imports_concrete_adapter`

```typescript
// src/application/usecases/CreateUser.ts — VIOLATION
import { PrismaUserRepository } from '../../adapters/persistence/PrismaUserRepository';
```

**Correct pattern:**

```typescript
// src/application/usecases/CreateUser.ts — OK
import type { UserRepository } from '../../domain/ports/UserRepository'; // interface only
```

---

## ESLint Enforcement

```json
// .eslintrc.json
{
  "plugins": ["import"],
  "rules": {
    "import/no-restricted-paths": [
      "error",
      {
        "zones": [
          {
            "target": "./src/domain",
            "from": "./src/adapters",
            "message": "Domain must not import adapters."
          },
          {
            "target": "./src/domain",
            "from": "./src/infrastructure",
            "message": "Domain must not import infrastructure."
          },
          {
            "target": "./src/application",
            "from": "./src/adapters",
            "message": "Application must not import concrete adapters."
          }
        ]
      }
    ]
  }
}
```

**Install:**

```bash
npm install --save-dev eslint eslint-plugin-import
```

---

## TypeScript `tsconfig.json` (strict mode)

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "paths": {
      "@domain/*": ["./src/domain/*"],
      "@application/*": ["./src/application/*"],
      "@adapters/*": ["./src/adapters/*"]
    }
  }
}
```

Using path aliases (`@domain/*`, `@application/*`) makes violations visually obvious
and easier to lint — any `@adapters/*` import inside `src/domain/` is immediately suspicious.

---

## Exception Example (M016 compliant)

```typescript
// src/domain/legacy/LegacyNotifier.ts
// eslint-disable-next-line import/no-restricted-paths
import { MailgunClient } from '../../adapters/messaging/MailgunClient';
// diagnosis: LegacyNotifier predates ports layer; extraction requires queue refactor
// evidence: https://github.com/org/repo/issues/731
// follow_up: issue #731 — extract to ports/NotificationPort before v2.0
```

---

## CI Setup

```yaml
# .github/workflows/ci.yml
- name: Type check
  run: npx tsc --noEmit

- name: Lint (includes import boundary rules)
  run: npx eslint . --ext .ts --max-warnings 0

- name: Tests
  run: npm test
```

`--max-warnings 0` ensures ESLint violations block the build even when flagged as warnings.
