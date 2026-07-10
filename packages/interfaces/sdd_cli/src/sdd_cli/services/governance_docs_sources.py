"""Docs-source registry validation and runtime handbook generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY = Path("docs/spec/canonical/governance-sources.yaml")
DEFAULT_HANDBOOK_DIR = Path(".sdd/source/handbook")
RUNTIME_TYPES = {"mandate", "guideline"}
ALLOWED_TYPES = RUNTIME_TYPES | {
    "policy",
    "rule",
    "handbook",
    "feature",
    "docs_only",
    "mirror",
}


@dataclass(frozen=True)
class DocsSourceReport:
    """Structured result for docs governance source validation."""

    ok: bool
    errors: list[str]
    warnings: list[str]
    mandate_ids: list[str]
    guideline_ids: list[str]
    handbook_ids: list[str]


@dataclass(frozen=True)
class HandbookLookupReport:
    """Runtime handbook lookup result for consultive guidance."""

    status: str
    diagnostic: str
    matches: list[dict[str, Any]]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _source_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("sources", [])
    return [entry for entry in entries if isinstance(entry, dict)]


def _entry_ids(entry: dict[str, Any]) -> list[str]:
    raw_ids = entry.get("ids", entry.get("id"))
    if isinstance(raw_ids, str):
        return [raw_ids]
    if isinstance(raw_ids, list):
        return [str(item) for item in raw_ids if str(item).strip()]
    return []


def _active(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "active")).lower() == "active"


def _load_runtime_ids(root: Path, relative_path: str, item_type: str) -> set[str]:
    path = root / relative_path
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("id"))
        for item in items
        if isinstance(item, dict) and str(item.get("type", "")).upper() == item_type
    }


def _metadata_mandate_ids(root: Path) -> set[str]:
    path = root / ".sdd/metadata.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    mandates = data.get("mandates", {})
    if isinstance(mandates, dict):
        return set(str(key) for key in mandates)
    return set()


def _add_duplicate_errors(
    errors: list[str], seen: dict[str, str], entry: dict[str, Any], source_type: str
) -> None:
    path = str(entry.get("path", ""))
    for source_id in _entry_ids(entry):
        previous = seen.get(source_id)
        if previous is not None:
            errors.append(
                f"duplicate active {source_type} id {source_id}: {previous} and {path}"
            )
        seen[source_id] = path


def _validate_entry_shape(
    root: Path, entry: dict[str, Any], errors: list[str], warnings: list[str]
) -> None:
    source_type = str(entry.get("type", "")).lower()
    if source_type not in ALLOWED_TYPES:
        errors.append(f"unsupported source type {source_type!r} for {entry.get('id')}")
    ids = _entry_ids(entry)
    if not ids:
        errors.append(f"source entry missing id/ids for path {entry.get('path')}")
    _validate_entry_path(root, entry, ids, errors)
    _validate_entry_type_contract(entry, ids, source_type, errors, warnings)


def _validate_entry_path(
    root: Path, entry: dict[str, Any], ids: list[str], errors: list[str]
) -> None:
    relative_path = str(entry.get("path", "")).strip()
    if not relative_path:
        errors.append(f"source entry {ids or ['<unknown>']} missing path")
    elif not (root / relative_path).exists():
        errors.append(f"source path does not exist: {relative_path}")


def _validate_entry_type_contract(
    entry: dict[str, Any],
    ids: list[str],
    source_type: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not ids:
        return
    if source_type == "docs_only" and entry.get("outputs"):
        outputs = [str(item) for item in entry.get("outputs", [])]
        runtime_outputs = [item for item in outputs if item.startswith(".sdd/")]
        if runtime_outputs:
            errors.append(f"docs_only source {ids[0]} declares runtime outputs")
    if source_type == "mirror" and not entry.get("source_doc"):
        errors.append(f"mirror source {ids[0]} must declare source_doc")
    if source_type == "handbook" and _active(entry):
        has_refs = bool(
            entry.get("refs")
            or entry.get("task_types")
            or entry.get("operation_phases")
        )
        if not has_refs:
            errors.append(f"handbook source {ids[0]} needs refs, task_types, or phases")
        load_policy = entry.get("load_policy", {})
        if not isinstance(load_policy, dict) or "max_tokens" not in load_policy:
            errors.append(f"handbook source {ids[0]} needs load_policy.max_tokens")
    if source_type in RUNTIME_TYPES and not entry.get("outputs"):
        warnings.append(f"runtime source {ids[0]} has no declared outputs")


def _collect_active_source_ids(
    root: Path,
    entries: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    mandate_seen: dict[str, str] = {}
    guideline_seen: dict[str, str] = {}
    handbook_ids: list[str] = []

    for entry in entries:
        _validate_entry_shape(root, entry, errors, warnings)
        source_type = str(entry.get("type", "")).lower()
        if not _active(entry):
            continue
        if source_type == "mandate":
            _add_duplicate_errors(errors, mandate_seen, entry, source_type)
        elif source_type == "guideline":
            _add_duplicate_errors(errors, guideline_seen, entry, source_type)
        elif source_type == "handbook":
            handbook_ids.extend(_entry_ids(entry))

    return mandate_seen, guideline_seen, handbook_ids


def _append_id_drift_error(
    errors: list[str],
    *,
    label: str,
    registry_ids: set[str],
    runtime_ids: set[str],
) -> None:
    if runtime_ids and registry_ids != runtime_ids:
        errors.append(
            f"{label}: "
            f"missing={sorted(runtime_ids - registry_ids)} "
            f"extra={sorted(registry_ids - runtime_ids)}"
        )


def _declared_handbook_outputs(entries: list[dict[str, Any]]) -> set[Path]:
    outputs: set[Path] = set()
    for entry in entries:
        if str(entry.get("type", "")).lower() != "handbook" or not _active(entry):
            continue
        outputs.add(DEFAULT_HANDBOOK_DIR / "index.yaml")
        for output in entry.get("outputs", []):
            output_path = Path(str(output))
            if str(output_path).startswith(".sdd/source/handbook/"):
                outputs.add(output_path)
    return outputs


def _declared_readable_source_outputs(entries: list[dict[str, Any]]) -> set[Path]:
    outputs: set[Path] = set()
    for entry in entries:
        if str(entry.get("type", "")).lower() == "handbook" and _active(entry):
            outputs.add(DEFAULT_HANDBOOK_DIR / "index.yaml")
        for output in entry.get("outputs", []):
            output_path = Path(str(output))
            if str(output_path).startswith(".sdd/source/"):
                outputs.add(output_path)
    return outputs


def _append_handbook_output_drift(
    root: Path, entries: list[dict[str, Any]], errors: list[str], warnings: list[str]
) -> None:
    declared = _declared_handbook_outputs(entries)
    for output in sorted(declared):
        if not (root / output).exists():
            errors.append(f"handbook runtime output missing: {output}")

    handbook_root = root / DEFAULT_HANDBOOK_DIR
    if not handbook_root.exists():
        return
    actual = {
        path.relative_to(root)
        for path in handbook_root.rglob("*.yaml")
        if path.is_file()
    }
    for output in sorted(actual - declared):
        warnings.append(f"stale handbook runtime output is not declared: {output}")


def _append_readable_source_output_drift(
    root: Path, entries: list[dict[str, Any]], warnings: list[str]
) -> None:
    source_root = root / ".sdd" / "source"
    if not source_root.exists():
        return
    declared = _declared_readable_source_outputs(entries)
    actual = {
        path.relative_to(root)
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix != ".sig"
    }
    for output in sorted(declared - actual):
        warnings.append(f"declared readable runtime output missing: {output}")
    for output in sorted(actual - declared):
        warnings.append(f"stale readable runtime output is not declared: {output}")


def validate_governance_sources(
    root: Path, registry_path: Path | None = None
) -> DocsSourceReport:
    """Validate docs-source registry and compare active IDs with runtime output."""
    registry_file = root / (registry_path or DEFAULT_REGISTRY)
    errors: list[str] = []
    warnings: list[str] = []
    if not registry_file.exists():
        return DocsSourceReport(
            False, [f"missing registry: {registry_file}"], [], [], [], []
        )

    registry = _load_yaml(registry_file)
    entries = _source_entries(registry)
    if str(registry.get("schema_version")) != "1":
        errors.append("governance source registry schema_version must be '1'")

    mandate_seen, guideline_seen, handbook_ids = _collect_active_source_ids(
        root, entries, errors, warnings
    )

    registry_mandates = set(mandate_seen)
    registry_guidelines = set(guideline_seen)
    registry_handbooks = set(handbook_ids)
    metadata_mandates = _metadata_mandate_ids(root)
    compiled_mandates = _load_runtime_ids(
        root, ".sdd/compiled/governance-core.json", "MANDATE"
    )
    compiled_guidelines = _load_runtime_ids(
        root, ".sdd/compiled/governance-client.json", "GUIDELINE"
    )

    _append_id_drift_error(
        errors,
        label="mandate registry drift vs .sdd/metadata.json",
        registry_ids=registry_mandates,
        runtime_ids=metadata_mandates,
    )
    _append_id_drift_error(
        errors,
        label="mandate registry drift vs compiled governance-core.json",
        registry_ids=registry_mandates,
        runtime_ids=compiled_mandates,
    )
    _append_id_drift_error(
        errors,
        label="guideline registry drift vs compiled governance-client.json",
        registry_ids=registry_guidelines,
        runtime_ids=compiled_guidelines,
    )
    handbook_collisions = registry_handbooks & (registry_mandates | registry_guidelines)
    if handbook_collisions:
        errors.append(f"handbook id collision: {sorted(handbook_collisions)}")
    _append_handbook_output_drift(root, entries, errors, warnings)
    _append_readable_source_output_drift(root, entries, warnings)

    return DocsSourceReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        mandate_ids=sorted(registry_mandates),
        guideline_ids=sorted(registry_guidelines),
        handbook_ids=sorted(set(handbook_ids)),
    )


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


def _heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def generate_runtime_handbook(
    root: Path,
    registry_path: Path | None = None,
    output_dir: Path | None = None,
    runtime_root: Path | None = None,
) -> list[Path]:
    """Generate selective runtime handbook entries from docs-source registry."""
    registry_file = root / (registry_path or DEFAULT_REGISTRY)
    if not registry_file.exists():
        return []
    registry = _load_yaml(registry_file)
    target_root = runtime_root or root
    handbook_root = target_root / (output_dir or DEFAULT_HANDBOOK_DIR)
    written: list[Path] = []
    index_items: list[dict[str, Any]] = []

    for entry in _source_entries(registry):
        if str(entry.get("type", "")).lower() != "handbook" or not _active(entry):
            continue
        source_path = root / str(entry["path"])
        metadata = _frontmatter(source_path).get("governance_source", {})
        if not isinstance(metadata, dict):
            metadata = {}
        source_id = _entry_ids(entry)[0]
        outputs = [str(item) for item in entry.get("outputs", [])]
        target = next(
            (
                target_root / item
                for item in outputs
                if item.startswith(".sdd/source/handbook/")
            ),
            handbook_root / f"{source_id.lower()}.yaml",
        )
        item = {
            "id": source_id,
            "title": metadata.get("title")
            or entry.get("title")
            or _heading(source_path),
            "kind": entry.get("kind") or metadata.get("kind", "reference"),
            "status": entry.get("status", metadata.get("status", "active")),
            "source_doc": str(entry["path"]),
            "mandate_refs": list(entry.get("refs", metadata.get("refs", []))),
            "task_types": list(entry.get("task_types", metadata.get("task_types", []))),
            "operation_phases": list(
                entry.get("operation_phases", metadata.get("operation_phases", []))
            ),
            "load_policy": entry.get("load_policy", metadata.get("load_policy", {})),
            "summary": metadata.get("summary", ""),
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(item, sort_keys=False), encoding="utf-8")
        written.append(target)
        index_items.append(
            {
                "id": item["id"],
                "title": item["title"],
                "source_doc": item["source_doc"],
                "runtime_doc": str(target.relative_to(target_root)),
                "mandate_refs": item["mandate_refs"],
                "task_types": item["task_types"],
                "operation_phases": item["operation_phases"],
            }
        )

    handbook_root.mkdir(parents=True, exist_ok=True)
    index_path = handbook_root / "index.yaml"
    index_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1",
                "generated_from": str(registry_file.relative_to(root)),
                "items": index_items,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    written.append(index_path)
    return written


def _matches_any(candidate_values: Any, requested_values: set[str]) -> bool:
    if not requested_values:
        return True
    if not isinstance(candidate_values, list):
        return False
    candidate_set = {str(item) for item in candidate_values}
    return bool(candidate_set & requested_values)


def _load_handbook_item(root: Path, runtime_doc: str) -> dict[str, Any] | None:
    path = root / runtime_doc
    if not path.exists():
        return None
    data = _load_yaml(path)
    return data if data else None


def _entry_matches_lookup(
    entry: dict[str, Any],
    *,
    task_types: set[str],
    phases: set[str],
    refs: set[str],
    risks: set[str],
) -> bool:
    return (
        _matches_any(entry.get("task_types"), task_types)
        and _matches_any(entry.get("operation_phases"), phases)
        and _matches_any(entry.get("mandate_refs"), refs)
        and (not risks or _matches_any(entry.get("risk_levels"), risks))
    )


def _handbook_match_payload(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    runtime_doc = str(entry.get("runtime_doc", ""))
    item = _load_handbook_item(root, runtime_doc) if runtime_doc else None
    return {
        "id": str(entry.get("id", "")),
        "title": str(entry.get("title", "")),
        "source_doc": str(entry.get("source_doc", "")),
        "runtime_doc": runtime_doc,
        "mandate_refs": list(entry.get("mandate_refs", [])),
        "task_types": list(entry.get("task_types", [])),
        "operation_phases": list(entry.get("operation_phases", [])),
        "load_policy": item.get("load_policy", {}) if item else {},
        "summary": str(item.get("summary", "")) if item else "",
    }


def lookup_runtime_handbook(
    root: Path,
    *,
    task_type: str | None = None,
    mandate_refs: list[str] | None = None,
    operation_phase: str | None = None,
    risk_level: str | None = None,
    limit: int = 5,
) -> HandbookLookupReport:
    """Lookup consultive runtime handbook entries without scanning docs/."""
    index_path = root / DEFAULT_HANDBOOK_DIR / "index.yaml"
    if not index_path.exists():
        return HandbookLookupReport(
            status="missing",
            diagnostic="handbook_index_missing",
            matches=[],
        )

    index = _load_yaml(index_path)
    entries = index.get("items", [])
    if not isinstance(entries, list):
        return HandbookLookupReport(
            status="invalid",
            diagnostic="handbook_index_invalid",
            matches=[],
        )

    task_types = {task_type} if task_type else set()
    phases = {operation_phase} if operation_phase else set()
    refs = set(mandate_refs or [])
    risks = {risk_level} if risk_level else set()
    matches: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not _entry_matches_lookup(
            entry,
            task_types=task_types,
            phases=phases,
            refs=refs,
            risks=risks,
        ):
            continue
        matches.append(_handbook_match_payload(root, entry))
        if len(matches) >= limit:
            break

    if not matches:
        return HandbookLookupReport(
            status="none",
            diagnostic="handbook_match=none",
            matches=[],
        )
    return HandbookLookupReport(
        status="matched",
        diagnostic=f"handbook_match={len(matches)}",
        matches=matches,
    )
