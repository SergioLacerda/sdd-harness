"""
PHASE 3: Governance Orchestrator
End-to-end orchestration of PHASE 1 (Pipeline) + PHASE 2 (Compiler)

Coordinates:
1. PHASE 1: Read core/ → Generate governance-core.json + governance-client.json
2. PHASE 2: Read JSONs → Generate msgpack files + metadata

This enables end-to-end validation of the complete compilation flow.
"""

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from sdd_compiler.governance_compiler import GovernanceCompiler
from sdd_core.governance.spec_bootstrapper import SourceSpecBootstrapper
from sdd_core.utils.environment import get_sdd_paths, resolve_profile
from sdd_integration.builders.governance.pipeline_builder import PipelineBuilder

logger = logging.getLogger(__name__)


class Phase1Result(TypedDict, total=False):
    """Phase1Result."""

    governance_core: dict[str, Any]
    governance_client: dict[str, Any]
    core_fingerprint: str
    client_fingerprint: str
    core_item_count: int
    client_item_count: int
    core_json: str
    client_json: str
    success: bool
    error: str


class Phase2Result(TypedDict, total=False):
    """Phase2Result."""

    core_msgpack_file: str
    client_msgpack_file: str
    core_fingerprint_salt: str
    client_fingerprint: str
    success: bool
    error: str


class PipelineResult(TypedDict):
    """PipelineResult."""

    full_pipeline_success: bool
    phase_1: Phase1Result
    phase_2: Phase2Result
    validated: bool


class GovernanceOrchestrator:
    """Orchestrates complete governance compilation pipeline (PHASE 1 + PHASE 2)"""

    def __init__(
        self,
        repo_root: str | None = None,
        spec_path: str | None = None,
        compiled_dir: str | None = None,
        emit: Callable[[str], None] | None = None,
        profile: str | None = None,
    ):
        """
        Initialize orchestrator with configurable paths to avoid hardcoded production dependencies.

        Args:
            repo_root: The root of the repository.
            spec_path: Override for the governance source files directory.
            compiled_dir: Override for the compiled artifacts directory.
            profile: Active profile override ("master" | "client"). When None,
                     resolved from .sdd/profile or SDD_PROFILE env var.
        """
        paths = get_sdd_paths()
        root_path = Path(repo_root) if repo_root is not None else paths["root"]
        self.repo_root = root_path

        self.spec = Path(spec_path) if spec_path else paths["source_spec"]

        if compiled_dir:
            self.compiled_dir = Path(compiled_dir)
            self.build_dir = paths["master_build"]
        else:
            active_profile = profile or self._resolve_active_profile(root_path)
            if active_profile == "master":
                self.compiled_dir = paths["master_compiled"]
                self.build_dir = paths["master_build"]
            else:
                self.compiled_dir = paths["client_compiled"]
                self.build_dir = paths["client_build"]

        # Ensure directories exist
        self.compiled_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._emit = emit

        # Delegate spec bootstrapping to dedicated class
        self._spec_bootstrapper = SourceSpecBootstrapper(
            self.spec, self.repo_root, emit
        )

    @staticmethod
    def _resolve_active_profile(root: Path) -> str:
        """Resolve active profile type, defaulting to 'master' on any error."""
        try:
            return resolve_profile(root=root).type
        except Exception:
            return "master"

    def _out(self, message: str, *, level: int = logging.INFO) -> None:
        """Emit execution status via logger and optional presenter callback."""
        logger.log(level, message)
        if self._emit is not None:
            self._emit(message)

    def run_full_pipeline(self) -> PipelineResult:
        """
        Run complete end-to-end pipeline

        Returns:
            Dictionary with results from both phases
        """
        self._out("🚀 Starting governance compilation pipeline...")

        # PHASE 1: Pipeline
        self._out("📝 PHASE 1: Building governance pipeline...")
        phase1_result = self._run_phase_1()
        if not phase1_result.get("success", False):
            self._out("❌ PHASE 1 failed", level=logging.ERROR)
            return {
                "full_pipeline_success": False,
                "phase_1": phase1_result,
                "phase_2": {},
                "validated": False,
            }

        self._out("✅ PHASE 1 complete:")
        self._out(f"   - Core items: {phase1_result['core_item_count']}")
        self._out(f"   - Client items: {phase1_result['client_item_count']}")
        self._out(f"   - Core fingerprint: {phase1_result['core_fingerprint'][:16]}...")

        # PHASE 2: Compiler
        self._out("🔨 PHASE 2: Compiling to msgpack...")
        phase2_result = self._run_phase_2()
        if not phase2_result.get("success", False):
            self._out("❌ PHASE 2 failed", level=logging.ERROR)
            return {
                "full_pipeline_success": False,
                "phase_1": phase1_result,
                "phase_2": phase2_result,
                "validated": False,
            }

        self._out("✅ PHASE 2 complete:")
        self._out(f"   - Core msgpack: {Path(phase2_result['core_msgpack_file']).name}")
        self._out(
            f"   - Client msgpack: {Path(phase2_result['client_msgpack_file']).name}"
        )

        # Combine results
        combined_result: PipelineResult = {
            "phase_1": phase1_result,
            "phase_2": phase2_result,
            "full_pipeline_success": False,
            "validated": False,
        }

        # Run validations
        self._out("✔️ Validating complete pipeline...")
        validated = self._validate_full_pipeline(combined_result)
        combined_result["validated"] = validated
        combined_result["full_pipeline_success"] = validated

        if validated:
            self._out("✅ All validations passed")
        else:
            self._out("❌ Validation failed", level=logging.ERROR)

        return combined_result

    def _run_phase_1(self) -> Phase1Result:
        """
        Run PHASE 1: Pipeline

        Returns:
            Result dictionary from pipeline
        """
        try:
            self._spec_bootstrapper.bootstrap()
            spec_mandates_path = self.repo_root / ".sdd" / "spec" / "mandates.json"
            builder = PipelineBuilder(
                str(self.spec),
                spec_mandates_path=spec_mandates_path
                if spec_mandates_path.exists()
                else None,
            )
            result = builder.build()

            # Save intermediate JSON outputs to build directory
            builder.save_outputs(str(self.build_dir))

            return {
                "governance_core": result["governance_core"],
                "governance_client": result["governance_client"],
                "core_fingerprint": result["governance_core"]["fingerprint"],
                "client_fingerprint": result["governance_client"]["fingerprint"],
                "core_item_count": len(result["core_items"]),
                "client_item_count": len(result["client_items"]),
                "core_json": str(self.build_dir / "governance-core.json"),
                "client_json": str(self.build_dir / "governance-client.json"),
                "success": True,
            }
        except Exception as e:
            self._out(f"❌ PHASE 1 error: {e}", level=logging.ERROR)
            return {"success": False, "error": str(e)}

    def _run_phase_2(self) -> Phase2Result:  # noqa: C901
        """
        Run PHASE 2: Compiler

        Returns:
            Result dictionary from sdd_compiler
        """
        try:
            # Compiler reads from build_dir (JSONs) and outputs to compiled_dir (msgpacks)
            compiler = GovernanceCompiler(str(self.build_dir))
            result = compiler.compile(str(self.compiled_dir))

            # Validate in the output directory
            if not compiler.validate_compilation(str(self.compiled_dir)):
                self._out("❌ Compilation validation failed", level=logging.ERROR)
                return {"success": False, "error": "Compilation validation failed"}

            # Copy JSON source files to compiled_dir so downstream consumers
            # can find governance-core.json / governance-client.json there.
            import shutil

            for json_file in ("governance-core.json", "governance-client.json"):
                src = self.build_dir / json_file
                dst = self.compiled_dir / json_file
                if src.exists():
                    shutil.copy2(src, dst)

            # Copy metadata artifacts from audit/ to compiled_dir root for consistency
            # (ensures compiled_dir/metadata-*.json matches audit/metadata-*.json)
            audit_dir = self.compiled_dir / "audit"
            if audit_dir.exists():
                for metadata_file in (
                    "metadata-core.json",
                    "metadata-client-template.json",
                ):
                    src = audit_dir / metadata_file
                    dst = self.compiled_dir / metadata_file
                    if src.exists():
                        shutil.copy2(src, dst)

            # Publish canonical artifacts to `.sdd/compiled` authority directory.
            # `/generated/*` remains legacy/derived output only.
            sdd_compiled_dir = self.repo_root / ".sdd" / "compiled"
            sdd_compiled_dir.mkdir(parents=True, exist_ok=True)
            sdd_audit_dir = sdd_compiled_dir / "audit"
            sdd_audit_dir.mkdir(parents=True, exist_ok=True)

            publish_files = [
                "governance-core.compiled.msgpack",
                "governance-client-template.compiled.msgpack",
                "governance-core.json",
                "governance-client.json",
                "metadata-core.json",
                "metadata-client-template.json",
            ]
            for filename in publish_files:
                src = self.compiled_dir / filename
                if src.exists():
                    shutil.copy2(src, sdd_compiled_dir / filename)
            for filename in (
                "metadata-core.json",
                "metadata-client-template.json",
                "governance-core.json",
                "governance-client.json",
            ):
                src = audit_dir / filename
                if src.exists():
                    shutil.copy2(src, sdd_audit_dir / filename)

            manifest_src = audit_dir / "DEPLOYMENT_MANIFEST.json"
            if manifest_src.exists():
                shutil.copy2(manifest_src, sdd_audit_dir / "DEPLOYMENT_MANIFEST.json")

            phase2_result: Phase2Result = {"success": True}
            core_msgpack_file = result.get("core_msgpack_file")
            client_msgpack_file = result.get("client_msgpack_file")
            core_fingerprint_salt = result.get("core_fingerprint_salt")
            client_fingerprint = result.get("client_fingerprint")
            if isinstance(core_msgpack_file, str):
                phase2_result["core_msgpack_file"] = core_msgpack_file
            if isinstance(client_msgpack_file, str):
                phase2_result["client_msgpack_file"] = client_msgpack_file
            if isinstance(core_fingerprint_salt, str):
                phase2_result["core_fingerprint_salt"] = core_fingerprint_salt
            if isinstance(client_fingerprint, str):
                phase2_result["client_fingerprint"] = client_fingerprint
            return phase2_result
        except Exception as e:
            self._out(f"❌ PHASE 2 error: {e}", level=logging.ERROR)
            return {"success": False, "error": str(e)}

    def _validate_full_pipeline(self, combined_result: PipelineResult) -> bool:
        """Validate that complete pipeline is working correctly"""
        p1 = combined_result.get("phase_1", {})
        p2 = combined_result.get("phase_2", {})

        # Phase 2 currently returns client_fingerprint/core_fingerprint_salt.
        # Keep fallback to legacy key names for compatibility.
        phase2_client_fp = p2.get("client_fingerprint") or p2.get("fingerprint")
        phase2_core_salt = p2.get("core_fingerprint_salt") or p2.get(
            "fingerprint_core_salt"
        )

        checks = [
            ("Phase 1 success", p1.get("success") is True),
            ("Phase 2 success", p2.get("success") is True),
            (
                "Client fingerprint preserved",
                p1.get("client_fingerprint") == phase2_client_fp,
            ),
            (
                "Core fingerprint used as salt",
                p1.get("core_fingerprint") == phase2_core_salt,
            ),
            (
                "Fingerprints different",
                p1.get("core_fingerprint") != p1.get("client_fingerprint"),
            ),
            ("Core items > 0", p1.get("core_item_count", 0) > 0),
            # Empty guideline/client sets are valid when docs-meta intentionally
            # contains no guideline definitions yet.
            ("Client items count valid", p1.get("client_item_count", 0) >= 0),
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            self._out(f"   {status} {check_name}")
            if not result:
                all_passed = False

        return all_passed

    def get_deployment_summary(self) -> dict[str, Any]:
        """Get summary ready for deployment"""
        return {
            "status": "ready_for_deployment",
            "artifacts": {
                "core_msgpack": str(
                    self.compiled_dir / "governance-core.compiled.msgpack"
                ),
                "client_msgpack": str(
                    self.compiled_dir / "governance-client-template.compiled.msgpack"
                ),
                "core_metadata": str(
                    self.compiled_dir / "audit" / "metadata-core.json"
                ),
                "client_metadata": str(
                    self.compiled_dir / "audit" / "metadata-client-template.json"
                ),
            },
            "deployment_location": "compiled/",
            "next_step": "PHASE 4: Deploy to runtime/",
        }


if __name__ == "__main__":
    orchestrator = GovernanceOrchestrator()
    result = orchestrator.run_full_pipeline()

    if result and result.get("full_pipeline_success"):
        print()  # noqa: T201
        print("=" * 60)  # noqa: T201
        print("🎉 PHASE 1 + PHASE 2 COMPLETE")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print()  # noqa: T201

        summary = orchestrator.get_deployment_summary()
        print("📦 Deployment Summary:")  # noqa: T201
        for key, value in summary.items():
            if key == "artifacts":
                print(f"  {key}:")  # noqa: T201
                for artifact_name, artifact_path in value.items():
                    print(f"    - {artifact_name}: {Path(artifact_path).name}")  # noqa: T201
            elif key != "deployment_location":
                print(f"  {key}: {value}")  # noqa: T201

        print()  # noqa: T201
        print(f"✅ Ready for: {summary['next_step']}")  # noqa: T201
    else:
        print()  # noqa: T201
        print("❌ Pipeline failed")  # noqa: T201
        sys.exit(1)
