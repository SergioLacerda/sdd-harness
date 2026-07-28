"""sdd ask — governed context query command.

Security:
  - Query text is NEVER logged; only sha256[:8] hash is recorded.
  - trace_id is uuid4 local-only; no external correlation.
  - Compliance JSONL is append-only at .sdd/runtime/compliance-events.jsonl.
"""

from __future__ import annotations

from contextvars import ContextVar

import typer

__all__ = [
    "app",
    "_JSON_MODE_OVERRIDE",
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
    "_write_runtime_cache",
    "_upsert_ask_session",
    "_emit_state_warnings",
    "_governance_footer_for_state",
    "_guard_budget_breach",
    "_guard_handshake",
    "_runtime_drift_check",
    "_root_seed_drift_check",
    "_build_dossier_lines",
    "_load_dossier_artifact",
    "TelemetrySink",
    "OtelBridge",
    "OtlpHttpExporter",
]

app: typer.Typer = typer.Typer(help="Query SDD governance context.")

_JSON_MODE_OVERRIDE: ContextVar[bool | None] = ContextVar(
    "ask_json_mode_override", default=None
)


from ._budget import _guard_budget_breach, _guard_handshake  # noqa: E402
from ._helpers import (  # noqa: E402
    _check_fingerprint_drift,
    _get_profile_state,
    _governance_footer_for_state,
    _hash_query,
    _load_compiled_governance,
    _render_context_output,
    _resolve_workspace_root,
    _root_seed_drift_check,
    _runtime_drift_check,
    _try_sdd_compiled_dir,
    _write_runtime_cache,
)
from ._helpers import _normalize_typer_value as _normalize_typer_value  # noqa: E402
from ._pipeline import (  # noqa: E402
    _should_use_organize,
    ask_cmd,
    build_governed_ask_snapshot,
    run_sdd_organize,
)
from ._pipeline_runtime import _ask_cmd_impl as _ask_cmd_impl  # noqa: E402
from ._pipeline_session import (  # noqa: E402
    _emit_state_warnings,
    _run_organize_intake,
)
from ._telemetry import (  # noqa: E402
    OtelBridge,
    OtlpHttpExporter,
    TelemetrySink,
    _build_dossier_lines,
    _capture_effective_tokens,
    _emit_ask_telemetry,
    _load_dossier_artifact,
    _resolve_tokens,
    _upsert_ask_session,
)
