"""Phase 4 Filter Guidelines."""

from pathlib import Path
from typing import Any

"""Phase 4: Filter guidelines by language and adoption level

This phase takes guidelines from Phase 2 and filters them based on:
1. Language (java, python, js)
2. Adoption level (LITE/FULL)

Note: Full adoption level filtering implementation pending guideline
priority metadata in compiled format.
"""

# Language tags that identify guidelines relevant to specific languages
LANGUAGE_TAGS = {
    "java": {
        "java",
        "jvm",
        "maven",
        "spring",
        "gradle",
        "checkstyle",
        "pmd",
        "spotbugs",
        "archunit",
    },
    "python": {
        "python",
        "pip",
        "pytest",
        "django",
        "flask",
        "poetry",
        "ruff",
        "mypy",
        "import-linter",
    },
    "js": {
        "javascript",
        "nodejs",
        "npm",
        "typescript",
        "react",
        "vue",
        "eslint",
        "tsc",
        "jest",
        "vitest",
    },
    "go": {"go", "golang", "golangci-lint", "go-vet", "gofmt"},
}


def filter_guidelines_by_language(
    guidelines: dict[str, Any], language: str
) -> tuple[dict[str, Any], list[str]]:
    """
    Filter guidelines by language relevance

    Guidelines without language tags are universal and always included.
    Guidelines with language tags are only included if they match the target language.

    Args:
        guidelines: Dictionary of all guidelines
        language: Target language (java, python, js)

    Returns:
        (filtered_guidelines, removed_ids)
    """
    filtered = {}
    removed = []
    lang_tags = LANGUAGE_TAGS.get(language, set())

    for guide_id, guide in guidelines.items():
        tags = guide.get("tags", [])

        # If no tags specified, guideline is universal
        if not tags:
            filtered[guide_id] = guide
            continue

        # If tags present, check if any match target language
        tags_set = set(tag.lower() for tag in tags)
        if tags_set & lang_tags:  # Intersection
            filtered[guide_id] = guide
        else:
            removed.append(guide_id)

    return (filtered, removed)


def phase_4_filter_guidelines(
    guidelines: dict[str, Any],
    language: str = "python",
    repo_root: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Filter guidelines by language and adoption level

    In v3.0, filtering is based on:
    - Language selection (user choice during Phase 1)
    - Adoption level selection (user choice during Phase 1)
    - CORE+CLIENT separation (immutable core, customizable client)

    Args:
        guidelines: Dictionary of all guidelines from Phase 2
        language: Target language (java, python, js)
        repo_root: Repository root (for logging context)

    Returns:
        (success: bool, report: Dict)
        report contains:
            - phase: 'PHASE_4_FILTER_GUIDELINES'
            - status: 'SUCCESS' | 'WARNING' | 'FAILED'
            - checks: dict of validation checks performed
            - data: dict with filtered_guidelines and filtering_details
            - statistics: counts and percentages
            - errors: list of error messages
            - warnings: list of warning messages
    """

    report: dict[str, Any] = {
        "phase": "PHASE_4_FILTER_GUIDELINES",
        "status": "PENDING",
        "checks": {
            "guidelines_provided": False,
            "language_valid": False,
            "language_filtering_applied": False,
        },
        "data": {
            "filtered_guidelines": {},
            "language": language,
            "filtering_details": {
                "language_removed": [],
            },
        },
        "statistics": {
            "total_guidelines": len(guidelines),
            "after_language_filter": 0,
            "language_filter_percentage": 0.0,
        },
        "errors": [],
        "warnings": [],
    }

    # Step 1: Validate input
    if not guidelines:
        report["errors"].append("No guidelines provided from Phase 2")
        report["status"] = "FAILED"
        return (False, report)

    report["checks"]["guidelines_provided"] = True

    # Step 2: Validate language
    valid_languages = set(LANGUAGE_TAGS.keys())
    if language not in valid_languages:
        report["errors"].append(f"Invalid language: {language}")
        report["errors"].append(f"Valid languages: {sorted(valid_languages)}")
        report["status"] = "FAILED"
        return (False, report)

    report["checks"]["language_valid"] = True

    # Step 3: Apply language filter only
    language_filtered, language_removed = filter_guidelines_by_language(
        guidelines, language
    )

    report["checks"]["language_filtering_applied"] = True
    report["data"]["filtering_details"]["language_removed"] = language_removed
    report["statistics"]["after_language_filter"] = len(language_filtered)

    if report["statistics"]["total_guidelines"] > 0:
        pct = (len(language_filtered) / report["statistics"]["total_guidelines"]) * 100
        report["statistics"]["language_filter_percentage"] = round(pct, 1)

    # Step 5: Validate result
    if not language_filtered:
        report["errors"].append("Filtering resulted in zero guidelines")
        report["status"] = "FAILED"
        return (False, report)

    report["data"]["filtered_guidelines"] = language_filtered
    report["status"] = "SUCCESS"

    return (True, report)
