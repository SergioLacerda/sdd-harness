"""DevinPluginGenerator: builds a self-contained SDD governance plugin bundle for Devin (Soft/Standalone profile)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..skill_loader import SkillLoader

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "devin_plugin"
_PLUGIN_VERSION = "0.1.0"
_PLACEHOLDER_DESCRIPTION = "no description available"
_SECTION_HEADING_RE = re.compile(r"^## (\S+): (.+)$")


def _policy_digest(skills: list[dict[str, Any]]) -> str:
    """Deterministic sha256 over a canonical JSON serialization of skill data."""
    canonical = json.dumps(skills, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_governance_sections(text: str) -> list[dict[str, Any]]:
    """Parse '## <ID>: <Title>' sections (mandates.md / guidelines/*.md shape).

    Each section is a heading, a metadata block of '**Field**: value' lines, and
    a trailing description paragraph. A description equal to the source's own
    "No description available" placeholder is reported as has_description=False
    rather than treated as real content — callers must not fabricate a summary
    for those sections.
    """
    sections: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    body_lines: list[str] = []

    def _finalize() -> None:
        if current is None:
            return
        description = " ".join(
            line.strip()
            for line in body_lines
            if line.strip() and not line.strip().startswith("**")
        ).strip()
        has_description = (
            bool(description) and description.lower() != _PLACEHOLDER_DESCRIPTION
        )
        sections.append(
            {
                "id": current["id"],
                "title": current["title"],
                "description": description if has_description else "",
                "has_description": has_description,
            }
        )

    for line in text.splitlines():
        match = _SECTION_HEADING_RE.match(line)
        if match:
            _finalize()
            current = {"id": match.group(1), "title": match.group(2).strip()}
            body_lines = []
            continue
        if current is not None:
            body_lines.append(line)
    _finalize()
    return sections


def _load_governance_summary(output_dir: Path) -> dict[str, Any]:
    """Load a best-effort SDD Harness governance summary for embedding.

    Degrades gracefully (empty lists, "unknown" fields) when .sdd/metadata.json
    or .sdd/source/mandates/mandates.md are absent — this is additive content,
    never a reason to fail plugin generation.
    """
    sdd_dir = Path(output_dir) / ".sdd"
    metadata_path = sdd_dir / "metadata.json"
    mandates_path = sdd_dir / "source" / "mandates" / "mandates.md"
    guidelines_dir = sdd_dir / "source" / "guidelines"

    governance_fingerprint = "unknown"
    workspace_version = "unknown"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            governance_fingerprint = str(
                metadata.get("governance_fingerprint", governance_fingerprint)
            )
            workspace_version = str(metadata.get("version", workspace_version))
        except (OSError, json.JSONDecodeError):
            pass

    mandates: list[dict[str, Any]] = []
    if mandates_path.exists():
        mandates = _parse_governance_sections(mandates_path.read_text(encoding="utf-8"))

    guideline_categories: list[str] = []
    guidelines: list[dict[str, Any]] = []
    if guidelines_dir.exists():
        for guideline_file in sorted(guidelines_dir.glob("*.md")):
            guideline_categories.append(guideline_file.stem)
            items = _parse_governance_sections(
                guideline_file.read_text(encoding="utf-8")
            )
            described = [item["description"] for item in items if item["has_description"]]
            guidelines.append(
                {
                    "category": guideline_file.stem,
                    "highlight": described[0] if described else "",
                    "has_highlight": bool(described),
                }
            )

    return {
        "governance_fingerprint": governance_fingerprint,
        "workspace_version": workspace_version,
        "mandate_count": len(mandates),
        "mandates": mandates,
        "guideline_categories": guideline_categories,
        "guidelines": guidelines,
    }


def _governance_summary_digest(summary: dict[str, Any]) -> str:
    """Deterministic sha256 over the governance summary, independent of _policy_digest."""
    canonical_input = {
        "governance_fingerprint": summary["governance_fingerprint"],
        "workspace_version": summary["workspace_version"],
        "mandate_count": summary["mandate_count"],
        "mandates": [
            {"id": m["id"], "title": m["title"], "has_description": m["has_description"]}
            for m in summary["mandates"]
        ],
        "guideline_categories": summary["guideline_categories"],
    }
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compiler_version() -> str:
    try:
        from importlib.metadata import version

        return version("sdd-adapters")
    except Exception:
        return "0.0.0+unknown"


@dataclass
class DevinPluginResult:
    """Result of Devin plugin bundle generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True
    policy_digest: str = ""
    governance_summary_digest: str = ""


class DevinPluginGenerator:
    """Generates a Soft/Standalone SDD governance plugin bundle for Devin."""

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.skill_loader = SkillLoader()

    def generate(
        self,
        output_dir: Path,
        dest: Path | None = None,
        *,
        source_revision: str = "unknown",
        built_at: str | None = None,
    ) -> DevinPluginResult:
        """
        Generate the Devin plugin bundle.

        Args:
            output_dir: project root where .sdd/ (and optionally LICENSE) live.
            dest: bundle output directory. Defaults to {output_dir}/dist/devin-plugin.
            source_revision: caller-supplied revision identifier (e.g. a git SHA
                obtained by the caller — this method never shells out to git).
            built_at: ISO-8601 timestamp. Defaults to current UTC time; pass a
                fixed value in tests for reproducible output.
        """
        result = DevinPluginResult()
        sdd_dir = Path(output_dir) / ".sdd"
        skills = self.skill_loader.load_skills(sdd_dir)

        if not skills:
            result.success = False
            result.errors.append(
                f"No skills found under {sdd_dir / 'skills' / 'registry.json'}"
            )
            return result

        skills_sorted = sorted(skills, key=lambda s: s.get("name", ""))
        digest = _policy_digest(skills_sorted)
        result.policy_digest = digest

        governance_summary = _load_governance_summary(output_dir)
        governance_summary_digest = _governance_summary_digest(governance_summary)
        result.governance_summary_digest = governance_summary_digest

        context = {
            "plugin_version": _PLUGIN_VERSION,
            "compiler_version": _compiler_version(),
            "schema_version": "1.0.0",
            "source_revision": source_revision,
            "built_at": built_at or datetime.now(timezone.utc).isoformat(),
            "policy_digest": digest,
            "governance_summary_digest": governance_summary_digest,
            "governance_fingerprint": governance_summary["governance_fingerprint"],
            "workspace_version": governance_summary["workspace_version"],
            "mandate_count": governance_summary["mandate_count"],
            "mandates": governance_summary["mandates"],
            "guideline_categories": governance_summary["guideline_categories"],
            "guidelines": governance_summary["guidelines"],
        }

        bundle_root = Path(dest) if dest else Path(output_dir) / "dist" / "devin-plugin"
        bundle_root.mkdir(parents=True, exist_ok=True)

        try:
            self._write(
                bundle_root / ".devin-plugin" / "plugin.json",
                "plugin.json",
                context,
                result,
            )
            self._write(bundle_root / "AGENTS.md", "AGENTS.md", context, result)
            self._write(
                bundle_root / "rules" / "sdd-harness-summary.md",
                "sdd-harness-summary.md",
                context,
                result,
            )
            self._write(bundle_root / "hooks.json", "hooks.json", context, result)
            self._write(
                bundle_root / "metadata" / "provenance.json",
                "provenance.json",
                context,
                result,
            )
            hook_script = self._write(
                bundle_root / "hooks" / "session-start-assurance.sh",
                "session-start-assurance.sh",
                context,
                result,
            )
            hook_script.chmod(
                hook_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
            )

            for skill in skills_sorted:
                skill_dir = bundle_root / "skills" / skill.get("name", "unknown")
                skill_dir.mkdir(parents=True, exist_ok=True)
                self._write(
                    skill_dir / "SKILL.md",
                    "SKILL.md",
                    {**context, "skill": skill},
                    result,
                )

            license_source = Path(output_dir) / "LICENSE"
            if license_source.exists():
                license_dest = bundle_root / "LICENSE"
                shutil.copyfile(license_source, license_dest)
                result.files_written.append(str(license_dest))
        except Exception as e:  # defensive: partial bundle is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write(
        self,
        path: Path,
        template_name: str,
        context: dict[str, Any],
        result: DevinPluginResult,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
