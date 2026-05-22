"""Governance loading helpers for ask flows."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# 7-tuple type alias:
# (source, fingerprint, mandates_count, authenticated, degraded, reason, trust_source)
GovResult = tuple[str, str, int, bool, bool, str, str]

_CANONICAL_GOVERNANCE_FILES = ("governance-core.json", "governance-client.json")


def _compiled_candidates(
    workspace_root: Path, *, compiled_active_dir_fn: Any
) -> list[Path]:
    """Return canonical compiled artifact candidate dirs."""
    return [compiled_active_dir_fn(workspace_root)]


def fingerprint_file(path: Path) -> str:
    """Return short sha256 fingerprint for file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def signature_mode() -> str:
    """Return effective signature mode: off|warn|strict."""
    mode = os.environ.get("SDD_SIGNATURE_MODE", "warn").strip().lower()
    if mode not in {"off", "warn", "strict"}:
        return "warn"
    return mode


def try_sdd_compiled_dir(
    sdd_compiled: Path,
    *,
    logger: Any | None = None,
) -> tuple[str, str, int] | None:
    """Load governance from canonical files in .sdd/compiled."""
    for name in _CANONICAL_GOVERNANCE_FILES:
        candidate = sdd_compiled / name
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            mandates = data.get("mandates", data.get("items"))
            if mandates is None:
                if logger is not None:
                    logger.debug("Skipping %s: missing 'items' or 'mandates' key", name)
                continue
            if not isinstance(mandates, list):
                continue
            fingerprint = data.get("fingerprint", fingerprint_file(candidate))[:8]
            return "compiled", fingerprint, len(mandates)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            if logger is not None:
                logger.debug(
                    "Skipping %s: failed to parse governance artifact: %s", name, exc
                )
            continue
    return None


def validate_signature_for_artifact(
    artifact_path: Path,
    *,
    signature_mode_value: str,
) -> tuple[bool, bool, str, str]:
    """Return (authenticated, degraded, reason, trust_source)."""
    if signature_mode_value == "off":
        return True, False, "", "none"
    try:
        from sdd_runtime.signatures import validate_artifact_signature

        result = validate_artifact_signature(
            artifact_path=artifact_path,
            sig_path=artifact_path.with_suffix(artifact_path.suffix + ".sig"),
            strict=signature_mode_value == "strict",
        )
    except Exception as exc:
        if signature_mode_value == "strict":
            return False, False, f"signature validation failed: {exc}", "none"
        return (
            False,
            True,
            f"signature validation unavailable in warn mode: {exc}",
            "none",
        )
    if result.ok:
        degraded = bool(result.deprecation_warning) and signature_mode_value == "warn"
        reason = result.deprecation_warning if degraded else ""
        return True, degraded, reason, result.trust_source
    if result.blocking:
        return False, False, f"{result.code}: {result.reason}", result.trust_source
    return False, True, f"{result.code}: {result.reason}", result.trust_source


def load_governance_via_runtime(
    workspace_root: Path,
    *,
    compiled_active_dir_fn: Any,
    logger: Any | None = None,
) -> tuple[str, str, int, str, str] | None:
    """Attempt loading governance via GovernanceInjector."""
    try:
        from sdd_runtime import GovernanceInjector

        injector = GovernanceInjector()
        for candidate_dir in _compiled_candidates(
            workspace_root, compiled_active_dir_fn=compiled_active_dir_fn
        ):
            if not candidate_dir.is_dir():
                continue
            result = injector.inject_from_path(candidate_dir)
            if result.loaded:
                return (
                    "compiled",
                    result.artifact_fingerprint[:8],
                    result.total_loaded,
                    result.auth_state,
                    result.trust_source,
                )
    except Exception as exc:
        if logger is not None:
            logger.debug(
                "GovernanceInjector unavailable, using fallback loader: %s", exc
            )
    return None


def try_sdd_compiled_fallback(
    sdd_compiled: Path,
    signature_mode_value: str,
    *,
    logger: Any | None = None,
) -> GovResult | None:
    """Priority 0: load from .sdd/compiled."""
    if not sdd_compiled.is_dir():
        return None
    result = try_sdd_compiled_dir(sdd_compiled, logger=logger)
    if result is None:
        return None
    source, fp, count = result
    artifact = sdd_compiled / "governance-core.json"
    if artifact.exists():
        authenticated, degraded, reason, trust_source = validate_signature_for_artifact(
            artifact,
            signature_mode_value=signature_mode_value,
        )
        return source, fp, count, authenticated, degraded, reason, trust_source
    if signature_mode_value == "strict":
        return (
            source,
            fp,
            count,
            False,
            False,
            "strict mode requires authenticated artifact",
            "none",
        )
    return (
        source,
        fp,
        count,
        False,
        signature_mode_value == "warn",
        "fallback artifact loaded without signature verification",
        "none",
    )


def log_sdd_metadata(workspace_root: Path, *, logger: Any | None = None) -> None:
    """Best-effort metadata side-check logging."""
    sdd_metadata = workspace_root / ".sdd" / "metadata.json"
    if not sdd_metadata.exists():
        return
    try:
        metadata = json.loads(sdd_metadata.read_text(encoding="utf-8"))
        if logger is not None:
            logger.debug(
                "Workspace metadata found: version=%s, item_count=%s",
                metadata.get("version"),
                metadata.get("item_count"),
            )
    except Exception as exc:
        if logger is not None:
            logger.debug(".sdd/metadata.json exists but invalid: %s", exc)


def load_compiled_governance(
    workspace_root: Path,
    *,
    compiled_active_dir_fn: Any,
    logger: Any | None = None,
    load_via_runtime_fn: Any = None,
) -> GovResult:
    """Load governance from compiled sources with runtime-first strategy."""
    mode = signature_mode()
    _load_via_runtime = load_via_runtime_fn or load_governance_via_runtime
    runtime_result = _load_via_runtime(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir_fn,
        logger=logger,
    )
    if runtime_result is not None:
        source, fp, count, auth_state, trust_source = runtime_result
        authenticated = auth_state == "verified"
        degraded = auth_state == "degraded"
        return source, fp, count, authenticated, degraded, "", trust_source

    for sdd_compiled in _compiled_candidates(
        workspace_root, compiled_active_dir_fn=compiled_active_dir_fn
    ):
        result = try_sdd_compiled_fallback(
            sdd_compiled,
            mode,
            logger=logger,
        )
        if result is not None:
            return result

    log_sdd_metadata(workspace_root, logger=logger)
    return "none", "", 0, False, False, "no governance artifacts found", "none"
