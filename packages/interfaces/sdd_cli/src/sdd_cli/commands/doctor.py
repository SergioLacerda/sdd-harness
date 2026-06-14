"""Doctor."""

import logging
from pathlib import Path

import typer

from sdd_cli.utils.command_errors import handle_cli_errors
from sdd_cli.utils.environment import detect_repo_root
from sdd_cli.utils.sdd_authority import (
    compiled_active_dir,
    enforce_path_policy,
    resolve_workspace_root,
)

app = typer.Typer(invoke_without_command=True)
logger = logging.getLogger(__name__)


def _get_default_spec() -> Path:
    """Resolve default spec path relative to repo root."""
    root = detect_repo_root()
    return (
        root
        / "packages"
        / "features"
        / "sdd_integration"
        / "src"
        / "sdd_integration"
        / "protocol"
        / "integration_flow.yaml"
    )


@app.callback()
def _(
    ctx: typer.Context,
    spec: Path = typer.Option(None, help="Path to integration flow spec"),  # noqa: B008
) -> None:
    """Run diagnostics."""
    if ctx.invoked_subcommand is None:
        run(spec=spec, mode="isolated", score_threshold=0, adherence_threshold=0)


def _apply_score_gate(score_threshold: int) -> None:
    """D4: governance score gate. Raises typer.Exit(1) if score is below threshold."""
    if score_threshold <= 0:
        return
    try:
        from sdd_core.governance.handshake import AgentHandshakeProtocol
        from sdd_core.utils.environment import (
            WorkspaceNotInitializedError,
            resolve_profile,
        )

        ws_root = resolve_workspace_root()
        ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
        if ws_root is None:
            return

        artifact_candidates = [compiled_active_dir(ws_root) / "governance-core.json"]
        ahp = AgentHandshakeProtocol(project_root=ws_root)
        _, ahp_report = ahp.validate(output_mode="silent")
        profile_ctx = None
        profile_ok = True
        try:
            profile_ctx = resolve_profile(root=ws_root)
        except WorkspaceNotInitializedError:
            profile_ok = False

        artifacts_ok = any(p.exists() for p in artifact_candidates)
        confidence_ok = ahp_report.confidence >= 50.0

        # Check 4: core_hash in profile matches compiled artifact (same logic as governance.py)
        hash_ok = False
        if profile_ctx is not None and profile_ctx.core_hash and artifacts_ok:
            try:
                import hashlib
                import json as _json

                art_path = next(p for p in artifact_candidates if p.exists())
                raw = art_path.read_bytes()
                data = _json.loads(raw)
                artifact_fp = str(data.get("fingerprint", "")).strip()

                if artifact_fp:
                    hash_ok = artifact_fp[:16] == profile_ctx.core_hash
                else:
                    clean = {
                        k: v
                        for k, v in data.items()
                        if k not in {"_signature", "fingerprint"}
                    }
                    computed = hashlib.sha256(
                        _json.dumps(clean, sort_keys=True).encode()
                    ).hexdigest()[:16]
                    hash_ok = computed == profile_ctx.core_hash
            except Exception:
                hash_ok = False

        # Use centralized score computation (includes all 4 checks for consistency)
        from sdd_core.governance.scoring import compute_governance_score

        checks = [
            ("profile valid", profile_ok, 30),
            ("artifacts compiled", artifacts_ok, 30),
            ("AHP confidence >= 50%", confidence_ok, 20),
            ("core_hash matches artifact", hash_ok, 20),
        ]
        score = compute_governance_score(checks)

        if score < score_threshold:
            typer.echo(
                f"[SDD] Governance score {score}/100 below threshold {score_threshold}. Run 'sdd governance score --verbose' for details.",
                err=True,
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.debug("Score gate check failed unexpectedly", exc_info=True)


def _apply_adherence_gate(adherence_threshold: int) -> None:
    """D4b: governance adherence gate. Raises typer.Exit(1) if adherence is below threshold."""
    if adherence_threshold <= 0:
        return
    try:
        from sdd_core.governance.compliance import compute_governance_adherence

        ws_root = resolve_workspace_root()
        adherence = compute_governance_adherence(workspace_root=ws_root)["score"]

        if adherence < adherence_threshold:
            typer.echo(
                f"[SDD] Governance adherence {adherence}/100 below threshold {adherence_threshold}. Run 'sdd governance adherence --verbose' for details.",
                err=True,
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.debug("Adherence gate check failed unexpectedly", exc_info=True)


@app.command()
@handle_cli_errors(
    command_name="doctor run",
    next_hint="run 'sdd setup run' to ensure dependencies are installed",
)
def run(
    spec: Path = typer.Option(None, help="Path to integration flow spec"),  # noqa: B008
    mode: str = typer.Option("isolated", help="Execution mode for doctor checks"),
    score_threshold: int = typer.Option(
        0,
        "--score-threshold",
        help="Minimum governance score (0-100). 0 disables the gate.",
    ),
    adherence_threshold: int = typer.Option(
        0,
        "--adherence-threshold",
        help="Minimum governance adherence score (0-100). 0 disables the gate.",
    ),
) -> None:
    """Run SDD diagnostics (integration flow)"""
    mode = mode.strip().lower()
    if mode not in {"isolated", "real"}:
        raise typer.BadParameter("mode must be 'isolated' or 'real'.")

    try:
        from sdd_integration.engine.integration_engine import IntegrationEngine
    except ImportError:
        typer.echo(
            "Command 'doctor' is unavailable because optional dependency 'sdd_integration' could not be loaded.\nRun `sdd setup run` or install the missing package dependencies.",
            err=True,
        )
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    enforce_path_policy(workspace_root, workspace_root=workspace_root, mode="normal")

    _apply_score_gate(score_threshold)
    _apply_adherence_gate(adherence_threshold)

    target_spec = spec or _get_default_spec()

    if not target_spec.exists():
        typer.echo(f"[red]ERROR: Spec file not found at {target_spec}[/red]", err=True)
        typer.echo(
            "  Next: run 'sdd setup run' to ensure all packages are installed", err=True
        )
        raise typer.Exit(1)

    typer.echo(f"Running SDD Doctor (Spec: {target_spec.name}, Mode: {mode})...\n")

    context_overrides = None
    if mode == "real":
        context_overrides = {"working_dir": str(detect_repo_root()), "isolation": False}

    engine = IntegrationEngine(str(target_spec), context_overrides=context_overrides)
    report = engine.run()

    typer.echo(report.pretty())

    if report.score() < 100:
        typer.echo(
            "  Next: review failing checks above and run 'sdd runtime status'", err=True
        )
        raise typer.Exit(1)
