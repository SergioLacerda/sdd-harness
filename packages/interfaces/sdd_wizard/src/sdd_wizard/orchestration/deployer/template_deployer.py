"""TemplateDeployer — copy IDE/CI config templates to the output directory."""

from __future__ import annotations

import contextlib
import os
import shutil
from importlib import resources
from pathlib import Path
from typing import Any

from sdd_core.utils.log import get_logger

logger = get_logger(__name__)


class TemplateDeployer:
    """Copy IDE config templates from sdd_integration to the output directory."""

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

        if os.environ.get("SDD_TEST_OUTPUT_DIR"):
            try:
                if self.output_base.resolve() == self.repo_root.resolve():
                    msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                    print(f"  ❌ {msg}")  # noqa: T201
                    raise PermissionError(msg)
            except (OSError, ValueError):
                pass

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    @property
    def _template_base(self) -> Path:
        for candidate in self._template_base_candidates():
            if candidate.exists():
                return candidate
        return self._template_base_candidates()[-1]

    def _template_base_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        with contextlib.suppress(ModuleNotFoundError, TypeError, AttributeError):
            pkg_root = resources.files("sdd_integration")
            candidates.append(Path(str(pkg_root)) / "templates")
        candidates.append(
            self.repo_root
            / "packages"
            / "features"
            / "sdd_integration"
            / "src"
            / "sdd_integration"
            / "templates"
        )
        candidates.append(
            Path(__file__).resolve().parent.parent.parent
            / "templates"
            / "bootstrap-fallback"
        )
        return candidates

    def _optional_hooks_enabled(self) -> bool:
        return bool(self.config.get("include_optional_hooks", False))

    def _ensure_cursor_rule_aliases(self) -> None:
        cursor_rules_dir = self.output_base / ".cursor" / "rules"
        spec_file = cursor_rules_dir / "spec.mdc"
        governance_file = cursor_rules_dir / "sdd-governance.mdc"
        if spec_file.exists() and not governance_file.exists():
            shutil.copy2(spec_file, governance_file)
            self._log("Created Cursor governance alias from spec.mdc")
        elif governance_file.exists() and not spec_file.exists():
            shutil.copy2(governance_file, spec_file)
            self._log("Created Cursor spec alias from sdd-governance.mdc")

    def copy_templates(self) -> bool:
        """Copy base templates to .github/workflows."""
        self._log("Copying templates")
        try:
            src_workflow = (
                self._template_base / ".github" / "workflows" / "sdd-validation.yml"
            )
            dst_workflow = (
                self.output_base / ".github" / "workflows" / "sdd-validation.yml"
            )
            dst_workflow.parent.mkdir(parents=True, exist_ok=True)
            if src_workflow.exists():
                shutil.copy2(src_workflow, dst_workflow)
                self._log("Copied sdd-validation.yml to .github/workflows/")
            else:
                self._log(f"Template not found: {src_workflow}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to copy templates: {e}")  # noqa: T201
            return False

    def create_ide_templates(self) -> bool:  # noqa: C901
        """Copy configuration templates from sdd_integration to output directory."""
        self._log("Copying IDE templates and project files")
        try:
            template_base = self._template_base
            if not template_base.exists():
                attempted = ", ".join(
                    str(path) for path in self._template_base_candidates()
                )
                print(f"  ❌ Template base not found: {template_base}")  # noqa: T201
                self._log(f"Attempted template bases: {attempted}")
                return False

            copied_count = 0
            dir_mappings: list[tuple[Path, Path]] = [
                (template_base / ".github", self.output_base / ".github"),
                (template_base / ".vscode", self.output_base / ".vscode"),
                (template_base / ".cursor", self.output_base / ".cursor"),
                (template_base / ".claude", self.output_base / ".claude"),
                (template_base / ".gemini", self.output_base / ".gemini"),
                (
                    template_base / ".sdd" / "templates",
                    self.output_base / ".sdd" / "templates",
                ),
            ]

            for src, dst in dir_mappings:
                try:
                    if src.exists() and src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        if (
                            dst == self.output_base / ".github"
                            and not self._optional_hooks_enabled()
                        ):
                            hook = dst / "setup-precommit-hook.sh"
                            if hook.exists():
                                hook.unlink()
                        self._log(f"Copied {src.name}/ directory")
                        copied_count += 1
                    else:
                        self._log(f"⚠️  Template directory not found: {src.name}/")
                except Exception as e:
                    self._log(f"⚠️  Failed to copy {src.name}/: {e}")

            optional_files: list[tuple[Path, Path]] = []
            if self._optional_hooks_enabled():
                optional_files.append(
                    (
                        template_base / ".pre-commit-config.yaml",
                        self.output_base / ".pre-commit-config.yaml",
                    )
                )
            for src, dst in optional_files:
                try:
                    if src.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                        self._log(f"Copied optional file {src.name}")
                except Exception as e:
                    self._log(f"⚠️  Failed to copy optional file {src.name}: {e}")

            if copied_count == 0:
                print("  ❌ No template files were copied")  # noqa: T201
                return False

            self._ensure_cursor_rule_aliases()
            self._log(f"Copied {copied_count} configuration files and project files")
            return True
        except Exception as e:
            print(f"  ❌ Failed to copy IDE templates: {e}")  # noqa: T201
            import traceback

            traceback.print_exc()
            return False
