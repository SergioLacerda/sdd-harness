#!/usr/bin/env python
"""
SDD v3.0 Integration Pipeline: Compile & Deploy

Workflow:
  1. Read SOURCE (core/*.spec/*.dsl)
  2. Validate syntax
  3. Compile to MessagePack binary (.bin)
  4. Deploy to runtime/
  5. Generate metadata.json with audit trail

This bridges migration → compiler → runtime → wizard

Location: compiler/src/integrate.py (orchestration logic)
Entry point: python compiler/compiler.py (from repository root)
Usage: from sdd_compiler.src.integrate import SDDIntegrator
"""

import hashlib
import json
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from sdd_compiler.compile_state import CompileState
from sdd_core.utils.environment import get_sdd_paths
from sdd_core.utils.text_io import read_text_utf8, write_text_utf8


def _utc_now_iso_z() -> str:
    """Return current UTC timestamp as ISO 8601 with trailing Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SDDIntegrator:
    """Orchestrate complete SDD v3.0 integration pipeline"""

    def __init__(
        self,
        repo_root: Path | None = None,
        emitter: Callable[[str], None] | None = None,
    ):
        """Initialize integrator with repository root"""
        paths = get_sdd_paths()
        self.repo = repo_root or paths["root"]
        self.paths = paths

        # Use standardized paths from registry
        self.source_core = paths["source_spec"]
        self.compiler_pkg = paths["packages"] / "core" / "sdd_compiler"
        self.core_pkg = paths["packages"] / "core" / "sdd_core"
        self.runtime_compiled = paths["master_compiled"]
        self.runtime_audit = self.runtime_compiled / "audit"
        self.compiler_src = self.compiler_pkg / "src" / "sdd_compiler"

        # Initialize compile state for incremental compilation
        self.compile_state_file = self.runtime_compiled / ".compile-state.json"
        self.compile_state = CompileState(self.compile_state_file)

        # Metrics
        self.metrics: dict[str, Any] = {
            "source": {},
            "compilation": {},
            "deployment": {},
        }
        self._emitter = emitter or print

    def _emit(self, message: str) -> None:
        if self._emitter is not None:
            self._emitter(message)

    def _resolve_source_file(self, base_name: str, exts: tuple[str, ...]) -> Path:
        """Resolve source file from source_spec using compatible extensions.

        This avoids hardcoded concatenation bugs when source_spec may provide
        markdown (canonical-only) or legacy DSL files.
        """
        for ext in exts:
            candidate = self.source_core / f"{base_name}{ext}"
            if candidate.exists():
                return candidate
        expected = ", ".join(
            str(self.source_core / f"{base_name}{ext}") for ext in exts
        )
        raise FileNotFoundError(
            f"Missing source file for '{base_name}'. Searched: {expected}"
        )

    def validate_paths(self) -> bool:
        """Verify all required directories and files exist"""
        try:
            mandate_source = self._resolve_source_file("mandate", (".spec", ".md"))
            guidelines_source = self._resolve_source_file("guidelines", (".dsl", ".md"))
        except FileNotFoundError as exc:
            self._emit(f"❌ Missing required files:\n  ❌ {exc}")
            return False

        required = {
            "docs/spec/canonical/core/": self.source_core,
            "mandate source": mandate_source,
            "guidelines source": guidelines_source,
            "dsl_compiler.py": self.compiler_src / "dsl_compiler.py",
            "runtime_compiled/": self.runtime_compiled,
        }

        missing = []
        for name, path in required.items():
            if not path.exists():
                missing.append(f"  ❌ {name}")

        if missing:
            self._emit("❌ Missing required files:")
            self._emit("\n".join(missing))
            return False

        self._emit("✅ All paths validated")
        return True

    @staticmethod
    def _file_hash(path: Path, truncate: int = 8) -> str:
        """Calculate SHA256 hash of file (truncated)"""
        return hashlib.sha256(path.read_bytes()).hexdigest()[:truncate]

    @staticmethod
    def _count_items(text: str, pattern: str) -> int:
        """Count regex matches in text"""
        return len(re.findall(pattern, text))

    def check_incremental_compilation(self) -> dict[str, bool]:
        """Check if sources have changed and compilation is needed

        Returns:
            Dict with 'mandate' and 'guidelines' keys indicating if each needs recompilation
        """
        try:
            mandate_file = self._resolve_source_file("mandate", (".spec", ".md"))
            guidelines_file = self._resolve_source_file("guidelines", (".dsl", ".md"))

            mandate_changed = self.compile_state.source_changed("mandate", mandate_file)
            guidelines_changed = self.compile_state.source_changed(
                "guidelines", guidelines_file
            )

            # Check if artifacts exist
            mandate_artifact = (
                self.runtime_compiled / "governance-core.compiled.msgpack"
            )
            guidelines_artifact = (
                self.runtime_compiled / "governance-client-template.compiled.msgpack"
            )

            return {
                "mandate": mandate_changed or not mandate_artifact.exists(),
                "guidelines": guidelines_changed or not guidelines_artifact.exists(),
            }

        except Exception as e:
            self._emit(f"  ⚠️  Could not check incremental state: {e}")
            return {"mandate": True, "guidelines": True}

    def analyze_sources(self) -> bool:
        """Analyze and validate source files"""
        self._emit("\n📊 Analyzing source files")

        try:
            mandate_file = self._resolve_source_file("mandate", (".spec", ".md"))
            guidelines_file = self._resolve_source_file("guidelines", (".dsl", ".md"))

            mandate_text = mandate_file.read_text(encoding="utf-8")
            guidelines_text = guidelines_file.read_text(encoding="utf-8")

            # Count items
            mandate_count = self._count_items(mandate_text, r"\[[MP]\d{3}\]")
            guideline_count = self._count_items(guidelines_text, r"guideline\s+G\d+")

            # Calculate hashes
            mandate_hash = self._file_hash(mandate_file)
            guidelines_hash = self._file_hash(guidelines_file)

            # Store metrics
            self.metrics["source"] = {
                "mandate_spec": {
                    "size": len(mandate_text),
                    "hash": mandate_hash,
                    "items": mandate_count,
                },
                "guidelines_dsl": {
                    "size": len(guidelines_text),
                    "hash": guidelines_hash,
                    "items": guideline_count,
                },
            }

            self._emit(
                f"  ✅ mandate.spec: {mandate_count} mandates ({len(mandate_text):,} bytes)"
            )
            self._emit(
                f"  ✅ guidelines.dsl: {guideline_count} guidelines ({len(guidelines_text):,} bytes)"
            )

            return True

        except Exception as e:
            self._emit(f"  ❌ Error analyzing sources: {e}")
            return False

    def compile_mandate(self, force: bool = False) -> bool:
        """Compile mandate.spec to binary

        Args:
            force: Force recompilation even if sources unchanged

        Returns:
            True if compilation succeeded or was skipped (cache hit)
        """
        input_file = self._resolve_source_file("mandate", (".spec", ".md"))
        output_file = self.runtime_compiled / "governance-core.compiled.msgpack"

        # Check for incremental compilation
        if not force:
            incremental = self.check_incremental_compilation()
            if not incremental["mandate"]:
                self._emit("\n📝 Compiling mandate.spec")
                self._emit(
                    f"  ⚡ Cache hit: mandate unchanged since {self.compile_state.get_last_compiled_time()}"
                )
                self.metrics["compilation"]["mandate"] = {
                    "status": "cached",
                    "output_size": output_file.stat().st_size
                    if output_file.exists()
                    else 0,
                    "format": "binary",
                }
                return True

        self._emit("\n📝 Compiling mandate.spec")

        script = self.compiler_src / "dsl_compiler.py"

        cmd = [
            sys.executable,
            str(script),
            str(input_file),
            str(output_file),
            "--format",
            "msgpack",
        ]

        try:
            from sdd_core.utils.process import SafeProcessRunner

            runner = SafeProcessRunner()
            result = runner.run(cmd, capture_output=True, timeout=15)

            if result.success:
                if output_file.exists():
                    size = output_file.stat().st_size
                    # Update compile state
                    self.compile_state.update_source("mandate", input_file)
                    self.compile_state.update_artifact("mandate_bin", output_file)
                    self.compile_state.save()

                    self.metrics["compilation"]["mandate"] = {
                        "status": "success",
                        "output_size": size,
                        "format": "binary",
                    }
                    self._emit(f"  ✅ mandate.bin ({size:,} bytes)")
                    return True
                else:
                    self._emit("  ⚠️  Binary not found, trying JSON fallback...")
                    return False
            else:
                self._emit("  ❌ Compilation failed:")
                self._emit(result.stderr)
                self.metrics["compilation"]["mandate"] = {
                    "status": "failed",
                    "error": result.stderr,
                }
                return False

        except Exception as e:
            self._emit(f"  ❌ Error: {e}")
            self.metrics["compilation"]["mandate"] = {
                "status": "error",
                "error": str(e),
            }
            return False

    def compile_guidelines(self, force: bool = False) -> bool:
        """Compile guidelines.dsl to binary

        Args:
            force: Force recompilation even if sources unchanged

        Returns:
            True if compilation succeeded or was skipped (cache hit)
        """
        input_file = self._resolve_source_file("guidelines", (".dsl", ".md"))
        output_file = (
            self.runtime_compiled / "governance-client-template.compiled.msgpack"
        )

        # Check for incremental compilation
        if not force:
            incremental = self.check_incremental_compilation()
            if not incremental["guidelines"]:
                self._emit("\n📝 Compiling guidelines.dsl")
                self._emit(
                    f"  ⚡ Cache hit: guidelines unchanged since {self.compile_state.get_last_compiled_time()}"
                )
                self.metrics["compilation"]["guidelines"] = {
                    "status": "cached",
                    "output_size": output_file.stat().st_size
                    if output_file.exists()
                    else 0,
                    "format": "binary",
                }
                return True

        self._emit("\n📝 Compiling guidelines.dsl")

        script = self.compiler_src / "dsl_compiler.py"

        cmd = [
            sys.executable,
            str(script),
            str(input_file),
            str(output_file),
            "--format",
            "msgpack",
        ]

        try:
            from sdd_core.utils.process import SafeProcessRunner

            runner = SafeProcessRunner()
            result = runner.run(cmd, capture_output=True, timeout=15)

            if result.success:
                if output_file.exists():
                    size = output_file.stat().st_size
                    # Update compile state
                    self.compile_state.update_source("guidelines", input_file)
                    self.compile_state.update_artifact("guidelines_bin", output_file)
                    self.compile_state.save()

                    self.metrics["compilation"]["guidelines"] = {
                        "status": "success",
                        "output_size": size,
                        "format": "binary",
                    }
                    self._emit(f"  ✅ guidelines.bin ({size:,} bytes)")
                    return True
                else:
                    self._emit("  ⚠️  Binary not found, trying JSON fallback...")
                    return False
            else:
                self._emit("  ❌ Compilation failed:")
                self._emit(result.stderr)
                self.metrics["compilation"]["guidelines"] = {
                    "status": "failed",
                    "error": result.stderr,
                }
                return False

        except Exception as e:
            self._emit(f"  ❌ Error: {e}")
            self.metrics["compilation"]["guidelines"] = {
                "status": "error",
                "error": str(e),
            }
            return False

    def generate_metadata(self) -> bool:
        """Generate metadata.json with audit trail and metrics"""
        self._emit("\n📊 Generating metadata.json")

        try:
            mandate_hash = self._file_hash(
                self._resolve_source_file("mandate", (".spec", ".md"))
            )
            guidelines_hash = self._file_hash(
                self._resolve_source_file("guidelines", (".dsl", ".md"))
            )

            # Count items from cached metrics
            source_metrics = self.metrics.get("source", {})
            mandate_count = source_metrics.get("mandate_spec", {}).get("items", 0)
            guideline_count = source_metrics.get("guidelines_dsl", {}).get("items", 0)

            # Check for artifacts
            mandate_exists = (self.runtime_compiled / "mandate.bin").exists()
            guidelines_exists = (self.runtime_compiled / "guidelines.bin").exists()

            metadata: dict[str, Any] = {
                "version": "3.0.0",
                "compiled_at": _utc_now_iso_z(),
                "source": {
                    "mandate_spec_hash": mandate_hash,
                    "guidelines_dsl_hash": guidelines_hash,
                },
                "statistics": {
                    "mandates": mandate_count,
                    "guidelines": guideline_count,
                },
                "artifacts": {
                    "mandate_bin": mandate_exists,
                    "guidelines_bin": guidelines_exists,
                },
                "audit_trail": [
                    {
                        "timestamp": _utc_now_iso_z(),
                        "action": "integration",
                        "status": "completed",
                    },
                ],
            }

            self.runtime_audit.mkdir(parents=True, exist_ok=True)
            metadata_file = self.runtime_audit / "metadata-core.json"
            write_text_utf8(metadata_file, json.dumps(metadata, indent=2))

            # Duplicate for client template to satisfy loader/tests
            metadata["type"] = "client-template"
            metadata["customizable"] = True
            metadata_client_file = self.runtime_audit / "metadata-client-template.json"
            write_text_utf8(metadata_client_file, json.dumps(metadata, indent=2))

            # Backward compatibility with legacy root metadata readers.
            write_text_utf8(
                self.runtime_compiled / "metadata-core.json",
                read_text_utf8(metadata_file),
            )
            write_text_utf8(
                self.runtime_compiled / "metadata-client-template.json",
                read_text_utf8(metadata_client_file),
            )

            self.metrics["deployment"]["metadata"] = {
                "status": "created",
                "size": metadata_file.stat().st_size,
            }

            self._emit(
                f"  ✅ metadata-core.json ({metadata_file.stat().st_size} bytes)"
            )
            self._emit(
                f"  ✅ metadata-client-template.json ({metadata_client_file.stat().st_size} bytes)"
            )
            self._emit(f"     • {mandate_count} mandates, {guideline_count} guidelines")

            return True

        except Exception as e:
            self._emit(f"  ❌ Error generating metadata: {e}")
            return False

    def verify_deployment(self) -> "DeploymentVerification":
        """Verify all artifacts deployed successfully"""
        self._emit("\n" + "=" * 60)
        self._emit("📦 Deployment Verification")
        self._emit("=" * 60)

        artifacts = {
            "governance-core.compiled.msgpack": self.runtime_compiled
            / "governance-core.compiled.msgpack",
            "governance-client-template.compiled.msgpack": self.runtime_compiled
            / "governance-client-template.compiled.msgpack",
            "audit/metadata-core.json": self.runtime_audit / "metadata-core.json",
        }

        manifest = []
        for name, path in artifacts.items():
            if path.exists():
                size = path.stat().st_size
                manifest.append(f"  ✅ {name:25s} {size:>10,} bytes")
            else:
                manifest.append(f"  ❌ {name:25s} NOT FOUND")

        self._emit("\nArtifacts in runtime/:")
        for line in manifest:
            self._emit(line)

        # Check if any critical files are missing
        critical = [
            self.runtime_compiled / "governance-core.compiled.msgpack",
            self.runtime_compiled / "governance-client-template.compiled.msgpack",
        ]

        all_present = all(p.exists() for p in critical)

        return {
            "all_present": all_present,
            "manifest": manifest,
            "critical_count": sum(1 for p in critical if p.exists()),
            "critical_required": len(critical),
        }

    def run_detailed(self) -> "IntegrationRunResult":
        """Execute complete compilation pipeline and return structured result."""
        self._emit("=" * 60)
        self._emit("🚀 SDD v3.0 Compiler - Integration Pipeline")
        self._emit("=" * 60)

        # Validate
        if not self.validate_paths():
            return {
                "ok": False,
                "phase": "validate_paths",
                "verification": None,
                "metrics": self.metrics,
            }

        # Analyze sources
        if not self.analyze_sources():
            return {
                "ok": False,
                "phase": "analyze_sources",
                "verification": None,
                "metrics": self.metrics,
            }

        # Compile
        mandate_ok = self.compile_mandate()
        guidelines_ok = self.compile_guidelines()

        if not (mandate_ok and guidelines_ok):
            self._emit("\n⚠️  One or more compilations failed!")
            return {
                "ok": False,
                "phase": "compile",
                "verification": None,
                "metrics": self.metrics,
            }

        # Generate metadata
        if not self.generate_metadata():
            return {
                "ok": False,
                "phase": "metadata",
                "verification": None,
                "metrics": self.metrics,
            }

        # Verify deployment
        verification = self.verify_deployment()

        if not verification["all_present"]:
            self._emit("\n❌ Critical artifacts missing!")
            return {
                "ok": False,
                "phase": "verify_deployment",
                "verification": verification,
                "metrics": self.metrics,
            }

        # Success
        self._emit("✅ Compilation complete!")
        self._emit("   Ready for wizard: python wizard/src/wizard.py")
        self._emit("   Or import: from sdd_compiler.src.integrate import SDDIntegrator")
        return {
            "ok": True,
            "phase": "completed",
            "verification": verification,
            "metrics": self.metrics,
        }

    def run(self) -> bool:
        """Backward-compatible pipeline execution."""
        return self.run_detailed()["ok"]


class DeploymentVerification(TypedDict):
    """DeploymentVerification."""

    all_present: bool
    manifest: list[str]
    critical_count: int
    critical_required: int


class IntegrationRunResult(TypedDict):
    """IntegrationRunResult."""

    ok: bool
    phase: str
    verification: DeploymentVerification | None
    metrics: dict[str, Any]


if __name__ == "__main__":
    # Allow running as main module
    integrator = SDDIntegrator(Path.cwd())
    success = integrator.run()
    sys.exit(0 if success else 1)
