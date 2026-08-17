"""DevinPluginGenerator: builds a self-contained SDD governance plugin bundle for Devin (Soft/Standalone profile)."""

from __future__ import annotations

import hashlib
import json
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


def _policy_digest(skills: list[dict[str, Any]]) -> str:
    """Deterministic sha256 over a canonical JSON serialization of skill data."""
    canonical = json.dumps(skills, sort_keys=True, separators=(",", ":"))
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

        context = {
            "plugin_version": _PLUGIN_VERSION,
            "compiler_version": _compiler_version(),
            "schema_version": "1.0.0",
            "source_revision": source_revision,
            "built_at": built_at or datetime.now(timezone.utc).isoformat(),
            "policy_digest": digest,
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
