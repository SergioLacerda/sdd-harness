"""sdd ask — command entrypoints and governed snapshot builder."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from sdd_runtime.cache import get_context_cache

from sdd_cli.commands._ask_backend import app
from sdd_cli.services.ask_organize import run_sdd_organize as run_sdd_organize
from sdd_cli.services.ask_organize import (
    should_use_organize as _should_use_organize,
)
from sdd_cli.utils.output import is_json_mode

from ._helpers import (
    _collect_learning_signals,
    _signature_mode,
)

if TYPE_CHECKING:
    from ._phase_timer import PhaseTimer

_HANDBOOK_LOOKUP_LIMIT = 5
_RUNBOOK_HANDBOOK_ID = "HBK-RUNBOOK-CONSULTATION"
_RUNBOOK_SIGNAL_TOKENS = (
    "diagnos",
    "erro",
    "error",
    "fail",
    "failure",
    "falha",
    "hotfix",
    "recovery",
    "recover",
    "recuper",
    "release",
    "asset",
    "runtime drift",
    "drift",
    "generated-runtime",
    "generated runtime",
    "governance runtime",
    "context budget",
    "token budget",
    "budget breach",
    "estouro de contexto",
    "orçamento de contexto",
)


def _cached_handbook_lookup(
    root: Path, *, query: str, task_type: str, operation_phase: str
) -> Any:
    """Look up runtime handbook entries via the shared `ContextLoader` cache.

    The default `sdd ask` snapshot path re-read and re-matched
    `index.yaml` on every call with zero caching benefit, unlike `--dossier`
    (which already uses this same in-memory LRU cache, 128 entries/5-min TTL,
    via `ContextLoader`). Reusing that cache here — keyed on the query plus
    task_type/operation_phase — avoids re-parsing the handbook index for a
    repeated/near-identical query within the TTL window.
    """
    from sdd_cli.services.governance_docs_sources import lookup_runtime_handbook

    cache = get_context_cache()
    artifact_id = f"handbook:{root.resolve()}"
    item_types = [task_type, f"phase:{operation_phase}"]
    cached = cache.get(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types)
    if cached is not None:
        return cached
    result = lookup_runtime_handbook(
        root, task_type=task_type, operation_phase=operation_phase
    )
    cache.set(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types, result)
    return result


__all__ = [
    "_should_use_organize",
    "ask_cmd",
    "build_runtime_handbook_hint",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
]


def _infer_handbook_task_type(query: str, skill: str | None) -> str:
    skill_value = (skill or "").strip().lower()
    if skill_value in {"planning", "implementation", "diagnosis"}:
        return skill_value
    if skill_value in {"diagnose", "debug", "stabilize"}:
        return "diagnosis"
    query_value = query.lower()
    if any(token in query_value for token in ("diagnos", "erro", "error", "fail")):
        return "diagnosis"
    if any(token in query_value for token in ("plan", "design", "proposal")):
        return "planning"
    return "implementation"


def _runbook_relevance_reason(query: str) -> str | None:
    query_value = query.casefold()
    matched = [token for token in _RUNBOOK_SIGNAL_TOKENS if token in query_value]
    if not matched:
        return None
    return f"runtime runbook signal matched: {', '.join(matched[:3])}"


def _compact_handbook_match(match: dict[str, Any]) -> dict[str, Any]:
    hint: dict[str, Any] = {
        "id": str(match.get("id", "")),
        "runtime_doc": str(match.get("runtime_doc", "")),
    }
    load_policy = match.get("load_policy")
    if isinstance(load_policy, dict) and load_policy:
        hint["load_policy"] = load_policy
    return hint


def build_runtime_handbook_hint(
    *,
    root: Path,
    query: str,
    skill: str | None,
    cached_handbook_task_type: str | None = None,
) -> dict[str, Any] | None:
    """Return a compact runtime-only handbook hint for cheap ask profiles.

    This is intentionally narrower than the full governed snapshot. It reads only
    generated runtime handbook files under `.sdd/source/handbook/**`, and it
    emits a hint only when the query has operational/runbook symptoms.
    """
    relevance_reason = _runbook_relevance_reason(query)
    if relevance_reason is None:
        return None
    handbook_task_type = (
        cached_handbook_task_type
        if cached_handbook_task_type is not None
        else _infer_handbook_task_type(query, skill)
    )
    try:
        lookup = _cached_handbook_lookup(
            root,
            query=query,
            task_type=handbook_task_type,
            operation_phase="context_loading",
        )
    except Exception as exc:
        return {
            "status": "skipped",
            "diagnostic": f"handbook_lookup_error:{type(exc).__name__}",
            "relevance_reason": relevance_reason,
        }
    matches = list(getattr(lookup, "matches", []))
    selected = next(
        (
            match
            for match in matches
            if str(match.get("id", "")) == _RUNBOOK_HANDBOOK_ID
        ),
        matches[0] if matches else None,
    )
    hint: dict[str, Any] = {
        "status": getattr(lookup, "status", "unknown"),
        "diagnostic": getattr(lookup, "diagnostic", ""),
        "relevance_reason": relevance_reason,
    }
    if isinstance(selected, dict):
        hint.update(_compact_handbook_match(selected))
    return hint


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Any | None = None,
    require_handshake: bool = True,
    cached_handbook_task_type: str | None = None,
    phase_timer: PhaseTimer | None = None,
) -> dict[str, Any]:
    """Build a governed ask snapshot with envelope + learning context.

    Callers that measure `ask.governance.snapshot` (e.g. `_load_ask_snapshot`)
    own that outer span themselves, wrapping the whole call — this keeps
    that phase observable even when this function is replaced by a test
    double. When `phase_timer` is supplied, the handbook lookup is
    additionally measured as its own `ask.runtime.handbook` phase. Because
    that phase is typically nested inside a caller's own
    `ask.governance.snapshot` span, its duration is counted in both —
    a known, documented limitation of `PhaseTimer.phase_total_ms()` /
    `unattributed_ms()` not being nesting-aware. The handbook lookup is a
    small fraction of the overall snapshot build, so the effect is minor.
    """
    from sdd_cli.commands import _ask_backend as _backend

    root = workspace_root or _backend._resolve_workspace_root()
    if require_handshake:
        _backend._guard_handshake(root)
    last_known_fingerprint = _backend._get_last_known_fingerprint(root)
    cached_snapshot = (
        _backend._get_cached_governance_snapshot(root, last_known_fingerprint)
        if last_known_fingerprint
        else None
    )
    if cached_snapshot is not None:
        context_source = cached_snapshot["context_source"]
        fingerprint = cached_snapshot["fingerprint"]
        mandates_count = cached_snapshot["mandates_count"]
        authenticated = cached_snapshot["authenticated"]
        degraded = cached_snapshot["degraded"]
        degrade_reason = cached_snapshot["degrade_reason"]
        trust_source = cached_snapshot["trust_source"]
        governance_snapshot_to_persist = None
    else:
        (
            context_source,
            fingerprint,
            mandates_count,
            authenticated,
            degraded,
            degrade_reason,
            trust_source,
        ) = _backend._load_compiled_governance(root)
        # Only a fresh (cache-miss) load is worth persisting — re-persisting on
        # a hit would slide `computed_at` forward without ever re-verifying
        # against the real compiled state, defeating the TTL bound that keeps
        # a post-recompile cache hit self-healing (design.md D-A).
        governance_snapshot_to_persist = {
            "context_source": context_source,
            "fingerprint": fingerprint,
            "mandates_count": mandates_count,
            "authenticated": authenticated,
            "degraded": degraded,
            "degrade_reason": degrade_reason,
            "trust_source": trust_source,
        }
    if _signature_mode() == "strict" and not authenticated:
        raise PermissionError(degrade_reason)
    drift_detected = _backend._runtime_drift_check(root, fingerprint)
    root_seed_drift_detected = _backend._root_seed_drift_check(root)
    learning_signals = _collect_learning_signals(workspace_root=root)
    handbook_task_type = (
        cached_handbook_task_type
        if cached_handbook_task_type is not None
        else _infer_handbook_task_type(query, skill)
    )

    handbook_phase = (
        phase_timer.phase("ask.runtime.handbook", latency_domain="governance")
        if phase_timer is not None
        else nullcontext()
    )
    with handbook_phase:
        handbook_lookup = _cached_handbook_lookup(
            root,
            query=query,
            task_type=handbook_task_type,
            operation_phase="context_loading",
        )
    return {
        "workspace_root": root,
        "context_source": context_source,
        "fingerprint": fingerprint,
        "mandates_count": mandates_count,
        "authenticated": authenticated,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "trust_source": trust_source,
        "drift_detected": drift_detected,
        "root_seed_drift_detected": root_seed_drift_detected,
        "learning_signals": learning_signals,
        "handbook_task_type": handbook_task_type,
        "handbook_lookup": {
            "status": handbook_lookup.status,
            "diagnostic": handbook_lookup.diagnostic,
            "matches": handbook_lookup.matches,
        },
        # Internal plumbing for the end-of-call write site (design.md D-A) —
        # None on a cache hit (nothing new to persist), the fresh compiled-
        # governance fields on a miss. Never surfaced in text/JSON output;
        # downstream consumers only read known top-level fields by name.
        "_governance_snapshot_to_persist": governance_snapshot_to_persist,
    }


# ---------------------------------------------------------------------------
# sdd ask
# ---------------------------------------------------------------------------


@app.command("ask")
def _ask_cli_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(  # noqa: UP045
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(  # noqa: UP045
        None, "--budget", help="Token budget ceiling for this query."
    ),
    full: bool = typer.Option(
        False, "--full", help="Emit detailed steps and full telemetry payload."
    ),
    log_path: str | None = typer.Option(  # noqa: UP045
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
    intake_only: bool = typer.Option(
        False,
        "--intake-only",
        help=(
            "Cheap hook-mode profile: execution_gate/intake_index_mode/intent "
            "with compact runtime handbook hints."
        ),
    ),
) -> None:
    """Query SDD governance context — minimal governed output."""
    from sdd_cli.commands import _ask_backend as _backend

    token = _backend._JSON_MODE_OVERRIDE.set(is_json_mode(ctx))
    try:
        ask_cmd(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        _backend._JSON_MODE_OVERRIDE.reset(token)


def ask_cmd(
    query: str,
    dossier: bool = False,
    skill: str | None = None,
    budget: int | None = None,
    full: bool = False,
    log_path: str | None = None,
    log_format: str = "jsonl",
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    *,
    intake_only: bool = False,
    output_json: bool | None = None,
) -> None:
    """Query SDD governance context — minimal governed output."""
    from sdd_cli.commands import _ask_backend as _backend

    token = (
        _backend._JSON_MODE_OVERRIDE.set(output_json)
        if output_json is not None
        else None
    )
    try:
        _backend._ask_cmd_impl(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        if token is not None:
            _backend._JSON_MODE_OVERRIDE.reset(token)
