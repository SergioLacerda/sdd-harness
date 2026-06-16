"""sdd ask — budget zone resolution and runtime token metric helpers."""

from __future__ import annotations

import logging
from typing import Any

from sdd_cli.commands._ask_backend._pipeline_runtime_support import (
    check_budget_zone_and_compress as _support_check_budget_zone_and_compress,
)
from sdd_cli.services.ask_types import _AskInputs

from ._helpers import _prefer_full_summary
from ._telemetry import _capture_effective_tokens_with_source

logger = logging.getLogger(__name__)


def _check_budget_zone_and_compress(
    query: str,
    estimated_context_bytes: int,
    mandates_count: int,
    *,
    prefer_full_summary_fn: Any = _prefer_full_summary,
    logger: logging.Logger = logger,
) -> tuple[int, float | None]:
    return _support_check_budget_zone_and_compress(
        query,
        estimated_context_bytes,
        mandates_count,
        prefer_full_summary_fn=prefer_full_summary_fn,
        logger=logger,
    )


def _resolve_runtime_token_metrics(
    inputs: _AskInputs, output_text: str
) -> tuple[int | None, int | None, str]:
    from sdd_cli.commands import _ask_backend as _backend

    tokens_in, tokens_out, token_source = _capture_effective_tokens_with_source(
        inputs.tokens_input, inputs.tokens_output
    )
    if tokens_in is None or tokens_out is None:
        est_in, est_out, est_source = _backend._resolve_tokens(
            inputs.query, output_text
        )
        if tokens_in is None:
            tokens_in = est_in
        if tokens_out is None:
            tokens_out = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source
    return tokens_in, tokens_out, token_source
