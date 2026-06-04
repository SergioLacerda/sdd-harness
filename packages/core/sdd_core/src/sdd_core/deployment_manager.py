"""
PHASE 4: Deployment Manager
Deploy compiled governance files to runtime/compiled/

Workflow:
1. Validate compiled files exist and are valid
2. Create runtime/compiled/ directory structure
3. Copy msgpack files to runtime location
4. Copy metadata files to runtime location
5. Create deployment checklist
6. Generate deployment manifest
7. Provide git commands for commit + tag
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from sdd_core.artifact_bootstrapper import (
    GOVERNANCE_ARTIFACTS,
)
from sdd_core.artifact_bootstrapper import (
    ArtifactBootstrapper as _ArtifactBootstrapper,
)
from sdd_core.deployment_file_system import DeploymentFileSystem
from sdd_core.deployment_reporter import DeploymentReporter
from sdd_core.deployment_validator import DeploymentValidator
from sdd_core.utils.environment import get_sdd_paths


class DeploymentResult(TypedDict):
    """DeploymentResult."""

    success: bool
    deployed_files: dict[str, str]
    deployment_location: str
    checklist: dict[str, bool]
    manifest: dict[str, Any]
    next_steps: list[str]


class DeploymentManager:
    """Manages deployment of compiled governance files to runtime"""

    def __init__(
        self,
        repo_root: str | None = None,
        workspace_root: str | None = None,
        emit: Callable[[str], None] | None = None,
    ):
        """Initialize deployment manager"""
        root_path = Path(repo_root).resolve() if repo_root is not None else None
        workspace_path = (
            Path(workspace_root).resolve() if workspace_root is not None else None
        )
        paths = get_sdd_paths(repo_root=root_path, workspace_root=workspace_path)

        self.repo_root = root_path or paths.get("repo_root", paths["root"])
        self.workspace_root = workspace_path or paths.get(
            "workspace_root", paths["root"]
        )
        self.paths = paths

        # Deployment target: Client Runtime (.sdd/compiled/)
        self.runtime_compiled = self.workspace_root / ".sdd" / "compiled"
        self.runtime_audit = self.runtime_compiled / "audit"

        # Source of truth for deployment: client/compiled only.
        self.compiled_dir = paths["client_compiled"]
        self.master_compiled_dir = paths["master_compiled"]
        self._emit = emit

        # Delegate artifact bootstrapping to dedicated class
        self._bootstrapper = _ArtifactBootstrapper(
            self.compiled_dir,
            self.master_compiled_dir,
            self.workspace_root,
            self._metadata_source,
            emit,
        )

    def _out(self, message: str) -> None:
        if self._emit is not None:
            self._emit(message)

    def _path_str(self, path: Path) -> str:
        """Return normalized POSIX-style path for cross-platform output assertions."""
        return path.as_posix()

    def _metadata_source(self, filename: str) -> Path:
        """Resolve metadata from compiled/audit first, then compiled root."""
        preferred = self.compiled_dir / "audit" / filename
        if preferred.exists():
            return preferred
        return self.compiled_dir / filename

    def deploy(self) -> DeploymentResult:
        """
        Execute complete deployment

        Returns:
            Dictionary with deployment results
        """
        self._out("🚀 Starting PHASE 4: Deployment...")

        # Step 1: Validate compiled files
        self._out("📋 Step 1: Validating compiled files...")
        if not self._validate_compiled_files():
            self._out("❌ Validation failed")
            return self._failed_result()
        self._out("✅ Validation passed")

        # Step 2: Create runtime directory structure
        self._out("📁 Step 2: Creating runtime directory structure...")
        self._create_runtime_structure()
        self._out("✅ Runtime structure created")

        # Step 3: Copy files
        self._out("📦 Step 3: Copying compiled files to runtime...")
        copy_result = self._copy_files_transactional()
        if not copy_result:
            self._out("❌ Copy failed")
            return self._failed_result()
        self._out("✅ Files copied successfully")

        # Step 4: Verify deployment
        self._out("✔️ Step 4: Verifying deployment...")
        if not self._verify_deployment():
            self._out("❌ Verification failed")
            return self._failed_result()
        self._out("✅ Deployment verified")

        # Step 5: Generate checklist and manifest
        checklist = self._generate_checklist()
        manifest = self._generate_manifest()
        self._cleanup_legacy_manifests()

        return {
            "success": True,
            "deployed_files": copy_result,
            "deployment_location": self._path_str(self.runtime_compiled),
            "checklist": checklist,
            "manifest": manifest,
            "next_steps": self._get_next_steps(),
        }

    def _failed_result(self) -> DeploymentResult:
        return {
            "success": False,
            "deployed_files": {},
            "deployment_location": self._path_str(self.runtime_compiled),
            "checklist": {},
            "manifest": {},
            "next_steps": [],
        }

    def _validate_compiled_files(self) -> bool:
        """Validate that all required compiled files exist"""
        return DeploymentValidator.validate_compiled_files(
            self.compiled_dir,
            GOVERNANCE_ARTIFACTS,
            self._metadata_source,
            self._bootstrapper,
            self._out,
        )

    def _create_runtime_structure(self) -> None:
        """Create runtime/compiled/ directory structure"""
        DeploymentFileSystem.create_runtime_structure(self.runtime_compiled, self._out)

    def _copy_files_transactional(self) -> dict[str, str]:
        """Copy files with rollback to last known good state on failure."""
        return DeploymentFileSystem.copy_files_transactional(
            self.compiled_dir,
            GOVERNANCE_ARTIFACTS,
            self._metadata_source,
            self.runtime_compiled,
            self.runtime_audit,
            self._out,
        )

    def _verify_deployment(self) -> bool:
        """Verify that deployment was successful"""
        return DeploymentValidator.verify_deployment(
            self.runtime_compiled, GOVERNANCE_ARTIFACTS, self._out
        )

    def _generate_checklist(self) -> dict[str, bool]:
        """Generate deployment checklist"""
        return DeploymentReporter.generate_checklist(
            self.runtime_compiled, self.runtime_audit, GOVERNANCE_ARTIFACTS
        )

    def _generate_manifest(self) -> dict[str, Any]:
        """Generate deployment manifest"""
        return DeploymentReporter.generate_manifest(
            self.runtime_compiled, self.runtime_audit, GOVERNANCE_ARTIFACTS
        )

    def _get_next_steps(self) -> list[str]:
        """Get next steps after deployment"""
        return DeploymentReporter.get_next_steps()

    def _cleanup_legacy_manifests(self) -> None:
        """Remove legacy manifest files replaced by .sdd/compiled/audit/."""
        DeploymentReporter.cleanup_legacy_manifests(
            self.repo_root, self.runtime_compiled
        )

    def get_deployment_status(self) -> dict[str, Any]:
        """Get current deployment status"""
        return DeploymentReporter.get_deployment_status(
            self.runtime_compiled, self.runtime_audit, GOVERNANCE_ARTIFACTS
        )


def main() -> None:
    """Run the deployment CLI entrypoint."""
    manager = DeploymentManager()
    result = manager.deploy()

    if result.get("success"):
        print()  # noqa: T201
        print("=" * 70)  # noqa: T201
        print("🎉 PHASE 4: DEPLOYMENT COMPLETE")  # noqa: T201
        print("=" * 70)  # noqa: T201
        print()  # noqa: T201

        print("📋 Deployment Checklist:")  # noqa: T201
        for check, status in result.get("checklist", {}).items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {check}")  # noqa: T201

        print()  # noqa: T201
        print("📦 Deployment Location:")  # noqa: T201
        print(f"  {result.get('deployment_location')}")  # noqa: T201

        print()  # noqa: T201
        print("📄 Artifacts Deployed:")  # noqa: T201
        for name, path in result.get("manifest", {}).get("artifacts", {}).items():
            print(f"  - {name}: {path}")  # noqa: T201

        print()  # noqa: T201
        print("🔗 Next Steps:")  # noqa: T201
        for step in result.get("next_steps", []):
            print(f"  {step}")  # noqa: T201

        print()  # noqa: T201
        status_value = result.get("manifest", {}).get("status")
        if isinstance(status_value, str):
            print(f"✅ Status: {status_value.upper()}")  # noqa: T201
        else:
            print("✅ Status: UNKNOWN")  # noqa: T201
    else:
        print()  # noqa: T201
        print("❌ Deployment failed")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    main()
