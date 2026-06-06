# Example: Dependency Direction — Java (adapts M001)

**Guideline ID:** G03 (sequential; see `guidelines.dsl`)
**Canonical mandate:** M001 — Clean Architecture
**Language:** Java

---

## DSL Entry

```
guideline G03 {
  type: HARD
  title: "Dependency Direction — Java"
  description: "Domain and application classes must not depend on infrastructure adapters, frameworks, or persistence providers directly. Use ArchUnit to enforce layer boundaries in CI."
  category: architecture
  mandate_ref: M001
  tags: ["java", "archunit", "checkstyle"]
  enforcement: {
    gate: ci
    severity: block
    tools: ["mvn verify", "./gradlew check", "archunit tests"]
  }
  violations: ["domain_imports_infrastructure", "app_imports_concrete_adapter", "framework_leaks_into_domain", "jpa_entity_in_domain_service"]
  exception_policy: {
    requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
    ttl: sprint
  }
  maturity_level: 3
  examples: ["import org.springframework.data.jpa.repository in domain/ -> VIOLATION", "interface UserRepository in domain/ports/ -> OK"]
}
```

---

## Package Structure

```
com.example.app/
  domain/          ← business rules; zero framework or JPA imports
    model/         ← entities (plain Java objects, no @Entity)
    service/       ← domain services
    ports/         ← interfaces (output ports)
  application/     ← use cases; imports domain + ports only
    usecases/
  adapters/        ← implements domain ports
    persistence/   ← JPA repositories, mappers
    web/           ← Spring controllers
    messaging/     ← Kafka, RabbitMQ
  infrastructure/  ← Spring Boot config, DataSource, beans
```

---

## Violation Patterns

### `domain_imports_infrastructure`

```java
// com/example/app/domain/service/UserService.java — VIOLATION
import org.springframework.stereotype.Service;          // ← framework in domain
import com.example.app.adapters.persistence.UserJpaRepo; // ← concrete adapter
```

**Correct pattern:**

```java
// com/example/app/domain/service/UserService.java — OK
import com.example.app.domain.ports.UserRepository; // interface only
import com.example.app.domain.model.User;

public class UserService {
    private final UserRepository userRepository; // injected, not resolved
    // ...
}
```

### `jpa_entity_in_domain_service`

```java
// com/example/app/domain/service/OrderService.java — VIOLATION
import javax.persistence.EntityManager; // ← JPA in domain
```

Domain objects must be plain Java — no `@Entity`, no `EntityManager`, no `@Column`.
JPA annotations belong in `adapters/persistence/` mappers only.

### `framework_leaks_into_domain`

```java
// com/example/app/domain/service/PaymentService.java — VIOLATION
import org.springframework.beans.factory.annotation.Autowired; // ← Spring in domain
import org.springframework.transaction.annotation.Transactional;
```

---

## ArchUnit Enforcement

ArchUnit tests run as part of the normal test suite in CI (`mvn verify`):

```java
// src/test/java/com/example/app/ArchitectureTest.java
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

@AnalyzeClasses(packages = "com.example.app")
class ArchitectureTest {

    @ArchTest
    static final ArchRule layer_dependencies_are_respected =
        layeredArchitecture().consideringAllDependencies()
            .layer("Domain").definedBy("..domain..")
            .layer("Application").definedBy("..application..")
            .layer("Adapters").definedBy("..adapters..")
            .layer("Infrastructure").definedBy("..infrastructure..")
            .whereLayer("Domain").mayNotAccessAnyLayer()
            .whereLayer("Application").mayOnlyAccessLayers("Domain")
            .whereLayer("Adapters").mayOnlyAccessLayers("Application", "Domain")
            .whereLayer("Infrastructure").mayOnlyAccessLayers("Adapters", "Application", "Domain");
}
```

**Maven dependency:**

```xml
<dependency>
    <groupId>com.tngtech.archunit</groupId>
    <artifactId>archunit-junit5</artifactId>
    <version>1.3.0</version>
    <scope>test</scope>
</dependency>
```

**Gradle dependency:**

```groovy
testImplementation 'com.tngtech.archunit:archunit-junit5:1.3.0'
```

---

## Exception Example (M016 compliant)

```java
// com/example/app/domain/legacy/LegacyOrderAdapter.java
@SuppressWarnings("ArchitectureViolation")
// diagnosis: LegacyOrderAdapter predates ports layer — full extraction blocked by Q3 freeze
// evidence: https://github.com/org/repo/issues/5102
// follow_up: issue #5102 — remove before v3.0
import com.example.app.adapters.persistence.LegacyOrderRepo;
```

---

## CI Setup

```yaml
# .github/workflows/ci.yml
- name: Build and test (includes ArchUnit)
  run: mvn verify
```

ArchUnit failures surface as standard JUnit test failures — no additional CI step needed.
