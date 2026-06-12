# ✅ Compliance & Quality Gates

**Status:** ✅ Complete
**Version:** 1.0
**Last Updated:** 2026-04-19
**Applicable To:** All [PROJECT_NAME] projects (100% inherited from CANONICAL/)

---

## 🎯 Overview

Compliance specification defining quality gates, done criteria, and mandatory compliance checks for all projects in the SPEC framework.

**Quality is MANDATORY** — Every project must implement all gates before code ships.

---

## 📋 Part 1: Code Quality Gates

### 1.1 Coverage Requirements

**Mandatory coverage targets:**

| Layer | Target | SLO |
|-------|--------|-----|
| **Domain (Entities)** | ≥ 95% | Minimum 90% (production code) |
| **Application (UseCases)** | ≥ 85% | Minimum 80% (orchestration) |
| **Infrastructure (Adapters)** | ≥ 80% | Minimum 70% (external integration) |
| **Interfaces (Controllers/Handlers)** | ≥ 80% | Minimum 70% (input/output) |
| **Overall** | ≥ 85% | Minimum 80% (total codebase) |

**Branch coverage:**

- Domain logic: ≥ 85% (decision paths tested)
- Application logic: ≥ 75% (happy path + errors)
- Infrastructure: ≥ 70% (normal + fault cases)

**Tools:** pytest with pytest-cov, sonarqube integration required.

### 1.2 Linting & Code Style

**Mandatory linting:**

- **pylint:** Score ≥ 9.0/10 (all modules)
- **mypy:** 100% type hint coverage (critical paths)
- **ruff:** Zero warnings in critical paths
- **black:** Enforced formatting (automated on commit)

**Configuration:** pyproject.toml must specify all linting rules (not optional).

### 1.3 Static Analysis

**Security scanning:**

- **bandit:** Zero HIGH severity issues
- **safety:** Zero known CVEs in dependencies
- **pip-audit:** Monthly audit, all issues tracked

**Maintainability:**

- **radon:** Complexity (CC) ≤ 10 per function
- **coverage:** No dead code pathways

---

## 📋 Part 2: Test Coverage Requirements

### 2.1 Test Types

**Mandatory test pyramid:**

```
        E2E (10%)
      /     \
    Integration (25%)
   /           \
 Unit (65%)
```

### 2.2 Unit Test Requirements

- ✅ All domain entities tested (≥ 95% coverage)
- ✅ All domain value objects tested (100% coverage)
- ✅ All use cases tested (≥ 85% coverage)
- ✅ All adapters tested (≥ 80% coverage)
- ✅ Error cases: Every error type must have test
- ✅ Edge cases: Boundary conditions must have tests

**Framework:** pytest (required)

### 2.3 Integration Test Requirements

- ✅ Port boundaries tested (adapters ↔ domain)
- ✅ Async workflows tested (with real async)
- ✅ Error handling across layers tested
- ✅ Concurrent scenarios tested (thread isolation)
- ✅ Performance under load tested (SLOs verified)

### 2.4 E2E Test Requirements

- ✅ Happy path fully tested
- ✅ Error scenarios tested
- ✅ Data persistence verified
- ✅ Async operations verified end-to-end

---

## 📋 Part 3: Documentation Gates

### 3.1 API Documentation

**Mandatory:**

- OpenAPI/Swagger spec (auto-generated from code)
- All endpoints documented with examples
- All error codes documented
- Rate limits documented

### 3.2 Architecture Decision Records (ADRs)

**Mandatory for:**

- New architectural decisions (ADR template)
- Breaking changes (requires ADR)
- Major refactorings (ADR required)
- Performance optimizations (ADR required)

**ADRs are immutable once merged** (see ARCHIVE/deprecated-decisions/).

### 3.3 Implementation Guides

**Mandatory for each module:**

- Module purpose (one sentence)
- Key classes/functions (documented)
- Common usage patterns
- Testing strategy

### 3.4 Runbooks

**Mandatory for production:**

- Deployment runbook
- Incident response runbook
- Scaling runbook
- Emergency procedures

---

## 📋 Part 4: Performance Gates

### 4.1 SLO Compliance

**Mandatory performance checks:**

- All API endpoints: ≤ p99 latency (see performance.md)
- Async operations: ≤ timeout budgets (ADR-002)
- Database queries: ≤ 100ms (p99)
- External API calls: ≤ configured timeouts

**Measurement:** Every commit must pass performance tests (not optional).

### 4.2 Load Testing

**Mandatory before production:**

- Sustained 50-100 concurrent users
- P99 latency maintained under load
- Error rate < 0.1% under load
- Memory/CPU stable (no leaks)

---

## 📋 Part 5: Compliance Validation

### 5.1 Automated Checks (CI/CD)

**Pre-commit (developer machine):**

- Black formatting
- Linting warnings (non-blocking)

**CI/CD Pipeline (GitHub Actions):**

- ✅ Test execution (pytest)
- ✅ Coverage verification (≥ min SLOs)
- ✅ Linting (mypy, pylint, bandit)
- ✅ Auto-fix hygiene (`ruff check --fix` + formatter + post-fix re-run)
- ✅ Security scanning (safety, pip-audit)
- ✅ SPEC compliance (see spec-enforcement.yml)

### 5.2 Manual Reviews

**Code Review checklist:**

- [ ] Does code follow clean architecture?
- [ ] Are all error cases handled?
- [ ] Is async/await used correctly?
- [ ] Are ports used (not infrastructure directly)?
- [ ] Is testing adequate?
- [ ] Does it follow conventions.md?

**Release Review:**

- [ ] All compliance gates pass
- [ ] Documentation complete
- [ ] Runbooks reviewed
- [ ] Performance budget respected

---

## 📋 Part 6: Definition of Done (DoD)

**Code CANNOT merge without:**

1. ✅ All tests pass (>= SLO coverage)
2. ✅ Linting clean (pylint ≥ 9.0)
3. ✅ Type checking clean (mypy 100% on new code)
4. ✅ Auto-fix executed when available and revalidation passes
5. ✅ No security issues (bandit, safety clear)
6. ✅ Documentation complete
7. ✅ ADR created (if architectural)
8. ✅ Code review approved
9. ✅ SPEC compliance verified

**Performance gates:**

- ✅ SLO budgets respected
- ✅ Load testing passed
- ✅ No regressions detected

---

## 🏁 Enforcement

**Responsibility:** CI/CD pipeline (automated, non-bypassable)
**Reference:** `.github/workflows/spec-enforcement.yml`
**Escalation:** Only maintainers can merge if gates fail (documented justification required)

- [ ] P99 latency must be < [X]ms
- [ ] Error rate must be < [X]%
- [ ] Throughput must be > [X] req/s
- [ ] Memory footprint must be < [X]MB

### 5. Security Gates

- [ ] No hardcoded secrets
- [ ] OWASP validation passed
- [ ] Dependency vulnerabilities < [X]
- [ ] Security audit completed

### 6. Compliance Gates (Project-Specific)

- [ ] GDPR compliance (if EU customers)
- [ ] HIPAA compliance (if health data)
- [ ] SOC 2 audit (if enterprise)
- [ ] Regulatory requirements met

## 🔗 Related Documents

- [Definition of Done](./definition_of_done.md) — Merge checklist
- [Testing Strategy](./testing.md) — Test patterns
- [Architecture Blueprint](./architecture.md) — Layer contracts

## 📅 Implementation Timeline

- **Phase 1** (2h): Define all gates
- **Phase 2** (2h): Implement pytest fixtures
- **Phase 3** (1h): CI/CD integration

**Applies to:** All projects (automatic inheritance)
**Owner:** QA Lead
**Target:** 2026-06-15

---

**Version:** 1.0
**Updated:** 2026-04-19
