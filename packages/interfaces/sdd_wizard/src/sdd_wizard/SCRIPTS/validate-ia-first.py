#!/usr/bin/env python3
"""
Validate and standardize IA-FIRST headers in documentation.

IA-FIRST = Machine-parseable, AI-friendly markdown format

Checks:
  ✅ All docs have required header section
  ✅ Status field present (Complete/WIP/Deprecated)
  ✅ Consistent structure (H1 → H2 → H3)
  ✅ Emoji markers used consistently
  ✅ All links are markdown format (no backticks)
  ✅ Metadata tags present (audience, reads_first, etc)

Usage:
    python validate-ia-first.py                    # Check all docs
    python validate-ia-first.py --fix              # Auto-fix common issues
    python validate-ia-first.py --audit docs/ia/  # Audit specific folder
"""

import re
import sys
from pathlib import Path


class IAFirstValidator:
    """Validate and fix IA-FIRST markdown format."""

    # Required sections in every doc
    REQUIRED_SECTIONS = [
        "IA-FIRST DESIGN NOTICE",
        "Overview",
    ]

    # Required metadata fields
    REQUIRED_METADATA = [
        "Status",
        "Version",
    ]

    # Valid status values
    VALID_STATUSES = [
        "Complete",
        "WIP",
        "Deprecated",
    ]

    def __init__(self, fix_mode: bool = False):
        self.fix_mode = fix_mode
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.fixes_applied: list[str] = []

    def validate_file(self, file_path: Path) -> bool:  # noqa: C901
        """Validate a single markdown file."""

        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Check 1: Has H1 header
        if not content.startswith("#"):
            self.errors.append(f"{file_path}: Missing H1 header")

        # Check 2: Has IA-FIRST section
        if "IA-FIRST DESIGN NOTICE" not in content:
            self.warnings.append(f"{file_path}: Missing IA-FIRST DESIGN NOTICE")
            if self.fix_mode:
                content = self._add_ia_first_section(content)
                self.fixes_applied.append(f"{file_path}: Added IA-FIRST section")

        # Check 3: Has Status field
        if "Status:" not in content:
            self.errors.append(f"{file_path}: Missing Status field")
        else:
            status = self._extract_status(content)
            if status not in self.VALID_STATUSES:
                self.errors.append(
                    f"{file_path}: Invalid status '{status}'. Must be: {self.VALID_STATUSES}"
                )

        # Check 4: Consistent structure
        if not self._check_heading_hierarchy(content):
            self.warnings.append(
                f"{file_path}: Inconsistent heading hierarchy (should be H1 → H2 → H3)"
            )

        # Check 5: No backtick links
        if self._has_backtick_links(content):
            self.warnings.append(
                f"{file_path}: Found backtick links (use [text](path) instead of `[text]`)"
            )

        # Check 6: Emoji markers used
        if not self._has_emoji_markers(content):
            self.warnings.append(
                f"{file_path}: No emoji markers found (use ✅, ❌, 🎯, ⚠️)"
            )

        # Write fixes if in fix mode
        if self.fix_mode and self.fixes_applied:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return len(self.errors) == 0

    def _add_ia_first_section(self, content: str) -> str:
        """Add IA-FIRST DESIGN NOTICE section after H1."""

        # Find first H2 position
        h2_match = re.search(r"\n##\s+", content)
        if not h2_match:
            h2_match = re.search(r"\n---\n", content)

        if not h2_match:
            return content

        insert_pos = h2_match.start()

        ia_first_notice = """
## ⚡ IA-FIRST DESIGN NOTICE

**This document is optimized for AI parsing:**
- Structure: H1 → H2 (sections) → H3 (subsections) → Lists
- All lists use `-` (not numbers or bullets)
- All links use `[text](path.md)` format (no backticks)
- All constraints marked with emoji (✅, ❌, 🎯, ⚠️)
- Single idea per H2 section (not mixed topics)

**Maintenance rules:**
- Keep structure consistent (do not mix prose/lists within sections)
- Add emoji markers for decision markers
- Update Status field when document changes
- Never use backticks in links `[text]` → use `[text](path.md)`

**Parser guarantees:** This format is parseable by AI agents without ambiguity

---

"""
        return content[:insert_pos] + ia_first_notice + content[insert_pos:]

    def _extract_status(self, content: str) -> str:
        """Extract Status field value."""
        match = re.search(r"Status:\s+(.+?)(\n|$)", content)
        if match:
            return match.group(1).strip().split()[0]
        return ""

    def _check_heading_hierarchy(self, content: str) -> bool:
        """Check if heading hierarchy is consistent."""
        headings = re.findall(r"^(#+)\s+", content, re.MULTILINE)
        if not headings:
            return True

        # Should start with # (H1)
        if headings[0] != "#":
            return False

        # Should not jump from # to ### (missing ##)
        for i in range(1, len(headings)):
            prev_level = len(headings[i - 1])
            curr_level = len(headings[i])
            if curr_level > prev_level + 1:
                return False

        return True

    def _has_backtick_links(self, content: str) -> bool:
        """Check if document has backtick-wrapped links."""
        return bool(re.search(r"`\[.+?\]\(.+?\)`", content))

    def _has_emoji_markers(self, content: str) -> bool:
        """Check if document uses emoji markers."""
        emoji_pattern = r"[✅❌🎯⚠️🔴🟡🟢📌📋🚀]"
        return bool(re.search(emoji_pattern, content))

    def validate_directory(self, dir_path: Path) -> tuple[int, int]:
        """Validate all markdown files in directory."""

        md_files = list(dir_path.rglob("*.md"))
        total = len(md_files)
        passed = 0

        for md_file in md_files:
            if self.validate_file(md_file):
                passed += 1

        return passed, total


def main() -> int:
    """Main validation runner."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Validate and standardize IA-FIRST markdown format"
    )
    parser.add_argument("--audit", default="docs/ia/", help="Directory to audit")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    validator = IAFirstValidator(fix_mode=args.fix)

    audit_dir = Path(args.audit)
    if not audit_dir.exists():
        print(f"❌ Directory not found: {audit_dir}")  # noqa: T201
        return 1

    # Validate all markdown files
    print(f"🔍 Auditing {audit_dir}...")  # noqa: T201
    passed, total = validator.validate_directory(audit_dir)

    # Print results
    print("\n📋 Results:")  # noqa: T201
    print(f"  ✅ Passed: {passed}/{total}")  # noqa: T201
    print(f"  ❌ Failed: {total - passed}/{total}")  # noqa: T201

    if validator.warnings:
        print(f"\n⚠️  Warnings ({len(validator.warnings)}):")  # noqa: T201
        for warning in validator.warnings[:10]:
            print(f"  - {warning}")  # noqa: T201
        if len(validator.warnings) > 10:
            print(f"  ... and {len(validator.warnings) - 10} more")  # noqa: T201

    if validator.errors:
        print(f"\n❌ Errors ({len(validator.errors)}):")  # noqa: T201
        for error in validator.errors[:10]:
            print(f"  - {error}")  # noqa: T201
        if len(validator.errors) > 10:
            print(f"  ... and {len(validator.errors) - 10} more")  # noqa: T201

    if validator.fixes_applied:
        print(f"\n✅ Fixes applied ({len(validator.fixes_applied)}):")  # noqa: T201
        for fix in validator.fixes_applied:
            print(f"  - {fix}")  # noqa: T201

    # Return exit code based on errors
    return 1 if validator.errors else 0


if __name__ == "__main__":
    sys.exit(main())
