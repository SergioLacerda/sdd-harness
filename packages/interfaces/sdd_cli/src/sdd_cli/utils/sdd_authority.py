"""Canonical `.sdd` authority path helpers.

Centralizes the operational contract:
- active profile: `.sdd/profile`
- executable governance: `.sdd/compiled`
- semantic governance source: `.sdd/source`
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Artifact root constants — explicit names document intent (Decision Log D3)
# ---------------------------------------------------------------------------

#: Sandbox for tests and CI — never the shipped product.
ARTIFACT_ROOT_TEST = Path("generated") / "tmp" / "build" / "final-template"

#: Product built by sdd_wizard — what the end-user installs.
ARTIFACT_ROOT_PRODUCTION = Path("generated") / "client" / "build" / "final-template"

# Internal alias kept for callers that relied on the old name.
# Resolves to the *test* root to preserve the existing default behavior.
DEFAULT_ARTIFACT_ROOT = ARTIFACT_ROOT_TEST

POLICY_ERR_CODE = "PATH_POLICY_VIOLATION"

# Valid values for SDD_RUNTIME_ENV
_RUNTIME_ENV_TEST = "test"
_RUNTIME_ENV_PRODUCTION = "production"
_VALID_RUNTIME_ENVS = {_RUNTIME_ENV_TEST, _RUNTIME_ENV_PRODUCTION}


class PathPolicyViolation(ValueError):
    """Raised when a path access violates artifact-first policy."""

    def __init__(self, requested_path: Path, reason: str, hint: str) -> None:
        self.code = POLICY_ERR_CODE
        self.requested_path = requested_path
        self.reason = reason
        self.hint = hint
        super().__init__(f"{self.code}: {reason} ({requested_path})")

    def as_dict(self) -> dict[str, str]:
        """As Dict."""
        return {
            "code": self.code,
            "requested_path": str(self.requested_path),
            "reason": self.reason,
            "hint": self.hint,
        }


def _repo_root() -> Path:
    from sdd_core.utils.environment import detect_repo_root, find_workspace_root

    ws_root = find_workspace_root()
    if ws_root is not None:
        return ws_root
    return detect_repo_root()


def _artifact_root_from_env(repo_root: Path) -> Path | None:  # noqa: ARG001
    """Check SDD_WORKSPACE_ROOT (highest priority explicit override)."""
    raw = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _read_toml_runtime_env() -> str:
    """Read runtime_env from [tool.sdd.runtime] in pyproject.toml.

    Returns empty string when the key is absent or the file cannot be parsed.
    """
    try:
        repo = _repo_root()
        toml_path = repo / "pyproject.toml"
        if not toml_path.exists():
            return ""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        return str(
            data.get("tool", {})
            .get("sdd", {})
            .get("runtime", {})
            .get("runtime_env", "")
        )
    except Exception:  # nosec B110
        return ""


def _runtime_env_artifact_root() -> Path:
    """Resolve artifact root from SDD_RUNTIME_ENV with pyproject.toml fallback.

    Resolution order:
    1. ``SDD_RUNTIME_ENV`` environment variable  (``test`` | ``production``)
    2. ``[tool.sdd.runtime] runtime_env`` in pyproject.toml
    3. Default: ``test`` (sandbox — never the shipped product)
    """
    # 1. Env var override
    env_val = os.environ.get("SDD_RUNTIME_ENV", "").strip().lower()

    # 2. pyproject.toml fallback
    if not env_val:
        env_val = _read_toml_runtime_env()

    # 3. Normalise and resolve
    if env_val not in _VALID_RUNTIME_ENVS:
        if env_val:
            import warnings

            warnings.warn(
                f"SDD_RUNTIME_ENV='{env_val}' is not a valid value "
                f"({', '.join(sorted(_VALID_RUNTIME_ENVS))}). "
                "Falling back to 'test'.",
                stacklevel=3,
            )
        env_val = _RUNTIME_ENV_TEST

    return (
        ARTIFACT_ROOT_PRODUCTION
        if env_val == _RUNTIME_ENV_PRODUCTION
        else ARTIFACT_ROOT_TEST
    )


def resolve_workspace_root(explicit_root: Path | None = None) -> Path:
    """Resolve artifact workspace root for operational commands/tests.

    Resolution order:
    1. ``explicit_root`` argument (``--workspace-root`` CLI flag)
    2. ``SDD_WORKSPACE_ROOT`` environment variable
    3. ``SDD_RUNTIME_ENV`` environment variable / ``pyproject.toml``
    4. Default: test sandbox (``generated/tmp/build/final-template``)
    """
    repo_root = _repo_root().resolve()
    if explicit_root is not None:
        return explicit_root.expanduser().resolve()

    # 2. Highest priority: explicit override via environment
    from_env = _artifact_root_from_env(repo_root)
    if from_env is not None:
        return from_env

    # 3. Mid priority: actual initialized workspace (.sdd/profile)
    # But ONLY if we are not explicitly in 'test' mode (which wants isolation)
    if os.environ.get("SDD_RUNTIME_ENV") != "test":
        from sdd_core.utils.environment import find_workspace_root

        ws_root = find_workspace_root()
        if ws_root is not None:
            return ws_root.resolve()

    # 4. Fallback: isolated sandbox for development (generated/tmp/...)
    return (repo_root / _runtime_env_artifact_root()).resolve()


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _is_within_system_temp(path: Path) -> bool:
    """Return True when *path* is under the current system temp directory."""
    try:
        sys_tmp = Path(tempfile.gettempdir()).resolve()
    except Exception:  # nosec B110
        return False
    return _is_relative_to(path, sys_tmp)


def enforce_path_policy(
    requested_path: Path,
    *,
    workspace_root: Path,
    mode: str = "normal",
) -> Path:
    """Enforce artifact-first policy for normal mode and audit override mode."""
    req = requested_path.resolve()
    ws = workspace_root.resolve()
    repo = _repo_root().resolve()
    generated_root = (repo / "generated").resolve()

    if mode == "extraordinary_audit":
        # Explicit opt-in mode for bilateral framework/artifact analysis.
        return req
    if mode != "normal":
        raise PathPolicyViolation(
            requested_path=req,
            reason=f"unsupported policy mode '{mode}'",
            hint="use mode='normal' or mode='extraordinary_audit'",
        )
    ws_in_generated = _is_relative_to(ws, generated_root)
    ws_in_tmp = (
        _is_relative_to(ws, Path("/tmp").resolve())  # nosec B108
        or _is_relative_to(ws, Path("/var/tmp").resolve())  # nosec B108
        or _is_within_system_temp(ws)
    )
    is_repo_workspace = (ws == repo) and (ws / ".sdd").is_dir()
    req_in_repo = _is_relative_to(req, repo)

    if (
        not ws_in_generated
        and not ws_in_tmp
        and not is_repo_workspace
        and not req_in_repo
    ):
        raise PathPolicyViolation(
            requested_path=ws,
            reason="workspace root must be under repository 'generated/' (or /tmp for ephemeral tests), or within repo root",
            hint=(
                "set SDD_RUNTIME_ENV=test (default) or SDD_RUNTIME_ENV=production, "
                "or use SDD_WORKSPACE_ROOT for a custom path"
            ),
        )
    if ws_in_generated and not _is_relative_to(req, generated_root):
        raise PathPolicyViolation(
            requested_path=req,
            reason="normal mode only permits reads under repository 'generated/'",
            hint="set SDD_RUNTIME_ENV=production or enable extraordinary audit mode",
        )
    if not _is_relative_to(req, ws):
        raise PathPolicyViolation(
            requested_path=req,
            reason="normal mode restricts reads to the active artifact root (X)",
            hint=f"use paths under '{ws}' or provide --workspace-root",
        )
    return req


def compiled_active_dir(root: Path | None = None) -> Path:
    """Compiled Active Dir."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".sdd" / "compiled"


def source_semantic_dir(root: Path | None = None) -> Path:
    """Source Semantic Dir."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".sdd" / "source"


def profile_active_path(root: Path | None = None) -> Path:
    """Profile Active Path."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".sdd" / "profile"
