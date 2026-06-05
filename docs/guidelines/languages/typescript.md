# TypeScript Engineering Guidelines

**DSL guidelines active when wizard language = TypeScript/JS:** G04, G08, G12, G16, G20
**Universal principles:** see [core-engineering-principles.md](../core-engineering-principles.md) (M018)

---

## 1. Code Style (G08 — SOFT)

**Tools required:**

```bash
npx tsc --noEmit
npx eslint . --ext .ts --max-warnings 0
npm test
```

**Rules:**

- Enable `strict: true`in`tsconfig.json` — no exceptions.

- No `any`to silence compiler errors — use`unknown` at boundaries and narrow explicitly.

- All `Promise`s must be awaited or explicitly handled with `.catch`.

- Business logic must not live in route handlers.

- External JSON must be validated with a schema library before use as domain types.

**`tsconfig.json` minimum:**

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

**Install:**

```bash
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-import
```

---

## 2. Architecture & Dependency Direction (G04 — HARD)

See [nodejs-typescript-dependency-direction.md](../architecture/examples/nodejs-typescript-dependency-direction.md) for full ESLint config.

**Summary:** `domain/`and`application/`must not import`adapters/`or`infrastructure/`. Use ESLint `import/no-restricted-paths` to enforce in CI.

---

## 3. Anti-Patterns (G12 — HARD)

### `any` Escape Hatch

```typescript
// VIOLATION
function process(data: any): any {
    return data.value;
}

// OK
function process(data: unknown): string {
    if (!isProcessableData(data)) {
        throw new Error(`Invalid data shape: ${JSON.stringify(data)}`);
    }
    return data.value;
}
```

### Floating Promises

```typescript
// VIOLATION — rejection silently lost
sendNotification(user);

// OK — explicit lifecycle
await sendNotification(user);

// OK — intentional fire-and-forget
void sendNotification(user).catch(logger.error);
```

### Business Logic in Route Handler

```typescript
// VIOLATION
app.post('/orders', async (req, res) => {
    if (req.body.total > 10000) {  // business rule in handler
        return res.status(400).json({ error: 'Order too large' });
    }
    const order = await db.orders.create(req.body);  // direct DB access
    res.json(order);
});

// OK
app.post('/orders', async (req, res) => {
    const result = await createOrderUseCase.execute(req.body);
    res.json(result);
});
```

### Unsafe Type Assertion

```typescript
// VIOLATION — no runtime validation
const user = response.data as User;

// OK — validated at boundary
import { z } from 'zod';
const UserSchema = z.object({ id: z.string(), email: z.string().email() });
const user = UserSchema.parse(response.data);
```

---

## 4. Performance (G16 — SOFT)

**Measure first:**

```bash
node --prof app.js
node --prof-process isolate-*.log

# or: clinic.js, autocannon for HTTP benchmarking
```

**Key rules:**

- Never block the event loop with CPU-intensive synchronous work — use worker threads.

- Batch database queries — never N+1 in a loop.

- Avoid re-parsing JSON or re-creating `RegExp` objects in hot paths — hoist them.

- Use streaming (`Transform`, `pipeline`) for large data instead of loading into memory.

- Avoid `setInterval` for polling — prefer event-driven patterns or queue-based processing.

```typescript
// VIOLATION — N+1 queries
const orders = await db.orders.findMany();
for (const order of orders) {
    order.items = await db.items.findMany({ where: { orderId: order.id } });
}

// OK — single query
const orders = await db.orders.findMany({
    include: { items: true }
});
```

---

## 5. Project Structure (G20 — SOFT)

```
src/
  domain/              # business rules; zero framework or ORM imports
    models/            # plain TypeScript classes/interfaces
    services/          # domain services
    ports/             # output port interfaces
  application/         # use cases; imports domain + ports only
    usecases/
  adapters/            # implements domain ports
    persistence/       # Prisma/TypeORM/Knex implementations
    http/              # Express/Fastify controllers
    messaging/         # Kafka, SQS adapters
  infrastructure/      # DI wiring, env config, DB connection
  main.ts              # composition root
tests/                 # mirrors src/
tsconfig.json
```

**Rules:**

- Path aliases required: `@domain/*`, `@application/*`, `@adapters/*`in`tsconfig.json`.

- No barrel files (`index.ts`re-exporting everything) — they hide boundaries and slow`tsc`.

- Tests must mirror `src/` directory structure.

**tsconfig.json path aliases:**

```json
{
  "compilerOptions": {
    "paths": {
      "@domain/*": ["./src/domain/*"],
      "@application/*": ["./src/application/*"],
      "@adapters/*": ["./src/adapters/*"]
    }
  }
}
```

---

## 6. CI Checklist

```bash
npx tsc --noEmit                          # type checking
npx eslint . --ext .ts --max-warnings 0   # linting (includes import boundaries)
npm test                                   # tests
npm run build                             # full build
```

`--max-warnings 0` ensures ESLint violations block the build even when flagged as warnings.
