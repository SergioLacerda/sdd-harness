# Java Engineering Guidelines

**DSL guidelines active when wizard language = Java:** G03, G07, G11, G15, G19
**Universal principles:** see [core-engineering-principles.md](../core-engineering-principles.md) (M018)

---

## 1. Code Style (G07 — SOFT)

**Tools required:**

```bash
mvn verify         # includes Checkstyle, PMD, tests
./gradlew check    # Gradle equivalent
```

**Rules:**

- Business logic must not live in controllers — delegate to application services.

- Domain classes must not depend on Spring annotations or JPA in the domain layer.

- Exceptions must be caught specifically; cause must be preserved.

- Prefer composition over deep inheritance hierarchies.

- No magic strings — use enums or constants for domain states.

**Maven dependencies:**

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-checkstyle-plugin</artifactId>
</plugin>
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-pmd-plugin</artifactId>
</plugin>
```

---

## 2. Architecture & Dependency Direction (G03 — HARD)

See [java-dependency-direction.md](../../guides/architecture/examples/java-dependency-direction.md) for full reference including ArchUnit test code.

**Summary:** `domain`and`application`packages must not import`adapters`or`infrastructure`. Use ArchUnit JUnit tests to enforce in CI.

---

## 3. Anti-Patterns (G11 — HARD)

### Business Logic in Controller

```java
// VIOLATION
@PostMapping("/orders")
public ResponseEntity<Order> createOrder(@RequestBody OrderRequest req) {
    // business rules directly in controller
    if (req.getTotal() > 10000) {
        throw new RuntimeException("Order too large");
    }
    Order order = orderRepository.save(new Order(req));
    return ResponseEntity.ok(order);
}

// OK
@PostMapping("/orders")
public ResponseEntity<OrderResponse> createOrder(@RequestBody OrderRequest req) {
    OrderResponse result = createOrderUseCase.execute(req.toCommand());
    return ResponseEntity.ok(result);
}
```

### Framework-Coupled Domain

```java
// VIOLATION
// com/example/domain/model/Order.java
@Entity
@Table(name = "orders")
public class Order {
    @Id
    @GeneratedValue
    private Long id;
    // JPA in domain model
}

// OK — plain Java in domain, JPA entity in adapters/persistence
public class Order {
    private final OrderId id;
    private final Money total;
    // no framework annotations
}
```

### Exception Swallowing

```java
// VIOLATION
try {
    service.process();
} catch (Exception e) {
    // silent
}

// OK
try {
    service.process();
} catch (SpecificException e) {
    throw new ApplicationException("failed to process: " + e.getMessage(), e);
}
```

### Over-Engineered Inheritance

```java
// VIOLATION
abstract class AbstractBaseServiceHelper<T, R, V extends Validator<T>> {
    // deep hierarchy for one concrete implementation
}

// OK
public class CreateUserService {
    private final UserRepository userRepository;
    private final PasswordEncoder encoder;

    public User execute(CreateUserCommand cmd) { ... }
}
```

---

## 4. Performance (G15 — SOFT)

**Measure first:**

```bash

# Add JMH benchmark module to project

# Or use async-profiler / JProfiler for production profiling
mvn test -Pbenchmark
```

**Key rules:**

- Use `StringBuilder`for string concatenation inside loops — never`+` in a loop.

- Avoid N+1 queries — use `@EntityGraph` or explicit JOIN FETCH for associations.

- Use connection pooling (HikariCP — already default in Spring Boot).

- Avoid `String.format`in hot paths — prefer concatenation or`MessageFormat`.

- Use `lazy` loading for large associations; fetch eagerly only at use boundaries.

```java
// VIOLATION — string concat in loop
String result = "";
for (String item : items) {
    result += item + "\n";
}

// OK
StringBuilder sb = new StringBuilder();
for (String item : items) {
    sb.append(item).append('\n');
}
String result = sb.toString();
```

---

## 5. Project Structure (G19 — SOFT)

```
src/
  main/
    java/
      com/example/app/
        domain/              # business rules; no framework or JPA imports
          model/             # plain Java objects
          service/           # domain services
          ports/             # interfaces (output contracts)
        application/         # use cases; imports domain + ports only
          usecases/
        adapters/            # implements domain ports
          persistence/       # JPA repositories, mappers
          web/               # Spring controllers
          messaging/         # Kafka, RabbitMQ
        infrastructure/      # Spring Boot config, DataSource, beans
    resources/
      application.yml
  test/
    java/
      com/example/app/
        ArchitectureTest.java   # ArchUnit layer tests
```

**Rules:**

- Domain package must not import application, adapters, or infrastructure.

- JPA `@Entity`annotations belong exclusively in`adapters/persistence/` mappers.

- `ArchitectureTest.java` is mandatory — see [java-dependency-direction.md](../../guides/architecture/examples/java-dependency-direction.md) for code.

---

## 6. CI Checklist

```bash
mvn verify          # compiles + Checkstyle + PMD + tests + ArchUnit

# or
./gradlew check     # Gradle equivalent
```

ArchUnit failures surface as standard JUnit test failures — no extra CI step needed.
