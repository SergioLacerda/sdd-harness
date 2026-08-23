# ⚡ Performance & SLOs

**Status:** ✅ Defined (Implementation in progress)

Specification of performance targets, SLOs, and budgets for all SPEC projects.

---

## 🎯 Overview

Performance targets are **immutable** and **project-agnostic**. All projects must achieve these SLOs.

**Golden Signals** monitored:

- 🟢 **Latency** (response time per layer)
- 🟢 **Traffic** (throughput & concurrency)
- 🟢 **Errors** (error rate & type)
- 🟢 **Saturation** (resource utilization)

---

## 1️⃣ Response Time Budgets (per layer)

**Mandatory:** All projects must respect these budgets

| Layer | SLO | P99 | Example |
|-------|-----|-----|---------|
| **Port/Adapter** | ≤ 5ms | ≤ 10ms | API gateway validation |
| **Interfaces** | ≤ 10ms | ≤ 20ms | HTTP routing, deserialization |
| **Application** | ≤ 50ms | ≤ 100ms | UseCase orchestration |
| **Domain** | ≤ 100ms | ≤ 200ms | Business logic |
| **Infrastructure** | ≤ 200ms | ≤ 500ms | DB query, external API |
| **Vector Index** | ≤ 150ms | ≤ 300ms | Semantic search |
| **Bootstrap** | ≤ 1s | ≤ 2s | Dependency injection |
| **Framework** | ≤ 20ms | ≤ 50ms | Event bus dispatch |

### Budget Allocation Formula

```
End-to-end latency = Sum(layer budgets) + overhead
Total SLO: ≤ 500ms (P99)

Breakdown:
- Adapters: 5ms
- Interfaces: 10ms
- Application: 50ms
- Domain: 100ms
- Infrastructure: 200ms
- Overhead (network, GC): 35ms
Total: 400ms (P99 = 500ms)
```

### Per-Endpoint Budgets

#### REST API Endpoints

| Endpoint | Operation | SLO | P99 |
|----------|-----------|-----|-----|
| `GET /campaigns/{id}` | Lookup | 50ms | 100ms |
| `POST /campaigns` | Create | 100ms | 200ms |
| `POST /narratives/generate` | AI generation | 5s | 10s |
| `GET /narratives/{id}` | Retrieve | 50ms | 100ms |
| `PUT /campaigns/{id}/state` | Update state | 100ms | 200ms |

#### Vector Search Endpoints

| Operation | SLO | P99 | Notes |
|-----------|-----|-----|-------|
| Semantic search | 150ms | 300ms | Top-K retrieval |
| Reranking | 50ms | 100ms | ML-based scoring |
| Hybrid search | 200ms | 400ms | Keyword + semantic |

---

## 2️⃣ Throughput Targets

**Mandatory minimums** for all projects:

### Request Throughput

| Endpoint | RPS Min | RPS Target | Concurrency |
|----------|---------|-----------|-------------|
| GET endpoints | 100 | 500 | 50 |
| POST endpoints | 50 | 200 | 20 |
| AI generation | 5 | 20 | 5 |
| Vector search | 50 | 200 | 20 |

**Definition:**

- **RPS** = Requests Per Second
- **Min** = Minimum acceptable (gate fails if below)
- **Target** = Expected performance level
- **Concurrency** = Simultaneous requests

### Event Bus Throughput

| Message Type | MPS Min | MPS Target |
|--------------|---------|-----------|
| Narrative events | 100 | 500 |
| State updates | 50 | 200 |
| AI feedback | 20 | 50 |

**Definition:**

- **MPS** = Messages Per Second
- Must handle bursts of 10x baseline

### Campaign Concurrency

| Metric | Min | Target | Max |
|--------|-----|--------|-----|
| Active campaigns | 10 | 100 | 1000 |
| Users per campaign | 1 | 10 | 100 |
| Concurrent executions | 1 | 5 | 50 |

---

## 3️⃣ Resource Limits

**Hard limits** (cannot exceed):

### Memory per Campaign

```
Total: 512MB per campaign (hard limit)

Breakdown:
- Narrative graph: 100MB
- Event log: 100MB
- Vector index cache: 200MB
- State/metadata: 50MB
- Overhead: 62MB
```

### Per-Request Memory

```
Total: 50MB per request (hard limit)

Breakdown:
- Request buffer: 10MB
- Processing stack: 20MB
- Response buffer: 10MB
- Overhead: 10MB
```

### CPU Allocation

```
Single request: ≤ 100ms CPU time (hard limit)
Rationale: P99 latency of 500ms / 5x safety margin

AI generation: ≤ 5s CPU time (hard limit)
Rationale: User timeout buffer
```

### Storage per Project

```
Total: 10GB per project (soft limit, scalable)

Breakdown:
- Event log: 5GB
- Vector indexes: 3GB
- Documents: 1GB
- Metadata: 1GB
```

### Network Bandwidth

```
Per-endpoint: ≤ 10Mbps average
Rationale: 1000 users × 10KB responses = 10MB/s

Burst capacity: ≤ 100Mbps (10s duration)
```

---

## 4️⃣ Success Metrics & Percentiles

### Latency Percentiles

**Mandatory measurement points:**

```
P50: < 100ms (median)
P95: < 300ms (95th percentile)
P99: < 500ms (99th percentile) ← CRITICAL
P99.9: < 1000ms (99.9th percentile)
Max: < 5000ms (absolute maximum)
```

**Definition:**

- **P50** = 50% of requests faster than this
- **P99** = 99% of requests faster than this
- **Max** = Worst-case observation

**Monitoring:**

- Sample: Every request
- Interval: Every 60 seconds
- Retention: 7 days

### Error Rate

**Thresholds:**

```
Acceptable: < 0.1% error rate (99.9% success)
Warning: 0.1% - 1% error rate
Critical: > 1% error rate
```

**Error types tracked:**

- 4xx (client errors)
- 5xx (server errors)
- Timeout errors (>5s)
- Network errors

### Availability SLO

**Target: 99.9% (3 nines)**

```
Calculation:
- Measurement period: 1 month
- Acceptable downtime: 43.2 minutes
- Any error >5% for >1min = downtime
```

### Recovery Time SLO

**After incident:**

```
RTO (Recovery Time Objective): ≤ 5 minutes
RPO (Recovery Point Objective): ≤ 1 minute of data
```

---

## 5️⃣ Performance Testing Requirements

### Benchmark Tests

**Mandatory** for each layer:

```python
# Example: UseCase benchmark
def test_usecase_latency_slo():
    """UseCase must complete within 50ms P50, 100ms P99"""
    results = []
    for _ in range(1000):
        start = time.perf_counter()
        usecase.execute()
        elapsed = time.perf_counter() - start
        results.append(elapsed * 1000)  # milliseconds

    p50 = np.percentile(results, 50)
    p99 = np.percentile(results, 99)

    assert p50 < 50, f"P50 latency {p50}ms exceeds 50ms budget"
    assert p99 < 100, f"P99 latency {p99}ms exceeds 100ms budget"
```

### Load Tests

**Required** for production readiness:

```bash
# Test endpoint throughput
wrk -t4 -c50 -d30s http://api/endpoint

# Expected: ≥ 100 RPS at p99 latency < 500ms
```

### Memory Profiling

**Required** for memory budgets:

```python
import tracemalloc

tracemalloc.start()
# ... execute operation ...
current, peak = tracemalloc.get_traced_memory()
assert peak < 50_000_000  # 50MB limit
```

---

## 6️⃣ Monitoring & Alerting

### Metrics to Export (OpenTelemetry)

```python
# Latency histogram
latency_histogram = metrics.create_histogram(
    "request_latency_ms", buckets=[5, 10, 50, 100, 200, 500, 1000, 5000]
)

# Throughput counter
request_counter = metrics.create_counter(
    "requests_total", attributes=["endpoint", "status"]
)

# Error counter
error_counter = metrics.create_counter(
    "errors_total", attributes=["error_type", "endpoint"]
)

# Resource utilization gauge
memory_gauge = metrics.create_gauge("memory_usage_bytes", attributes=["campaign_id"])
```

### Alert Rules

**Critical (Page on-call):**

- P99 latency > 1000ms for > 5min
- Error rate > 5% for > 1min
- Availability < 99%

**Warning (Create ticket):**

- P99 latency > 500ms for > 15min
- Error rate > 1% for > 5min
- Memory per campaign > 400MB

---

## 7️⃣ Degradation Policy

**When SLOs cannot be met:**

1. **Backpressure** — Reject new requests (fail fast)
2. **Queue** — Queue if queue < 1000 requests
3. **Timeout** — 5s max timeout
4. **Fallback** — Serve cached results if available
5. **Degrade** — Reduce feature scope (e.g., limit top-K)

**Example: Vector search degradation**

```
High load: 150ms → 100ms (reduce top-K from 100 to 50)
Higher:    100ms → 50ms (use fast index, skip reranking)
Critical:  50ms → timeout (fail fast)
```

---

## 🔗 Related Documents

- [ADR-001: Clean Architecture](spec/decisions/ADR-001-clean-architecture-8-layer.md) — Layer structure
- [ADR-002: Async-first](../../decisions/ADR-002-async-first-no-blocking.md) — No blocking I/O
- [ADR-003: Ports & Adapters](../../decisions/ADR-003-ports-adapters-pattern.md) — Performance boundaries

---

## 📅 Validation & Review

### Quarterly Review (3 months)

- Compare actual P99 vs budgets
- Identify bottlenecks
- Update budgets if needed
- Publish performance report

### Annual Review (1 year)

- Renegotiate SLOs with stakeholders
- Update infrastructure targets
- Archive old metrics
- Plan capacity for next year

---

## 📊 Implementation Checklist

- [x] Define response time budgets per layer
- [x] Define throughput targets
- [x] Define resource limits
- [x] Define success metrics
- [ ] Implement benchmark tests (next phase)
- [ ] Implement load tests (next phase)
- [ ] Configure alerting (next phase)
- [ ] Set up dashboards (next phase)

---

**Version:** 1.0 (Complete)
**Status:** ✅ Ready for Implementation
**Updated:** 2026-04-19
**Owner:** Performance Lead
**Review Cycle:** Quarterly (3 months)

**Applies to:** All SPEC projects (automatic inheritance)
