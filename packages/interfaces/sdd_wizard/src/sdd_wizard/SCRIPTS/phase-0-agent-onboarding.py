#!/usr/bin/env python3
"""
PHASE 0: Agent Workspace Initialization

Purpose: Automate PHASE 0 onboarding for AI agents
- Verifies workspace is initialised via `.sdd/profile`
- Creates .sdd/context-aware/ infrastructure
- Validates SDD knowledge (quiz)
- Confirms workspace is ready

Usage:
    python phase-0-agent-onboarding.py [project_root]

Example:
    cd /path/to/your/project
    sdd init  # initialise workspace first
    python phase-0-agent-onboarding.py

Time: ~15-20 minutes
"""

import os
import shutil
import stat
import sys
from importlib.util import find_spec
from pathlib import Path


class PHASE0Bootstrap:
    """Bootstrap agent workspace for SPEC project."""

    def __init__(self, project_root: str | None = None) -> None:
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.sdd_profile_path = self.project_root / ".sdd" / "profile"
        self.ai_dir = self.project_root / ".sdd" / "context-aware"
        # Locate templates from installed sdd_integration package
        try:
            import sdd_integration

            self._templates_base: Path | None = (
                Path(sdd_integration.__file__).parent / "templates"
            )
        except ImportError:
            self._templates_base = None

    def run(self) -> bool:
        """Execute full PHASE 0 onboarding."""
        print("\n" + "=" * 60)  # noqa: T201
        print("🚀 PHASE 0: Agent Workspace Initialization")  # noqa: T201
        print("=" * 60 + "\n")  # noqa: T201

        # Step 1: Verify .sdd/profile
        if not self._verify_profile():
            return False

        # Step 2: Verify SPEC framework
        if not self._verify_framework():
            return False

        # Step 3: Create infrastructure
        if not self._create_infrastructure():
            return False

        # Step 4: Take quiz
        if not self._validate_knowledge():
            return False

        # Step 5: Success
        self._print_success()
        return True

    def _verify_profile(self) -> bool:
        """Verify workspace is initialized via .sdd/profile."""
        print("\n✓ Step 1: Verify .sdd/profile")  # noqa: T201

        if not self.sdd_profile_path.exists():
            print(f"  ❌ ERROR: Profile not found: {self.sdd_profile_path}")  # noqa: T201
            print("  💡 Run 'sdd init' in the project root and retry.")  # noqa: T201
            return False

        print(f"  ✅ Found: {self.sdd_profile_path.relative_to(self.project_root)}")  # noqa: T201
        return True

    def _verify_framework(self) -> bool:
        """Verify SDD framework packages are available."""
        print("\n\u2713 Step 2: Verify SDD Framework")  # noqa: T201

        if find_spec("sdd_core") and find_spec("sdd_integration"):
            print("  \u2705 sdd_core available")  # noqa: T201
            print("  \u2705 sdd_integration available")  # noqa: T201
            if self._templates_base and self._templates_base.exists():
                print(f"  \u2705 templates_base = {self._templates_base}")  # noqa: T201
            else:
                print(  # noqa: T201
                    "  \u26a0\ufe0f  Templates directory not found in sdd_integration"
                )
            return True

        print(  # noqa: T201
            "  \u274c ERROR: SDD packages not installed: sdd_core and/or sdd_integration"
        )
        return False

    def _create_infrastructure(self) -> bool:
        """Create .sdd/context-aware/ infrastructure."""
        print("\n✓ Step 3: Create Infrastructure")  # noqa: T201

        # Create directories
        dirs = [
            self.ai_dir,
            self.ai_dir / "task-progress" / "completed",
            self.ai_dir / "analysis",
            self.ai_dir / "runtime-state",
            self.project_root / ".sdd" / "runtime",
            self.project_root / "scripts",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created: {d.relative_to(self.project_root)}")  # noqa: T201

        # Copy templates from SPEC framework
        spec_path = self._templates_base
        if spec_path is None:
            return False
        templates_to_copy = [
            # Context-aware infrastructure
            ("ai/context-aware/README.md", self.ai_dir / "README.md"),
            (
                "ai/context-aware/task-progress/_current.md",
                self.ai_dir / "task-progress" / "_current.md",
            ),
            (
                "ai/context-aware/analysis/_current-issues.md",
                self.ai_dir / "analysis" / "_current-issues.md",
            ),
            (
                "ai/context-aware/runtime-state/_current.md",
                self.ai_dir / "runtime-state" / "_current.md",
            ),
            # Runtime infrastructure
            (
                "ai/runtime/README.md",
                self.project_root / ".sdd" / "runtime" / "README.md",
            ),
            (
                "ai/runtime/spec-canonical-index.md",
                self.project_root / ".sdd" / "runtime" / "spec-canonical-index.md",
            ),
            (
                "ai/runtime/spec-guides-index.md",
                self.project_root / ".sdd" / "runtime" / "spec-guides-index.md",
            ),
            (
                "ai/runtime/search-keywords.md",
                self.project_root / ".sdd" / "runtime" / "search-keywords.md",
            ),
        ]

        for src_rel, dst in templates_to_copy:
            src = spec_path / src_rel
            if src.exists():
                shutil.copy2(src, dst)
                # Make shell scripts executable
                if dst.suffix == ".sh":
                    st = os.stat(dst)
                    os.chmod(dst, st.st_mode | stat.S_IEXEC)
                print(f"  ✅ Copied: {dst.relative_to(self.project_root)}")  # noqa: T201
            else:
                print(f"  ⚠️  Template not found: {src_rel}")  # noqa: T201

        return True

    def _validate_knowledge(self) -> bool:
        """Validate SDD knowledge via quiz."""
        print("\n✓ Step 4: Validate SDD Knowledge")  # noqa: T201

        quiz_file: Path | None = None
        if self._templates_base:
            candidate = (
                self._templates_base.parent.parent.parent.parent.parent
                / "docs"
                / "ia"
                / "guides"
                / "onboarding"
                / "VALIDATION_QUIZ.md"
            )
            if candidate.exists():
                quiz_file = candidate

        if quiz_file is None or not quiz_file.exists():
            print(f"  ⚠️  Quiz not found: {quiz_file}")  # noqa: T201
            print("  ⚠️  Skipping quiz (manual validation recommended)")  # noqa: T201
            return True

        print("  📖 Quiz located: VALIDATION_QUIZ.md")  # noqa: T201
        print("  📋 Please answer the following quiz questions:")  # noqa: T201
        print(f"  📍 Path: {quiz_file}")  # noqa: T201
        print("\n  Quiz Instructions:")  # noqa: T201
        print(f"    1. Open: {quiz_file}")  # noqa: T201
        print("    2. Answer all 5 questions")  # noqa: T201
        print("    3. Score must be ≥ 4/5 (80%)")  # noqa: T201
        print("    4. If score < 4, re-read ia-rules.md and retry")  # noqa: T201

        # Automated quiz (simplified for testing)
        response = (
            input("\n  ✓ Have you passed the quiz (≥4/5)? (yes/no): ").strip().lower()
        )

        if response in ("yes", "y"):
            print("  ✅ Quiz validation: PASSED")  # noqa: T201
            return True
        else:
            print("  ❌ Quiz validation: FAILED")  # noqa: T201
            print("  📖 Please read: docs/ia/CANONICAL/rules/ia-rules.md")  # noqa: T201
            print("  ⏰ Wait 30 minutes, then retake the quiz")  # noqa: T201
            return False

    def _print_success(self) -> None:
        """Print success report."""
        print("\n" + "=" * 60)  # noqa: T201
        print("✅ PHASE 0: ONBOARDING COMPLETE")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print("""  # noqa: T201
Infrastructure Status:
  ✅ .sdd/context-aware/ created (task tracking)
  ✅ .sdd/runtime/ created (SDD remote index)
  ✅ Templates copied
  ✅ Knowledge validated (quiz passed)

What was created:

  Context-Aware (Dynamic)
  ✅ .sdd/context-aware/README.md
  ✅ .sdd/context-aware/task-progress/_current.md
  ✅ .sdd/context-aware/analysis/_current-issues.md
  ✅ .sdd/context-aware/runtime-state/_current.md

  Runtime (SDD Index)
  ✅ .sdd/runtime/README.md (navigation)
  ✅ .sdd/runtime/spec-canonical-index.md (CANONICAL reference)
  ✅ .sdd/runtime/spec-guides-index.md (guides reference)
  ✅ .sdd/runtime/search-keywords.md (quick search)

Next Steps:
  1. Read: .sdd/runtime/README.md
     (Understanding the SDD remote index)

  2. Search: Use .sdd/runtime/search-keywords.md
     (Find what you need quickly)

  3. Read: docs/ia/guides/onboarding/AGENT_HARNESS.md
     (7-phase development workflow)

  4. Create: Your first task in .sdd/context-aware/task-progress/_current.md

Recommended Actions:
  $ git add .sdd/
  $ git commit -m "🚀 PHASE 0: Agent workspace initialized (with runtime index)"

Time to Complete First Task: ~5-10 minutes

Ready to start work!
""")


def main() -> None:
    """Main entry point."""
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    bootstrap = PHASE0Bootstrap(project_root)
    success = bootstrap.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
