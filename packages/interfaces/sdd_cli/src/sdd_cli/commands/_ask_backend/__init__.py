"""sdd ask — governed context query command.

Security:
  - Query text is NEVER logged; only sha256[:8] hash is recorded.
  - trace_id is uuid4 local-only; no external correlation.
  - Compliance JSONL is append-only at .sdd/runtime/compliance-events.jsonl.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

import typer

__all__ = [
    "app",
    "ask_cmd",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
    "_should_use_organize",
    "_resolve_tokens",
    "_capture_effective_tokens",
    "_emit_ask_telemetry",
    "_resolve_workspace_root",
    "_get_profile_state",
    "_run_organize_intake",
    "_render_context_output",
    "_try_sdd_compiled_dir",
    "_hash_query",
    "_load_compiled_governance",
    "_check_fingerprint_drift",
    "_check_budget_zone_and_compress",
    "_write_runtime_cache",
    "_upsert_ask_session",
    "_emit_state_warnings",
    "_governance_footer_for_state",
    "_guard_budget_breach",
    "_guard_handshake",
    "TelemetrySink",
    "OtelBridge",
    "OtlpHttpExporter",
]

app: typer.Typer = typer.Typer(help="Query SDD governance context.")
logger = logging.getLogger(__name__)
_LEARNING_WINDOW_DAYS = 7


_TRUE_VALUES = {"1", "true", "yes", "on"}
_JSON_MODE_OVERRIDE: ContextVar[bool | None] = ContextVar(
    "ask_json_mode_override", default=None
)
_BREACH_EXIT_CODE = 3


from ._budget import _guard_budget_breach, _guard_handshake  # noqa: E402
from ._helpers import (  # noqa: E402
    _check_fingerprint_drift,
    _get_profile_state,
    _governance_footer_for_state,
    _hash_query,
    _load_compiled_governance,
    _render_context_output,
    _resolve_workspace_root,
    _try_sdd_compiled_dir,
    _write_runtime_cache,
)
from ._helpers import _normalize_typer_value as _normalize_typer_value  # noqa: E402
from ._pipeline import (  # noqa: E402
    _emit_state_warnings,
    _run_organize_intake,
    _should_use_organize,
    ask_cmd,
    build_governed_ask_snapshot,
    run_sdd_organize,
)
from ._pipeline_runtime import _ask_cmd_impl as _ask_cmd_impl  # noqa: E402
from ._pipeline_runtime import _check_budget_zone_and_compress  # noqa: E402
from ._telemetry import (  # noqa: E402
    OtelBridge,
    OtlpHttpExporter,
    TelemetrySink,
    _capture_effective_tokens,
    _emit_ask_telemetry,
    _resolve_tokens,
    _upsert_ask_session,
)
