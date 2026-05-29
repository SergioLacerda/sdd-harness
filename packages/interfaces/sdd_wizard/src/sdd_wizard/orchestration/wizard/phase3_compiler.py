"""Phase3 Compiler."""

import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sdd_core.utils.environment import get_sdd_paths

from .models import ParsedItems, Phase3RunResult

"""
SDD Wizard v3 - 3-Phase Flow with Status-aware Governance

Phase 1: Generate markdown templates with status fields
    Input: mandate.spec, guidelines.dsl from spec/ (with canonical resolution)
  Output: generated/client/build/phase-1-choices/

Phase 2: Manual user review & customization
  Input: generated/client/build/phase-1-choices/
  Action: User edits status values in place
  Output: generated/client/build/phase-1-choices/ (User-edited markdown templates)

Phase 3: Compile & fingerprint governance
    Input: generated/client/build/phase-2-input/ (staged user-edited markdown)
  Output: generated/client/compiled/ (Final msgpack/json artifacts)
"""


@dataclass
class Phase3Compiler:
    """Compile edited markdown templates to governance JSON with complete project structure"""

    PHASE2_INPUT_DIRNAME = "phase-2-input"
    WIZARD_CONFIG_FILENAME = "wizard-config.json"

    def __init__(
        self,
        markdown_input_path: Path,
        output_path: Path,
        repo_root: Path,
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        """
        Args:
            markdown_input_path: Path to phase-2-input/ folder with edited markdown files
            output_path: Base output path (generated/client/compiled)
            repo_root: Root of sdd-harness repo
            verbose: Print detailed logs
        """
        self.markdown_input_path = markdown_input_path
        self.output_path = output_path
        self.repo_root = repo_root
        self.verbose = verbose
        self.language = "Python"  # default
        self.config: dict[str, Any] = {}
        self.selected_guidelines: list[
            str
        ] = []  # Track which guidelines are selected (required/custom)
        self.last_error: str | None = None
        self.client_build_dir = self.markdown_input_path.parent
        self.phase2_input_dir = self.client_build_dir / self.PHASE2_INPUT_DIRNAME
        self.wizard_config_path = self.client_build_dir / self.WIZARD_CONFIG_FILENAME
        self._emit = emitter or print

    def log(self, message: str) -> None:
        """Log."""
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def has_staged_input_files(self) -> bool:
        """Return True when phase-2-input contains at least one file."""
        if not self.markdown_input_path.exists():
            return False
        return any(path.is_file() for path in self.markdown_input_path.iterdir())

    def load_wizard_config(self) -> bool:
        """Load wizard configuration to get selected language"""
        try:
            config_path = self.wizard_config_path
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.language = self.config.get("language", "Python")
                    self.log(f"Loaded config: language={self.language}")
                    return True
            else:
                self.log(
                    f"Config not found at {config_path}, using default language: Python"
                )
                return True
        except Exception as e:
            self._emit(f"  ❌ Error loading config: {e}")
            return False

    def create_structure(self) -> bool:
        """Create governance directory structure in generated/client/compiled"""
        try:
            # We use the standardized client_compiled directory
            dir = self.output_path
            source_dir = dir / "source"

            source_dir.mkdir(parents=True, exist_ok=True)

            self.log(f"Created structure in: {dir}")
            return True
        except Exception as e:
            self._emit(f"  ❌ Error creating structure: {e}")
            return False

    def copy_language_templates(self) -> bool:  # noqa: C901
        """Copy language-specific templates to templates/, conditionally include CI/CD workflows"""
        try:
            templates_dir = self.repo_root / "packages" / "wizard" / "templates"
            language_lower = self.language.lower()

            # Map language names to template directory names
            language_dir_map = {
                "python": "python",
                "java": "java",
                "typescript": "js",  # TypeScript/JavaScript use same templates in js/ folder
            }

            template_dir_name = language_dir_map.get(language_lower, language_lower)

            # Copy language-specific templates
            language_template_dir = templates_dir / "languages" / template_dir_name
            if language_template_dir.exists():
                target_dir = self.output_path / "templates"
                target_dir.mkdir(parents=True, exist_ok=True)

                import shutil

                for item in language_template_dir.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(language_template_dir)
                        target_file = target_dir / rel_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target_file)

                self.log(f"Copied {language_lower} language templates to templates/")

            # Copy base templates, but selectively include .github/workflows
            base_template_dir = templates_dir / "base"
            if base_template_dir.exists():
                target_dir = self.output_path / "templates"
                target_dir.mkdir(parents=True, exist_ok=True)

                import shutil

                for item in base_template_dir.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(base_template_dir)

                        # Check if this is a workflow file
                        is_workflow_file = (
                            ".github" in rel_path.parts
                            and "workflows" in rel_path.parts
                        )

                        # Only copy workflow files if G151 is selected
                        if is_workflow_file and "G151" not in self.selected_guidelines:
                            self.log(
                                f"Skipping workflow template (G151 not selected): {rel_path}"
                            )
                            continue

                        target_file = target_dir / rel_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        # Don't overwrite language-specific templates
                        if not target_file.exists():
                            shutil.copy2(item, target_file)

                if "G151" in self.selected_guidelines:
                    self.log(
                        "Copied base templates with CI/CD workflow (G151 selected)"
                    )
                else:
                    self.log(
                        "Copied base templates (workflow skipped - G151 not selected)"
                    )

            return True
        except Exception as e:
            self._emit(f"  ❌ Error copying language templates: {e}")
            import traceback

            traceback.print_exc()
            return False

    def copy_seedlings(self) -> bool:
        """Copy seedling templates from sdd_integration to output directory"""
        try:
            # Look for seedling templates in sdd_integration
            source_seedling_dir = (
                self.repo_root
                / "packages"
                / "features"
                / "sdd_integration"
                / "src"
                / "sdd_integration"
                / "templates"
            )

            if not source_seedling_dir.exists():
                self.log(
                    f"Seedling templates directory not found at {source_seedling_dir}, skipping"
                )
                return True

            target_base = self.output_path
            target_base.mkdir(parents=True, exist_ok=True)

            import shutil

            # Copy .github, .vscode, .cursor directories directly to output_path
            for seedling_type in [".github", ".vscode", ".cursor"]:
                source_path = source_seedling_dir / seedling_type
                if source_path.exists():
                    target_path = target_base / seedling_type
                    target_path.mkdir(parents=True, exist_ok=True)

                    for item in source_path.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(source_path)
                            target_file = target_path / rel_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, target_file)

            self.log(
                "Copied seedling templates (.github, .vscode, .cursor) to final-output/"
            )
            return True
        except Exception as e:
            self._emit(f"  ❌ Error copying seedlings: {e}")
            import traceback

            traceback.print_exc()
            return False

    def parse_markdown_status(self, content: str) -> str:
        """Extract status from markdown content"""
        # Match: **Status:** `required: true` or **Status:** `optional: true`
        match = re.search(
            r"\*\*Status:\*\*\s*`(required|optional|custom):\s*(?:true|false)`", content
        )
        if match:
            return match.group(1)
        return "required"  # Default if not found

    def parse_markdown_items(self) -> ParsedItems:
        """Parse edited markdown files from phase-2-input"""
        mandates = []
        guidelines = []

        try:
            # Find all .md files in phase-2-input
            md_files = list(self.markdown_input_path.glob("*.md"))

            if not md_files:
                self.log(
                    "No markdown files staged; continuing with docs-meta source compilation"
                )
                return ParsedItems(mandates=[], guidelines=[])

            for md_file in md_files:
                content = md_file.read_text(encoding="utf-8")

                # Parse items: ## ID: Title
                pattern = r"## ([GM]\d+):\s*(.+?)\n(.*?)(?=##|$)"
                for match in re.finditer(pattern, content, re.DOTALL):
                    item_id = match.group(1)
                    title = match.group(2).strip()
                    item_content = match.group(3)

                    # Get status
                    status = self.parse_markdown_status(item_content)

                    # Skip optional items
                    if status == "optional":
                        self.log(f"Skipping optional item {item_id}")
                        continue

                    item = {
                        "id": item_id,
                        "title": title,
                        "status": status,
                        "type": "HARD" if item_id.startswith("M") else "SOFT",
                    }

                    if item_id.startswith("M"):
                        mandates.append(item)
                    else:
                        guidelines.append(item)
                        # Store guideline ID for conditional template generation
                        self.selected_guidelines.append(item_id)

                    self.log(f"Parsed {item_id}: {title} (status: {status})")

            return ParsedItems(mandates=mandates, guidelines=guidelines)

        except Exception as e:
            self._emit(f"  ❌ Error parsing markdown: {e}")
            return ParsedItems(mandates=[], guidelines=[])

    def compile_with_pipeline_builder(self, items: ParsedItems) -> bool:
        """Compile governance using PipelineBuilder (package-based, no hacks)"""
        try:
            from sdd_integration.builders.governance.pipeline_builder import (
                PipelineBuilder,
            )

            self.log("Importing PipelineBuilder (package mode)...")

            try:
                paths = get_sdd_paths()
                spec_path = paths.get("docs_meta", paths["client_build"] / "docs-meta")
            except RuntimeError:
                spec_path = (
                    self.repo_root / "generated" / "client" / "build" / "docs-meta"
                )

            builder = PipelineBuilder(
                str(spec_path),
                parsed_items=cast(dict[str, list[dict[str, Any]]], items),
            )
            self.log(f"Building with spec path: {spec_path}")

            _ = builder.build()
            self.log("Build complete")

            # Create directories
            source = self.output_path / "source"
            source.mkdir(parents=True, exist_ok=True)

            # Persist artifacts using the builder contract (governance_core/governance_client).
            builder.save_outputs(str(source))

            core_file = source / "governance-core.json"
            client_file = source / "governance-client.json"

            self.log(f"Wrote {core_file}")
            self.log(f"Wrote {client_file}")

            return True

        except ImportError as e:
            self._emit("❌ PipelineBuilder not available as package")
            self._emit("   → Did you install sdd-build?")
            self._emit(f"   Error: {e}")
            return False

        except Exception as e:
            self._emit(f"❌ Pipeline builder error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def load_compiled_governance(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Load mandates and guidelines from compiled governance JSONs"""
        try:
            source_dir = self.output_path / "source"
            core_file = source_dir / "governance-core.json"
            client_file = source_dir / "governance-client.json"

            mandates: list[dict[str, Any]] = []
            guidelines: list[dict[str, Any]] = []

            # Load mandates from governance-core.json
            if core_file.exists():
                with open(core_file, encoding="utf-8") as f:
                    governancepackages = json.load(f)

                for item in governancepackages.get("items", []):
                    if item["type"] == "MANDATE":
                        mandates.append(item)

            # Load guidelines from governance-client.json
            if client_file.exists():
                with open(client_file, encoding="utf-8") as f:
                    governance_client = json.load(f)

                for item in governance_client.get("items", []):
                    if item["type"] == "GUIDELINE":
                        guidelines.append(item)

            self.log(
                f"Loaded {len(mandates)} mandates and {len(guidelines)} guidelines"
            )
            return mandates, guidelines
        except Exception as e:
            self._emit(f"  ❌ Error loading compiled governance: {e}")
            import traceback

            traceback.print_exc()
            return [], []

    def generate_mandates_file(self, mandates: list[dict[str, Any]]) -> bool:
        """Generate mandates.md with IA-FIRST optimization"""
        try:
            mandates_dir = self.output_path / "source" / "mandates"
            mandates_dir.mkdir(parents=True, exist_ok=True)

            mandates_file = mandates_dir / "mandates.md"

            content = f"""# Mandates - SDD v3.0

⚡ IA-FIRST DESIGN NOTICE
- **Status**: Architecture-level governance rules
- **Optimization**: Optimized for AI agent parsing
- **Version**: 3.0
- **Language**: {self.language}
- **Generated**: {datetime.now().isoformat()}

## Core Mandates

Mandatory rules that CANNOT be customized or skipped.

"""

            for mandate in mandates:
                content += f"""## {mandate["id"]}: {mandate["title"]}

**Criticality**: {mandate.get("criticality", "MANDATORY")}
**Customizable**: No

{mandate.get("description", mandate.get("content", "No description available"))}

"""

            with open(mandates_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.log(f"Generated mandates.md ({len(mandates)} mandates)")
            return True
        except Exception as e:
            self._emit(f"  ❌ Error generating mandates.md: {e}")
            import traceback

            traceback.print_exc()
            return False

    def generate_guidelines_files(self, guidelines: list[dict[str, Any]]) -> bool:
        """Generate guidelines organized by category"""
        try:
            guidelines_dir = self.output_path / "source" / "guidelines"
            guidelines_dir.mkdir(parents=True, exist_ok=True)

            # Organize by category
            by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for guideline in guidelines:
                cat = guideline.get("category", "general")
                by_category[cat].append(guideline)

            # Generate file for each category
            for category, items in sorted(by_category.items()):
                filename = category.lower().replace(" ", "-")
                filepath = guidelines_dir / f"{filename}.md"

                content = f"""# {category.title()} Guidelines

⚡ IA-FIRST DESIGN NOTICE
- **Status**: Customizable best practices
- **Optimization**: Optimized for AI agent parsing
- **Category**: {category.title()}
- **Count**: {len(items)} guidelines
- **Generated**: {datetime.now().isoformat()}

## Overview

Guidelines in this category provide structured recommendations for {category.lower()}.

"""

                for guideline in items:
                    content += f"""## {guideline["id"]}: {guideline["title"]}

**Type**: {guideline.get("type", "GUIDELINE")}
**Status**: {guideline.get("status", "required")}
**Customizable**: {"Yes" if guideline.get("customizable", True) else "No"}

{guideline.get("description", guideline.get("content", "No description available"))}

"""

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                self.log(f"Generated {filename}.md ({len(items)} guidelines)")

            return True
        except Exception as e:
            self._emit(f"  ❌ Error generating guidelines files: {e}")
            import traceback

            traceback.print_exc()
            return False

    def generate_source_readme(
        self, mandates: list[dict[str, Any]], guidelines: list[dict[str, Any]]
    ) -> bool:
        """Generate README.md with agent instructions for .sdd/source"""
        try:
            source_dir = self.output_path / "source"
            readme_file = source_dir / "README.md"

            # Get categories from guidelines
            categories = sorted(set(g.get("category", "general") for g in guidelines))
            if not categories:
                categories = ["general"]
            categories_list = "\n".join(f"- {cat.title()}" for cat in categories)

            # Build guidelines file references
            "\n".join(f"- {cat.lower()}.md" for cat in categories)

            content = f"""# .sdd/source - Governance Source of Truth

⚡ **For AI Agents: This is your primary query directory**

## Overview

This directory contains the **compiled and optimized** governance specifications that agents should reference.

**Generated**: {datetime.now().isoformat()}
**Language**: {self.language}

## Directory Structure

```
.sdd/source/
├── mandates/
│   └── mandates.md              ← Read mandates first (hard rules)
├── guidelines/
│   ├── {categories[0]}.md
│   ├── {categories[1] if len(categories) > 1 else "other"}.md
│   └── (organized by category)
└── README.md                    ← This file
```

## For AI Agents: How to Use This

### 1. Query Mandates First

Always read `.sdd/source/mandates/mandates.md` to understand **hard rules** that CANNOT be customized.

```bash
cat .sdd/source/mandates/mandates.md
```

### 2. Query Relevant Guidelines

Based on the task, read relevant guidelines:

```bash
# For category-related work
cat .sdd/source/guidelines/category.md
```

### 3. Use As Pre-Cache Context

These files are **optimized for AI parsing** (IA-FIRST format):
- Flat hierarchy (H2 sections, no skipped levels)
- Clear lists instead of prose
- Emoji markers for decisions
- Markdown links only
- No nested HTML or complex formatting

This reduces token usage when including in agent context.

### 4. Reference in Agent Prompts

Example agent prompt structure:

```
You are a development assistant following SDD (Specification-Driven Development).

MANDATES (Hard Rules):
<read from .sdd/source/mandates/mandates.md>

GUIDELINES (Best Practices):
<read from .sdd/source/guidelines/{{relevant-category}}.md>

TASK:
<your specific task>
```

## Pre-Cache Strategy

For optimal performance when using these with agents:

1. **Load once**: Read governance files once per session
2. **Cache in memory**: Store in agent context/memory
3. **Reference later**: Use markdown file references instead of re-reading
4. **Update on changes**: Re-read if .sdd/source files change

## File Organization

### Mandates (Non-customizable)
- Location: `.sdd/source/mandates/mandates.md`
- Count: {len(mandates)}
- Rule: **MUST** be followed (no exceptions)

### Guidelines (Customizable)
- Location: `.sdd/source/guidelines/`
- Count: {len(guidelines)}
- Rule: Should be followed (exceptions allowed with documentation)

### Categories Covered

{categories_list}

## Next Steps

1. **Read Mandates**: Start with `.sdd/source/mandates/mandates.md`
2. **Browse Guidelines**: Review `.sdd/source/guidelines/` for your domain
3. **Use in Tasks**: Reference these when making decisions
4. **Cache Strategically**: Load once, reuse across multiple agent calls

---

**Generated by SDD Wizard v3.0**
"""

            with open(readme_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.log("Generated .sdd/source/README.md")
            return True
        except Exception as e:
            self._emit(f"  ❌ Error generating source README: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _generate_spec_file(self) -> None:
        """Write .sdd/spec/mandates.json to the template from canonical mandate files."""
        try:
            from sdd_integration.builders.governance.pipeline_builder import (
                PipelineBuilder,
            )

            canonical_dir = (
                self.repo_root / "docs" / "spec" / "canonical" / "core" / "mandates"
            )
            if not canonical_dir.is_dir() or not list(canonical_dir.glob("M*.md")):
                self.log("No canonical mandate files found; skipping spec generation")
                return

            spec_output = self.output_path / "spec" / "mandates.json"
            result = PipelineBuilder.generate_spec_file(
                canonical_mandates_dir=canonical_dir,
                output_path=spec_output,
                generated_by="sdd-wizard",
            )
            self.log(
                f"Generated .sdd/spec/mandates.json "
                f"({result['mandates_written']} mandates)"
            )
            self._emit(
                f"  ✅ Spec file: {result['mandates_written']} mandates → {spec_output}"
            )
        except Exception as e:
            self._emit(f"  ⚠️  Spec file generation skipped: {e}")

    def _generate_source_files(
        self,
        mandates: list[dict[str, Any]],
        guidelines: list[dict[str, Any]],
    ) -> str | None:
        """Generate AI-optimised source files; returns error string or None on success."""
        if not self.generate_mandates_file(mandates):
            return "Failed to generate mandates.md"
        if not self.generate_guidelines_files(guidelines):
            return "Failed to generate guidelines files"
        if not self.generate_source_readme(mandates, guidelines):
            return "Failed to generate source README"
        return None

    def run(self) -> Phase3RunResult:
        """Execute Phase 3: Read edited markdown and compile with complete structure"""
        self._emit("\n⚙️  PHASE 3: Compile Governance from Staged Templates")
        self._emit("=" * 70)
        self._emit(f"  📂 Input (phase-2-input): {self.markdown_input_path}")
        self._emit(f"  📂 Output (client-compiled): {self.output_path}")

        if not self.has_staged_input_files():
            return {
                "success": False,
                "error": (
                    f"No staged files found in {self.markdown_input_path}. "
                    "Run Phase 2 after editing templates to populate phase-2-input."
                ),
            }

        if not self.load_wizard_config():
            return {"success": False, "error": "Failed to load config"}

        if not self.create_structure():
            return {"success": False, "error": "Failed to create .sdd structure"}

        items = self.parse_markdown_items()
        self._emit(
            f"  ✅ Parsed {len(items['mandates'])} mandates, {len(items['guidelines'])} guidelines"
        )
        self._emit("  ℹ️  (Skipped optional items)")

        if not self.compile_with_pipeline_builder(items):
            return {"success": False, "error": "Failed to compile"}

        self._generate_spec_file()

        if not self.copy_language_templates():
            return {"success": False, "error": "Failed to copy language templates"}

        if not self.copy_seedlings():
            return {"success": False, "error": "Failed to copy seedlings"}

        mandates, guidelines = self.load_compiled_governance()
        if mandates or guidelines:
            err = self._generate_source_files(mandates, guidelines)
            if err:
                return {"success": False, "error": err}

        self._emit("  ✅ Compiled governance artifacts")
        self._emit("  ✅ Generated complete .sdd structure")
        self._emit(f"  📂 Output: {self.output_path}")

        return {
            "success": True,
            "output_path": str(self.output_path),
            "language": self.language,
            "files": [
                "governance-core.json",
                "governance-client.json",
                "templates/",
                "seedling/",
                "mandates.md",
                "guidelines/",
            ],
            "mandates": len(mandates),
            "guidelines": len(guidelines),
        }
