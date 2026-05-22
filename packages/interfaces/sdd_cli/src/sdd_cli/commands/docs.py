"""Docs."""

import json
import os
import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import typer

from sdd_core.utils.environment import get_sdd_paths

app = typer.Typer(help="Documentation commands")


@dataclass(frozen=True)
class DiscoveredItem:
    """DiscoveredItem."""

    id: str
    title: str
    type: str
    category: str
    source_path: str
    group: str
    confidence: int


DEFAULT_BLACKLIST = ("archive", "spec/reality", "spec/reference")


def _detect_group(relative_path: Path) -> str:
    as_posix = relative_path.as_posix()
    if "/canonical/" in f"/{as_posix}":
        return "canonical"
    if "/decisions/" in f"/{as_posix}":
        return "decisions"
    if "/guides/" in f"/{as_posix}":
        return "guides"
    return "other"


def _detect_category(relative_path: Path) -> str:
    parts = relative_path.parts
    if "canonical" in parts:
        idx = parts.index("canonical")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if "decisions" in parts:
        return "decisions"
    if "guides" in parts:
        return "guides"
    return "general"


def _source_priority(relative_path: str) -> int:
    """Higher score means better source candidate for canonical item extraction."""
    normalized = f"/{relative_path}"
    priorities = [
        "/spec/canonical/core/mandates/",
        "/spec/canonical/core/guidelines/",
        "/spec/canonical/core/",
        "/spec/canonical/",
        "/spec/decisions/",
        "/spec/guides/",
    ]
    for idx, marker in enumerate(priorities):
        if marker in normalized:
            return len(priorities) - idx
    return 0


def _is_guideline_definition_path(relative_path: Path) -> bool:
    normalized = f"/{relative_path.as_posix()}"
    markers = [
        "/spec/canonical/core/guidelines/",
        "/spec/guides/",
        "/guidelines/",
    ]
    return any(marker in normalized for marker in markers)


def _is_mandate_definition_path(relative_path: Path) -> bool:
    normalized = f"/{relative_path.as_posix()}"
    markers = [
        "/spec/canonical/core/mandates/",
        "/spec/canonical/features/",
        "/spec/decisions/",
        "/spec/guides/",
    ]
    return any(marker in normalized for marker in markers)


def _sanitize(value: str) -> str:
    return value.replace('"', '\\"').strip()


_ADR_METADATA_PATTERN = re.compile(r"^-\s+\w[\w\s]*:\s+\S", re.IGNORECASE)


def _extract_first_sentence(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # Skip ADR frontmatter metadata lines like "- Status: Accepted", "- Date: ..."
        if _ADR_METADATA_PATTERN.match(stripped):
            continue
        return stripped[:280]
    return "No description provided"


def _extract_heading_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip()
        title = re.sub(r"^Mandate:\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"^Guideline:\s*", "", title, flags=re.IGNORECASE)
        return title
    return ""


def _parse_markdown_items(content: str, relative_path: Path) -> list[DiscoveredItem]:
    items: list[DiscoveredItem] = []
    group = _detect_group(relative_path)
    category = _detect_category(relative_path)
    allow_guideline_patterns = _is_guideline_definition_path(relative_path)
    allow_mandate_patterns = _is_mandate_definition_path(relative_path)

    heading_title = _extract_heading_title(content)

    # Most reliable format in canonical mandate files:
    # **ID:** M001 (+ title from heading)
    for match in re.finditer(r"\*\*ID:\*\*\s*((?:M\d{3})|(?:G\d{2,3}))", content):
        item_id = match.group(1)
        if item_id.startswith("M") and not allow_mandate_patterns:
            continue
        item_type = "MANDATE" if item_id.startswith("M") else "GUIDELINE"
        title = heading_title or item_id
        items.append(
            DiscoveredItem(
                id=item_id,
                title=title,
                type=item_type,
                category=category,
                source_path=relative_path.as_posix(),
                group=group,
                confidence=100,
            )
        )

    # Matches: - [M001] **Title**
    for match in re.finditer(
        r"-\s*\[((?:M\d{3})|(?:G\d{2,3}))\]\s*\*\*([^*]+)\*\*", content
    ):
        item_id = match.group(1)
        if item_id.startswith("M") and not allow_mandate_patterns:
            continue
        if item_id.startswith("G") and not allow_guideline_patterns:
            continue
        title = match.group(2).strip()
        item_type = "MANDATE" if item_id.startswith("M") else "GUIDELINE"
        items.append(
            DiscoveredItem(
                id=item_id,
                title=title,
                type=item_type,
                category=category,
                source_path=relative_path.as_posix(),
                group=group,
                confidence=80,
            )
        )

    # Matches headings: ## M001: Title or ## G001 - Title
    for match in re.finditer(
        r"^#{1,3}\s*((?:M\d{3})|(?:G\d{2,3}))\s*[:\-]\s*(.+)$", content, re.MULTILINE
    ):
        item_id = match.group(1)
        if item_id.startswith("M") and not allow_mandate_patterns:
            continue
        if item_id.startswith("G") and not allow_guideline_patterns:
            continue
        title = match.group(2).strip()
        item_type = "MANDATE" if item_id.startswith("M") else "GUIDELINE"
        items.append(
            DiscoveredItem(
                id=item_id,
                title=title,
                type=item_type,
                category=category,
                source_path=relative_path.as_posix(),
                group=group,
                confidence=70,
            )
        )

    items.extend(
        _parse_dsl_items(
            content, allow_guideline_patterns, category, group, relative_path
        )
    )

    if not items:
        items.extend(
            _parse_fallback_item(
                content,
                allow_guideline_patterns,
                allow_mandate_patterns,
                category,
                group,
                relative_path,
            )
        )

    return items


def _parse_dsl_items(
    content: str,
    allow_guideline_patterns: bool,
    category: str,
    group: str,
    relative_path: Path,
) -> list[DiscoveredItem]:
    """Parse DSL block format embedded in markdown (mandate M001 { … } / guideline G01 { … })."""
    items: list[DiscoveredItem] = []
    for match in re.finditer(r"mandate\s+(M\d{3})\s*\{([^}]+)\}", content, re.DOTALL):
        item_id = match.group(1)
        block = match.group(2)
        title_m = re.search(r'title:\s*"([^"]+)"', block)
        items.append(
            DiscoveredItem(
                id=item_id,
                title=title_m.group(1).strip() if title_m else item_id,
                type="MANDATE",
                category=category,
                source_path=relative_path.as_posix(),
                group=group,
                confidence=40,
            )
        )
    if allow_guideline_patterns:
        for match in re.finditer(
            r"guideline\s+(G\d{2,3})\s*\{([^}]+)\}", content, re.DOTALL
        ):
            item_id = match.group(1)
            block = match.group(2)
            title_m = re.search(r'title:\s*"([^"]+)"', block)
            items.append(
                DiscoveredItem(
                    id=item_id,
                    title=title_m.group(1).strip() if title_m else item_id,
                    type="GUIDELINE",
                    category=category,
                    source_path=relative_path.as_posix(),
                    group=group,
                    confidence=40,
                )
            )
    return items


def _parse_fallback_item(
    content: str,
    allow_guideline_patterns: bool,
    allow_mandate_patterns: bool,
    category: str,
    group: str,
    relative_path: Path,
) -> list[DiscoveredItem]:
    """Fallback: infer a single item from the first ID mention in the file."""
    inferred = re.search(r"\b((?:M\d{3})|(?:G\d{2,3}))\b", content)
    if not inferred:
        return []
    item_id = inferred.group(1)
    if item_id.startswith("M") and not allow_mandate_patterns:
        return []
    if item_id.startswith("G") and not allow_guideline_patterns:
        return []
    return [
        DiscoveredItem(
            id=item_id,
            title=_extract_first_sentence(content),
            type="MANDATE" if item_id.startswith("M") else "GUIDELINE",
            category=category,
            source_path=relative_path.as_posix(),
            group=group,
            confidence=10,
        )
    ]


def _deduplicate_items(
    discovered: list[DiscoveredItem],
) -> tuple[dict[str, DiscoveredItem], dict[str, list[str]]]:
    """Resolve duplicates deterministically; return (by_id, duplicates_report)."""
    by_id: dict[str, DiscoveredItem] = {}
    duplicates: dict[str, list[str]] = {}
    for item in discovered:
        existing = by_id.get(item.id)
        if existing and existing.source_path != item.source_path:
            duplicates.setdefault(item.id, [existing.source_path]).append(
                item.source_path
            )
            if item.confidence > existing.confidence:
                by_id[item.id] = item
                continue
            if item.confidence < existing.confidence:
                continue
            current_score = _source_priority(existing.source_path)
            candidate_score = _source_priority(item.source_path)
            if candidate_score > current_score or (
                candidate_score == current_score
                and item.source_path < existing.source_path
            ):
                by_id[item.id] = item
            continue
        by_id[item.id] = item
    return by_id, duplicates


def _is_blacklisted(relative_path: Path, blacklist: Iterable[str]) -> bool:
    normalized = relative_path.as_posix()
    for entry in blacklist:
        prefix = entry.strip().lstrip("/")
        if not prefix:
            continue
        if normalized.startswith(prefix):
            return True
    return False


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(target)


def _build_mandate_spec(items: list[DiscoveredItem]) -> str:
    lines: list[str] = ["# Generated by sdd docs update", ""]
    mandates = sorted(
        (item for item in items if item.type == "MANDATE"), key=lambda i: i.id
    )
    for mandate in mandates:
        lines.extend(
            [
                f"mandate {mandate.id} {{",
                '  type: "MANDATE"',
                f'  title: "{_sanitize(mandate.title)}"',
                f'  description: "{_sanitize(mandate.title)}"',
                f'  category: "{_sanitize(mandate.category)}"',
                f'  rationale: "Derived from {mandate.source_path}"',
                "}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_guidelines_dsl(items: list[DiscoveredItem]) -> str:
    lines: list[str] = ["# Generated by sdd docs update", ""]
    guidelines = sorted(
        (item for item in items if item.type == "GUIDELINE"), key=lambda i: i.id
    )
    for guideline in guidelines:
        lines.extend(
            [
                f"guideline {guideline.id} {{",
                '  type: "GUIDELINE"',
                f'  title: "{_sanitize(guideline.title)}"',
                f'  description: "{_sanitize(guideline.title)}"',
                f'  category: "{_sanitize(guideline.category)}"',
                "}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_discovery_index(items: list[DiscoveredItem]) -> str:
    payload = {
        "generated_by": "sdd docs update",
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "type": item.type,
                "category": item.category,
                "group": item.group,
                "source_path": item.source_path,
            }
            for item in sorted(items, key=lambda i: i.id)
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


@app.callback()
def _() -> None:
    """Documentation operations."""


@app.command("deploy")
def deploy(force: bool = typer.Option(True, help="Force deploy to gh-pages")) -> None:
    """Deploy MkDocs documentation if mkdocs config exists."""
    config_files = [Path("mkdocs.yml"), Path("mkdocs.yaml")]
    if not any(cfg.exists() for cfg in config_files):
        typer.echo(
            "No mkdocs config found (mkdocs.yml/mkdocs.yaml). Skipping docs deploy."
        )
        return

    if shutil.which("mkdocs") is None:
        typer.echo(
            "ERROR: mkdocs command not found. Install with: pip install mkdocs mkdocs-material"
        )
        raise typer.Exit(1)

    from sdd_core.utils.process import (
        AUTHORIZED_BINARIES,
        ProcessAuthorizationError,
        ProcessNonZeroExitError,
        ProcessSpawnError,
        ProcessTimeoutError,
        SafeProcessRunner,
    )

    cmd = ["mkdocs", "gh-deploy"]
    if force:
        cmd.append("--force")

    try:
        # Extend authorized binaries (don't replace) to maintain governance integrity
        runner = SafeProcessRunner(authorized_binaries=AUTHORIZED_BINARIES | {"mkdocs"})
        runner.run(cmd, check=True, capture_output=False)
    except ProcessNonZeroExitError as err:
        typer.echo(f"ERROR: docs deploy failed: {err}", err=True)
        raise typer.Exit(1) from None
    except ProcessAuthorizationError as err:
        typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
        raise typer.Exit(2) from None
    except ProcessTimeoutError:
        typer.echo("ERROR: docs deploy timed out", err=True)
        raise typer.Exit(124) from None
    except ProcessSpawnError as err:
        typer.echo(f"ERROR: could not start docs deploy: {err}", err=True)
        raise typer.Exit(127) from None


@app.command("update")
def update(
    dry_run: bool = typer.Option(
        False, help="Preview discovery without writing docs-meta artifacts"
    ),
) -> None:
    """Discover markdown canonical docs and generate docs-meta artifacts for wizard consumption."""
    paths = get_sdd_paths()
    docs_root = paths["root"] / "docs"
    output_dir = paths["client_build"] / "docs-meta"

    if not docs_root.exists():
        typer.echo(f"ERROR: docs directory not found: {docs_root}")
        raise typer.Exit(1)

    md_files = sorted(path for path in docs_root.rglob("*.md") if path.is_file())
    discovered: list[DiscoveredItem] = []
    blacklisted_count = 0

    for md_file in md_files:
        relative = md_file.relative_to(docs_root)
        if _is_blacklisted(relative, DEFAULT_BLACKLIST):
            blacklisted_count += 1
            continue

        content = md_file.read_text(encoding="utf-8", errors="ignore")
        discovered.extend(_parse_markdown_items(content, relative))

    if not discovered:
        typer.echo("ERROR: no governance items discovered from markdown docs")
        raise typer.Exit(1)

    by_id, duplicates = _deduplicate_items(discovered)

    if duplicates and os.getenv("SDD_DOCS_WARN_DUPLICATES", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        typer.echo("WARN: duplicate IDs found; using deterministic source precedence:")
        for item_id, sources in sorted(duplicates.items()):
            unique_sources = sorted(set(sources))
            selected = by_id[item_id].source_path
            typer.echo(
                f"  - {item_id}: selected={selected}; candidates={', '.join(unique_sources)}"
            )

    items = sorted(by_id.values(), key=lambda item: item.id)
    mandate_spec = _build_mandate_spec(items)
    guidelines_dsl = _build_guidelines_dsl(items)
    discovery_index = _build_discovery_index(items)

    typer.echo(
        "Discovery summary: "
        f"files_scanned={len(md_files)}, blacklisted={blacklisted_count}, "
        f"items={len(items)}"
    )

    if dry_run:
        typer.echo("Dry-run enabled: no files were written.")
        return

    _atomic_write(output_dir / "mandate.spec", mandate_spec)
    _atomic_write(output_dir / "guidelines.dsl", guidelines_dsl)
    _atomic_write(output_dir / "discovery-index.json", discovery_index)

    typer.echo(f"Generated docs-meta artifacts in: {output_dir}")
