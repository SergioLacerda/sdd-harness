"""Top-level `sdd ask` command entrypoint (no duplicated subcommand token)."""

from __future__ import annotations

import typer

app = typer.Typer(help="Query SDD governance context (minimal).")


@app.callback(invoke_without_command=True)
def ask(
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(
        None, "--budget", help="Token budget ceiling for this query."
    ),
) -> None:
    """Run governed ask query."""
    normalized_query = query.strip()
    if not normalized_query or normalized_query.lower() in {"null", "nula"}:
        return

    from sdd_cli.commands._ask_backend import ask_cmd

    ask_cmd(query=normalized_query, dossier=dossier, skill=skill, budget=budget)
