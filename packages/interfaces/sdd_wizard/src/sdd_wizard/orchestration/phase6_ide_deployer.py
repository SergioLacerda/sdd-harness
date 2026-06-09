"""
IdeTemplateDeployer — Phase 6 step: copy IDE/CI templates and inject bootstrap metadata.
"""

import os
from pathlib import Path
from typing import Any

from .deployer.seedling_injector import SeedlingInjector
from .deployer.template_deployer import TemplateDeployer


class IdeTemplateDeployer:
    """Copy IDE config templates from sdd_integration and inject governance metadata."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        config: dict[str, Any] | None = None,
        verbose: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.output_base = output_base
        self.config = config or {}
        self.verbose = verbose

        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                if self.output_base.resolve() == self.repo_root.resolve():
                    should_block = True
            except (OSError, ValueError):
                pass
            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"  ❌ {msg}")  # noqa: T201
                raise PermissionError(msg)

        self._deployer = TemplateDeployer(repo_root, output_base, self.config, verbose)
        self._injector = SeedlingInjector(repo_root, output_base, verbose)

    def _log(self, message: str) -> None:
        self._deployer._log(message)

    @property
    def _template_base(self) -> Path:
        return self._deployer._template_base

    def _template_base_candidates(self) -> list[Path]:
        return self._deployer._template_base_candidates()

    def _optional_hooks_enabled(self) -> bool:
        return self._deployer._optional_hooks_enabled()

    def _ensure_cursor_rule_aliases(self) -> None:
        self._deployer._ensure_cursor_rule_aliases()

    def copy_templates(self) -> bool:
        """Copy IDE/CI templates from the integration package."""
        return self._deployer.copy_templates()

    def create_ide_templates(self) -> bool:
        """Create IDE config files from the bootstrap template base."""
        return self._deployer.create_ide_templates()

    def inject_bootstrap_metadata(
        self,
        fingerprint: str,
        generated_at: str,
        mandates_count: int,
    ) -> None:
        """Append governance fingerprint block to bootstrap markdown files."""
        self._injector.inject_bootstrap_metadata(
            fingerprint, generated_at, mandates_count
        )

    def populate_ide_rules(
        self,
        mandates: list[dict[str, Any]],
        fingerprint: str,
    ) -> None:
        """Replace template placeholders in IDE rule files with live governance data."""
        self._injector.populate_ide_rules(mandates, fingerprint)
