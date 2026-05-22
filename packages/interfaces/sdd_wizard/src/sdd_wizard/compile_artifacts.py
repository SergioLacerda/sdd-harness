#!/usr/bin/env python
"""Compile mandate.spec and guidelines.dsl to runtime artifacts"""

import json
import re
from pathlib import Path
from typing import Any


def parse_mandate_spec(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse mandate.spec DSL format into structured data"""
    mandates = []

    # Find all mandate blocks
    mandate_pattern = r"mandate\s+(\w+)\s*\{([^}]*)\}"

    for match in re.finditer(mandate_pattern, text, re.DOTALL):
        mandate_id = match.group(1)
        mandate_body = match.group(2)

        # Extract fields
        type_match = re.search(r"type:\s*(\w+)", mandate_body)
        title_match = re.search(r'title:\s*"([^"]*)"', mandate_body)
        description_match = re.search(
            r'description:\s*"([^"]*)"', mandate_body, re.DOTALL
        )

        mandate = {
            "id": mandate_id,
            "type": type_match.group(1) if type_match else "UNKNOWN",
            "title": title_match.group(1) if title_match else "",
            "description": (
                description_match.group(1).replace("\n", " ").strip()[:200]
                if description_match
                else ""
            ),
        }
        mandates.append(mandate)

    return len(mandates), mandates


def parse_guidelines_dsl(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse guidelines.dsl DSL format into structured data"""
    guidelines = []

    # Find all guideline blocks
    guideline_pattern = r"guideline\s+(\w+)\s*\{([^}]*)\}"

    guide_num = 0
    for match in re.finditer(guideline_pattern, text, re.DOTALL):
        guide_id = match.group(1)
        guide_body = match.group(2)

        # Extract fields
        type_match = re.search(r"type:\s*(\w+)", guide_body)
        title_match = re.search(r'title:\s*"([^"]*)"', guide_body)
        description_match = re.search(
            r'description:\s*"([^"]*)"', guide_body, re.DOTALL
        )
        category_match = re.search(r"category:\s*(\w+)", guide_body)

        # Extract number from guide_id (G01 -> 1)
        num_match = re.search(r"G(\d+)", guide_id)
        guide_num = int(num_match.group(1)) if num_match else guide_num + 1

        guideline = {
            "id": guide_num,
            "type": type_match.group(1) if type_match else "SOFT",
            "title": title_match.group(1) if title_match else "",
            "description": (
                description_match.group(1).replace("\n", " ").strip()[:300]
                if description_match
                else ""
            ),
            "category": (
                category_match.group(1).lower() if category_match else "general"
            ),
        }
        guidelines.append(guideline)

    return len(guidelines), guidelines


def compile_artifacts(repo_root: Path) -> None:
    """Compile mandate and guidelines to runtime artifacts"""

    # Load source files (moved to _spec in PHASE 4.5)
    mandate_spec_file = repo_root / "_spec" / "mandate.spec"
    guidelines_dsl_file = repo_root / "_spec" / "guidelines.dsl"

    if not mandate_spec_file.exists():
        raise FileNotFoundError(f"mandate.spec not found at {mandate_spec_file}")
    if not guidelines_dsl_file.exists():
        raise FileNotFoundError(f"guidelines.dsl not found at {guidelines_dsl_file}")

    mandate_text = mandate_spec_file.read_text(encoding="utf-8")
    guidelines_text = guidelines_dsl_file.read_text(encoding="utf-8")

    # Parse
    mandate_count, mandates = parse_mandate_spec(mandate_text)
    guideline_count, guidelines = parse_guidelines_dsl(guidelines_text)

    # Create runtime directory
    runtime_dir = repo_root / "runtime"
    runtime_dir.mkdir(exist_ok=True)

    # Write mandate.bin (JSON format)
    mandate_artifact = {
        "version": "3.0",
        "type": "mandate",
        "count": mandate_count,
        "mandates": mandates,
    }
    mandate_bin = runtime_dir / "mandate.bin"
    mandate_bin.write_text(json.dumps(mandate_artifact, indent=2), encoding="utf-8")
    print(f"✅ Compiled mandate.spec → mandate.bin ({mandate_count} mandates)")  # noqa: T201

    # Write guidelines.bin (JSON format)
    guideline_artifact = {
        "version": "3.0",
        "type": "guidelines",
        "count": guideline_count,
        "guidelines": guidelines,
    }
    guidelines_bin = runtime_dir / "guidelines.bin"
    guidelines_bin.write_text(
        json.dumps(guideline_artifact, indent=2), encoding="utf-8"
    )
    print(f"✅ Compiled guidelines.dsl → guidelines.bin ({guideline_count} guidelines)")  # noqa: T201

    # Write metadata.json
    metadata = {
        "compiled_at": "2026-04-22T16:57:00",
        "source": {
            "mandate_spec": {
                "file": "_spec/mandate.spec",
                "count": mandate_count,
                "ids": [m["id"] for m in mandates],
            },
            "guidelines_dsl": {
                "file": "_spec/guidelines.dsl",
                "count": guideline_count,
                "ids": [f"G{g['id']:02d}" for g in guidelines],
            },
        },
        "artifacts": {
            "mandate": "runtime/mandate.bin",
            "guidelines": "runtime/guidelines.bin",
        },
    }
    metadata_file = runtime_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("✅ Created metadata.json")  # noqa: T201

    print("\n🎉 Compilation complete!")  # noqa: T201
    print(f"  - {mandate_count} mandates")  # noqa: T201
    print(f"  - {guideline_count} guidelines")  # noqa: T201
    print("  - 3 artifact files")  # noqa: T201


if __name__ == "__main__":
    repo_root = Path.cwd()
    compile_artifacts(repo_root)
