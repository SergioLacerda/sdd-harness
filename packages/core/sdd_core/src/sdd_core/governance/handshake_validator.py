"""Handshake validation engine (4-layer protocol)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str
    layer: str


class GovernanceValidator:
    """Executes 4-layer validation protocol."""

    def __init__(self, project_root: Path):
        """Initialize validator."""
        self.project_root = project_root

    def layer_1_discovery(self) -> tuple[str, list[ValidationResult]]:
        """
        Layer 1: DISCOVERY — Is governance present?

        Checks for .sdd/ directory (primary marker) and governance artifacts.
        """
        results = []

        # Primary: check .sdd/ directory (replaces .spec.config)
        sdd_dir = self.project_root / ".sdd"
        sdd_exists = sdd_dir.exists()
        results.append(
            ValidationResult(
                name=".sdd/ directory",
                passed=sdd_exists,
                message=(
                    f"Found at {sdd_dir}"
                    if sdd_exists
                    else "Not initialized — run 'sdd init'"
                ),
                layer="DISCOVERY",
            )
        )

        # Check .sdd/profile exists
        profile_path = sdd_dir / "profile"
        profile_exists = profile_path.exists()
        results.append(
            ValidationResult(
                name=".sdd/profile",
                passed=profile_exists,
                message="Found" if profile_exists else "Missing — run 'sdd init'",
                layer="DISCOVERY",
            )
        )

        # Check governance-core.json (A1 fix: correct paths)
        governance_candidates = [
            self.project_root
            / "generated"
            / "client"
            / "compiled"
            / "governance-core.json",
            self.project_root
            / "generated"
            / "master"
            / "compiled"
            / "governance-core.json",
        ]
        governance_exists = any(p.exists() for p in governance_candidates)
        results.append(
            ValidationResult(
                name="governance-core.json",
                passed=governance_exists,
                message=(
                    "Found"
                    if governance_exists
                    else "Not compiled (optional at this stage)"
                ),
                layer="DISCOVERY",
            )
        )

        layer_state = "CONNECTED" if sdd_exists else "NOT_CONNECTED"
        return layer_state, results

    def layer_2_link_validation(self) -> tuple[str, list[ValidationResult]]:
        """
        Layer 2: LINK VALIDATION — Are connections valid?

        Checks .sdd/profile is parseable and points to valid paths.
        """
        results = []

        profile_path = self.project_root / ".sdd" / "profile"
        profile_readable = False
        profile_valid = False

        if profile_path.exists():
            try:
                import configparser

                parser = configparser.ConfigParser()
                parser.read(profile_path)
                profile_type = parser.get("sdd", "type", fallback="").strip().lower()
                profile_readable = True
                profile_valid = profile_type in ("master", "client")
            except Exception:
                profile_readable = False

        results.append(
            ValidationResult(
                name=".sdd/profile readable",
                passed=profile_readable,
                message=(
                    "Parses correctly" if profile_readable else "Invalid or missing"
                ),
                layer="LINK_VALIDATION",
            )
        )
        results.append(
            ValidationResult(
                name=".sdd/profile type valid",
                passed=profile_valid,
                message=(
                    "type=master|client"
                    if profile_valid
                    else "type field missing or invalid"
                ),
                layer="LINK_VALIDATION",
            )
        )

        core_accessible = (self.project_root / "packages").exists()
        results.append(
            ValidationResult(
                name="packages framework",
                passed=core_accessible,
                message="Framework accessible" if core_accessible else "Not found",
                layer="LINK_VALIDATION",
            )
        )

        if profile_readable and profile_valid:
            layer_state = "LINK_OK"
        elif profile_path.exists():
            layer_state = "BROKEN_LINK"
        else:
            layer_state = "NO_CONFIG"

        return layer_state, results

    def layer_3_runtime_validation(self) -> tuple[str, list[ValidationResult]]:
        """
        Layer 3: RUNTIME VALIDATION — Is it operational?

        Checks .sdd/runtime/, state files, and PHASE 0 marker.
        """
        results = []

        runtime_dir = self.project_root / ".sdd" / "runtime"
        runtime_exists = runtime_dir.exists()
        results.append(
            ValidationResult(
                name=".sdd/runtime/",
                passed=runtime_exists,
                message="Initialized" if runtime_exists else "Not initialized",
                layer="RUNTIME_VALIDATION",
            )
        )

        state_file = (
            runtime_dir / "governance-state.json" if runtime_dir.exists() else None
        )
        state_file_exists = state_file is not None and state_file.exists()
        results.append(
            ValidationResult(
                name="state cache",
                passed=state_file_exists,
                message=(
                    "Cache initialized" if state_file_exists else "Cache not created"
                ),
                layer="RUNTIME_VALIDATION",
            )
        )

        phase_0_marker = self.project_root / ".sdd" / "runtime" / ".phase-0-complete"
        phase_0_done = phase_0_marker.exists()
        results.append(
            ValidationResult(
                name="PHASE 0 setup",
                passed=phase_0_done,
                message="Completed" if phase_0_done else "Not run yet",
                layer="RUNTIME_VALIDATION",
            )
        )

        if phase_0_done and state_file_exists:
            layer_state = "READY"
        elif runtime_exists:
            layer_state = "PARTIAL"
        else:
            layer_state = "NOT_INITIALIZED"

        return layer_state, results

    def layer_4_governance_health(self) -> tuple[str, list[ValidationResult]]:
        """
        Layer 4: GOVERNANCE HEALTH — Is it healthy?

        A4 fix: checks compiled artifacts, not installed packages.
        """
        results = []

        # A1 fix: correct candidates pointing to generated/*/compiled/
        governance_candidates = [
            self.project_root
            / "generated"
            / "client"
            / "compiled"
            / "governance-core.json",
            self.project_root
            / "generated"
            / "master"
            / "compiled"
            / "governance-core.json",
        ]
        governance_path = next((p for p in governance_candidates if p.exists()), None)
        governance_valid = False
        governance_items = 0

        if governance_path is not None:
            try:
                with open(governance_path, encoding="utf-8") as f:
                    gov_data = json.load(f)
                governance_valid = True
                governance_items = len(gov_data.get("items", []))
            except Exception:
                governance_valid = False

        results.append(
            ValidationResult(
                name="governance integrity",
                passed=governance_valid,
                message=(
                    f"Valid ({governance_items} items)"
                    if governance_valid
                    else "Not compiled"
                ),
                layer="GOVERNANCE_HEALTH",
            )
        )

        # A4 fix: check compiled artifacts, not package directories
        artifact_checks = [
            self.project_root / "generated" / "client" / "compiled",
            self.project_root / "generated" / "master" / "compiled",
        ]
        artifacts_present = sum(1 for p in artifact_checks if p.exists())
        artifacts_ok = artifacts_present >= 1
        results.append(
            ValidationResult(
                name="compiled artifacts",
                passed=artifacts_ok,
                message=(
                    f"Present ({artifacts_present}/{len(artifact_checks)} dirs)"
                    if artifacts_ok
                    else "No compiled artifacts found — run 'sdd governance compile'"
                ),
                layer="GOVERNANCE_HEALTH",
            )
        )

        if governance_valid and artifacts_ok:
            layer_state = "HEALTHY"
        elif governance_valid or artifacts_ok:
            layer_state = "DEGRADED"
        else:
            layer_state = "UNKNOWN"

        return layer_state, results

    @staticmethod
    def compute_final_state(l1: str, l2: str, l3: str, l4: str) -> str:
        """Compute final system state from 4-layer results."""
        if l1 == "NOT_CONNECTED":
            return "NOT_CONNECTED"
        if l2 == "BROKEN_LINK":
            return "MISCONFIGURED"
        if l3 == "NOT_INITIALIZED":
            return "NOT_INITIALIZED"
        if "PARTIAL" in [l1, l2, l3, l4]:
            return "PARTIAL"
        return "HEALTHY"

    @staticmethod
    def compute_confidence(all_results: list[ValidationResult]) -> float:
        """Compute confidence score (0-100%)."""
        if not all_results:
            return 0.0
        passed = sum(1 for r in all_results if r.passed)
        return (passed / len(all_results)) * 100
