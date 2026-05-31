"""Phase 5 Apply Template."""

import shutil
from pathlib import Path
from typing import Any

"""Phase 5: Apply template scaffold and customizations.

Copies base governance scaffolding only. Language-specific code templates are
intentionally not copied to client outputs.
"""


def _get_base_template_dir() -> Path:
    """Get base template directory"""
    wizard_root = Path(__file__).parent.parent
    return wizard_root / "templates" / "base"


def _copy_template_files(
    source_dir: Path, target_dir: Path, ignored_patterns: list[str] | None = None
) -> tuple[int, list[str]]:
    """Copy template files from source to target directory

    Returns:
        (files_copied, errors)
    """
    if not source_dir.exists():
        return (0, [f"Template directory not found: {source_dir}"])

    errors = []
    files_copied = 0

    try:
        for item in source_dir.rglob("*"):
            if item.is_file():
                # Calculate relative path
                rel_path = item.relative_to(source_dir)
                target_file = target_dir / rel_path

                # Create parent directories
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(item, target_file)
                files_copied += 1
    except Exception as e:
        errors.append(f"Error copying template files: {e}")

    return (files_copied, errors)


def _apply_placeholder_replacements(text: str, replacements: dict[str, str]) -> str:
    """Replace placeholders in text

    Args:
        text: Text content with placeholders
        replacements: Dict of {placeholder: value}

    Returns:
        Text with placeholders replaced
    """
    result = text
    for placeholder, value in replacements.items():
        result = result.replace(f"{{{{{placeholder}}}}}", str(value))

    return result


def _customize_file_for_language(file_path: Path, language: str) -> tuple[bool, str]:
    """Apply language-specific customizations to a file

    Returns:
        (success, message)
    """
    if not file_path.exists():
        return (False, f"File not found: {file_path}")

    try:
        # Read file
        content = file_path.read_text(encoding="utf-8")

        # Language-specific placeholders
        replacements = {
            "LANGUAGE": language.upper(),
            "language": language.lower(),
        }

        # Apply replacements
        customized = _apply_placeholder_replacements(content, replacements)

        # Write back
        file_path.write_text(customized, encoding="utf-8")

        return (True, f"Customized for {language}")
    except Exception as e:
        return (False, f"Error customizing file: {e}")


def phase_5_apply_template(
    scaffolding_dir: Path, language: str = "python", repo_root: Path | None = None
) -> tuple[bool, dict[str, Any]]:
    """Apply template scaffold and customizations

    Args:
        scaffolding_dir: Output directory for scaffolding
        language: Target language (java|python|js)
        repo_root: Repository root

    Returns:
        (success, report))
    """
    report: dict[str, Any] = {
        "phase": "PHASE_5_APPLY_TEMPLATE",
        "status": "PENDING",
        "data": {},
        "statistics": {
            "base_files_copied": 0,
            "language_files_copied": 0,
            "customizations_applied": 0,
        },
        "warnings": [],
        "errors": [],
    }

    try:
        # Create scaffolding directory
        scaffolding_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy base templates
        base_dir = _get_base_template_dir()
        if not base_dir.exists():
            report["errors"].append(f"Base template directory not found: {base_dir}")
            report["status"] = "FAILED"
            return (False, report)

        base_copied, base_errors = _copy_template_files(base_dir, scaffolding_dir)
        report["statistics"]["base_files_copied"] = base_copied
        if base_errors:
            report["warnings"].extend(base_errors)

        # 2. Language-specific templates are intentionally disabled.
        report["statistics"]["language_files_copied"] = 0

        # 3. Apply customizations
        customizations_count = 0
        for file_path in scaffolding_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".md",
                ".json",
                ".yml",
                ".yaml",
                ".txt",
                ".cfg",
            ]:
                # Apply language customization
                success, msg = _customize_file_for_language(file_path, language)
                if success:
                    customizations_count += 1

        report["statistics"]["customizations_applied"] = customizations_count

        # 5. Create required directories
        (scaffolding_dir / ".sdd" / "CANONICAL").mkdir(parents=True, exist_ok=True)
        (scaffolding_dir / "core").mkdir(parents=True, exist_ok=True)
        (scaffolding_dir / "src").mkdir(parents=True, exist_ok=True)

        report["data"] = {
            "scaffolding_dir": str(scaffolding_dir),
            "language": language,
            "total_files": base_copied + report["statistics"]["language_files_copied"],
        }

        report["status"] = "SUCCESS"
        return (True, report)

    except Exception as e:
        report["errors"].append(str(e))
        report["status"] = "FAILED"
        return (False, report)
