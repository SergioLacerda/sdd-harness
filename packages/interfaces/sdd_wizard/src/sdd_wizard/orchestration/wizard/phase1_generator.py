"""Phase1 Generator."""

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sdd_core.utils.environment import get_sdd_paths

from .models import Guideline, Mandate, Phase1RunResult

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
class Phase1Generator:
    """Generate markdown templates from documentation with status fields"""

    PHASE2_INPUT_DIRNAME = "phase-2-input"

    def __init__(
        self,
        core_path: Path,
        output_path: Path,
        verbose: bool = False,
        config: dict[str, Any] | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.core_path = core_path
        self.output_path = output_path
        self.verbose = verbose
        self.config = config or {}
        self.language = config.get("language", "Python") if config else "Python"
        self.adoption_level = config.get("adoption_level", "FULL") if config else "FULL"
        self.mandates: list[Mandate] = []
        self.guidelines: list[Guideline] = []
        self.last_error: str | None = None
        self.resolved_source_files: dict[str, Path] = {}
        self.local_source_dir = self.output_path.parent
        self.source_spec_dirs: list[Path] = []
        self._emit = emitter or print

        try:
            paths = get_sdd_paths()
            docs_meta_dir = paths.get("docs_meta", self.local_source_dir / "docs-meta")
            source_spec_dir = paths.get("source_spec", docs_meta_dir)

            # Prefer project-local docs-meta when running from generated templates,
            # then global docs-meta/source_spec as canonical fallbacks.
            self.source_spec_dirs = [
                self.local_source_dir / "docs-meta",
                docs_meta_dir,
                source_spec_dir,
            ]
        except RuntimeError:
            self.source_spec_dirs = [self.local_source_dir / "docs-meta"]

        # Deduplicate while preserving order.
        seen: set[Path] = set()
        deduped: list[Path] = []
        for _p in self.source_spec_dirs:
            if _p not in seen:
                seen.add(_p)
                deduped.append(_p)
        self.source_spec_dirs = deduped

    def _candidate_names(self, filename: str) -> list[str]:
        """Return compatible source names for canonical-only and docs-meta modes."""
        if filename == "mandate.spec":
            return ["mandate.spec", "mandate.md"]
        if filename == "guidelines.dsl":
            return ["guidelines.dsl", "guidelines.md"]
        return [filename]

    def log(self, message: str) -> None:
        """Log."""
        if self.verbose:
            self._emit(f"  ℹ️  {message}")

    def _resolve_source_file(self, filename: str) -> Path | None:
        """Resolve governance source files from generated docs-meta artifacts."""
        candidates: list[Path] = []
        for source_dir in self.source_spec_dirs:
            for name in self._candidate_names(filename):
                candidates.append(source_dir / name)

        for candidate in candidates:
            if candidate.exists():
                self.resolved_source_files[filename] = candidate
                self.log(f"Using source file: {candidate}")
                return candidate

        searched = ", ".join(str(p) for p in candidates)
        self.last_error = (
            f"{filename} not found. Searched: {searched}. "
            "Run 'sdd governance compile' to regenerate governance artifacts."
        )
        self._emit(f"  ❌ {self.last_error}")
        return None

    def _materialize_local_source_file(self, filename: str) -> Path | None:
        """Backward-compatible wrapper now delegated to docs-meta source resolution."""
        return self._resolve_source_file(filename)

    def parse_mandate_spec(self) -> bool:
        """Parse mandate.spec file"""
        mandate_file = self._resolve_source_file("mandate.spec")
        if mandate_file is None:
            return False

        content = mandate_file.read_text(encoding="utf-8")

        # Canonical-only fallback: parse markdown headings if mandate.md is used.
        if mandate_file.suffix == ".md":
            md_matches = re.findall(
                r"^#{1,3}\s+(M\d{3})[:\s-]+(.+)$", content, re.MULTILINE
            )
            for mandate_id, title in md_matches:
                mandate = Mandate(
                    id=mandate_id,
                    type="MANDATE",
                    title=title.strip(),
                    description=title.strip(),
                    category="core",
                    rationale="",
                )
                self.mandates.append(mandate)
                self.log(f"Parsed markdown mandate {mandate_id}: {title.strip()}")
            return len(self.mandates) > 0

        # Parse mandate blocks: mandate M001 { ... }
        pattern = r"mandate\s+(\w+)\s*\{([^}]+)\}"
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            mandate_id = match.group(1)
            mandate_content = match.group(2)

            title = self._extract_field(mandate_content, "title")
            desc = self._extract_field(mandate_content, "description")
            type_ = self._extract_field(mandate_content, "type")
            category = self._extract_field(mandate_content, "category")
            rationale = self._extract_field(mandate_content, "rationale")

            mandate = Mandate(
                id=mandate_id,
                type=type_,
                title=title,
                description=desc,
                category=category,
                rationale=rationale,
            )
            self.mandates.append(mandate)
            self.log(f"Parsed mandate {mandate_id}: {title}")

        if not self.mandates:
            bullet_matches = re.findall(
                r"^-\s+\[(\w+)\]\s+\*\*(.+?)\*\*", content, re.MULTILINE
            )
            for mandate_id, title in bullet_matches:
                mandate = Mandate(
                    id=mandate_id,
                    type="MANDATE",
                    title=title.strip(),
                    description=title.strip(),
                    category="core",
                    rationale="",
                )
                self.mandates.append(mandate)
                self.log(f"Parsed bullet-list mandate {mandate_id}: {title.strip()}")

        return len(self.mandates) > 0

    def parse_guidelines_dsl(self) -> bool:
        """Parse guidelines.dsl file"""
        guidelines_file = self._resolve_source_file("guidelines.dsl")
        if guidelines_file is None:
            return False

        content = guidelines_file.read_text(encoding="utf-8")

        # Canonical-only fallback: parse markdown headings if guidelines.md is used.
        if guidelines_file.suffix == ".md":
            md_matches = re.findall(
                r"^#{1,3}\s+(G\d{3})[:\s-]+(.+)$", content, re.MULTILINE
            )
            for guideline_id, title in md_matches:
                guideline = Guideline(
                    id=guideline_id,
                    type="GUIDELINE",
                    title=title.strip(),
                    description=title.strip(),
                    category="core",
                )
                self.guidelines.append(guideline)
                self.log(f"Parsed markdown guideline {guideline_id}: {title.strip()}")

            if len(self.guidelines) == 0:
                self.log(
                    "No guidelines discovered in markdown source; continuing with mandates only"
                )
            return True

        # Parse guideline blocks: guideline G01 { ... }
        pattern = r"guideline\s+(\w+)\s*\{([^}]+)\}"
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            guideline_id = match.group(1)
            guideline_content = match.group(2)

            title = self._extract_field(guideline_content, "title")
            desc = self._extract_field(guideline_content, "description")
            type_ = self._extract_field(guideline_content, "type")
            category = self._extract_field(guideline_content, "category")

            guideline = Guideline(
                id=guideline_id,
                type=type_,
                title=title,
                description=desc,
                category=category,
            )
            self.guidelines.append(guideline)
            if len(self.guidelines) <= 5:
                self.log(f"Parsed guideline {guideline_id}: {title}")

        if len(self.guidelines) > 5:
            self.log(f"... and {len(self.guidelines) - 5} more guidelines")

        if len(self.guidelines) == 0:
            self.log(
                "No guidelines discovered in guidelines.dsl; continuing with mandates only"
            )

        # Empty guideline set is valid when docs-meta intentionally has no guideline definitions.
        return True

    def _extract_field(self, content: str, field: str) -> str:
        """Extract field value from content block"""
        pattern = rf'{field}:\s*"([^"]*)"'
        match = re.search(pattern, content)
        return match.group(1) if match else ""

    def generate_markdown_templates(self) -> bool:  # noqa: C901
        """Generate markdown files by category with status fields"""
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.log(f"Creating output directory: {self.output_path}")

        # Remove stale generated files so current docs-meta state is reflected deterministically.
        for pattern in ("mandates-*.md", "guidelines-*.md", "README.md"):
            for stale in self.output_path.glob(pattern):
                if stale.is_file():
                    stale.unlink()

        # Group mandates by category
        if self.mandates:
            mandates_by_cat: dict[str, list[Mandate]] = defaultdict(list)
            for mandate in self.mandates:
                mandates_by_cat[mandate.category].append(mandate)

            for category, mandates in mandates_by_cat.items():
                filename = self.output_path / f"mandates-{category}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"# Mandates - {category.upper()}\n\n")
                    f.write("⚠️ HARD RULES - These are mandatory by default\n\n")

                    for mandate in mandates:
                        f.write(f"## {mandate.id}: {mandate.title}\n\n")
                        f.write(f"**Type:** {mandate.type}\n\n")
                        f.write(f"**Description:** {mandate.description}\n\n")
                        if mandate.rationale:
                            f.write(f"**Rationale:** {mandate.rationale}\n\n")

                        # NEW: Status fields with defaults
                        f.write("**Status:** `required: true` (Default: mandatory)\n\n")
                        f.write(
                            "**Customizable:** `false` (Hard rules cannot be modified)\n\n"
                        )
                        f.write("**Optional:** `false` (Not negotiable)\n\n")

                        f.write("---\n\n")

                self.log(f"Created {filename}")

        # Group guidelines by category
        if self.guidelines:
            guidelines_by_cat: dict[str, list[Guideline]] = defaultdict(list)
            for guideline in self.guidelines:
                guidelines_by_cat[guideline.category].append(guideline)

            for category, guidelines in guidelines_by_cat.items():
                filename = self.output_path / f"guidelines-{category}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"# Guidelines - {category.upper()}\n\n")
                    f.write(
                        "💡 SOFT RECOMMENDATIONS - These are optional/customizable\n\n"
                    )

                    for guideline in guidelines:
                        f.write(f"## {guideline.id}: {guideline.title}\n\n")
                        f.write(f"**Type:** {guideline.type}\n\n")
                        if guideline.description:
                            f.write(f"**Description:** {guideline.description}\n\n")

                        # NEW: Status fields with defaults
                        f.write("**Status:** `required: true` (Default: include)\n\n")
                        f.write("**Customizable:** `true` (Change below if needed)\n\n")
                        f.write("**Optional:** `false` (Included by default)\n\n")

                        f.write("### To Customize This Rule:\n\n")
                        f.write("Change the Status line above to ONE of:\n")
                        f.write("- `required: true` — Keep as mandatory\n")
                        f.write("- `optional: true` — Skip this rule\n")
                        f.write("- `custom: true` — Include but customizable\n\n")

                        f.write("---\n\n")

                self.log(f"Created {filename}")

        # Generate README with instructions
        readme = self.output_path / "README.md"
        with open(readme, "w", encoding="utf-8") as f:
            f.write(f"""# Phase 1: Governance Rules Templates

**Generated:** {datetime.now().isoformat()}

## Configuration

- **Language:** {self.language}
- **Adoption Level:** {self.adoption_level}

## What You Have

Raw templates for all mandates and guidelines, organized by category:
- `mandates-*.md` — Core architectural rules (hard, non-negotiable)
- `guidelines-*.md` — Best practices (soft, customizable)

Total: {len(self.mandates)} mandates + {len(self.guidelines)} guidelines

## Status Field Defaults

Each rule starts with:
```
**Status:** required: true
**Customizable:** true/false
**Optional:** false
```

## Phase 2: What to Do Now

### Step 1: Edit the Files

For each `.md` file in this folder:

1. **Open** in your editor
2. **Read** each rule (understand what it does)
3. **For each rule**, decide its status:
   - Keep as required: `required: true` → Include in final governance
   - Make optional: `optional: true` → Skip this rule
   - Make customizable: `custom: true` → Include but allow customization

### Step 2: Change Status Lines

Find lines like:
```markdown
**Status:** `required: true` (Default: include)
```

Change to ONE of:
```markdown
**Status:** `required: true`
**Status:** `optional: true`
**Status:** `custom: true`
```

### Step 3: Run Phase 3

Once you've edited the markdown files, just run:

```bash
./wizard.sh
# Choose: [3] Phase 3
```

Phase 3 will:
1. Read your edited markdown files from this folder
2. Parse the status fields (required/optional/custom)
3. Skip items marked as optional
4. Compile to final governance JSON

No need to convert to YAML or move files - edit in place!

## Questions?

- Mandates: Always required (cannot customize)
- Guidelines: Can be required/optional/custom
- Default: Everything starts as required (you decide what to change)
""")
        self.log(f"Created {readme}")

        return True

    def run(self) -> Phase1RunResult:
        """Execute Phase 1"""
        self._emit("\n📝 PHASE 1: Generate Governance Templates")
        self._emit("=" * 70)

        mandate_file = self._resolve_source_file("mandate.spec")
        if mandate_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate mandate.spec",
            }

        guidelines_file = self._resolve_source_file("guidelines.dsl")
        if guidelines_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate guidelines.dsl",
            }

        if not self.parse_mandate_spec():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse mandate.spec",
            }

        if not self.parse_guidelines_dsl():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse guidelines.dsl",
            }

        if not self.generate_markdown_templates():
            return {"success": False, "error": "Failed to generate markdown templates"}

        # Create input directory for Phase 2 user review
        phase2_input = self.output_path.parent / self.PHASE2_INPUT_DIRNAME
        phase2_input.mkdir(parents=True, exist_ok=True)
        self.log("Created phase-2-input directory (ready for Phase 2 customization)")

        self._emit(f"  ✅ Generated {len(self.mandates)} mandates")
        self._emit(f"  ✅ Generated {len(self.guidelines)} guidelines")
        self._emit(f"  📄 Source mandate: {mandate_file}")
        self._emit(f"  📄 Source guidelines: {guidelines_file}")
        self._emit(f"  📂 Templates: {self.output_path}")
        self._emit(f"  📂 Ready for Phase 2: {phase2_input}")
        self._emit("\n📋 NEXT STEPS:")
        self._emit(f"   1. Review files in: {self.output_path}")
        self._emit("   2. Edit status fields for each rule (required/optional/custom)")
        self._emit("   3. Run wizard Phase 3 to compile")

        return {
            "success": True,
            "mandate_count": len(self.mandates),
            "guideline_count": len(self.guidelines),
            "mandate_spec_output": str(mandate_file),
            "output_path": str(self.output_path),
            "mandates": [m.to_dict() for m in self.mandates],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }
