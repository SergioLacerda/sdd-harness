"""
IdeTemplateDeployer — Phase 6 step: copy IDE/CI templates and inject bootstrap metadata.
"""

import os
import shutil
from pathlib import Path
from typing import Any

from sdd_core.utils.log import get_logger

logger = get_logger(__name__)


class IdeTemplateDeployer:
    """Copy IDE config templates from sdd_integration and inject governance metadata."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        verbose: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.output_base = output_base
        self.verbose = verbose

        # Safeguard: Never mutate the project root during tests
        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                repo_root_abs = self.repo_root.resolve()
                output_base_abs = self.output_base.resolve()
                if output_base_abs == repo_root_abs:
                    should_block = True
            except (OSError, ValueError):
                # Fallback if resolve fails — can't reliably detect root, so we continue
                pass

            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"  ❌ {msg}")  # noqa: T201
                raise PermissionError(msg)

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    @property
    def _template_base(self) -> Path:
        return (
            self.repo_root
            / "packages"
            / "features"
            / "sdd_integration"
            / "src"
            / "sdd_integration"
            / "templates"
        )

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
                print(f"  ❌ Template base not found: {template_base}")  # noqa: T201
                return False

            file_mappings: list[tuple[Path, Path]] = [
                (
                    template_base / ".pre-commit-config.yaml",
                    self.output_base / ".pre-commit-config.yaml",
                ),
                (
                    template_base / ".github" / "setup-precommit-hook.sh",
                    self.output_base / ".github" / "setup-precommit-hook.sh",
                ),
            ]

            copied_count = 0
            for src, dst in file_mappings:
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if src.exists():
                        shutil.copy2(src, dst)
                        if src.suffix == ".sh":
                            os.chmod(dst, 0o700)
                        self._log(f"Copied {src.name}")
                        copied_count += 1
                    else:
                        self._log(f"⚠️  Template not found: {src.name}")
                except Exception as e:
                    self._log(f"⚠️  Failed to copy {src.name}: {e}")

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
                        self._log(f"Copied {src.name}/ directory")
                        copied_count += 1
                    else:
                        self._log(f"⚠️  Template directory not found: {src.name}/")
                except Exception as e:
                    self._log(f"⚠️  Failed to copy {src.name}/: {e}")

            tests_src = template_base / "tests"
            if tests_src.exists() and tests_src.is_dir():
                tests_dst = self.output_base / "tests"
                try:
                    shutil.copytree(tests_src, tests_dst, dirs_exist_ok=True)
                    self._log("Copied tests/ directory")
                    copied_count += 1
                except Exception as e:
                    self._log(f"⚠️  Failed to copy tests/: {e}")

            if copied_count == 0:
                print("  ❌ No template files were copied")  # noqa: T201
                return False

            self._log(f"Copied {copied_count} configuration files and project files")
            return True
        except Exception as e:
            print(f"  ❌ Failed to copy IDE templates: {e}")  # noqa: T201
            import traceback

            traceback.print_exc()
            return False

    def inject_bootstrap_metadata(
        self,
        fingerprint: str,
        generated_at: str,
        mandates_count: int,
    ) -> None:
        """Append governance fingerprint block to generated bootstrap markdown files."""
        # Safeguard: Never mutate the project root during tests
        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                repo_root_abs = self.repo_root.resolve()
                output_base_abs = self.output_base.resolve()
                if output_base_abs == repo_root_abs:
                    should_block = True
            except (OSError, ValueError):
                # Fallback if resolve fails — can't reliably detect root, so we continue
                pass

            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"  ❌ {msg}")  # noqa: T201
                raise PermissionError(msg)

        footer = (
            "\n\n<!-- sdd:bootstrap-metadata\n"
            f"governance_fingerprint : {fingerprint}\n"
            f"mandates_count         : {mandates_count}\n"
            f"generated_at           : {generated_at}\n"
            "load_compiled_from     : .sdd/source\n"
            "-->"
        )

        bootstrap_files = [
            self.output_base / ".github" / "copilot-instructions.md",
            self.output_base / ".vscode" / "ai-rules.md",
            self.output_base / ".claude" / "claude-instructions.md",
            # .gemini/gemini-instructions.md excluded: ai_seeds.py overwrites it
            # in the same wizard run, so injecting here would be lost.
            self.output_base / ".antigravity" / "antigravity-instructions.md",
            self.output_base / ".ia" / "ia-instructions.md",
            self.output_base / ".ai" / "ai-instructions.md",
        ]

        injected = 0
        for path in bootstrap_files:
            try:
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8")
                if "sdd:bootstrap-metadata" in content:
                    continue
                path.write_text(content + footer, encoding="utf-8")
                injected += 1
            except Exception as e:
                self._log(f"⚠️  Failed to inject metadata into {path.name}: {e}")

        if injected:
            self._log(f"Injected governance metadata into {injected} bootstrap files")

    def populate_ide_rules(
        self,
        mandates: list[dict[str, Any]],
        fingerprint: str,
    ) -> None:
        """Populate IDE rule files with governance fingerprint and mandate count."""
        ide_rule_files = [
            self.output_base / ".vscode" / "ai-rules.md",
            self.output_base / ".cursor" / "rules" / "sdd-governance.mdc",
        ]
        for rules_file in ide_rule_files:
            if not rules_file.exists():
                continue
            try:
                content = rules_file.read_text(encoding="utf-8")
                content = content.replace("{FINGERPRINT}", fingerprint)
                content = content.replace("{MANDATES_COUNT}", str(len(mandates)))
                rules_file.write_text(content, encoding="utf-8")
                self._log(
                    f"Populated {rules_file.name} with fingerprint + mandate count"
                )
            except Exception as e:
                self._log(f"⚠️  Failed to populate {rules_file.name}: {e}")
