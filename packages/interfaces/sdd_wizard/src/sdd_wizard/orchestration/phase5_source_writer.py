"""
SddSourceWriter — Phase 5 step: write .sdd/source/ and .sdd/runtime/ content.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from sdd_core.utils.logging import get_logger

logger = get_logger(__name__)


class SddSourceWriter:
    """Create directories and generate all .sdd/source/ + .sdd/runtime/ markdown files."""

    def __init__(
        self,
        output_base: Path,
        source_dir: Path,
        runtime_dir: Path,
        mandates_dir: Path,
        guidelines_dir: Path,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self.output_base = output_base
        self.source_dir = source_dir
        self.runtime_dir = runtime_dir
        self.mandates_dir = mandates_dir
        self.guidelines_dir = guidelines_dir
        self.mandates = mandates
        self.guidelines = guidelines
        self.guidelines_by_category = guidelines_by_category
        self.config = config
        self.verbose = verbose

        # Safeguard: Never mutate the project root during tests
        import os

        from sdd_core.utils.environment import is_repo_root

        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                # Check if output_base is a known repo root (has .sdd/ or is a pyproject.toml repo)
                output_resolved = self.output_base.resolve()
                if is_repo_root(output_resolved):
                    should_block = True
            except (OSError, ValueError):
                # Fallback if resolve fails
                pass

            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"  ❌ {msg}")  # noqa: T201
                raise PermissionError(msg)

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def create_directories(self) -> bool:
        """Create output directory structure."""
        self._log("Creating directory structure")
        try:
            self.mandates_dir.mkdir(parents=True, exist_ok=True)
            self.guidelines_dir.mkdir(parents=True, exist_ok=True)
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            workflows_dir = self.output_base / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            self._log("Created directories: .sdd, .github")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create directories: {e}")  # noqa: T201
            return False

    def generate_mandates_file(self) -> bool:
        """Generate mandates.md with IA-FIRST optimization."""
        self._log("Generating mandates.md")
        try:
            mandates_file = self.mandates_dir / "mandates.md"
            content = f"""# Mandates - SDD v3.0

⚡ IA-FIRST DESIGN NOTICE
- **Status**: Architecture-level governance rules
- **Optimization**: Optimized for AI agent parsing
- **Version**: 3.0
- **Generated**: {datetime.now().isoformat()}

## Core Mandates

Mandatory rules that CANNOT be customized or skipped.

"""
            for mandate in self.mandates:
                mandate_id = mandate.get("id", "M000")
                mandate_title = mandate.get("title") or f"Mandate {mandate_id}"
                content += f"""### {mandate_id}: {mandate_title}

**Criticality**: {mandate.get("criticality", "OBRIGATÓRIO")}
**Customizable**: No

{mandate.get("content") or mandate.get("description") or mandate.get("summary_minimal") or "No description available"}

"""
            with open(mandates_file, "w", encoding="utf-8") as f:
                f.write(content)
            self._log(f"Generated mandates.md ({len(self.mandates)} mandates)")
            return True
        except Exception as e:
            print(f"  ❌ Failed to generate mandates.md: {e}")  # noqa: T201
            return False

    def generate_guidelines_files(self) -> bool:
        """Generate guidelines organized by category."""
        self._log("Generating guidelines by category")
        try:
            category_names = {
                "architecture": "Architecture",
                "testing": "Testing",
                "git": "Git Workflow",
                "naming": "Naming Conventions",
                "docs": "Documentation",
                "style": "Code Style",
                "performance": "Performance",
                "security": "Security",
                "other": "Other Guidelines",
            }
            for category, guidelines in self.guidelines_by_category.items():
                friendly_name = category_names.get(category, category.title())
                guidelines_file = self.guidelines_dir / f"{category}.md"
                content = f"""# {friendly_name} Guidelines

⚡ IA-FIRST DESIGN NOTICE
- **Status**: Customizable best practices
- **Optimization**: Optimized for AI agent parsing
- **Category**: {friendly_name}
- **Count**: {len(guidelines)} guidelines
- **Generated**: {datetime.now().isoformat()}

## Overview

Guidelines in this category provide structured recommendations for {friendly_name.lower()}.

"""
                for guideline in guidelines:
                    guideline_id = guideline.get("id", "G000")
                    guideline_title = (
                        guideline.get("title") or f"Guideline {guideline_id}"
                    )
                    content += f"""### {guideline_id}: {guideline_title}

**Type**: {guideline.get("type", "GUIDELINE")}
**Status**: {guideline.get("status", "required")}
**Customizable**: {"Yes" if guideline.get("customizable", True) else "No"}

{guideline.get("content", "No description available")}

"""
                with open(guidelines_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self._log(f"Generated {category}.md ({len(guidelines)} guidelines)")
            return True
        except Exception as e:
            print(f"  ❌ Failed to generate guidelines files: {e}")  # noqa: T201
            return False

    def generate_source_readme(self) -> bool:
        """Generate README.md with agent instructions for .sdd/source."""
        self._log("Generating .sdd/source/README.md")
        try:
            source_readme = self.source_dir / "README.md"
            categories_list = "\n".join(
                f"- {cat.title()}" for cat in sorted(self.guidelines_by_category.keys())
            )
            content = f"""# .sdd/source - Governance Source of Truth

⚡ **For AI Agents: This is your primary query directory**

## Overview

This directory contains the **compiled and optimized** governance specifications that agents should reference.

**Generated**: {datetime.now().isoformat()}
**Language**: {self.config.get("language", "Python")}
**Adoption Level**: {self.config.get("adoption_level", "FULL")}

## Directory Structure

```
.sdd/source/
├── mandates/
│   └── mandates.md              ← Read mandates first (hard rules)
├── guidelines/
│   ├── git.md                   ← Git workflow
│   ├── testing.md               ← Testing strategies
│   ├── naming.md                ← Naming conventions
│   ├── docs.md                  ← Documentation standards
│   ├── style.md                 ← Code style
│   └── performance.md           ← Performance guidelines
└── README.md                    ← This file
```

## For AI Agents: How to Use This

### 1. Query Mandates First

Always read `.sdd/source/mandates/mandates.md` to understand **hard rules** that CANNOT be customized.

```
cat .sdd/source/mandates/mandates.md
```

### 2. Query Relevant Guidelines

Based on the task, read relevant guidelines:

```
# For git-related work
cat .sdd/source/guidelines/git.md

# For testing-related work
cat .sdd/source/guidelines/testing.md

# For naming decisions
cat .sdd/source/guidelines/naming.md
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

See `.sdd/runtime/README.md` for detailed pre-cache instructions.

## File Organization

### Mandates (Non-customizable)
- Location: `.sdd/source/mandates/mandates.md`
- Count: {len(self.mandates)}
- Rule: **MUST** be followed (no exceptions)

### Guidelines (Customizable)
- Location: `.sdd/source/guidelines/`
- Count: {len(self.guidelines)}
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
            with open(source_readme, "w", encoding="utf-8") as f:
                f.write(content)
            self._log("Generated .sdd/source/README.md")
            return True
        except Exception as e:
            print(f"  ❌ Failed to generate source README: {e}")  # noqa: T201
            return False

    def generate_runtime_readme(self) -> bool:
        """Generate README.md with pre-cache instructions for .sdd/runtime."""
        self._log("Generating .sdd/runtime/README.md")
        try:
            runtime_readme = self.runtime_dir / "README.md"
            content = f"""# .sdd/runtime - Agent Pre-Cache Strategy

⚡ **For AI Agents: Instructions on using .sdd/source as pre-cache**

## Overview

This directory provides guidance on how to use `.sdd/source/` as a **pre-cache**
mechanism for AI agents to reduce context token usage and improve performance.

**Generated**: {datetime.now().isoformat()}

## What is Pre-Caching?

Pre-caching is a strategy where:

1. Governance files are loaded **once** at the start of an agent session
2. Content is cached **in memory** (not re-read from disk)
3. Subsequent tasks **reference** the cached content instead of re-reading files

**Result**: Lower token usage, faster execution, consistent governance adherence.

## Pre-Cache Workflow

### Session Start (Agent Initialization)

```python
# When agent starts, load governance once
def init_agent():
    mandates = read_file('.sdd/source/mandates/mandates.md')
    guidelines = {{}}
    for category in ['git', 'testing', 'naming', 'docs', 'style', 'performance']:
        guidelines[category] = read_file(f'.sdd/source/guidelines/{{category}}.md')

    # Cache in agent memory/context
    agent.context['mandates'] = mandates
    agent.context['guidelines'] = guidelines
```

### Task Execution (Reference, Don't Re-Read)

```python
# During task execution, reference cached content
def execute_task(task):
    relevant_category = determine_category(task)
    guideline = agent.context['guidelines'][relevant_category]

    # Use guideline in task execution
    # DO NOT re-read from .sdd/source
```

### Session End

- Cached content is available for entire agent session
- No disk reads for governance after initial load
- Only refresh if files are explicitly updated

## Integration with Agent Frameworks

### With LangChain/LlamaIndex

```python
from langchain.memory import ConversationBufferMemory

# Store governance in agent memory
agent.memory['mandates'] = read_governance('mandates')
agent.memory['guidelines'] = read_governance('guidelines')

# Use in prompts
system_prompt = f'''
You follow SDD governance.

MANDATES:
{{agent.memory['mandates']}}

GUIDELINES:
{{agent.memory['guidelines'][task_category]}}
'''
```

### With Custom Agents

```python
class SDDAgent:
    def __init__(self, project_root):
        self.governance = {{}}
        self.load_governance(project_root)

    def load_governance(self, project_root):
        '''Load governance once at startup'''
        source_dir = Path(project_root) / '.sdd' / 'source'

        self.governance['mandates'] = (source_dir / 'mandates' / 'mandates.md').read_text()
        self.governance['guidelines'] = {{}}

        for category_file in (source_dir / 'guidelines').glob('*.md'):
            category = category_file.stem
            self.governance['guidelines'][category] = category_file.read_text()

    def execute(self, task):
        '''Execute task with cached governance'''
        relevant_guideline = self.governance['guidelines'].get(task.category)
        # Use cached guideline
        return self.process_task(task, relevant_guideline)
```

## Memory Organization Strategy

### By Category (Recommended)

```
agent.memory = {{
    'mandates': <mandates_content>,
    'guidelines': {{
        'git': <git_guidelines>,
        'testing': <testing_guidelines>,
        'naming': <naming_guidelines>,
        'docs': <docs_guidelines>,
        'style': <style_guidelines>,
        'performance': <performance_guidelines>
    }},
    'last_updated': <timestamp>,
    'cache_validity': 86400  # 24 hours in seconds
}}
```

### By Usage Frequency (Alternative)

```
agent.memory = {{
    'frequent': {{
        'mandates': <mandates_content>,
        'git_guidelines': <git_guidelines>,
        'testing_guidelines': <testing_guidelines>
    }},
    'occasional': {{
        'naming_guidelines': <naming_guidelines>,
        'style_guidelines': <style_guidelines>
    }},
    'reference': {{
        'docs_guidelines': <docs_guidelines>,
        'performance_guidelines': <performance_guidelines>
    }}
}}
```

## Cache Invalidation

Re-read governance from `.sdd/source/` if:

1. **Manual update**: Files are explicitly updated by developer
2. **Time-based**: Cache expires (e.g., 24 hours)
3. **Version change**: Metadata indicates version change
4. **Explicit refresh**: Agent receives refresh command

Example cache validity check:

```python
def should_refresh_cache(agent):
    last_update = agent.memory.get('governance_updated')
    current_time = time.time()

    # Refresh if older than 24 hours or no timestamp
    cache_age = current_time - (last_update or 0)
    return cache_age > 86400
```

## Optimization Tips

### 1. Lazy Loading (For Large Governance)

Don't load all guidelines at once. Load on demand:

```python
def get_guideline(category):
    if category not in agent.memory.get('guidelines', {{}}):
        path = Path('.sdd/source/guidelines') / f'{{category}}.md'
        agent.memory['guidelines'][category] = path.read_text()
    return agent.memory['guidelines'][category]
```

### 2. Compression (For Token Efficiency)

Compress guidelines before caching:

```python
import gzip
import base64

def compress_guideline(content):
    compressed = gzip.compress(content.encode())
    return base64.b64encode(compressed).decode()

def decompress_guideline(encoded):
    compressed = base64.b64decode(encoded)
    return gzip.decompress(compressed).decode()
```

### 3. Summarization (For Context Window)

Create summaries instead of full files:

```python
# For each guideline, create a 1-paragraph summary
summaries = {{
    'git': 'Use conventional commits, protect main, PR reviews required, ...',
    'testing': 'Write tests first, >80% coverage required, run CI on all PRs, ...',
    ...
}}
```

## Troubleshooting

### Issue: Agent doesn't follow governance

**Solution**: Verify cache was loaded and is up-to-date
```python
print(agent.memory.get('governance_updated'))  # noqa: T201
print(len(agent.memory.get('mandates', '')))  # noqa: T201
```

### Issue: Out of memory with large governance

**Solution**: Use lazy loading or compression (see Optimization Tips)

### Issue: Stale governance after updates

**Solution**: Implement cache invalidation based on file mtime
```python
governance_mtime = Path('.sdd/source/mandates/mandates.md').stat().st_mtime
if governance_mtime > agent.memory.get('governance_loaded_at', 0):
    refresh_cache()
```

## Best Practices

1. ✅ **Load once per session** - Don't re-read governance files repeatedly
2. ✅ **Cache in memory** - Keep governance in agent context/memory
3. ✅ **Reference by category** - Use structured memory keys
4. ✅ **Implement cache invalidation** - Refresh on updates
5. ✅ **Monitor cache size** - Warn if governance grows too large
6. ✅ **Document cache strategy** - Clarify to team how governance is cached

## Metrics to Track

- Cache hit rate (% of requests using cached vs fresh)
- Average token savings per session
- Cache refresh frequency
- Cache size in memory

---

**Generated by SDD Wizard v3.0**
"""
            with open(runtime_readme, "w", encoding="utf-8") as f:
                f.write(content)
            self._log("Generated .sdd/runtime/README.md")
            return True
        except Exception as e:
            print(f"  ❌ Failed to generate runtime README: {e}")  # noqa: T201
            return False
