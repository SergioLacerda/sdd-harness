"""Top-level `sdd ask-full` compatibility entrypoint."""

from __future__ import annotations

import click
import typer

from sdd_cli.utils.output import is_json_mode

app = typer.Typer(
    help="Query SDD governance context (full output compatibility alias).",
    context_settings={"allow_interspersed_args": True},
)


@app.callback(invoke_without_command=True)
def ask_full(
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
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
    """Run governed ask query in full-output mode."""
    normalized_query = query.strip()
    if not normalized_query or normalized_query.lower() in {"null", "nula"}:
        return

    from sdd_cli.commands._ask_backend import ask_full_cmd

    ask_full_cmd(
        query=normalized_query,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        json_output=is_json_mode(click.get_current_context(silent=True)),
    )
