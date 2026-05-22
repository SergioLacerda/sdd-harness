"""Output/render helpers for governance score and adherence commands."""

from __future__ import annotations

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
