"""Template for the seedlings verify.py script."""

from __future__ import annotations


def build_verification_script(mandate_ids_str: str) -> str:
    """Render verify.py content."""
    return f'''#!/usr/bin/env python3
"""Governance Activation Verification Script

This script verifies that governance seedlings are properly activated.

Usage:
    python3 verify.py
    python3 verify.py --verbose
"""

import json
import sys
from pathlib import Path


class GovernanceVerifier:
    """Verify governance activation status"""

    def __init__(self, project_root: Path = None, verbose: bool = False):
        self.project_root = project_root or Path.cwd()
        self.verbose = verbose
        self.checks = {{}}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, message: str):
        if self.verbose:
            logger.info(f"  {{message}}")

    def check_directory(self, path: str, description: str) -> bool:
        full_path = self.project_root / path
        passed = full_path.exists() and full_path.is_dir()
        status = "✅" if passed else "❌"
        logger.info(f"  {{status}} {{description}}: {{path}}")
        self.checks[description] = "pass" if passed else "fail"
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        return passed

    def check_file(self, path: str, description: str, must_be_json: bool = False) -> bool:
        full_path = self.project_root / path
        exists = full_path.exists() and full_path.is_file()

        if not exists:
            logger.warning(f"  ❌ {{description}}: {{path}}")
            self.checks[description] = "fail"
            self.failed += 1
            return False

        if must_be_json:
            try:
                with open(full_path, "r") as f:
                    json.load(f)
                status = "✅"
                result = True
            except json.JSONDecodeError as e:
                status = "❌"
                result = False
                logger.info(f"  {{status}} {{description}} (Invalid JSON): {{path}}")
                self.failed += 1
                return False
        else:
            status = "✅"
            result = True

        logger.info(f"  {{status}} {{description}}: {{path}}")
        self.checks[description] = "pass"
        if result:
            self.passed += 1
        return result

    def check_seedling_loader(self) -> bool:
        """Test SeedlingLoader discovery"""
        try:
            # Robust path discovery: search for tools directory up to 4 levels deep
            root = self.project_root
            found_root = False
            for _ in range(5):
                if (root / "tools" / "governance").exists():
                    sys.path.insert(0, str(root))
                    found_root = True
                    break
                if root == root.parent:
                    break
                root = root.parent

            if not found_root:
                # Fallback: try to find repository root by looking for 'packages' or '.git'
                current_path = Path(__file__).resolve().parent
                repo_root = None
                for _ in range(10): # Limit depth to prevent infinite loop
                    if (current_path / "packages").is_dir() or (current_path / ".git").is_dir():
                        repo_root = current_path
                        break
                    if current_path == current_path.parent: # Reached filesystem root
                        break
                    current_path = current_path.parent

                if repo_root:
                    sys.path.insert(0, str(repo_root))
                else:
                    # Last resort, might not be correct for all setups
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

            from tools.governance.seedling_loader import SeedlingLoader

            loader = SeedlingLoader(self.project_root)
            loaded = loader.load_all()

            if len(loaded) >= 3:
                logger.info(f"  ✅ SeedlingLoader: Discovered {{len(loaded)}} seedlings")
                self.checks["SeedlingLoader"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"  ⚠️  SeedlingLoader: Found only {{len(loaded)}} seedlings (expected 3+)")
                self.checks["SeedlingLoader"] = "warn"
                self.warnings += 1
                return False
        except Exception as e:
            logger.warning(f"  ⚠️  SeedlingLoader: Could not test")
            self.checks["SeedlingLoader"] = "warn"
            self.warnings += 1
            return False

    def verify_mandates(self) -> bool:
        """Verify mandates are configured"""
        expected = {{'{mandate_ids_str}'}}
        gov_seed_path = self.project_root / ".sdd/seedlings/governance.seed.json"

        try:
            with open(gov_seed_path, "r") as f:
                data = json.load(f)
                configured = set(data.get("project_metadata", {{}}).get("mandates_selected", []))

            if configured == expected:
                logger.info(f"  ✅ Mandates: {{', '.join(expected)}}")
                self.checks["Mandates"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"  ❌ Mandates mismatch: Expected {{expected}}, got {{configured}}")
                self.checks["Mandates"] = "fail"
                self.failed += 1
                return False
        except Exception as e:
            logger.warning(f"  ❌ Mandates: Could not verify")
            self.checks["Mandates"] = "fail"
            self.failed += 1
            return False

    def run(self) -> bool:
        """Run all verification checks"""
        logger.debug("=" * 70)
        logger.info("🔍 Governance Activation Verification")
        logger.debug("=" * 70)

        logger.info("\\n📂 Directory Structure:")
        self.check_directory(".sdd/source/mandates", ".sdd/source/mandates")
        self.check_directory(".sdd/source/guidelines", ".sdd/source/guidelines")
        self.check_directory(".sdd/runtime", ".sdd/runtime")
        self.check_directory(".sdd/seedlings", ".sdd/seedlings")

        logger.info("\\n📄 Required Files:")
        self.check_file(".sdd/metadata.json", ".sdd/metadata.json", must_be_json=True)
        self.check_file(".sdd/runtime/mandate.bin", "mandate.bin")
        self.check_file(".sdd/source/mandates/mandates.md", "mandates.md")
        self.check_file(".sdd/seedlings/governance.seed.json", "governance.seed.json", must_be_json=True)
        self.check_file(".sdd/seedlings/agent-prep.seed.json", "agent-prep.seed.json", must_be_json=True)
        self.check_file(".sdd/seedlings/compliance.seed.json", "compliance.seed.json", must_be_json=True)

        logger.info("\\n🔑 Governance Configuration:")
        self.verify_mandates()

        logger.info("\\n🧩 Integration Tests:")
        self.check_seedling_loader()

        logger.debug("=" * 70)
        logger.info("📊 Summary")
        logger.debug("=" * 70)
        logger.info(f"✅ Passed: {{self.passed}}")
        if self.warnings:
            logger.info(f"⚠️  Warnings: {{self.warnings}}")
        if self.failed:
            logger.info(f"❌ Failed: {{self.failed}}")

        if self.failed == 0 and self.warnings == 0:
            logger.info("\\n🎉 Governance is fully activated!")
            return True
        elif self.failed == 0:
            logger.info(f"\\n⚠️  Governance is mostly activated ({{self.warnings}} warnings)")
            return True
        else:
            logger.info(f"\\n❌ Governance activation failed ({{self.failed}} critical issues)")
            logger.info("\\n💡 Next Steps:")
            logger.info("   1. Review ACTIVATION_GUIDE.md for troubleshooting")
            logger.info("   2. Verify all files copied from wizard output")
            logger.info("   3. Restart IDE and try again")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify governance activation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--project",
        "-p",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )

    args = parser.parse_args()

    verifier = GovernanceVerifier(project_root=args.project, verbose=args.verbose)
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
    '''
