# ADR-015: Python-to-Go Compiler Migration Performance Comparison

**Status:** Accepted
**Proposed:** 2026-07-01
**Accepted:** 2026-07-01

---

## Context

`packages/core/sdd_compiler`, the Python DSL/governance compiler, was replaced
by `tools/sdd-compile`, a Go binary, in commit `d48706d` (`refactor: replace
Python-based sdd_compiler package with new Go-based sdd-compile tool`).

The migration rationale is recorded in `tools/sdd-compile/DECISIONS.md`, which
cites parsing and validation performance on large mandate/guideline sets as the
primary motivation.

No document compared actual performance between the two implementations. The
only published numbers, in `docs/spec/guides/PERFORMANCE.md` section 5.3.C, did
not measure the real Python compiler.

## Prior Benchmark Was A Placeholder

`tests/perf/benchmark_performance.py` (`CompileTimeBenchmark.run()`) is the
source of the 1K/5K/10K mandate numbers published in `PERFORMANCE.md`. Its
compile step only split strings and counted lines. It never called
`sdd_compiler.dsl_compiler.compile_string` or any other compiler code.

Those figures describe a placeholder, not the real Python compiler. This ADR
replaces them with a real measurement.

## Measurement Method

Both implementations were run on the same machine, an Intel i5-4460 at 3.20GHz,
against the same synthetic input: 400 mandates, matching the existing Go
regression test.

| Implementation | Method |
|---|---|
| Go | `go test ./tests/ -bench BenchmarkCompile400Mandates -benchtime=20x`, calling `internal/compiler.Compile` directly |
| Python | Deleted `sdd_compiler` source checked out from `d48706d^`, calling `sdd_compiler.dsl_compiler.compile_string` directly |

## Results

| Implementation | Input | Result |
|---|---|---|
| Python (`compile_string`, real) | 400 mandates | avg 4.76ms, min 4.68ms |
| Go (`compiler.Compile`) | 400 mandates | 3.27ms/op |

Go is about 1.45 times faster than the real Python compiler at this scale. That
is a real but modest gain, not the 2-3 orders of magnitude implied by the old
placeholder-derived figures.

This does not contradict the migration decision. `tools/sdd-compile/DECISIONS.md`
also cites signing without an OpenSSL subprocess, msgpack number fidelity, and
consolidation with other Go tooling.

## Decision

- Treat `PERFORMANCE.md` section 5.3.C figures as superseded by this ADR for
  compiler implementation comparisons.
- Any future compiler benchmark suite must exercise the real compile path.
- Go benchmarks should call `internal/compiler.Compile`.
- Historical Python comparisons should call `compile_string`.

## Consequences

Positive:

- Establishes an honest, reproducible baseline for the Go compiler's
  performance relative to what it replaced.
- Documents the placeholder defect in `tests/perf/benchmark_performance.py`.

Negative:

- `tests/perf/benchmark_performance.py` itself was not fixed or removed as part
  of this ADR. It remains a placeholder and should not be used for compiler
  performance claims until corrected.

## References

- `tools/sdd-compile/DECISIONS.md`
- `tools/sdd-compile/tests/perf_test.go`
- `tests/perf/benchmark_performance.py`
- `docs/spec/guides/PERFORMANCE.md` section 5.3.C
- Commit `d48706d`
