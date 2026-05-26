# Performance SLO Testing Guide

**Status:** ✅ Defined and Ready
**Date:** 2026-04-19

---

## 📋 Overview

Performance SLOs are defined in `../specifications/performance.md` and enforced via pytest tests in `tests/quality/test_performance_slos.py`.

This guide explains how to measure, validate, and improve performance.

---

## 🎯 SLO Summary

### Response Time Budgets (P99 Latencies)

| Layer | Budget | Example |
|-------|--------|---------|
| Adapter | 10ms | API validation |
| Interface | 20ms | HTTP routing |
| Application | 100ms | UseCase logic |
| Domain | 200ms | Business logic |
| Infrastructure | 500ms | DB query |
| Vector Index | 300ms | Semantic search |
| Bootstrap | 2000ms | App startup |
| Framework | 50ms | Event dispatch |

### Throughput Minimums

| Endpoint | Minimum RPS |
|----------|------------|
| GET endpoints | 100 |
| POST endpoints | 50 |
| AI generation | 5 |
| Vector search | 50 |

### Resource Limits

| Resource | Limit |
|----------|-------|
| Memory per campaign | 512 MB |
| Memory per request | 50 MB |
| CPU per request | 100 ms |
| Storage per project | 10 GB |

---

## 🧪 Running Performance Tests

### View All SLOs

```bash
# Display configuration
pytest tests/quality/test_performance_slos.py::test_performance_slo_configuration -v -s

# Output:
# ✅ All SLO configurations valid
```

### Generate Performance Report

```bash
# Show all defined SLOs
pytest tests/quality/test_performance_slos.py::test_generate_performance_report -v -s

# Output shows:
# 📊 PERFORMANCE SLO REPORT
# - Layer budgets (P99 latency)
# - Throughput minimums (RPS)
# - Resource limits
```

### Run Example Benchmarks

```bash
# Test adapter layer latency
pytest tests/quality/test_performance_slos.py::test_example_adapter_layer_latency -v -s

# Test GET endpoint throughput
pytest tests/quality/test_performance_slos.py::test_example_get_endpoint_throughput -v -s

# Run all examples
pytest tests/quality/test_performance_slos.py -k example -v -s
```

### Run Full Test Suite

```bash
pytest tests/quality/test_performance_slos.py -v
```

---

## 🔍 Interpreting Results

### ✅ Test Passed

```
test_example_adapter_layer_latency PASSED

✅ adapter P99: 7.2ms (limit: 10ms)
  Measured: P50=2.1ms, P99=7.2ms, Max=9.8ms
```

**Interpretation:**

- Adapter layer meets latency budget
- 99% of requests complete in 7.2ms
- Well within 10ms limit

### ❌ Test Failed

```
test_example_application_layer_latency FAILED

❌ application P99: 156.3ms (limit: 100ms, 56% over budget)
  Measured: P50=80.5ms, P99=156.3ms, Max=250.1ms
```

**Interpretation:**

- Application layer exceeds latency budget
- P99 is 56% over the 100ms limit
- Needs optimization

---

## 📝 Writing Project-Specific Benchmarks

### Template

```python
def test_my_layer_latency(slo_validator):
    """My layer must meet latency SLO."""

    # 1. Define operation to measure
    def my_operation():
        # Replace with actual code
        result = my_module.execute()
        return result

    # 2. Measure latency
    latencies = slo_validator.measure_latency(
        my_operation,
        iterations=100  # Run 100 times
    )

    # 3. Validate against SLO
    passed, message = slo_validator.validate_latency_slo(
        "application",  # or your layer
        latencies["p99"]
    )

    # 4. Report and assert
    print(f"\n{message}")
    print(f"  P50={latencies['p50']:.1f}ms, "
          f"P95={latencies['p95']:.1f}ms, "
          f"P99={latencies['p99']:.1f}ms")

    assert passed, message
```

### Registering New Layer

Edit `../specifications/performance.md` and `PerformanceSLOValidator` class:

```python
LAYER_BUDGETS = {
    "my_layer": {"p50": 50, "p99": 100},  # Add your layer
}
```

---

## 🚀 Optimization Workflow

### Step 1: Measure Current Performance

```bash
pytest tests/quality/test_performance_slos.py::test_example_application_layer_latency -v -s
```

### Step 2: Identify Bottleneck

```
❌ application P99: 156.3ms (limit: 100ms, 56% over budget)

Layers contributing to latency:
- Adapter: 5ms
- Interface: 15ms
- Application: 80ms ← BOTTLENECK (56% over 50ms budget)
- Domain: 45ms
- Infrastructure: 8ms
```

### Step 3: Optimize

Example optimizations:

```python
# BEFORE: Takes 80ms
def usecase_execute(request):
    # Process all items
    results = [process(item) for item in request.items]
    return results

# AFTER: Takes 40ms (parallel execution)
async def usecase_execute(request):
    # Process items concurrently
    results = await asyncio.gather(
        *[process_async(item) for item in request.items]
    )
    return results
```

### Step 4: Verify Improvement

```bash
pytest tests/quality/test_performance_slos.py::test_example_application_layer_latency -v -s

# Expected:
# ✅ application P99: 48.2ms (limit: 100ms)
```

### Step 5: Commit Optimization

```bash
git add -A
git commit -m "Optimize application layer latency: 156ms → 48ms

- Implement async processing
- Reduce batch size
- Add caching

Metrics:
- Before: P99=156ms (56% over budget)
- After: P99=48ms (52% under budget)
- Improvement: 69% faster"
```

---

## 📊 Real-World Example: RPG Narrative Server

### UseCase Layer Optimization

**Baseline (Failing):**

```
❌ application P99: 180ms (limit: 100ms)

Problem: Narrative generation takes too long
- Generate narrative: 120ms
- Validate narrative: 40ms
- Serialize response: 20ms
```

**Optimized:**

```
✅ application P99: 85ms (limit: 100ms)

Solution: Async generation + caching
- Generate narrative (async): 60ms
- Validate (parallel): 15ms
- Serialize (optimized): 10ms
```

**Benchmark Proof:**

```bash
$ pytest tests/quality/test_performance_slos.py -k narrative -v

test_narrative_usecase_latency PASSED
✅ application P99: 85.3ms (limit: 100ms)
  P50=42.1ms, P95=78.5ms, P99=85.3ms, Max=92.1ms
```

---

## 🔗 Integration with CI/CD

### GitHub Actions

Performance tests run on every PR:

```yaml
# .github/workflows/performance.yml
jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/quality/test_performance_slos.py -v

      # Fail if P99 > limit
      - if: failure()
        run: echo "❌ Performance tests failed"
```

### Pre-commit Hook

Check performance before committing:

```bash
pytest tests/quality/test_performance_slos.py
```

---

## 📈 Performance Monitoring

### Local Development

Monitor performance during development:

```bash
# Run tests with detailed output
pytest tests/quality/test_performance_slos.py -v -s

# Run with profiling
pytest tests/quality/test_performance_slos.py --profile
```

### Production Monitoring

Metrics exported to observability platform:

```python
# Prometheus metrics
latency_histogram.record(request_latency_ms)
throughput_counter.add(1)
error_counter.add(1, attributes={"error_type": "timeout"})
```

**Dashboards:**

- P50/P95/P99 latency per endpoint
- Throughput (RPS) over time
- Error rates by type
- Resource utilization

---

## 🆘 Troubleshooting

### Test Fails: "No successful measurements"

**Cause:** Function throwing exceptions

**Fix:**

```python
def my_operation():
    try:
        # Your code
        pass
    except Exception as e:
        print(f"Error: {e}")
        raise
```

### Test Fails: "Layer P99 exceeds budget"

**Cause:** Performance degradation

**Solution:**

1. Profile code to find bottleneck
2. Optimize slow operation
3. Re-run tests
4. Commit changes

### "Unknown layer" Error

**Cause:** Layer not registered in SLO validator

**Fix:** Add to `LAYER_BUDGETS`:

```python
LAYER_BUDGETS = {
    "my_layer": {"p50": 50, "p99": 100},
}
```

---

## 📚 References

- [Performance Specification](../specifications/performance.md)
- [Architecture (with layer budgets)](../specifications/architecture.md)
- [Monitoring Guide](../specifications/observability.md) (WIP)
- [Test Strategy](../specifications/testing.md)

---

## ✅ Checklist for Performance Review

Before merging:

- [ ] All existing performance tests still pass
- [ ] New code has performance tests (if applicable)
- [ ] P99 latency within budget
- [ ] Throughput meets minimum
- [ ] Memory footprint acceptable
- [ ] Performance report generated

---

**Framework:** SPEC v1.0
**Owner:** Performance Lead
**Review Cycle:** Quarterly (3 months)
**Status:** ✅ Production-Ready
