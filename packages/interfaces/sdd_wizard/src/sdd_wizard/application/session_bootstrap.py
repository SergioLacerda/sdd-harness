"""Session bootstrap for the canonical wizard entrypoint."""

from __future__ import annotations

from pathlib import Path

from sdd_wizard.application.finalization import build_wizard_result
from sdd_wizard.application.phase_runtime import PhaseRuntime
from sdd_wizard.contracts import WizardInvocation, WizardResult


class SessionBootstrap:
    """Resolve invocation state and execute the current runtime."""

    def __init__(self, invocation: WizardInvocation) -> None:
        self._invocation = WizardInvocation(
            project_root=invocation.project_root or Path.cwd(),
            non_interactive=invocation.non_interactive,
            output_path=invocation.output_path,
            language=invocation.language,
        )

    def run(self) -> WizardResult:
        """Execute the runtime and translate the result into the public contract."""
        success = PhaseRuntime(self._invocation).execute()
        return build_wizard_result(success)
