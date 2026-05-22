"""Final-template consolidation and layout helpers."""

import shutil
from pathlib import Path
from typing import TypedDict

CONTEXT_CACHE_TEMPLATE = """# SDD Context Cache (M003)

## Current Objective
- [ ] Define objective

## Active Sub-task
- [ ] Define active sub-task

## Completed Milestones
- None yet

## Shared Variables/States
- Profile: unknown
- Governance fingerprint: unknown

## Pending Risks
- None

## Validation Quiz
- Pending
"""


class ConsolidationResult(TypedDict):
    """ConsolidationResult."""

    success: bool
    source_dir: str
    target_dir: str
    moved_items: int
    error: str
    awareness_pack: dict[str, object]


def validate_awareness_pack(target_dir: Path) -> dict[str, object]:
    """Validate skills/commands/CLI awareness artifacts in consolidated output."""
    required_paths = [
        ".sdd/seedlings/ACTIVATION_GUIDE.md",
        "AGENTS.md",
        ".github/prompts",
        ".cursor/rules/sdd-commands.mdc",
        ".gemini/commands.md",
        "CLAUDE.md",
    ]
    missing = [item for item in required_paths if not (target_dir / item).exists()]
    return {
        "status": "ok" if not missing else "incomplete",
        "missing_items": missing,
    }


def ensure_context_cache(target_dir: Path, cache_relative_path: str) -> None:
    """Ensure the context cache file exists (M003 requirement)."""
    cache_file = target_dir / cache_relative_path
    if cache_file.exists():
        return
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(CONTEXT_CACHE_TEMPLATE, encoding="utf-8")


def consolidate_final_template(
    *,
    source_dir: Path,
    target_dir: Path,
    compiled_files: tuple[str, ...],
    audit_files: tuple[str, ...],
    manifest_file: str,
    context_cache_relative_file: str,
) -> ConsolidationResult:
    """Move compiled artifacts into final-template and normalize layout."""
    if not source_dir.exists():
        return {
            "success": False,
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
            "moved_items": 0,
            "error": f"Compiled artifacts directory not found: {source_dir}",
            "awareness_pack": {"status": "incomplete", "missing_items": []},
        }

    source_items = [item for item in source_dir.iterdir()]
    if not source_items:
        return {
            "success": False,
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
            "moved_items": 0,
            "error": f"No artifacts found in {source_dir} to consolidate",
            "awareness_pack": {"status": "incomplete", "missing_items": []},
        }

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in source_items:
        shutil.move(str(item), str(target_dir / item.name))

    organize_final_template_layout(
        target_dir=target_dir,
        compiled_files=compiled_files,
        audit_files=audit_files,
        manifest_file=manifest_file,
        context_cache_relative_file=context_cache_relative_file,
    )

    source_dir.mkdir(parents=True, exist_ok=True)
    awareness_pack = validate_awareness_pack(target_dir)
    return {
        "success": True,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "moved_items": len(source_items),
        "error": "",
        "awareness_pack": awareness_pack,
    }


def organize_final_template_layout(
    *,
    target_dir: Path,
    compiled_files: tuple[str, ...],
    audit_files: tuple[str, ...],
    manifest_file: str,
    context_cache_relative_file: str,
) -> None:
    """Keep runtime governance artifacts under .sdd/ to reduce top-level clutter."""
    sdd_dir = target_dir / ".sdd"
    move_compiled_artifacts(target_dir, sdd_dir, compiled_files)
    move_audit_artifacts(target_dir, sdd_dir, audit_files)
    move_manifest(target_dir, sdd_dir, manifest_file)
    merge_and_normalize_source(target_dir, sdd_dir)
    remove_deployment_only_dirs(target_dir)
    ensure_context_cache(target_dir, context_cache_relative_file)


def move_compiled_artifacts(
    target_dir: Path, sdd_dir: Path, compiled_files: tuple[str, ...]
) -> None:
    """Move governance compiled artifacts to .sdd/compiled."""
    sdd_compiled_dir = sdd_dir / "compiled"
    sdd_audit_dir = sdd_compiled_dir / "audit"
    sdd_compiled_dir.mkdir(parents=True, exist_ok=True)
    sdd_audit_dir.mkdir(parents=True, exist_ok=True)

    for filename in compiled_files:
        top_level_file = target_dir / filename
        nested_file = sdd_compiled_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))


def move_audit_artifacts(
    target_dir: Path, sdd_dir: Path, audit_files: tuple[str, ...]
) -> None:
    """Move JSON governance snapshots and audit dir to .sdd/audit."""
    sdd_audit_dir = sdd_dir / "audit"
    sdd_compiled_audit_dir = sdd_dir / "compiled" / "audit"
    sdd_audit_dir.mkdir(parents=True, exist_ok=True)
    sdd_compiled_audit_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("governance-core.json", "governance-client.json"):
        top_level_file = target_dir / filename
        nested_file = sdd_audit_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))

    top_level_audit_dir = target_dir / "audit"
    if top_level_audit_dir.exists() and top_level_audit_dir.is_dir():
        shutil.copytree(top_level_audit_dir, sdd_audit_dir, dirs_exist_ok=True)
        shutil.rmtree(top_level_audit_dir)

    for filename in audit_files:
        top_level_file = target_dir / filename
        nested_file = sdd_audit_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))

    shutil.copytree(sdd_audit_dir, sdd_compiled_audit_dir, dirs_exist_ok=True)


def move_manifest(target_dir: Path, sdd_dir: Path, manifest_file: str) -> None:
    """Move deployment manifest to .sdd and mirror it in .sdd/compiled/audit."""
    top_level_manifest = target_dir / manifest_file
    sdd_manifest = sdd_dir / manifest_file
    audit_manifest = sdd_dir / "compiled" / "audit" / manifest_file
    if not top_level_manifest.exists():
        return
    sdd_manifest.parent.mkdir(parents=True, exist_ok=True)
    audit_manifest.parent.mkdir(parents=True, exist_ok=True)

    if sdd_manifest.exists():
        sdd_manifest.unlink()
    if audit_manifest.exists():
        audit_manifest.unlink()

    shutil.move(str(top_level_manifest), str(sdd_manifest))
    shutil.copy2(str(sdd_manifest), str(audit_manifest))


def merge_and_normalize_source(target_dir: Path, sdd_dir: Path) -> None:
    """Merge governance source files under .sdd/source."""
    top_level_source = target_dir / "source"
    nested_source = sdd_dir / "source"

    if not (top_level_source.exists() and top_level_source.is_dir()):
        return

    nested_source.mkdir(parents=True, exist_ok=True)
    for item in top_level_source.iterdir():
        destination = nested_source / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
            shutil.rmtree(item)
            continue
        if destination.exists():
            destination.unlink()
        shutil.move(str(item), str(destination))

    if not any(top_level_source.iterdir()):
        top_level_source.rmdir()


def remove_deployment_only_dirs(target_dir: Path) -> None:
    """Remove directories used only in deployment, not in final handoff."""
    backup_dir = target_dir / "backup"
    if backup_dir.exists() and backup_dir.is_dir():
        shutil.rmtree(backup_dir)
