# 🔍 Observability Contract

**Status:** ✅ Complete
**Version:** 1.0
**Last Updated:** 2026-04-19
**Applicable To:** All [PROJECT_NAME] projects (100% inherited from CANONICAL/)

---

## 🎯 Overview

Complete observability specification defining what MUST be observable in production to maintain system visibility, operability, and reliability.

Observability is NOT optional — Every project must implement **all four pillars**:

1. **Logging** — What happened?
2. **Tracing** — How did it happen? (request flow)
3. **Metrics** — Is it healthy? (golden signals)
4. **On-Call** — How do we respond?

**Framework compliance:**

- Implements ADR-002: Async-First (all observability must be non-blocking)
- Uses ports for observability (see ADR-003)
- Respects Performance SLOs (see performance.md)

---

## 📋 Part 1: Logging Strategy

### 1.1 Log Levels

**Standard Log Levels (in order of severity):**

| Level | When to Use | Example |
|-------|------------|---------|
| **DEBUG** | Development only, very detailed | "Entering function X with args {a, b, c}" |
| **INFO** | Important state changes | "Campaign created: id=123", "User logged in" |
| **WARNING** | Potential problems | "Rate limit approaching", "Retry #2 of 3" |
| **ERROR** | Failures that don't stop system | "Failed to call OpenAI API", "Invalid input" |
| **CRITICAL** | System-wide failures | "Database connection lost", "Out of memory" |

**Production Log Levels:**

- Production: INFO, WARNING, ERROR, CRITICAL (DEBUG disabled)
- Staging: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Local: DEBUG (all)

---

### 1.2 Logging at Each Layer

**Layer 1: Entities (Domain)**

- Minimal logging (domain models should be pure)
- Never log PII directly
- Log changes: "Entity X created" (log hash of ID, not ID)

**Layer 2: Domain (Business Logic)**

- Business decisions: "Narrative rejected: quality score too low"
- Validation failures: "Invalid campaign name"
- Calculations: "Narrative context limited to 5000 tokens"

**Layer 3: Ports (Abstractions)**

- Port calls: "VectorReaderPort.search() called"
- Port errors: "VectorReaderPort error: connection timeout"

**Layer 4: Use Cases (Orchestration)**

- Request start/end: "ExecuteActionUseCase started"
- Critical decisions: "LLM generation started with context size X"
- Failures: "UseCase failed at step X: {error}"

**Layer 5: Error Mapping**

- Map errors to HTTP status: "Domain error → HTTP 400"
- Log mapped error details

**Layer 6: Adapters (Implementation)**

- External service calls: "Calling OpenAI API"
- Service responses: "OpenAI returned 200 OK"
- Service errors: "OpenAI returned 429 rate limit"
- Retry logic: "Retry #1: exponential backoff 2s"

**Layer 7: DTOs**

- Minimal logging (data transformation)
- Log only if serialization fails

**Layer 8: Controllers/Interfaces**

- HTTP request received: "POST /campaigns (200ms)"
- Response status: "Response: 200 OK"
- HTTP errors: "Request validation failed"

---

### 1.3 Log Format Specification

**Standard Log Format:**

```
[timestamp] [level] [logger_name] [request_id] [user_hash] [component] message [key=value pairs]
```

**Example Log Entry:**

```
2026-04-19T10:45:32.123Z INFO rpg_narrative_server.usecases.execute_action [req-abc123] [user_hash=7f3a] narrative NarrativeGenerationUseCase started LLM_model=gpt-4 context_size=2048 campaign_id=campaign_hash
```

**JSON Log Format (for structured logging):**

```json
{
  "timestamp": "2026-04-19T10:45:32.123Z",
  "level": "INFO",
  "logger": "rpg_narrative_server.usecases.execute_action",
  "request_id": "req-abc123",
  "user_hash": "7f3a",
  "component": "narrative",
  "message": "NarrativeGenerationUseCase started",
  "context": {
    "llm_model": "gpt-4",
    "context_size": 2048,
    "campaign_id": "campaign_hash"
  }
}
```

**Log Field Meanings:**

| Field | Meaning | Rules |
|-------|---------|-------|
| timestamp | When did this occur? | ISO 8601 format, UTC |
| level | Severity | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| logger | Which component logged this? | Use `__name__` in Python |
| request_id | Which HTTP request is this from? | Generate on request entry |
| user_hash | Which user (anonymized)? | Hash user_id, never log raw |
| component | What logical subsystem? | "narrative", "vector", "memory", etc. |
| message | Human readable message | Short, specific |
| context | Additional structured data | Key-value pairs |

---

### 1.4 What To Log (and What NOT To Log)

**✅ DO Log:**

- Function entry/exit (for critical paths only)
- External service calls (LLM, Vector DB)
- Validation failures (with error reason, not input)
- Performance milestones ("Processing took 245ms")
- State changes ("Campaign created", "User joined")
- Errors with full stack trace
- Request ID on every log (for correlation)

**❌ DON'T Log:**

- Sensitive data (passwords, API keys, tokens)
- Personally identifiable information (names, emails, IPs)
- Raw user input (unless validation failure)
- Full error responses (summarize instead)
- DEBUG logs in production
- Binary data or huge objects
- System passwords or configuration secrets

**❌ NEVER Log:**

- Database credentials
- OAuth tokens or API keys
- Session IDs or tokens
- User passwords
- Credit card numbers
- Medical information
- Private keys

**Pattern: Safe Logging:**

```python
# ❌ WRONG - Logs sensitive data
logger.info(f"User {user.email} logged in with password {password}")

# ✅ RIGHT - Anonymized and safe
import hashlib

user_hash = hashlib.sha256(user.id.encode()).hexdigest()[:8]
logger.info(
    f"User authentication successful",
    extra={"user_hash": user_hash, "auth_method": "jwt"},
)

# ❌ WRONG - Logs full request
logger.error(f"Request failed: {request.json()}")

# ✅ RIGHT - Summarizes without sensitive data
logger.error(
    f"Request validation failed",
    extra={
        "request_type": "create_campaign",
        "error": "name too long",
        "provided_length": len(request.name),
    },
)
```

---

### 1.5 Log Retention & Cleanup

**Retention Policy:**

| Log Type | Retention | Storage |
|----------|-----------|---------|
| Application logs | 30 days | Active logs |
| Access logs | 60 days | Active logs |
| Audit/Security logs | 90 days | Secure storage |
| Error logs | 30 days | Error tracking service |
| Debug logs | 7 days | Development only |

**Cleanup Process:**

```python
async def cleanup_old_logs():
    """Run daily at 03:00 UTC"""
    # Remove logs older than 30 days
    log_manager.delete_before(days=30)

    # Archive audit logs (keep 90 days)
    log_manager.archive_old(type="audit", older_than_days=30, keep_until_days=90)

    logger.info("Log cleanup complete")
```

---

## 📋 Part 2: Tracing Strategy (Distributed)

### 2.1 OpenTelemetry Setup

**Tracing Framework:** OpenTelemetry (OTLP format)

**Why OpenTelemetry?**

- Vendor-neutral standard
- Python library: `opentelemetry-api`
- Exporters: Jaeger, Zipkin, DataDog, etc.
- W3C Trace Context standard

**Installation:**

```bash
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-jaeger
pip install opentelemetry-instrumentation-fastapi
```

---

### 2.2 Trace Context Propagation

**Request Flow with Tracing:**

```
┌─ HTTP Request (incoming)
│  │
│  ├─ Extract trace context from headers
│  │  (trace_id, span_id, trace_flags)
│  │
│  └─ Create root span "http_request"
│     │
│     ├─ Call UseCase (create child span)
│     │  │
│     │  ├─ Call Port (create child span)
│     │  │  │
│     │  │  └─ Call Adapter (create child span)
│     │  │     │
│     │  │     └─ External service call
│     │  │
│     │  └─ Return from Adapter
│     │
│     └─ Return to Controller
│
└─ Send response + trace ID to client
```

**Trace Context Headers:**

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate: vendor-data
```

**Implementation:**

```python
from opentelemetry.trace import get_tracer

tracer = get_tracer(__name__)


async def execute_action(action_request: ActionRequest):
    with tracer.start_as_current_span("execute_action") as span:
        # Add attributes to span
        span.set_attribute("campaign_id", action_request.campaign_id)
        span.set_attribute("action_type", action_request.type)
        span.set_attribute("user_hash", user_hash)

        # Call UseCase (trace context propagates automatically)
        result = await usecase.execute(action_request)

        span.set_attribute("status", "success")
        return result
```

---

### 2.3 Span Naming Conventions

**Span Name Format:**

```
[service_name].[layer].[operation]
```

**Examples:**

| Component | Span Name | Duration | Attributes |
|-----------|-----------|----------|-----------|
| HTTP Controller | `rpg.http.post_campaigns` | 245ms | method, path, status |
| UseCase | `rpg.usecase.execute_action` | 200ms | action_type, campaign_id |
| Port Call | `rpg.port.vector_search` | 85ms | query_size, result_count |
| External API | `rpg.adapter.openai_completion` | 1230ms | model, tokens, api_version |
| Database Query | `rpg.adapter.query_campaigns` | 15ms | query_type, result_count |

**Span Attributes to Always Include:**

```python
span.set_attribute("service.name", "rpg-narrative-server")
span.set_attribute("service.version", "1.0.0")
span.set_attribute("deployment.environment", "production")

# User context (anonymized)
span.set_attribute("user_hash", user_hash)
span.set_attribute("request_id", request_id)

# Business context
span.set_attribute("campaign_id", campaign_id)
span.set_attribute("action_type", action_type)

# Performance context
span.set_attribute("duration_ms", duration)
span.set_attribute("status", status)  # "success", "error", "timeout"
```

---

### 2.4 Sampling Strategy

**Sampling:** Don't trace 100% (too much data), sample intelligently

**Sampling Rules:**

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace import ProbabilitySampler

# Probability-based sampling
sampler = ProbabilitySampler(rate=0.1)  # 10% of requests

# Environment-based sampling
if ENVIRONMENT == "production":
    sample_rate = 0.05  # 5% of requests in production
elif ENVIRONMENT == "staging":
    sample_rate = 0.5  # 50% in staging
else:
    sample_rate = 1.0  # 100% in development

sampler = ProbabilitySampler(rate=sample_rate)
```

**Adaptive Sampling:**

```python
# Always sample errors (even if low probability)
if error_detected:
    span.set_attribute("always_sample", True)

# Always sample slow requests (> 1 second)
if duration_ms > 1000:
    span.set_attribute("always_sample", True)
```

---

## 📋 Part 3: Metrics Strategy (Golden Signals)

### 3.1 Golden Signals

**The Four Golden Signals (by Google SRE):**

1. **Latency** — How long does it take?
2. **Traffic** — How many requests?
3. **Errors** — How many failures?
4. **Saturation** — How full is the system?

**Per-Endpoint Metrics:**

| Endpoint | Latency | Traffic | Errors | Saturation |
|----------|---------|---------|--------|-----------|
| POST /campaigns | P50, P99 | RPS | Error % | Queue depth |
| POST /actions | P50, P99 | RPS | Error % | Task count |
| GET /campaigns/{id} | P50, P99 | RPS | Error % | N/A |
| POST /ai/generate | P50, P99 | RPS | Error % | LLM queue |

### 3.2 Metrics Collection

**Using OpenTelemetry Metrics:**

```python
from opentelemetry import metrics

# Create meter
meter = metrics.get_meter(__name__)

# Latency histogram
latency_histogram = meter.create_histogram(
    name="http_request_duration_ms", description="HTTP request latency", unit="ms"
)

# Traffic counter
traffic_counter = meter.create_counter(
    name="http_requests_total", description="Total HTTP requests", unit="1"
)

# Error counter
error_counter = meter.create_counter(
    name="http_errors_total", description="Total HTTP errors", unit="1"
)

# Saturation gauge
queue_gauge = meter.create_observable_gauge(
    name="request_queue_depth",
    description="Number of queued requests",
    unit="1",
    callbacks=[lambda: get_queue_depth()],
)
```

**Recording Metrics:**

```python
import time


async def http_middleware(request, call_next):
    start = time.perf_counter()

    # Call handler
    response = await call_next(request)

    # Record metrics
    duration_ms = (time.perf_counter() - start) * 1000

    latency_histogram.record(
        duration_ms,
        attributes={
            "endpoint": request.url.path,
            "method": request.method,
            "status": response.status_code,
        },
    )

    traffic_counter.add(
        1, attributes={"endpoint": request.url.path, "status": response.status_code}
    )

    if response.status_code >= 400:
        error_counter.add(
            1, attributes={"endpoint": request.url.path, "status": response.status_code}
        )

    return response
```

---

### 3.3 Per-Layer Metrics

**Adapter Layer (Infrastructure):**

- External API latency (OpenAI, vector DB)
- Connection pool usage
- Retry rate

**Application Layer:**

- UseCase latency
- Validation failure rate

**Domain Layer:**

- Business logic latency
- Domain event count

**Interface Layer:**

- HTTP request latency
- Error rate by endpoint

---

### 3.4 Alerting Rules

**Critical Alerts (Page on-call):**

```yaml
- name: high_error_rate
  condition: error_rate > 5% for 1 minute
  severity: critical
  action: page on-call engineer

- name: high_latency_p99
  condition: p99_latency > 1000ms for 5 minutes
  severity: critical
  action: page on-call engineer

- name: system_down
  condition: availability < 99% for 1 minute
  severity: critical
  action: page on-call engineer
```

**Warning Alerts (Create ticket):**

```yaml
- name: elevated_latency
  condition: p99_latency > 500ms for 15 minutes
  severity: warning
  action: create jira ticket

- name: elevated_error_rate
  condition: error_rate > 1% for 5 minutes
  severity: warning
  action: create jira ticket

- name: high_memory_usage
  condition: memory > 80% for 10 minutes
  severity: warning
  action: create jira ticket
```

---

## 📋 Part 4: On-Call Model

### 4.1 Alert Routing

**On-Call Schedule:**

```
Mon-Fri: Primary on-call (9am-5pm)
Mon-Fri: Secondary on-call (5pm-9am)
Sat-Sun: Rotating on-call (24h)
```

**Alert Routes:**

| Severity | Route | Response Time | Escalation |
|----------|-------|---------------|-----------|
| CRITICAL | Page on-call | 5 minutes | Escalate after 15 min |
| WARNING | Slack channel | 30 minutes | Create ticket if not resolved |
| INFO | Logs only | N/A | Review in standup |

**Escalation Policy:**

```
Level 1: Primary on-call engineer
  ↓ (10 min no response)
Level 2: Secondary on-call engineer
  ↓ (10 min no response)
Level 3: Engineering manager
  ↓ (10 min no response)
Level 4: VP Engineering
```

---

### 4.2 Incident Response Runbooks

**Runbook Template:**

```markdown
# [Service] Down/Degraded

## Symptoms
- [What the alert says]
- [What users see]
- [What metrics show]

## Diagnosis
1. Check status page
2. Check logs for errors
3. Check metrics for anomalies
4. Check deployment history

## Resolution Steps
1. [Step 1]
2. [Step 2]
...

## Rollback
1. [How to rollback if needed]

## Post-Incident
- Update runbook
- Create tickets for improvements
- Blameless post-mortem
```

**Example Runbooks:**

- [Vector Search Down](./runbooks/vector-search-down.md)
- [LLM API Rate Limited](./runbooks/llm-rate-limited.md)
- [Memory Leak Detected](./runbooks/memory-leak.md)
- [Database Slow Queries](./runbooks/db-slow-queries.md)

---

### 4.3 Blameless Post-Mortems

**Process (within 24 hours):**

1. **Timeline** — When did it start? When was it fixed?
2. **Root Cause** — Technical + human + process failures
3. **Impact** — Users affected, data loss, downtime
4. **Immediate Fixes** — What we did to stop it
5. **Preventive Fixes** — What we'll do to prevent it
6. **Action Items** — Who, what, when

**Example Template:**

```markdown
# Incident: LLM API Timeouts (2026-04-19 10:45-11:30)

## Impact
- 450 users affected
- 45 minutes of degraded service
- 0 data loss

## Timeline
10:45 - Alerts firing (response time > 1s)
10:47 - On-call page received
10:50 - Root cause identified (OpenAI API degraded)
11:00 - Temporary mitigation (fallback to cached responses)
11:30 - OpenAI recovered
11:45 - All systems normal

## Root Cause
OpenAI API experiencing high latency (~5s). Our system had 30s timeout, causing cascading failures.

## Why Did This Happen?
- We weren't monitoring OpenAI status (human error)
- We didn't have fallback for degraded external APIs (design issue)
- No circuit breaker on external calls (process gap)

## Fixes
### Immediate
- [x] Revert to cached responses when API slow

### Short-term (This sprint)
- [ ] Add circuit breaker to OpenAI adapter
- [ ] Monitor OpenAI status page
- [ ] Add alerting for OpenAI latency > 2s

### Long-term
- [ ] Implement local LLM fallback
- [ ] Test failover procedures quarterly

## Action Items
- Alice: Implement circuit breaker (due Friday)
- Bob: Add OpenAI monitoring (due Wednesday)
- Carol: Plan local LLM evaluation (due next sprint)
```

---

### 4.4 On-Call Best Practices

**Before Being On-Call:**

- [ ] Read all runbooks
- [ ] Practice incident response (simulation)
- [ ] Know escalation procedures
- [ ] Have personal escalation plan (who covers if you're unavailable)

**During On-Call:**

- [ ] Respond to alerts within response time
- [ ] Keep incident channel updated
- [ ] Don't make changes without testing
- [ ] Communicate with users (status page)

**After Incident:**

- [ ] Blameless post-mortem within 24h
- [ ] Action items assigned
- [ ] Update runbooks
- [ ] Share learnings

**Off-Call:**

- [ ] Review post-mortems from incidents you missed
- [ ] Improve runbooks
- [ ] Fix preventive items
- [ ] Give feedback to engineering

---

## 🔗 Related Documents

- [ADR-002: Async-First](../../decisions/ADR-002-async-first-no-blocking.md) — All observability must be async
- [ADR-001: Clean Architecture](../../decisions/ADR-001-clean-architecture-8-layer.md) — Observation points
- [Performance Model](./performance.md) — SLOs for observability operations
- [Security Model](./security-model.md) — Privacy-preserving logging

---

## 📚 Implementation Roadmap

**Phase 1 (Week 1):**

- [ ] Setup structured JSON logging
- [ ] Add request ID propagation
- [ ] Configure log retention
- [ ] Verify no secrets in logs

**Phase 2 (Week 2):**

- [ ] Install OpenTelemetry
- [ ] Add tracing to main endpoints
- [ ] Setup trace exporter (Jaeger/Zipkin)
- [ ] Test trace context propagation

**Phase 3 (Week 3):**

- [ ] Add metrics collection
- [ ] Setup prometheus scraping
- [ ] Create Grafana dashboards
- [ ] Configure alerting rules

**Phase 4 (Week 4):**

- [ ] Document runbooks
- [ ] Conduct on-call training
- [ ] Run incident simulation
- [ ] Fine-tune alert thresholds

---

## ✅ Validation

**Logging Validation:**

```bash
# Check no secrets in logs
tail -f /var/log/app.log | grep -i "password\|api_key\|secret"

# Verify JSON format
cat /var/log/app.log | jq .
```

**Tracing Validation:**

```bash
# View traces in Jaeger
# Open: http://localhost:16686

# Query for spans
# Find trace by request_id
```

**Metrics Validation:**

```bash
# Scrape metrics endpoint
curl http://localhost:9090/metrics

# Check Prometheus
# Open: http://localhost:9090
```

**On-Call Validation:**

```bash
# Trigger test alert
# Verify on-call receives page
# Measure response time
```

---

**Status:** ✅ Production-Ready
**Framework:** SPEC v1.0
**Owner:** DevOps/SRE Lead
**Review Cycle:** Quarterly (3 months)
**Next Review:** 2026-07-19
