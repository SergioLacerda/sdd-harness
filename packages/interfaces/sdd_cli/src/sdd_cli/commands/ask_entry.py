"""Top-level `sdd ask` command entrypoint (no duplicated subcommand token)."""

from __future__ import annotations

import click
import typer

from sdd_cli.utils.output import is_json_mode

app = typer.Typer(
    help="Query SDD governance context (minimal).",
    context_settings={"allow_interspersed_args": True},
)


@app.callback(invoke_without_command=True)
def ask(
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
) -> None:
    """Run governed ask query."""
    normalized_query = query.strip()
    if not normalized_query or normalized_query.lower() in {"null", "nula"}:
        return

    if full:
        from sdd_cli.commands._ask_backend import ask_full_cmd

        ask_full_cmd(
            query=normalized_query,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            json_output=is_json_mode(click.get_current_context(silent=True)),
        )
        return

    from sdd_cli.commands._ask_backend import ask_cmd

    ask_cmd(
        query=normalized_query,
        dossier=dossier,
        skill=skill,
        budget=budget,
        output_json=is_json_mode(click.get_current_context(silent=True)),
    )
