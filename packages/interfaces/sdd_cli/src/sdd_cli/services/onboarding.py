"""OnboardingOrchestrator — orchestrates client workspace bootstrap sequence."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import typer

from sdd_core.utils.process import SafeProcessRunner


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
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        runner = SafeProcessRunner()
        result = runner.run(
            ["sdd"] + args,
            cwd=self.cwd,
            env=env,
            capture_output=False,
        )
        return result.success

    def step_governance(self, *, force: bool) -> bool:
        """[2/4] Generate governance artifacts. Skips if already compiled and not forced."""
        compiled = self.cwd / ".sdd" / "compiled" / "governance-core.json"
        if not force and compiled.exists():
            typer.echo(
                "[2/4] Generating governance artifacts... (skipped — already compiled)"
            )
            return True
        typer.echo("[2/4] Generating governance artifacts...")
        ok = self._run_step(
            "governance generate",
            ["governance", "generate", "--full-bootstrap"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} governance generate")
        return ok

    def step_skills(self, *, force: bool) -> bool:
        """[3/4] Initialize skills. Skips if already seeded and not forced."""
        seeds_dir = self.cwd / ".sdd" / "skills"
        if not force and seeds_dir.exists() and any(seeds_dir.iterdir()):
            typer.echo("[3/4] Initializing skills... (skipped — already seeded)")
            return True
        typer.echo("[3/4] Initializing skills...")
        ok = self._run_step(
            "skills bootstrap",
            ["skills", "--full-bootstrap", "--regenerate-seeds"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} skills bootstrap")
        return ok

    def step_validate(self) -> bool:
        """[4/4] Validate runtime state with sdd runtime status --force."""
        typer.echo("[4/4] Validating runtime state...")
        ok = self._run_step(
            "runtime status",
            ["runtime", "status", "--force"],
        )
        typer.echo(f"      {'✓' if ok else '✗'} runtime status")
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
        return OnboardingResult(success=True, exit_code=0)
