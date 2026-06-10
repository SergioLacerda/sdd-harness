"""Output/render helpers for governance score and adherence commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table


def render_governance_score_output(
    *,
    checks: list[tuple[str, bool, int]],
    final_score: int,
    threshold: int,
    verbose: bool,
    console: Console,
) -> None:
    """Render governance score output and enforce threshold exit policy."""
    if verbose:
        table = Table(
            title="Governance Score Breakdown", show_header=True, header_style="bold"
        )
        table.add_column("Check", style="cyan")
        table.add_column("Weight", style="yellow")
        table.add_column("Status", style="green")
        for label, passed, weight in checks:
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(label, str(weight), status)
        console.print(table)

    color = "green" if final_score >= threshold else "red"
    console.print(
        f"[{color}]Governance score: {final_score}/100 (threshold: {threshold})[/{color}]"
    )

    if final_score < threshold:
        raise typer.Exit(1)


def render_governance_adherence_output(
    *,
    result: dict[str, Any],
    threshold: int,
    window: int,
    verbose: bool,
    console: Console,
) -> None:
    """Render governance adherence output and enforce threshold exit policy."""
    score = int(result["score"])
    details = result["details"]

    if verbose:
        table = Table(
            title="Governance Adherence Breakdown",
            show_header=True,
            header_style="bold",
        )
        table.add_column("Dimension", style="cyan")
        table.add_column("Max", style="yellow", justify="right")
        table.add_column("Score", style="green", justify="right")
        table.add_column("Detail")
        table.add_row(
            "Behavioral",
            "50",
            str(details["behavioral_score"]),
            (
                f"allows={details['allows']} warns={details['warns']} "
                f"blocks={details['blocks']} (last {window}h)"
            ),
        )
        table.add_row(
            "Structural",
            "30",
            str(details["structural_score"]),
            details["structural_status"],
        )
        table.add_row(
            "Freshness",
            "20",
            str(details["freshness_score"]),
            details["freshness_status"],
        )
        console.print(table)

    color = "green" if score >= threshold else "red"
    console.print(
        f"[{color}]Governance adherence: {score}/100 (threshold: {threshold})[/{color}]"
    )

    if score < threshold:
        raise typer.Exit(1)


def run_governance_score(
    *,
    ws_root: Path,
    verbose: bool,
    threshold: int,
    console: Console,
) -> None:
    """Execute governance score checks and render output."""
    from sdd_cli.utils.sdd_authority import compiled_active_dir
    from sdd_core.governance.handshake import AgentHandshakeProtocol
    from sdd_core.governance.scoring import compute_governance_score
    from sdd_core.utils.environment import WorkspaceNotInitializedError, resolve_profile

    checks: list[tuple[str, bool, int]] = []

    # Check 1 (30): .sdd/profile present + valid type
    try:
        profile_ctx = resolve_profile(root=ws_root)
        checks.append((".sdd/profile valid", True, 30))
    except WorkspaceNotInitializedError:
        checks.append((".sdd/profile valid", False, 30))
        profile_ctx = None

    # Check 2 (30): governance artifacts compiled
    artifact_candidates = [compiled_active_dir(ws_root) / "governance-core.json"]
    artifacts_ok = any(p.exists() for p in artifact_candidates)
    checks.append(("governance artifacts compiled", artifacts_ok, 30))

    # Check 3 (20): AHP confidence >= 50%
    ahp = AgentHandshakeProtocol(project_root=ws_root)
    ahp_state, ahp_report = ahp.validate(output_mode="silent", force_recheck=True)
    confidence_ok = ahp_report.confidence >= 50.0
    checks.append(
        (
            f"AHP confidence >= 50% (actual: {ahp_report.confidence:.1f}%)",
            confidence_ok,
            20,
        )
    )

    # Check 4 (20): core_hash in profile matches compiled artifact
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
                # Backward compatibility for artifacts without embedded fingerprint.
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
    checks.append(("core_hash matches artifact", hash_ok, 20))

    final_score = compute_governance_score(checks)
    render_governance_score_output(
        checks=checks,
        final_score=final_score,
        threshold=threshold,
        verbose=verbose,
        console=console,
    )


def run_governance_score_cmd(
    *, verbose: bool, threshold: int, console: Console
) -> None:
    """Resolve workspace root and run governance score."""
    from sdd_cli.utils.sdd_authority import enforce_path_policy, resolve_workspace_root

    ws_root = resolve_workspace_root()
    if ws_root is None:
        Console(stderr=True).print("[red]ERROR: No workspace found.[/red]")
        import typer

        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    run_governance_score(
        ws_root=ws_root, verbose=verbose, threshold=threshold, console=console
    )


def run_governance_adherence_cmd(
    *, verbose: bool, threshold: int, window: int, console: Console
) -> None:
    """Compute and render governance adherence score."""
    from sdd_cli.utils.sdd_authority import resolve_workspace_root
    from sdd_core.governance.compliance import compute_governance_adherence

    ws_root = resolve_workspace_root()
    try:
        result = compute_governance_adherence(
            workspace_root=ws_root, window_hours=window
        )
    except Exception as exc:
        Console(stderr=True).print(
            f"[red]ERROR computing governance adherence: {exc}[/red]"
        )
        import typer

        raise typer.Exit(1) from exc
    render_governance_adherence_output(
        result=result,
        threshold=threshold,
        window=window,
        verbose=verbose,
        console=console,
    )
