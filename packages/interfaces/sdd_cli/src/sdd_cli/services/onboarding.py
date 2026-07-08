"""OnboardingOrchestrator — orchestrates client workspace bootstrap sequence."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import typer

from sdd_cli.utils.operational_errors import operational_error_from_exception
from sdd_core.utils.environment import resolve_sdd_child_cmd
from sdd_core.utils.process import ProcessRunnerError, SafeProcessRunner


@dataclass
class OnboardingResult:
    """Result of a client workspace bootstrap sequence."""

    success: bool
    failed_step: str | None = None
    exit_code: int = 0
    messages: list[str] = field(default_factory=list)


class OnboardingOrchestrator:
    """Runs the 3-step post-profile bootstrap for --type client workspaces."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def _run_step(self, _label: str, args: list[str]) -> bool:
        sdd_cmd = resolve_sdd_child_cmd()
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        runner = SafeProcessRunner()
        command = [sdd_cmd] + args
        try:
            result = runner.run(
                command,
                cwd=self.cwd,
                env=env,
                capture_output=False,
            )
        except (OSError, ProcessRunnerError) as exc:
            operational_error = operational_error_from_exception(
                exc,
                headline=f"Bootstrap step failed while running '{_label}'.",
                command="sdd init",
                step=_label,
                operation="run child command",
                path=self.cwd,
                next_hint=f"retry: {' '.join(command)}",
            )
            if operational_error is None:
                raise
            raise operational_error from exc
        return result.success

    def step_governance(self, *, force: bool) -> bool:
        """[2/5] Generate governance artifacts. Skips if already compiled and not forced."""
        compiled = self.cwd / ".sdd" / "compiled" / "governance-core.json"
        if not force and compiled.exists():
            typer.echo(
                "[2/5] Generating governance artifacts... (skipped — already compiled)"
            )
            return True
        typer.echo("[2/5] Generating governance artifacts...")
        ok = self._run_step(
            "governance generate",
            ["governance", "generate", "--full-bootstrap"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} governance generate")
        return ok

    def step_skills(self, *, force: bool) -> bool:
        """[3/5] Initialize skills. Skips if already seeded and not forced."""
        seeds_dir = self.cwd / ".sdd" / "skills"
        if not force and seeds_dir.exists() and any(seeds_dir.iterdir()):
            typer.echo("[3/5] Initializing skills... (skipped — already seeded)")
            return True
        typer.echo("[3/5] Initializing skills...")
        ok = self._run_step(
            "skills bootstrap",
            ["skills", "--full-bootstrap", "--regenerate-seeds"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} skills bootstrap")
        return ok

    def step_validate(self) -> bool:
        """[4/5] Validate runtime state with sdd runtime status --force."""
        typer.echo("[4/5] Validating runtime state...")
        ok = self._run_step(
            "runtime status",
            ["runtime", "status", "--force"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} runtime status")
        return ok

    def step_hooks(self, *, force: bool) -> bool:
        """[5/5] Install git hooks. Skips if not a git repo or already installed."""
        git_dir = self.cwd / ".git"
        if not git_dir.exists():
            typer.echo("[5/5] Installing git hooks... (skipped — not a git repository)")
            return True
        pre_commit_hook = git_dir / "hooks" / "pre-commit"
        if not force and pre_commit_hook.is_symlink():
            typer.echo("[5/5] Installing git hooks... (skipped — already installed)")
            return True
        typer.echo("[5/5] Installing git hooks...")
        sdd_cmd = resolve_sdd_child_cmd()
        ok = self._run_step(
            "setup git-hooks",
            ["setup", "git-hooks"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} setup git-hooks")
        if not ok:
            typer.echo(
                f"      executable used: {sdd_cmd}\n"
                "      validate the command tree with: sdd setup --help\n"
                f"      then retry: {sdd_cmd} setup git-hooks",
                err=True,
            )
        return ok

    def run(self, *, force: bool) -> OnboardingResult:
        """Execute the full bootstrap sequence. Stops immediately on first failure."""
        if not self.step_governance(force=force):
            return OnboardingResult(
                success=False,
                failed_step="governance",
                exit_code=2,
                messages=[
                    "governance generate failed — re-run with --verbose for detail"
                ],
            )
        if not self.step_skills(force=force):
            return OnboardingResult(
                success=False,
                failed_step="skills",
                exit_code=3,
                messages=["skills bootstrap failed — check permissions and seed files"],
            )
        if not self.step_validate():
            return OnboardingResult(
                success=False,
                failed_step="validate",
                exit_code=4,
                messages=[
                    "workspace initialized but governance not active",
                    "run: sdd runtime status --verbose",
                ],
            )
        if not self.step_hooks(force=force):
            sdd_cmd = resolve_sdd_child_cmd()
            return OnboardingResult(
                success=False,
                failed_step="hooks",
                exit_code=5,
                messages=[
                    f"git hooks install failed — run: {sdd_cmd} setup git-hooks",
                    "validate command tree first: sdd setup --help",
                ],
            )
        return OnboardingResult(success=True, exit_code=0)
