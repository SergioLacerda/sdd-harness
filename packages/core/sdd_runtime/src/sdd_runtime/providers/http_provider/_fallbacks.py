"""Fallback results and response deserialization for HttpProvider."""

from __future__ import annotations

from typing import Any

from sdd_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
)


def _degraded_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        task_class="unknown",
        complexity_score=0.5,
        suggested_path_id="A",
        keywords=[],
        provider="http",
    )


def _fallback_compressed_context(context: ContextBundle) -> CompressedContext:
    compressed_bytes = sum(len(item.encode()) for item in context.items)
    return CompressedContext(
        items=context.items,
        original_bytes=compressed_bytes,
        compressed_bytes=compressed_bytes,
        compression_ratio=1.0,
        provider="http",
    )


def _fallback_budget_estimate() -> BudgetEstimate:
    return BudgetEstimate(
        estimated_bytes=50_000,
        suggested_path_id="A",
        confidence=0.2,
        provider="http",
    )


def _deserialize_response(
    result_type: type[Any], response_data: dict[str, Any], provider_name: str
) -> Any:
    """Deserialize a raw HTTP response payload into the requested result type."""
    if result_type == AnalysisResult:
        return AnalysisResult(
            task_class=response_data.get("task_class", "unknown"),
            complexity_score=response_data.get("complexity_score", 0.5),
            suggested_path_id=response_data.get("suggested_path_id", "A"),
            keywords=response_data.get("keywords", []),
            provider=provider_name,
        )
    elif result_type == CompressedContext:
        return CompressedContext(
            items=response_data.get("items", []),
            original_bytes=response_data.get("original_bytes", 0),
            compressed_bytes=response_data.get("compressed_bytes", 0),
            compression_ratio=response_data.get("compression_ratio", 1.0),
            provider=provider_name,
        )
    elif result_type == BudgetEstimate:
        return BudgetEstimate(
            estimated_bytes=response_data.get("estimated_bytes", 50_000),
            suggested_path_id=response_data.get("suggested_path_id", "A"),
            confidence=response_data.get("confidence", 0.5),
            provider=provider_name,
        )
    else:
        raise ValueError(f"Unknown result type: {result_type}")
