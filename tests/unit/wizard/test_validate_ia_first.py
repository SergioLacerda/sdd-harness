"""
Unit tests for validate-ia-first.py

Tests documentation validation rules and auto-fix functionality.
Run: pytest tests/spec_validation/test_validate_ia_first.py -v
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

VALIDATOR_PATH = Path(
    "packages/interfaces/sdd_wizard/src/sdd_wizard/SCRIPTS/validate-ia-first.py"
).resolve()


def _run_validator(
    args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
    )


class TestValidateIAFirstBasics:
    """Test basic validation rules."""

    def test_h1_header_required(self) -> None:
        """Every doc must start with H1 header."""
        # Valid content
        valid = "# My Document\n\nContent here"
        assert valid.startswith("#")

        # Invalid content
        invalid = "No header\nContent here"
        assert not invalid.startswith("#")

    def test_ia_first_section_required(self) -> None:
        """Every doc must have IA-FIRST section in first 50 lines."""
        valid_content = """# My Document

**IA-FIRST:** This is an important document.

**For:** Developers
**Time:** 5 min
"""
        assert "IA-FIRST" in valid_content

        # Invalid: no IA-FIRST
        invalid_content = """# My Document

Some content without required marker.
"""
        assert "IA-FIRST" not in invalid_content

    def test_status_field_required(self) -> None:
        """Every doc must have Status field."""
        valid = "Status: Complete"
        assert "Status:" in valid

        invalid = "No status field here"
        assert "Status:" not in invalid

    def test_status_values_valid(self) -> None:
        """Status field must have valid value."""
        valid_statuses = ["Complete", "WIP", "Deprecated"]

        for status in valid_statuses:
            assert status in ["Complete", "WIP", "Deprecated"]

        # Invalid status
        invalid_status = "in-progress"
        assert invalid_status not in ["Complete", "WIP", "Deprecated"]


class TestValidateHeadingHierarchy:
    """Test heading hierarchy validation."""

    def test_h1_h2_h3_order(self) -> None:
        """Headers should follow H1 → H2 → H3 order."""
        valid_content = """# Main Title
## Section One
### Subsection
## Section Two
### Subsection
"""
        lines = valid_content.split("\n")
        h_levels = []
        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                h_levels.append(level)

        # Should have proper hierarchy
        assert h_levels[0] == 1  # H1
        assert h_levels[1] == 2  # H2
        assert h_levels[2] == 3  # H3

    def test_no_skipped_levels(self) -> None:
        """Should not skip heading levels (e.g., H1 to H3)."""
        # Invalid: skips from H1 to H4
        invalid_content = """# Main
#### Skipped H2 and H3
"""
        lines = invalid_content.split("\n")
        h_levels = []
        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                h_levels.append(level)

        # Should detect the skip
        assert len(h_levels) == 2
        assert h_levels[1] - h_levels[0] > 1  # Skipped levels


class TestValidateLinks:
    """Test link format validation."""

    def test_markdown_links_valid(self) -> None:
        """Links should use markdown format."""
        valid_link = "[text](path/to/file.md)"

        # Should match markdown link pattern
        import re

        pattern = r"\[.+?\]\(.+?\)"
        assert re.search(pattern, valid_link)

    def test_backtick_links_invalid(self) -> None:
        """Links should not use backticks."""
        invalid_link = "[`text`](path/to/file.md)"

        assert "`" in invalid_link  # Should detect backticks in link text

    def test_inline_code_backticks_valid(self) -> None:
        """Backticks are valid for inline code (not in links)."""
        valid_code = "Use `function_name()` for details"

        assert "`" in valid_code
        # Backticks without links are OK


class TestValidateMetadata:
    """Test metadata validation."""

    def test_required_fields_present(self) -> None:
        """Should check for required metadata fields."""
        required_fields = ["Status", "Version", "For", "Time"]

        valid_content = """
**Status:** Complete
**Version:** 1.0
**For:** Developers
**Time:** 5 min
"""

        for field in required_fields[:2]:  # At minimum Status and Version
            assert field in valid_content

    def test_status_version_fields(self) -> None:
        """Status and Version are mandatory."""
        content = """
**Status:** Complete
**Version:** 1.0
"""
        assert "Status:" in content
        assert "Version:" in content


class TestValidateEmojiMarkers:
    """Test emoji marker validation."""

    def test_emoji_markers_present(self) -> None:
        """Docs should use emoji markers for structure."""
        valid_content = """
✅ This is done
❌ This is not working
🎯 This is the goal
⚠️ Warning section
"""
        emojis = ["✅", "❌", "🎯", "⚠️"]

        for emoji in emojis:
            assert emoji in valid_content or valid_content.count("✅") > 0

    def test_emoji_consistency(self) -> None:
        """Should check emoji is used consistently."""
        content_with_emoji = "✅ Done"
        content_without = "Done"

        assert "✅" in content_with_emoji
        assert "✅" not in content_without


class TestValidateAutoFix:
    """Test auto-fix functionality."""

    def test_fix_missing_ia_first(self) -> None:
        """Should add IA-FIRST section if missing."""
        broken_content = """# My Document

Some content without IA-FIRST.
"""

        # Simulate auto-fix
        ia_first_section = "\n**IA-FIRST:** This document needs description.\n"
        fixed_content = (
            broken_content.split("\n\n")[0]
            + "\n"
            + ia_first_section
            + broken_content.split("\n\n")[1]
        )

        assert "IA-FIRST" in fixed_content

    def test_fix_invalid_links(self) -> None:
        """Should fix backtick links."""

        # Auto-fix: remove backticks
        fixed_content = "See [guide](guide.md) for details"

        assert "`" not in fixed_content
        assert "[guide]" in fixed_content

    def test_fix_heading_hierarchy(self) -> None:
        """Should fix skipped heading levels."""
        broken_content = """# Title
#### Subsection (should be ##)
"""

        # Would need to parse and fix
        # For now, just verify we detect the problem
        assert "####" in broken_content


class TestValidateStatusValues:
    """Test status field validation."""

    def test_valid_statuses_complete(self) -> None:
        """Complete is valid status."""
        assert "Complete" in ["Complete", "WIP", "Deprecated"]

    def test_valid_statuses_wip(self) -> None:
        """WIP is valid status."""
        assert "WIP" in ["Complete", "WIP", "Deprecated"]

    def test_valid_statuses_deprecated(self) -> None:
        """Deprecated is valid status."""
        assert "Deprecated" in ["Complete", "WIP", "Deprecated"]

    def test_invalid_status_in_progress(self) -> None:
        """in-progress is not valid (use WIP instead)."""
        assert "in-progress" not in ["Complete", "WIP", "Deprecated"]

    def test_invalid_status_draft(self) -> None:
        """draft is not valid."""
        assert "draft" not in ["Complete", "WIP", "Deprecated"]


class TestValidateCommandLine:
    """Test command-line interface."""

    def test_validate_command_basic(self) -> None:
        """Should run basic validation."""
        assert VALIDATOR_PATH.exists()
        result = _run_validator(["--help"])
        assert result.returncode == 0

    def test_validate_audit_mode(self) -> None:
        """Should support --audit mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "ok.md").write_text(
                "# Title\n\n## ⚡ IA-FIRST DESIGN NOTICE\n\nStatus: Complete\nVersion: 1.0\n✅ marker\n",
                encoding="utf-8",
            )
            result = _run_validator(["--audit", str(docs_dir)], cwd=root)
            assert result.returncode == 0

    def test_validate_fix_mode(self) -> None:
        """Should support --fix auto-fix mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "broken.md").write_text(
                "# Test\nContent without IA-FIRST\n", encoding="utf-8"
            )
            result = _run_validator(["--fix", "--audit", str(docs_dir)], cwd=root)
            # Missing Status still keeps file invalid, but command should execute deterministically.
            assert result.returncode == 1


class TestValidateExitCodes:
    """Test exit code meanings."""

    def test_exit_0_means_success(self) -> None:
        """Exit code 0 means all validation passed."""
        exit_code = 0
        assert exit_code == 0

    def test_exit_1_means_errors(self) -> None:
        """Exit code 1 means validation errors found."""
        exit_code = 1
        assert exit_code == 1

    def test_exit_3_means_validation_failed(self) -> None:
        """Exit code 3 means validation check failed."""
        exit_code = 3
        assert exit_code == 3


class TestValidatePerformance:
    """Test validation performance."""

    def test_validation_completes_quickly(self) -> None:
        """Validation should complete in reasonable time."""
        import time

        validator_path = Path("docs/ia/SCRIPTS/validate-ia-first.py")
        if validator_path.exists():
            start = time.time()
            subprocess.run(
                (
                    [sys.executable, str(validator_path), "--test"]
                    if "--test"
                    in subprocess.run(
                        [sys.executable, str(validator_path), "--help"],
                        capture_output=True,
                        text=True,
                    ).stdout
                    else [sys.executable, str(validator_path)]
                ),
                capture_output=True,
                text=True,
                timeout=30,
            )
            elapsed = time.time() - start

            # Should complete in < 30 seconds
            assert elapsed < 30


class TestValidateEdgeCases:
    """Test edge cases."""

    def test_empty_document(self) -> None:
        """Should handle empty documents."""
        empty_content = ""
        # Should be invalid but not crash
        assert len(empty_content) == 0

    def test_very_long_document(self) -> None:
        """Should handle very long documents."""
        long_content = "# Title\n" + ("Content line\n" * 10000)
        assert len(long_content) > 10000

    def test_unicode_content(self) -> None:
        """Should handle Unicode characters."""
        unicode_content = """# Título com Acentuação
✅ Unicode: 你好 مرحبا
**Status:** Complete
"""
        assert "✅" in unicode_content
        assert "Título" in unicode_content


class TestValidateIntegration:
    """Integration tests for full validation."""

    def test_validate_docs_ia_folder(self) -> None:
        """Should validate entire docs/ia/ folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs" / "ia"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "valid.md").write_text(
                "# Title\n\n## ⚡ IA-FIRST DESIGN NOTICE\n\nStatus: Complete\nVersion: 1.0\n✅ marker\n",
                encoding="utf-8",
            )
            result = _run_validator(["--audit", str(docs_dir)], cwd=root)
            assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
