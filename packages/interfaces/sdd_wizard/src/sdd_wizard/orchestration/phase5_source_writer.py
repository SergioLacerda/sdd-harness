"""
SddSourceWriter — Phase 5 step: write .sdd/source/ and .sdd/runtime/ content.
"""

from pathlib import Path
from typing import Any

from sdd_core.utils.log import get_logger

from .writers.guidelines_writer import GuidelinesWriter
from .writers.mandates_writer import MandatesWriter
from .writers.readme_writer import ReadmeWriter

logger = get_logger(__name__)


class SddSourceWriter:
    """Create directories and generate all .sdd/source/ + .sdd/runtime/ markdown files."""

    def __init__(
        self,
        output_base: Path,
        source_dir: Path,
        runtime_dir: Path,
        mandates_dir: Path,
        guidelines_dir: Path,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self.output_base = output_base
        self.source_dir = source_dir
        self.runtime_dir = runtime_dir
        self.mandates_dir = mandates_dir
        self.guidelines_dir = guidelines_dir
        self.mandates = mandates
        self.guidelines = guidelines
        self.guidelines_by_category = guidelines_by_category
        self.config = config
        self.verbose = verbose

        import os

        from sdd_core.utils.environment import is_repo_root

        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                output_resolved = self.output_base.resolve()
                if is_repo_root(output_resolved):
                    should_block = True
            except (OSError, ValueError):
                pass

            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"  ❌ {msg}")  # noqa: T201
                raise PermissionError(msg)

        self._mandates_writer = MandatesWriter(mandates_dir, mandates, config, verbose)
        self._guidelines_writer = GuidelinesWriter(
            guidelines_dir, guidelines_by_category, verbose
        )
        self._readme_writer = ReadmeWriter(
            source_dir,
            runtime_dir,
            mandates,
            guidelines,
            guidelines_by_category,
            config,
            verbose,
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def create_directories(self) -> bool:
        """Create output directory structure."""
        self._log("Creating directory structure")
        try:
            self.mandates_dir.mkdir(parents=True, exist_ok=True)
            self.guidelines_dir.mkdir(parents=True, exist_ok=True)
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            workflows_dir = self.output_base / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            self._log("Created directories: .sdd, .github")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create directories: {e}")  # noqa: T201
            return False

    def generate_mandates_file(self) -> bool:
        """Generate .sdd/source/mandates/mandates.md."""
        return self._mandates_writer.generate()

    def generate_guidelines_files(self) -> bool:
        """Generate per-category guidelines markdown files."""
        return self._guidelines_writer.generate()

    def generate_source_readme(self) -> bool:
        """Generate .sdd/source/README.md."""
        return self._readme_writer.generate_source_readme()

    def generate_runtime_readme(self) -> bool:
        """Generate .sdd/runtime/README.md."""
        return self._readme_writer.generate_runtime_readme()

    def generate_plugin_workspace(self) -> bool:
        """Generate plugin protocol directories and files."""
        self._log(
            "Generating plugin workspace (.sdd/plugins, .sdd/contracts, .sdd/analysis, .sdd/docs)"
        )
        try:
            from sdd_cli.generators._contracts import generate_contracts
            from sdd_cli.generators._plugins import generate_plugins_registry

            output_dir = str(self.output_base)

            plugins_result = generate_plugins_registry(output_dir, self.config)
            self._log(f"  plugins registry: {plugins_result.get('registry_path')}")

            contracts_result = generate_contracts(output_dir, self.config)
            self._log(
                f"  contracts: {contracts_result.get('files_written')} files written"
            )

            for state in ("todo", "pending", "refined", "done"):
                state_dir = self.output_base / ".sdd" / "analysis" / state
                state_dir.mkdir(parents=True, exist_ok=True)
            self._log("  analysis workspace: todo/pending/refined/done created")

            docs_dir = self.output_base / ".sdd" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            self._log("  docs dir created")

            return True
        except Exception as e:
            print(f"  ❌ Failed to generate plugin workspace: {e}")  # noqa: T201
            return False
