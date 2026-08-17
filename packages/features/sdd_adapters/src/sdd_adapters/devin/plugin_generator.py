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
_STANDALONE_TEMPLATES_DIR = _TEMPLATES_DIR / "standalone"
_PLUGIN_VERSION = "0.1.0"
_SOFT_GOVERNANCE_RULESET_VERSION = "1.0.0"
_STANDALONE_RULESET_VERSION = "1.0.0"
_STANDALONE_RULE_NAMES = (
    "architecture",
    "git-safety",
    "testing",
    "generated-artifacts",
    "python",
    "go",
    "documentation",
)
_PLACEHOLDER_DESCRIPTION = "no description available"
_SECTION_HEADING_RE = re.compile(r"^#{2,3} (\S+): (.+)$")

_ANTI_PATTERN_SOURCES = (
    "COGNITIVE_OVERLOAD",
    "PREMATURE_EXECUTION",
    "RESOLUTION_BYPASS",
    "SCOPE_CREEP",
    "SYMPTOM_FIXING",
)
_ANTI_PATTERNS_DIR = Path("docs") / "cognition" / "anti-patterns"
_GO_RESOLUTION_BYPASS_PATH = (
    Path("docs") / "cognition" / "anti-patterns" / "lang" / "GO_RESOLUTION_BYPASS.md"
)

# Matched by substring, not exact phrase — heading wording is not identical
# across the 5 source files (e.g. RESOLUTION_BYPASS.md uses "The Universal
# Cure" while the others use "The Cure"). Order matters only for readability;
# lookup below checks all keys regardless of order.
_ANTI_PATTERN_SECTION_KEYS = {
    "problem": "Problem",
    "cure": "Cure",
    "benchmark": "Benchmark",
    "symptoms": "Symptoms",
    "danger": "Dangerous",
}
_REQUIRED_ANTI_PATTERN_KEYS = ("problem", "cure", "benchmark")


def _policy_digest(skills: list[dict[str, Any]]) -> str:
    """Deterministic sha256 over a canonical JSON serialization of skill data."""
    canonical = json.dumps(skills, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_governance_sections(text: str) -> list[dict[str, Any]]:
    """Parse '## <ID>: <Title>' or '### <ID>: <Title>' sections (mandates.md /
    guidelines/*.md shape — heading level is inconsistent across source files,
    e.g. general.md uses '##' and other.md uses '###').

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


def _match_section_marker(heading_text: str, keys: dict[str, str]) -> tuple[str | None, str]:
    """Find which key's marker appears in heading_text; return (key, trailing_content).

    trailing_content is whatever follows the marker on the same line. Some
    source files jam heading and content onto one line with no line break
    (e.g. GO_RESOLUTION_BYPASS.md's '## \U0001f4cf Rule> Your code should...') —
    without this, that content would be silently dropped rather than captured.
    """
    for key, marker in keys.items():
        idx = heading_text.find(marker)
        if idx != -1:
            return key, heading_text[idx + len(marker) :].strip()
    return None, ""


def _parse_anti_pattern(text: str, source_name: str) -> dict[str, Any]:
    """Parse a docs/cognition/anti-patterns/*.md file.

    Unlike _parse_governance_sections, a missing required section is NOT a
    tolerable state here — these are fixed, hand-authored, first-party files
    with a confirmed-consistent shape, so a missing Problem/Cure/Benchmark
    section means the source itself is structurally broken. Raises ValueError
    rather than degrading silently (R-008 mitigation from
    .analysis/refined/20260817-devin-plugin-cognition-runtime-go-case/design.md).
    """
    lines = text.splitlines()
    title: str | None = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        raise ValueError(f"{source_name}: missing title ('# <Title>' heading)")

    sections: dict[str, str] = {}
    current_key: str | None = None
    body: list[str] = []
    in_code_fence = False

    def _flush() -> None:
        if current_key is not None:
            sections[current_key] = "\n".join(body).strip()

    for line in lines:
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            if current_key is not None:
                body.append(line)
            continue
        if not in_code_fence and line.startswith("## "):
            # Only a real, unfenced '## ' line is a section boundary — a
            # heading-shaped line *inside* an illustrative code block (e.g.
            # SCOPE_CREEP.md's fenced '## Parking Lot' example) is example
            # content, not a real section, and must not truncate the
            # section it appears in.
            _flush()
            heading_text = line[3:].strip()
            current_key, trailing = _match_section_marker(
                heading_text, _ANTI_PATTERN_SECTION_KEYS
            )
            body = [trailing] if trailing else []
            continue
        if current_key is not None:
            body.append(line)
    _flush()

    missing = [
        _ANTI_PATTERN_SECTION_KEYS[key]
        for key in _REQUIRED_ANTI_PATTERN_KEYS
        if not sections.get(key)
    ]
    if missing:
        raise ValueError(
            f"{source_name}: missing required section(s): {', '.join(missing)}"
        )

    return {
        "id": source_name,
        "title": title,
        "problem": sections.get("problem", ""),
        "cure": sections.get("cure", ""),
        "benchmark": sections.get("benchmark", ""),
        "symptoms": sections.get("symptoms", ""),
        "danger": sections.get("danger", ""),
        "has_symptoms": bool(sections.get("symptoms")),
        "has_danger": bool(sections.get("danger")),
    }


def _load_coding_practices(output_dir: Path) -> dict[str, Any] | None:
    """Load the Go-pilot coding practices content.

    The whole docs/cognition/anti-patterns/ category is optional and degrades
    gracefully (returns None) when entirely absent — this content is specific
    to the SDD Harness repository itself, not something every consuming
    project has (unlike .sdd/, which the wizard scaffolds everywhere). But once
    the category is present, an individual missing file or malformed section
    within it is a hard failure (ValueError) — that indicates the source
    itself is broken, not that the feature is optional for this project.
    """
    anti_patterns_dir = Path(output_dir) / _ANTI_PATTERNS_DIR
    if not anti_patterns_dir.exists():
        return None

    anti_patterns = []
    for source_name in _ANTI_PATTERN_SOURCES:
        path = anti_patterns_dir / f"{source_name}.md"
        if not path.exists():
            raise ValueError(f"missing anti-pattern source: {path}")
        anti_patterns.append(
            _parse_anti_pattern(path.read_text(encoding="utf-8"), str(path))
        )

    go_path = Path(output_dir) / _GO_RESOLUTION_BYPASS_PATH
    if not go_path.exists():
        raise ValueError(f"missing anti-pattern source: {go_path}")
    go_resolution_bypass = _parse_go_resolution_bypass(
        go_path.read_text(encoding="utf-8"), str(go_path)
    )

    return {
        "anti_patterns": anti_patterns,
        "go_resolution_bypass": go_resolution_bypass,
    }


def _parse_go_resolution_bypass(text: str, source_name: str) -> dict[str, Any]:
    """Parse docs/cognition/anti-patterns/lang/GO_RESOLUTION_BYPASS.md.

    Simpler, single-purpose parse — only one file has this shape today, so
    _parse_anti_pattern's generality isn't needed. Same loud-failure contract:
    a missing required section raises ValueError.
    """
    sections: dict[str, str] = {}
    current_key: str | None = None
    body: list[str] = []
    keys = {
        "hacks": "Go-Specific Hacks",
        "cures": "Go Cures",
        "detection": "Detection",
        "rule": "Rule",
    }

    def _flush() -> None:
        if current_key is not None:
            sections[current_key] = "\n".join(body).strip()

    for line in text.splitlines():
        if line.startswith("## "):
            _flush()
            heading_text = line[3:].strip()
            current_key, trailing = _match_section_marker(heading_text, keys)
            body = [trailing] if trailing else []
            continue
        if current_key is not None:
            body.append(line)
    _flush()

    missing = [
        keys[key] for key in ("hacks", "cures", "rule") if not sections.get(key)
    ]
    if missing:
        raise ValueError(
            f"{source_name}: missing required section(s): {', '.join(missing)}"
        )

    return {
        "hacks": sections.get("hacks", ""),
        "cures": sections.get("cures", ""),
        "detection": sections.get("detection", ""),
        "rule": sections.get("rule", ""),
    }


def _coding_practices_digest(coding_practices: dict[str, Any]) -> str:
    """Deterministic sha256 over coding-practices content, independent of the
    other three digest/version fields."""
    canonical_input = {
        "anti_patterns": [
            {
                "id": ap["id"],
                "title": ap["title"],
                "problem": ap["problem"],
                "cure": ap["cure"],
                "benchmark": ap["benchmark"],
            }
            for ap in coding_practices["anti_patterns"]
        ],
        "go_resolution_bypass": coding_practices["go_resolution_bypass"],
    }
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
        "mandate_described_count": sum(1 for m in mandates if m["has_description"]),
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
class DevinStandaloneResult:
    """Result of standalone (zero-SDD-mention) Devin config generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


@dataclass
class DevinPluginResult:
    """Result of Devin plugin bundle generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True
    policy_digest: str = ""
    governance_summary_digest: str = ""
    coding_practices_digest: str = ""


class DevinPluginGenerator:
    """Generates a Soft/Standalone SDD governance plugin bundle for Devin."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        standalone_templates_dir: Path | None = None,
    ):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.standalone_templates_dir = (
            Path(standalone_templates_dir)
            if standalone_templates_dir
            else _STANDALONE_TEMPLATES_DIR
        )
        self.standalone_env = Environment(
            loader=FileSystemLoader(str(self.standalone_templates_dir)),
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
        include_skills: bool = True,
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
            include_skills: when False, skip the SDD skill catalog entirely
                (no skills/ directory, no "skills" key in plugin.json). Each
                skill's "Allowed CLI" commands assume the sdd CLI is installed
                in the Devin environment — a real dependency the base
                AGENTS.md/rules/ governance summary does not have. Default True
                preserves existing behavior.
        """
        result = DevinPluginResult()
        sdd_dir = Path(output_dir) / ".sdd"
        skills_sorted: list[dict[str, Any]] = []

        if include_skills:
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

        try:
            coding_practices = _load_coding_practices(output_dir)
        except ValueError as e:
            result.success = False
            result.errors.append(str(e))
            return result
        coding_practices_digest = (
            _coding_practices_digest(coding_practices) if coding_practices else ""
        )
        result.coding_practices_digest = coding_practices_digest

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
            "mandate_described_count": governance_summary["mandate_described_count"],
            "mandates": governance_summary["mandates"],
            "guideline_categories": governance_summary["guideline_categories"],
            "guidelines": governance_summary["guidelines"],
            "include_skills": include_skills,
            "soft_governance_ruleset_version": _SOFT_GOVERNANCE_RULESET_VERSION,
            "has_coding_practices": coding_practices is not None,
            "anti_patterns": coding_practices["anti_patterns"] if coding_practices else [],
            "go_resolution_bypass": (
                coding_practices["go_resolution_bypass"] if coding_practices else None
            ),
            "coding_practices_digest": coding_practices_digest,
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
            self._write(
                bundle_root / "rules" / "sdd-soft-governance-behavior.md",
                "sdd-soft-governance-behavior.md",
                context,
                result,
            )
            if coding_practices is not None:
                self._write(
                    bundle_root / "rules" / "sdd-coding-practices.md",
                    "sdd-coding-practices.md",
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

    def generate_standalone(
        self, output_dir: Path, dest: Path | None = None
    ) -> DevinStandaloneResult:
        """
        Generate a zero-SDD-mention Devin project configuration: AGENTS.md,
        .devin/config.json, .devin/hooks.v1.json, .devin/rules/*.md (7 files).

        Args:
            output_dir: project root (used only to resolve the default dest).
            dest: output directory. Defaults to {output_dir}/dist/devin-standalone
                — a build artifact, same convention as generate()'s
                dist/devin-plugin default, never the project's real root files.
        """
        result = DevinStandaloneResult()
        context = {"standalone_ruleset_version": _STANDALONE_RULESET_VERSION}
        root = Path(dest) if dest else Path(output_dir) / "dist" / "devin-standalone"

        try:
            self._write_standalone(root / "AGENTS.md", "AGENTS.md", context, result)
            self._write_standalone(
                root / ".devin" / "config.json", "config.json", context, result
            )
            self._write_standalone(
                root / ".devin" / "hooks.v1.json", "hooks.v1.json", context, result
            )
            for rule_name in _STANDALONE_RULE_NAMES:
                self._write_standalone(
                    root / ".devin" / "rules" / f"{rule_name}.md",
                    f"rules/{rule_name}.md",
                    context,
                    result,
                )
        except Exception as e:  # defensive: partial output is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write_standalone(
        self,
        path: Path,
        template_name: str,
        context: dict[str, Any],
        result: DevinStandaloneResult,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.standalone_env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
