from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .handshake_cache import HandshakeCache
from .handshake_models import HandshakeReport

if TYPE_CHECKING:
    from ._handshake_validation_result import ValidationResult
    from .handshake import AgentHandshakeProtocol


def find_project_root(project_root: Path | None) -> Path:
    if project_root is not None:
        return project_root
    current = Path.cwd()
    if current.name == "packages":
        return current.parent
    for parent in [current, *list(current.parents)]:
        if (parent / "packages").exists():
            return parent
    return current


def resolve_cache_ttl(
    project_root: Path, cache_file: Path, cache_dir: Path, cache_ttl_minutes: int | None
) -> timedelta:
    if cache_ttl_minutes is not None:
        return timedelta(minutes=cache_ttl_minutes)
    temp_cache = HandshakeCache(
        cache_file, cache_dir, timedelta(minutes=30), project_root, ""
    )
    return timedelta(minutes=temp_cache.resolve_ttl_minutes())


def hydrate_cache_state(
    protocol: AgentHandshakeProtocol, cache: dict[str, Any]
) -> None:
    if "gap_version" in cache:
        protocol.gap_status = cache.get("status", "NOT_ACTIVE")
        protocol.agent_id = cache.get("agent_id", protocol.agent_id)
        protocol.spec_fingerprint = cache.get("spec_fingerprint", "")
        protocol.mandates_loaded = cache.get("mandates_loaded", [])
        protocol.skill_profile = cache.get("skill_profile", "default")
    else:
        protocol.mandates_loaded = protocol._extract_mandates()
        protocol.spec_fingerprint = protocol._compute_spec_fingerprint()
        protocol.gap_status = protocol._map_ahp_to_gap(
            cache.get("state", "NOT_CONNECTED"), cache.get("confidence", 0)
        )
    protocol.current_confidence = cache.get("confidence", 0)


def cached_report(
    protocol: AgentHandshakeProtocol, cache: dict[str, Any]
) -> tuple[str, HandshakeReport]:
    hydrate_cache_state(protocol, cache)
    report = HandshakeReport(
        state=cache["state"],
        confidence=cache["confidence"],
        checks=[],
        actions=protocol.ACTIONS.get(cache["state"], []),
        cached=True,
        cache_age_seconds=int(
            (
                datetime.now() - datetime.fromisoformat(cache["last_check"])
            ).total_seconds()
        ),
    )
    return cache["state"], report


def fresh_validation(protocol: AgentHandshakeProtocol) -> tuple[str, HandshakeReport]:
    l1_state, l1_results = protocol._layer_1_discovery()
    l2_state, l2_results = protocol._layer_2_link_validation()
    l3_state, l3_results = protocol._layer_3_runtime_validation()
    l4_state, l4_results = protocol._layer_4_governance_health()
    all_results: list[ValidationResult] = (
        l1_results + l2_results + l3_results + l4_results
    )
    final_state = protocol._compute_final_state(l1_state, l2_state, l3_state, l4_state)
    confidence = protocol._compute_confidence(all_results)
    protocol.mandates_loaded = protocol._extract_mandates()
    protocol.spec_fingerprint = protocol._compute_spec_fingerprint()
    protocol.gap_status = protocol._map_ahp_to_gap(final_state, confidence)
    protocol.current_confidence = confidence
    checks = [asdict(result) for result in all_results]
    protocol._save_cache(final_state, checks, confidence)
    protocol._emit_governance_event(final_state, confidence)
    return final_state, HandshakeReport(
        state=final_state,
        confidence=round(confidence, 1),
        checks=checks,
        actions=protocol.ACTIONS.get(final_state, []),
        cached=False,
        cache_age_seconds=None,
    )
