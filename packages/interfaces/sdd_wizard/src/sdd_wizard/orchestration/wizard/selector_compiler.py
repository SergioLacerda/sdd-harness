"""Compile governed selector data and static assets."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ._selector_models import (
    SelectorItem,
    _bool_or_default,
    _list_or_default,
    _now,
    _parse_section_body,
    _require_text,
    _text_or_default,
    _validate_dependencies,
    _validate_unique_ids,
    _write_json,
)


@dataclass
class SelectorCompiler:
    """Compile selector payload from governed mandate and guideline sources."""

    repo_root: Path
    asset_source_dir: Path | None = None

    def build_payload(self) -> dict[str, object]:
        """Build the selector payload."""
        items = self._build_items()
        return {
            "version": "1.0",
            "generated_at": _now(),
            "items": [item.to_dict() for item in items],
        }

    def build_site(self, output_dir: Path) -> Path:
        """Write data.json and static assets into a site directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "data.json", self.build_payload())
        self._copy_assets(output_dir)
        return output_dir

    def _build_items(self) -> list[SelectorItem]:
        if not self._metadata_path().exists() or not self._mandates_path().exists():
            import sys

            print(
                f"[selector_compiler] WARN: governance artifacts not found at {self.repo_root / '.sdd'}. "
                "Run 'sdd governance generate' to populate. Emitting empty selector.",
                file=sys.stderr,
            )
            return []
        metadata = self._load_metadata()
        sections = self._parse_mandate_sections()
        mandate_items = [
            self._build_item(item_id, metadata, sections, "mandate")
            for item_id in metadata
        ]

        guideline_items: list[SelectorItem] = []
        if self._guidelines_path().exists():
            g_metadata = self._load_guidelines_metadata()
            g_sections = self._parse_guideline_dsl_sections()
            guideline_items = [
                self._build_item(gid, g_metadata, g_sections, "guideline")
                for gid in g_metadata
            ]

        all_items = mandate_items + guideline_items
        _validate_unique_ids(all_items)
        _validate_dependencies(all_items)
        return all_items

    def _build_item(
        self,
        item_id: str,
        metadata: dict[str, str],
        sections: dict[str, dict[str, object]],
        item_type: str = "mandate",
    ) -> SelectorItem:
        section = sections.get(item_id)
        if section is None:
            raise ValueError(f"Missing selector section for {item_id}")
        return SelectorItem(
            id=item_id,
            title=metadata[item_id],
            description=_require_text(section.get("description"), item_id),
            category=_text_or_default(section.get("category"), item_type),
            mandatory=_bool_or_default(section.get("mandatory"), True),
            tags=_list_or_default(section.get("tags"), [item_type]),
            depends_on=_list_or_default(section.get("depends_on"), []),
            item_type=item_type,
        )

    def _load_metadata(self) -> dict[str, str]:
        payload = json.loads(self._metadata_path().read_text(encoding="utf-8"))
        mandates = payload.get("mandates")
        if not isinstance(mandates, dict):
            raise ValueError(".sdd/metadata.json mandates must be a mapping.")
        return {str(key): str(value) for key, value in mandates.items()}

    def _load_guidelines_metadata(self) -> dict[str, str]:
        """Parse guidelines.dsl and return {id: title} mapping."""
        content = self._guidelines_path().read_text(encoding="utf-8")
        result: dict[str, str] = {}
        for match in re.finditer(
            r"guideline\s+(\w+)\s*\{([^}]+)\}", content, re.MULTILINE | re.DOTALL
        ):
            gid = match.group(1)
            body = match.group(2)
            title_match = re.search(r'title:\s*"([^"]*)"', body)
            if title_match:
                result[gid] = title_match.group(1)
        return result

    def _parse_mandate_sections(self) -> dict[str, dict[str, object]]:
        content = self._mandates_path().read_text(encoding="utf-8")
        matches = list(re.finditer(r"^## (M\d+): (.+)$", content, flags=re.MULTILINE))
        sections: dict[str, dict[str, object]] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = (
                matches[index + 1].start() if index + 1 < len(matches) else len(content)
            )
            section_body = content[start:end].strip()
            item_id = match.group(1)
            if item_id in sections:
                raise ValueError(f"Duplicate mandate section for {item_id}")
            sections[item_id] = _parse_section_body(section_body)
        return sections

    def _parse_guideline_dsl_sections(self) -> dict[str, dict[str, object]]:
        """Parse all guideline blocks from guidelines.dsl."""
        content = self._guidelines_path().read_text(encoding="utf-8")
        sections: dict[str, dict[str, object]] = {}
        for match in re.finditer(
            r"guideline\s+(\w+)\s*\{([^}]+)\}", content, re.MULTILINE | re.DOTALL
        ):
            gid = match.group(1)
            sections[gid] = self._parse_guideline_dsl_block(match.group(2))
        return sections

    def _parse_guideline_dsl_block(self, body: str) -> dict[str, object]:
        """Extract fields from a single guideline DSL block body."""
        desc_match = re.search(r'description:\s*"([^"]*)"', body)
        cat_match = re.search(r"category:\s*(\w+)", body)
        type_match = re.search(r"\btype:\s*(HARD|SOFT)\b", body)
        tags_match = re.search(r"tags:\s*\[([^\]]*)\]", body)

        tags: list[str] | None = None
        if tags_match:
            raw = tags_match.group(1)
            tags = [
                t.strip().strip('"') for t in raw.split(",") if t.strip().strip('"')
            ]

        return {
            "description": desc_match.group(1) if desc_match else None,
            "category": cat_match.group(1) if cat_match else None,
            "mandatory": (type_match.group(1) == "HARD") if type_match else None,
            "tags": tags,
            "depends_on": None,
        }

    def _copy_assets(self, output_dir: Path) -> None:
        asset_dir = self._asset_dir()
        for name in ("index.html", "selector.js", "style.css"):
            shutil.copy2(asset_dir / name, output_dir / name)

    def _asset_dir(self) -> Path:
        if self.asset_source_dir is not None:
            return self.asset_source_dir
        asset_root = (
            resources.files("sdd_wizard").joinpath("templates").joinpath("selector")
        )
        return Path(str(asset_root))

    def _metadata_path(self) -> Path:
        return self.repo_root / ".sdd" / "metadata.json"

    def _mandates_path(self) -> Path:
        return self.repo_root / ".sdd" / "source" / "mandates" / "mandates.md"

    def _guidelines_path(self) -> Path:
        return self.repo_root / ".sdd" / "source" / "guidelines.dsl"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build selector site assets.")
    parser.add_argument("--repo-root", default=".", help="Workspace root.")
    parser.add_argument("--output-dir", required=True, help="Selector output dir.")
    return parser.parse_args()


def main() -> None:
    """CLI entry point for building selector assets."""
    args = _parse_args()
    compiler = SelectorCompiler(repo_root=Path(args.repo_root).resolve())
    compiler.build_site(Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
