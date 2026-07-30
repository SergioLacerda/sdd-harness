"""Tools."""

import json
from pathlib import Path

import click
import typer

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.services.tools_registry import (
    ToolEntry,
    ToolsRegistry,
    ToolsRegistryError,
    load_tools_registry,
)

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List tool commands."),
) -> None:
    """Developer and maintenance tools."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Tools", ["list", "run"])
        raise typer.Exit(0)


def _find_repo_root() -> Path:
    from sdd_cli.utils.environment import detect_repo_root

    return detect_repo_root()


@app.command("list")
def list_tools(
    include_all: bool = typer.Option(False, "--all", help="Include every manifest entry."),
    include_internal: bool = typer.Option(
        False, "--include-internal", help="Include internal tools."
    ),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include deprecated tools."
    ),
    include_projects: bool = typer.Option(
        False, "--include-projects", help="Include self-contained tool projects."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """List available developer and maintenance tools."""
    root = _find_repo_root()
    tools_dir = root / "tools"

    if not tools_dir.is_dir():
        typer.echo(f"Error: tools directory not found at {tools_dir}", err=True)
        raise click.exceptions.Exit(1)

    try:
        registry = load_tools_registry(root)
    except ToolsRegistryError as exc:
        typer.echo(f"Error: invalid tools registry: {exc}", err=True)
        raise click.exceptions.Exit(1) from None

    if registry is not None:
        entries = _filter_manifest_entries(
            registry,
            include_all=include_all,
            include_internal=include_internal,
            include_deprecated=include_deprecated,
            include_projects=include_projects,
        )
        if json_output:
            typer.echo(
                json.dumps(
                    {
                        "source": "manifest",
                        "registry_path": str(registry.path.relative_to(root)),
                        "tools": [entry.as_dict() for entry in entries],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        typer.echo("Available tools in tools/registry.yaml:")
        for entry in entries:
            typer.echo(f"  - {_format_manifest_entry(entry)}")
        return

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "source": "legacy",
                    "tools": [
                        {"path": str(script.relative_to(tools_dir))}
                        for script in _legacy_python_scripts(tools_dir)
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    typer.echo("Available tools in tools/:")
    for script in _legacy_python_scripts(tools_dir):
        rel_path = script.relative_to(tools_dir)
        typer.echo(f"  - {rel_path}")


@app.command()
def run(
    name: str = typer.Argument(
        ...,
        help="Path to the tool script relative to tools/ (e.g. health/health_check.py)",
    ),
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments to pass to the tool"
    ),
) -> None:
    """Run a tool script using 'uv run'."""
    root = _find_repo_root()
    try:
        registry = load_tools_registry(root)
    except ToolsRegistryError as exc:
        typer.echo(f"Error: invalid tools registry: {exc}", err=True)
        raise click.exceptions.Exit(1) from None

    if registry is not None:
        entry = registry.resolve(name)
        if entry is not None:
            _run_manifest_entry(root, entry, args)
            return

    script_path = _resolve_legacy_script(root, name)

    if not script_path.exists():
        typer.echo(f"Error: tool '{name}' not found at {script_path}", err=True)
        raise click.exceptions.Exit(1)

    _run_command(["uv", "run", str(script_path)], args)


def _legacy_python_scripts(tools_dir: Path) -> list[Path]:
    return sorted(
        script for script in tools_dir.rglob("*.py") if not script.name.startswith("__")
    )


def _filter_manifest_entries(
    registry: ToolsRegistry,
    *,
    include_all: bool,
    include_internal: bool,
    include_deprecated: bool,
    include_projects: bool,
) -> list[ToolEntry]:
    if include_all:
        return list(registry.tools)

    entries = []
    for entry in registry.tools:
        if entry.visibility == "public" and entry.status == "active":
            entries.append(entry)
            continue
        if include_internal and entry.visibility == "internal":
            entries.append(entry)
            continue
        if include_deprecated and (
            entry.visibility == "deprecated" or entry.status == "deprecated"
        ):
            entries.append(entry)
            continue
        if include_projects and entry.visibility == "project":
            entries.append(entry)
    return entries


def _format_manifest_entry(entry: ToolEntry) -> str:
    details = f"{entry.id} ({entry.path}) - {entry.description}"
    labels = []
    if entry.visibility != "public":
        labels.append(entry.visibility)
    if entry.status != "active" and entry.status != entry.visibility:
        labels.append(entry.status)
    if labels:
        details = f"{details} [{' '.join(labels)}]"
    if entry.replacement:
        details = f"{details} replacement: {entry.replacement}"
    return details


def _resolve_legacy_script(root: Path, name: str) -> Path:
    script_path = root / "tools" / name

    if not script_path.exists() and not name.endswith(".py"):
        # Try adding .py extension if missing
        script_path = root / "tools" / f"{name}.py"
    return script_path


def _run_manifest_entry(root: Path, entry: ToolEntry, args: list[str] | None) -> None:
    if not _manifest_entry_can_run(entry):
        message = (
            f"Error: tool '{entry.id}' is not runnable from manifest "
            f"(visibility: {entry.visibility}, status: {entry.status})"
        )
        if entry.replacement:
            message = f"{message}; replacement: {entry.replacement}"
        typer.echo(message, err=True)
        raise click.exceptions.Exit(1)

    target = root / entry.path
    if not target.exists():
        typer.echo(f"Error: tool '{entry.id}' not found at {target}", err=True)
        raise click.exceptions.Exit(1)

    if entry.runner == "uv-python":
        _run_command(["uv", "run", str(target)], args)
        return

    if entry.runner == "python-module" and entry.module:
        _run_command(["uv", "run", "python", "-m", entry.module], args)
        return

    typer.echo(
        f"Error: runner '{entry.runner}' is not directly executable for tool '{entry.id}'",
        err=True,
    )
    raise click.exceptions.Exit(1)


def _manifest_entry_can_run(entry: ToolEntry) -> bool:
    if entry.visibility == "public" and entry.status in {"active", "experimental"}:
        return True
    return entry.allow_direct_run


def _run_command(cmd: list[str], args: list[str] | None) -> None:
    from sdd_core.utils.process import (
        ProcessAuthorizationError,
        ProcessSpawnError,
        SafeProcessRunner,
    )

    if args:
        cmd.extend(args)

    typer.echo(f"Running: {' '.join(cmd)}")
    try:
        # Stream tool output directly to the terminal/CI logs for debuggability.
        result = SafeProcessRunner().run(cmd, check=False, capture_output=False)
        raise click.exceptions.Exit(result.returncode)
    except ProcessAuthorizationError as exc:
        typer.echo(f"Error: execution blocked by policy: {exc}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessSpawnError:
        typer.echo(
            "Error: 'uv' not found in path. Please install uv (https://github.com/astral-sh/uv).",
            err=True,
        )
        raise click.exceptions.Exit(127) from None
