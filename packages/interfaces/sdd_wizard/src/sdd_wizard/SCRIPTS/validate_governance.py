#!/usr/bin/env python3
"""
GOVERNANCE VALIDATOR
Verifies ia-rules.md and governance files are intact.

Usage:
    python docs/ia/scripts/validate_governance.py

Exit codes:
    0 = All governance checks pass
    1 = Governance violation detected
"""

import importlib
import sys
from pathlib import Path

# Ensure packages is in path for tests.path_config
root = Path(__file__).resolve().parents[3]
if str(root / "packages") not in sys.path:
    sys.path.insert(0, str(root / "packages"))

CANONICAL_SPEC = importlib.import_module("tests.path_config").CANONICAL_SPEC


class GovernanceValidator:
    """Validates governance documents integrity"""

    REQUIRED_FILES = {
        "ia-rules.md": "16 execution protocols (MANDATORY)",
        "GOVERNANCE_RULES.md": "Immutable governance layer",
        "RUNTIME_STATE.md": "Mutable runtime layer",
        "specs/constitution.md": "Immutable principles",
    }

    REQUIRED_PROTOCOLS = {
        "port": "Port abstraction is mandatory",
        "thread": "Thread isolation required",
        "blocking": "Async-first approach (no blocking)",
        "execution_state": "State awareness required",
        "architecture": "Clean architecture pattern",
    }

    def __init__(self) -> None:
        self.root = CANONICAL_SPEC
        self.violations: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Run all governance validations"""
        print("🔍 GOVERNANCE VALIDATION")  # noqa: T201
        print("-" * 60)  # noqa: T201

        # Check required files exist
        self._check_required_files()

        # Check ia-rules.md has key protocols
        self._check_ia_rules()

        # Check governance files weren't modified suspiciously
        self._check_governance_integrity()

        # Print results
        return self._print_results()

    def _check_required_files(self) -> None:
        """Check all required governance files exist"""
        print("\n📋 Checking required files...")  # noqa: T201
        for file_path, description in self.REQUIRED_FILES.items():
            full_path = self.root / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"  ✅ {file_path:<30} ({size:,} bytes) — {description}")  # noqa: T201
            else:
                msg = f"  ❌ {file_path:<30} MISSING!"
                print(msg)  # noqa: T201
                self.violations.append(msg)

    def _check_ia_rules(self) -> None:
        """Check ia-rules.md has core protocols"""
        print("\n📝 Checking ia-rules.md protocols...")  # noqa: T201
        ia_rules_file = self.root / "ia-rules.md"

        if not ia_rules_file.exists():
            self.violations.append("ia-rules.md does not exist!")
            return

        try:
            content = ia_rules_file.read_text(encoding="utf-8")
            found_count = 0

            for protocol, _description in self.REQUIRED_PROTOCOLS.items():
                if protocol in content:
                    found_count += 1
                    print(f"  ✅ Concept found: {protocol:<40}")  # noqa: T201
                else:
                    msg = f"  ⚠️  Concept missing: {protocol:<40}"
                    print(msg)  # noqa: T201
                    self.warnings.append(msg)

            print(  # noqa: T201
                f"\n  Score: {found_count}/{len(self.REQUIRED_PROTOCOLS)} core concepts found"
            )
            if found_count < len(self.REQUIRED_PROTOCOLS) // 2:
                self.violations.append(
                    f"ia-rules.md is missing too many core concepts ({found_count}/{len(self.REQUIRED_PROTOCOLS)})"
                )

        except Exception as e:
            self.violations.append(f"Error reading ia-rules.md: {e}")

    def _check_governance_integrity(self) -> None:
        """Check governance files haven't been gutted"""
        print("\n🔐 Checking governance file integrity...")  # noqa: T201

        governance_files = {
            "GOVERNANCE_RULES.md": 2000,  # Min 2KB
            "RUNTIME_STATE.md": 5000,  # Min 5KB
            "specs/constitution.md": 1000,  # Min 1KB
        }

        for file_path, min_size in governance_files.items():
            full_path = self.root / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                if size >= min_size:
                    print(f"  ✅ {file_path:<30} ({size:,} bytes) — OK")  # noqa: T201
                else:
                    msg = f"  ⚠️  {file_path:<30} ({size:,} bytes) — SUSPICIOUSLY SMALL (min: {min_size:,})"
                    print(msg)  # noqa: T201
                    self.warnings.append(msg)

    def _print_results(self) -> bool:
        """Print validation results"""
        print("\n" + "=" * 60)  # noqa: T201
        print("VALIDATION RESULTS")  # noqa: T201
        print("=" * 60)  # noqa: T201

        if self.violations:
            print(f"\n🔴 VIOLATIONS: {len(self.violations)}")  # noqa: T201
            for v in self.violations:
                print(f"  {v}")  # noqa: T201

        if self.warnings:
            print(f"\n🟡 WARNINGS: {len(self.warnings)}")  # noqa: T201
            for w in self.warnings:
                print(f"  {w}")  # noqa: T201

        if not self.violations:
            print("\n✅ GOVERNANCE VALIDATION PASSED")  # noqa: T201
            return True
        else:
            print("\n❌ GOVERNANCE VALIDATION FAILED")  # noqa: T201
            return False


if __name__ == "__main__":
    validator = GovernanceValidator()
    success = validator.validate()
    sys.exit(0 if success else 1)
