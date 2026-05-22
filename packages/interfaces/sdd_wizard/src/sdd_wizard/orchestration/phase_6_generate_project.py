"""Phase 6 Generate Project."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

"""Phase 6: Generate complete project structure

Generates the final project with specifications, guidelines, and language-specific structure
"""


def _create_project_directories(project_dir: Path) -> tuple[bool, list[str]]:
    """Create all required project directories

    Returns:
        (success, messages)
    """
    messages = []

    try:
        dirs = [
            project_dir / ".sdd" / "CANONICAL",
            project_dir / "guidelines",
            project_dir / "src",
            project_dir / "tests",
            project_dir / ".github" / "workflows",
            project_dir / "docs",
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
            messages.append(f"Created: {directory.relative_to(project_dir)}")

        return (True, messages)
    except Exception as e:
        return (False, [f"Error creating directories: {e}"])


def _write_specification_files(
    project_dir: Path, mandate_text: str, guidelines_text: str, metadata: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Write specification files to .sdd/CANONICAL/

    Returns:
        (success, messages)
    """
    messages = []

    try:
        dir = project_dir / ".sdd" / "CANONICAL"

        # Write mandate.spec
        mandate_file = dir / "mandate.spec"
        mandate_file.write_text(mandate_text, encoding="utf-8")
        messages.append(f"Generated: {mandate_file.relative_to(project_dir)}")

        # Write guidelines.dsl
        guidelines_file = dir / "guidelines.dsl"
        guidelines_file.write_text(guidelines_text, encoding="utf-8")
        messages.append(f"Generated: {guidelines_file.relative_to(project_dir)}")

        # Write metadata.json
        metadata_file = dir / "metadata.json"
        metadata_with_timestamp = {
            **metadata,
            "generated_at": datetime.now().isoformat(),
            "generation_phase": "phase_6",
        }
        metadata_file.write_text(
            json.dumps(metadata_with_timestamp, indent=2), encoding="utf-8"
        )
        messages.append(f"Generated: {metadata_file.relative_to(project_dir)}")

        return (True, messages)
    except Exception as e:
        return (False, [f"Error writing specification files: {e}"])


def _generate_guideline_markdowns(
    project_dir: Path, guidelines: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Generate markdown files for guidelines

    Args:
        project_dir: Project output directory
        guidelines: Filtered guidelines dict

    Returns:
        (success, messages)
    """
    messages = []

    try:
        guidelines_dir = project_dir / "guidelines"

        # Create index markdown
        index_content = "# Guidelines Reference\n\n"
        index_content += f"Generated: {datetime.now().isoformat()}\n\n"
        index_content += f"Total Guidelines: {len(guidelines)}\n\n"
        index_content += "## Guidelines\n\n"

        # Generate individual guideline files
        for guide_id, guide in guidelines.items():
            # Create guideline markdown
            title = guide.get("title", "Untitled")
            description = guide.get("description", "No description")

            guideline_content = f"# {title}\n\n"
            guideline_content += f"**ID:** {guide_id}\n\n"
            guideline_content += f"## Description\n\n{description}\n\n"

            if guide.get("examples"):
                guideline_content += f"## Examples\n\n{guide['examples']}\n\n"

            # Write guideline file
            guideline_file = guidelines_dir / f"{guide_id}.md"
            guideline_file.write_text(guideline_content, encoding="utf-8")

            # Add to index
            index_content += f"- [{title}]({guide_id}.md)\n"

        # Write index
        index_file = guidelines_dir / "README.md"
        index_file.write_text(index_content, encoding="utf-8")

        messages.append(f"Generated: {len(guidelines)} guideline markdown files")
        messages.append(f"Generated: {index_file.relative_to(project_dir)}")

        return (True, messages)
    except Exception as e:
        return (False, [f"Error generating guideline markdowns: {e}"])


def _generate_build_files(
    project_dir: Path, language: str, metadata: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Generate language-specific build files

    Args:
        project_dir: Project output directory
        language: Target language (java|python|js)
        metadata: Project metadata

    Returns:
        (success, messages)
    """
    messages = []

    try:
        if language == "java":
            # Generate pom.xml
            pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.sdd.generated</groupId>
    <artifactId>project</artifactId>
    <version>1.0.0</version>

    <name>SDD Project Seed</name>
    <description>Project generated from SDD v3.0 specifications</description>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
</project>"""
            pom_file = project_dir / "pom.xml"
            pom_file.write_text(pom_content, encoding="utf-8")
            messages.append(f"Generated: {pom_file.relative_to(project_dir)}")

        elif language == "python":
            # Generate requirements.txt
            requirements_content = """# Generated from SDD v3.0
# Add your dependencies here
pytest>=7.0
"""
            req_file = project_dir / "requirements.txt"
            req_file.write_text(requirements_content, encoding="utf-8")
            messages.append(f"Generated: {req_file.relative_to(project_dir)}")

            # Generate pyproject.toml
            pyproject_content = """[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sdd-project-seed"
version = "1.0.0"
description = "Project generated from SDD v3.0 specifications"

[project.optional-dependencies]
dev = ["pytest>=7.0"]
"""
            pyproject_file = project_dir / "pyproject.toml"
            pyproject_file.write_text(pyproject_content, encoding="utf-8")
            messages.append(f"Generated: {pyproject_file.relative_to(project_dir)}")

        elif language == "js":
            # Generate package.json
            package_content = json.dumps(
                {
                    "name": "sdd-project-seed",
                    "version": "1.0.0",
                    "description": "Project generated from SDD v3.0 specifications",
                    "main": "src/index.js",
                    "scripts": {
                        "test": "jest",
                        "dev": "node src/index.js",
                    },
                    "devDependencies": {
                        "jest": "^29.0.0",
                    },
                },
                indent=2,
            )
            package_file = project_dir / "package.json"
            package_file.write_text(package_content, encoding="utf-8")
            messages.append(f"Generated: {package_file.relative_to(project_dir)}")

        return (True, messages)
    except Exception as e:
        return (False, [f"Error generating build files: {e}"])


def _generate_readme(
    project_dir: Path,
    language: str,
    mandates: dict[str, Any],
    guidelines_count: int,
) -> tuple[bool, list[str]]:
    """Generate main README.md

    Returns:
        (success, messages)
    """
    messages = []

    try:
        readme_content = f"""# SDD Project Seed

**Generated:** {datetime.now().isoformat()}

## Overview

This project was generated from SDD v3.0 specifications.

### Language
- **Target:** {language.upper()}

### Specifications
- **Mandates:** {len(mandates)}
- **Guidelines:** {guidelines_count}

### Structure

```
.
├── .sdd/                    # Compiled specifications (read-only)
│   └── CANONICAL/
│       ├── mandate.spec     # Mandate specifications
│       ├── guidelines.dsl   # Design guidelines
│       └── metadata.json    # Generation metadata
├── guidelines/         # Organized guidelines
├── src/                     # Source code
├── tests/                   # Test files
└── docs/                    # Documentation
```

### Mandates

"""

        for mandate_id, mandate in mandates.items():
            title = mandate.get("title", "Untitled")
            readme_content += f"- **{mandate_id}**: {title}\n"

        readme_content += """

### Getting Started

1. Review specifications in `.sdd/CANONICAL/`
2. Check guidelines in `guidelines/`
3. Follow the architecture patterns
4. Run tests: `pytest` (Python) or `mvn test` (Java) or `npm test` (JS)

### Guidelines

For detailed guidelines, see `guidelines/README.md`

---

**Generated by SDD v3.0 Wizard**
"""

        readme_file = project_dir / "README.md"
        readme_file.write_text(readme_content, encoding="utf-8")
        messages.append(f"Generated: {readme_file.relative_to(project_dir)}")

        return (True, messages)
    except Exception as e:
        return (False, [f"Error generating README: {e}"])


def phase_6_generate_project(
    filtered_mandates: dict[str, Any],
    filtered_guidelines: dict[str, Any],
    mandate_text: str,
    guidelines_text: str,
    metadata: dict[str, Any],
    output_dir: Path,
    language: str = "python",
    repo_root: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Generate complete project structure

    Args:
        filtered_mandates: Mandates from Phase 3
        filtered_guidelines: Guidelines from Phase 4
        mandate_text: Original mandate text from Phase 1
        guidelines_text: Original guidelines text from Phase 1
        metadata: Metadata from Phase 2
        output_dir: Output directory for generated project
        language: Target language
        repo_root: Repository root

    Returns:
        (success, report)
    """
    report: dict[str, Any] = {
        "phase": "PHASE_6_GENERATE_PROJECT",
        "status": "PENDING",
        "data": {},
        "statistics": {
            "directories_created": 0,
            "files_generated": 0,
            "specifications_written": 3,  # mandate, guidelines, metadata
            "guideline_markdowns": len(filtered_guidelines),
            "build_files": 1,
        },
        "warnings": [],
        "errors": [],
    }

    try:
        # 1. Create project directories
        success, messages = _create_project_directories(output_dir)
        if not success:
            report["errors"].extend(messages)
            report["status"] = "FAILED"
            return (False, report)
        report["statistics"]["directories_created"] = len(messages)

        # 2. Write specification files
        success, messages = _write_specification_files(
            output_dir, mandate_text, guidelines_text, metadata
        )
        if not success:
            report["errors"].extend(messages)
        else:
            report["statistics"]["files_generated"] += 3

        # 3. Generate guideline markdowns
        success, messages = _generate_guideline_markdowns(
            output_dir, filtered_guidelines
        )
        if not success:
            report["warnings"].extend(messages)
        else:
            report["statistics"]["files_generated"] += 1

        # 4. Generate build files
        success, messages = _generate_build_files(output_dir, language, metadata)
        if not success:
            report["warnings"].extend(messages)
        else:
            report["statistics"]["files_generated"] += 1

        # 5. Generate README
        success, messages = _generate_readme(
            output_dir, language, filtered_mandates, len(filtered_guidelines)
        )
        if not success:
            report["warnings"].extend(messages)
        else:
            report["statistics"]["files_generated"] += 1

        report["data"] = {
            "output_dir": str(output_dir),
            "language": language,
            "mandates_count": len(filtered_mandates),
            "guidelines_count": len(filtered_guidelines),
            "total_files_generated": report["statistics"]["files_generated"],
        }

        report["status"] = "SUCCESS"
        return (True, report)

    except Exception as e:
        report["errors"].append(str(e))
        report["status"] = "FAILED"
        return (False, report)
