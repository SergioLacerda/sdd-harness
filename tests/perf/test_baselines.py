"""Performance SLO baseline checks for CI.

These checks validate configured SLOs and compare existing benchmark snapshots
against configured thresholds without running heavy benchmarks in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.perf

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def _load_pyproject() -> dict:
    path = Path("pyproject.toml")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _performance_config() -> dict:
    data = _load_pyproject()
    tool = data.get("tool", {})
    sdd = tool.get("sdd", {})
    perf = sdd.get("performance")
    assert isinstance(perf, dict), "Missing [tool.sdd.performance] in pyproject.toml"
    return perf


def test_performance_slo_contract_present() -> None:
    perf = _performance_config()
    expected = {
        "runtime_bootstrap_ms": 500,
        "governance_compile_ms": 1000,
        "skill_routing_p99_ms": 100,
        "concurrent_agents_min": 50,
    }
    for key, value in expected.items():
        assert key in perf, f"Missing performance SLO key: {key}"
        assert perf[key] == value, f"Unexpected SLO value for {key}: {perf[key]}"


def test_performance_slo_values_are_positive() -> None:
    perf = _performance_config()
    for key in (
        "runtime_bootstrap_ms",
        "governance_compile_ms",
        "skill_routing_p99_ms",
        "concurrent_agents_min",
    ):
        value = perf[key]
        assert isinstance(value, int), f"{key} must be int, got {type(value).__name__}"
        assert value > 0, f"{key} must be > 0, got {value}"


def test_benchmark_snapshot_within_slo_when_available() -> None:
    perf = _performance_config()
    snapshot = Path("tests/perf/benchmark_results.json")
    if not snapshot.exists():
        pytest.skip("Benchmark snapshot not available")

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    compilation = data.get("compilation", {})
    ask_latency = data.get("ask_latency", {})

    compile_1k = compilation.get("1000", {})
    compile_1k_ms = compile_1k.get("compile_time_ms")
    ask_p99_ms = ask_latency.get("latency_p99_ms")

    assert isinstance(compile_1k_ms, int | float), "Missing 1K compile_time_ms"
    assert isinstance(ask_p99_ms, int | float), "Missing ask latency_p99_ms"

    assert compile_1k_ms <= perf["governance_compile_ms"], (
        f"1K compile_time_ms={compile_1k_ms} exceeds governance_compile_ms="
        f"{perf['governance_compile_ms']}"
    )
    assert ask_p99_ms <= perf["skill_routing_p99_ms"], (
        f"ask latency_p99_ms={ask_p99_ms} exceeds skill_routing_p99_ms="
        f"{perf['skill_routing_p99_ms']}"
    )
