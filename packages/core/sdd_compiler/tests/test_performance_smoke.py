from __future__ import annotations

import json
import os
from time import perf_counter

import pytest

from sdd_compiler.dsl_compiler import compile_string

pytestmark = pytest.mark.unit


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _build_dataset(mandates: int = 400, guidelines: int = 200) -> str:
    parts: list[str] = []
    for i in range(1, mandates + 1):
        parts.append(
            f"- [M{i:03d}] **Mandate {i}** Description {i} with category: core\n---"
        )
    for i in range(1, guidelines + 1):
        parts.append(
            "\n".join(
                [
                    f"guideline G{i:02d} {{",
                    "  type: SOFT",
                    f'  title: "Guideline {i}"',
                    f'  description: "Description {i}"',
                    "  category: general",
                    "}",
                ]
            )
        )
    return "\n".join(parts)


def test_dsl_compiler_performance_smoke() -> None:
    max_compile_ms = _int_env("SDD_COMPILER_SMOKE_MAX_MS", 3000)
    max_size_multiplier = _float_env("SDD_COMPILER_SMOKE_MAX_SIZE_MULTIPLIER", 3.0)

    dsl = _build_dataset()

    start = perf_counter()
    output, metrics = compile_string(dsl)
    elapsed_ms = (perf_counter() - start) * 1000

    assert output is not None
    assert metrics.success
    assert elapsed_ms <= max_compile_ms, (
        f"Compile smoke regression: {elapsed_ms:.1f}ms > {max_compile_ms}ms"
    )
    assert metrics.input_size > 0
    size_multiplier = metrics.output_size / metrics.input_size
    assert size_multiplier <= max_size_multiplier, (
        "Unexpected output-size regression: "
        f"output/input={size_multiplier:.3f} > {max_size_multiplier:.3f}"
    )

    summary_path = os.environ.get("SDD_COMPILER_PERF_SUMMARY_PATH", "").strip()
    if summary_path:
        payload = {
            "elapsed_ms": round(elapsed_ms, 3),
            "max_compile_ms": max_compile_ms,
            "input_size": metrics.input_size,
            "output_size": metrics.output_size,
            "size_multiplier": round(size_multiplier, 6),
            "max_size_multiplier": max_size_multiplier,
            "parse_mode": metrics.parse_mode,
            "parse_backend": metrics.parse_backend,
            "parse_fallback_used": metrics.parse_fallback_used,
            "warnings": metrics.warnings,
        }
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=True)
