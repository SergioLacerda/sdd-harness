# SDD Governance Projection for Claude Code (Soft/Standalone) Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Generate a self-contained, zero-SDD-mention Claude Code project
configuration (Soft/Standalone profile) from this repository's own governed
markdown sources, using only Claude Code's real, currently-documented file
conventions — no invented schema, no network or external runtime dependency,
reproducible golden-tested output. This is the Claude analogue of the existing
`DevinPluginGenerator.generate_standalone()` and
`CopilotStandaloneGenerator.generate_standalone()` (see
`docs/plans/2026-08-17-devin-governance-projection-soft-standalone.md` and
`docs/plans/2026-08-18-copilot-governance-projection-soft-standalone.md`), built to
the same criteria.

**Architecture:** New `packages/features/sdd_adapters/src/sdd_adapters/claude/`
subpackage, alongside (not replacing) two pre-existing, unrelated Claude-specific
mechanisms: the existing `AdapterGenerator` Claude target (`.claude/commands/*.md`,
SDD-branded, wizard-integrated per-skill output) and the `sdd governance generate`
wizard subsystem that produces this repository's own root `CLAUDE.md`.
`ClaudeStandaloneGenerator` reuses `sdd_adapters/devin/_content_sources.py`'s
`_load_governance_summary` and `_load_coding_practices` unmodified — both are
already generic over `output_dir: Path` with no Devin-specific coupling. Output
goes to `dist/claude-standalone/` (a build artifact, never scattered into the
consuming project's real `CLAUDE.md`/`.claude/`), mirroring every other
`dist/*-standalone` / `dist/*-plugin` convention in this package.

**Tech Stack:** Python 3.10+, Jinja2 (already a `sdd_adapters` dependency), pytest,
existing `sdd_adapters.devin._content_sources` functions.

---

## Context you need before starting

- Read `packages/features/sdd_adapters/src/sdd_adapters/copilot/generator.py`
  (the nearest direct precedent — standalone-only, no branded sibling mode) and
  `devin/_content_sources.py` first — this plan reuses both directly.
- Read `docs/spec/guides/claude-plugin-provider-surface-evidence.md` (Task 1 of
  this plan's discovery predecessor) — the verified real Claude Code file
  conventions this plan generates. Do not invent a file shape not listed there.
- Real Claude Code customization surface relevant here (verified 2026-08-19):
  - `CLAUDE.md` — project root, always-on, read as persistent context at session
    start. This plan's primary always-on output file (equivalent of Devin's
    `AGENTS.md`).
  - `.claude/rules/{topic}.md` — loaded per the `InstructionsLoaded` hook event
    description ("When CLAUDE.md or .claude/rules/*.md loaded"). This plan's
    equivalent of Devin's 7 `.devin/rules/*.md` topic files.
  - `.claude/settings.json` — supports both a `permissions.allow`/`permissions.deny`
    block (format `"ToolName(pattern)"`, deny > ask > allow evaluation order) and a
    `hooks` block. **Decision D-2** (from `proposal.md`): standalone mode ships
    `permissions` only, no `hooks` — by symmetry with Devin's own
    standalone-vs-plugin split, where `.devin/hooks.v1.json` exists only in the
    *plugin* bundle, never in `generate_standalone()`.
  - **Decision D-1** (from `proposal.md`): "standalone" means this plain
    project-config form, not the separate, richer `.claude-plugin/plugin.json`
    installable-plugin-bundle system Claude Code also supports (own manifest,
    `commands/`/`agents/`/`skills/` directories, marketplace registration). That
    form is out of scope for this plan.
  - Unlike Copilot, no structural-gap disclosure is needed in the generated
    `CLAUDE.md` — Claude Code's real surface has a confirmed equivalent for every
    element of Devin's standalone bundle (see evidence note's comparison table).

## Non-Goals (do not implement)

- Any change to `AdapterGenerator` or `templates/adapters/claude/*.tpl` — the
  existing SDD-branded per-skill Claude integration is untouched.
- Any change to the `sdd governance generate` wizard subsystem
  (`sdd_cli/commands/governance.py`, `sdd_wizard/...`) that produces this
  repository's own root `CLAUDE.md` — a separate, unrelated, SDD-branded
  mechanism.
- A `.claude-plugin/plugin.json` marketplace-installable plugin bundle (Decision
  D-1) — a structurally different deliverable, left to a future plan if the user
  wants it.
- A `hooks` block in the standalone `.claude/settings.json` (Decision D-2).
- Wiring `ClaudeStandaloneGenerator` into the wizard's automatic pipeline — stays
  an explicit, opt-in CLI action, same posture as the Devin and Copilot
  generators.

---

### Task 1: Scaffold the `claude` subpackage

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/claude/__init__.py`
- Modify: `packages/features/sdd_adapters/src/sdd_adapters/__init__.py`

**Step 1: Create the subpackage init**

```python
# packages/features/sdd_adapters/src/sdd_adapters/claude/__init__.py
"""Claude Code standalone governance projection generation (Soft/Standalone profile)."""

from .generator import ClaudeStandaloneGenerator, ClaudeStandaloneResult

__all__ = ["ClaudeStandaloneGenerator", "ClaudeStandaloneResult"]
```

This will fail to import until Task 3 creates `generator.py` — expected, nothing
imports `sdd_adapters.claude` yet.

**Step 2: Export from the package root**

Add `ClaudeStandaloneGenerator`, `ClaudeStandaloneResult` to
`sdd_adapters/__init__.py`'s imports and `__all__`, alongside the existing
`AdapterGenerator`/`DevinPluginGenerator`/`CopilotStandaloneGenerator` exports.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/claude/__init__.py packages/features/sdd_adapters/src/sdd_adapters/__init__.py
git commit -m "feat(sdd_adapters): scaffold claude standalone subpackage"
```

---

### Task 2: Standalone templates

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/claude_plugin/standalone/CLAUDE.md.tpl`
- Create: `.../standalone/rules/architecture.md.tpl`
- Create: `.../standalone/rules/git-safety.md.tpl`
- Create: `.../standalone/rules/testing.md.tpl`
- Create: `.../standalone/rules/generated-artifacts.md.tpl`
- Create: `.../standalone/rules/go.md.tpl`
- Create: `.../standalone/rules/documentation.md.tpl`
- Create: `.../standalone/rules/token-economy.md.tpl`
- Create: `.../standalone/settings.json.tpl`

No test in this step — inert until Task 3 renders them.

**`CLAUDE.md.tpl`** — must include, at minimum:
- A profile disclosure block equivalent to Devin's `AGENTS.md.tpl` (`policy_source:
  embedded_snapshot`, `assurance: reduced`, `external_dependencies: none`).
- The same governance-summary rendering already proven in Devin's
  `sdd-harness-summary.md.tpl`/`sdd-soft-governance-behavior.md.tpl` (mandate count,
  guideline categories) and, when present, `sdd-coding-practices.md.tpl`'s
  anti-pattern rendering — reuse the same Jinja2 context shape
  `devin/plugin_generator.py`'s `generate()` already builds
  (`governance_fingerprint`, `mandate_count`, `mandates`, `guideline_categories`,
  `guidelines`, `anti_patterns`, `go_resolution_bypass`), so all three generators
  stay content-consistent.
- No structural-gap disclosure section (unlike Copilot's `copilot-instructions.md.tpl`)
  — Claude's real surface has a confirmed equivalent for every Devin standalone
  element; see the evidence note's comparison table.

**Each `rules/{topic}.md.tpl`** — content adapted from the corresponding
`templates/devin_plugin/standalone/rules/{topic}.md.tpl` (same 7 topics, same
subject matter). Before finalizing frontmatter/scoping shape:
`[NEEDS CLARIFICATION: verify whether .claude/rules/*.md supports any per-file,
path-scoped loading mechanism — analogous to Copilot's applyTo glob frontmatter —
against code.claude.com/docs/en/settings; the evidence note found no confirmation
either way. If none exists, omit any scoping frontmatter and note in the file
header that the rule always loads in full for the session.]`

**`settings.json.tpl`** — emits only a `permissions` block
(`permissions.allow`/`permissions.deny`), populated with a conservative default rule
set (e.g. deny destructive git/filesystem commands, matching the spirit of Devin's
`config.json.tpl` deny list). No `hooks` key (Decision D-2).

**Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/templates/claude_plugin/
git commit -m "feat(sdd_adapters): add claude standalone templates"
```

---

### Task 3: `ClaudeStandaloneGenerator.generate_standalone()` (TDD)

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/claude/generator.py`
- Test: `packages/features/sdd_adapters/tests/test_claude_standalone_generator.py`

**Step 1: Write the failing test**

```python
# packages/features/sdd_adapters/tests/test_claude_standalone_generator.py
from __future__ import annotations

from pathlib import Path

from sdd_adapters.claude.generator import ClaudeStandaloneGenerator

_TOPICS = (
    "architecture", "git-safety", "testing", "generated-artifacts",
    "go", "documentation", "token-economy",
)


def test_generate_standalone_writes_full_surface(tmp_path: Path) -> None:
    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True
    root = tmp_path / "dist" / "claude-standalone"
    assert (root / "CLAUDE.md").exists()
    assert (root / ".claude" / "settings.json").exists()
    for topic in _TOPICS:
        assert (root / ".claude" / "rules" / f"{topic}.md").exists()


def test_generate_standalone_settings_has_no_hooks_key(tmp_path: Path) -> None:
    import json

    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True

    settings = json.loads(
        (tmp_path / "dist" / "claude-standalone" / ".claude" / "settings.json").read_text()
    )
    assert "permissions" in settings
    assert "hooks" not in settings  # Decision D-2


def test_generate_standalone_is_deterministic(tmp_path: Path) -> None:
    r1 = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    r2 = ClaudeStandaloneGenerator().generate_standalone(
        output_dir=tmp_path, dest=tmp_path / "dist2"
    )

    a = (tmp_path / "dist" / "claude-standalone" / "CLAUDE.md").read_text()
    b = (tmp_path / "dist2" / "CLAUDE.md").read_text()
    assert a == b
    assert r1.success and r2.success


def test_generate_standalone_never_touches_the_network(tmp_path: Path, monkeypatch) -> None:
    import socket

    def _blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted during standalone generation")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_claude_standalone_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdd_adapters.claude.generator'`

**Step 3: Implement `ClaudeStandaloneGenerator`**

Mirror `CopilotStandaloneGenerator.generate_standalone()` structurally:

```python
# packages/features/sdd_adapters/src/sdd_adapters/claude/generator.py
"""ClaudeStandaloneGenerator: zero-SDD-mention Claude Code governance projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..devin._content_sources import (
    _coding_practices_digest,
    _governance_summary_digest,
    _load_coding_practices,
    _load_governance_summary,
)

_TEMPLATES_DIR = (
    Path(__file__).parent.parent / "templates" / "claude_plugin" / "standalone"
)
_STANDALONE_RULESET_VERSION = "1.0.0"
_TOPIC_NAMES = (
    "architecture", "git-safety", "testing", "generated-artifacts",
    "go", "documentation", "token-economy",
)


@dataclass
class ClaudeStandaloneResult:
    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True
    governance_summary_digest: str = ""
    coding_practices_digest: str = ""


class ClaudeStandaloneGenerator:
    """Generates a zero-SDD-mention Claude Code governance projection (Soft/Standalone)."""

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_standalone(
        self, output_dir: Path, dest: Path | None = None
    ) -> ClaudeStandaloneResult:
        result = ClaudeStandaloneResult()

        governance_summary = _load_governance_summary(output_dir)
        result.governance_summary_digest = _governance_summary_digest(governance_summary)

        try:
            coding_practices = _load_coding_practices(output_dir)
        except ValueError as e:
            result.success = False
            result.errors.append(str(e))
            return result
        result.coding_practices_digest = (
            _coding_practices_digest(coding_practices) if coding_practices else ""
        )

        context: dict[str, Any] = {
            "standalone_ruleset_version": _STANDALONE_RULESET_VERSION,
            "governance_fingerprint": governance_summary["governance_fingerprint"],
            "workspace_version": governance_summary["workspace_version"],
            "mandate_count": governance_summary["mandate_count"],
            "mandates": governance_summary["mandates"],
            "guideline_categories": governance_summary["guideline_categories"],
            "guidelines": governance_summary["guidelines"],
            "has_coding_practices": coding_practices is not None,
            "anti_patterns": coding_practices["anti_patterns"] if coding_practices else [],
            "go_resolution_bypass": (
                coding_practices["go_resolution_bypass"] if coding_practices else None
            ),
        }

        root = Path(dest) if dest else Path(output_dir) / "dist" / "claude-standalone"

        try:
            self._write(root / "CLAUDE.md", "CLAUDE.md", context, result)
            for topic in _TOPIC_NAMES:
                self._write(
                    root / ".claude" / "rules" / f"{topic}.md",
                    f"rules/{topic}.md",
                    context,
                    result,
                )
            self._write(
                root / ".claude" / "settings.json", "settings.json", context, result
            )
        except Exception as e:  # defensive: partial output is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write(
        self, path: Path, template_name: str, context: dict[str, Any], result: ClaudeStandaloneResult
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_claude_standalone_generator.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/claude/generator.py packages/features/sdd_adapters/tests/test_claude_standalone_generator.py
git commit -m "feat(sdd_adapters): implement ClaudeStandaloneGenerator.generate_standalone()"
```

---

### Task 4: End-to-end test against this repo's real governance sources

**Files:**
- Modify: `packages/features/sdd_adapters/tests/test_claude_standalone_generator.py`

**Step 1: Write the test**

```python
def test_generate_standalone_against_real_repo_sources(tmp_path: Path) -> None:
    # tests/ -> sdd_adapters/ -> features/ -> packages/ -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / ".sdd" / "metadata.json").exists(), (
        "sanity check: adjust the parents[] index above if the package moves"
    )

    result = ClaudeStandaloneGenerator().generate_standalone(
        output_dir=repo_root, dest=tmp_path / "claude-standalone"
    )

    assert result.success is True, result.errors
    assert (tmp_path / "claude-standalone" / "CLAUDE.md").exists()
```

**Step 2: Run it**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_claude_standalone_generator.py::test_generate_standalone_against_real_repo_sources -v`
Expected: PASS. If `parents[4]` is wrong, the sanity-check assertion fails clearly.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/tests/test_claude_standalone_generator.py
git commit -m "test(sdd_adapters): verify claude standalone generation against real repo governance sources"
```

---

### Task 5: CLI command — `sdd claude build --standalone`

**Files:**
- Create: `packages/interfaces/sdd_cli/src/sdd_cli/commands/claude.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`
- Test: `packages/interfaces/sdd_cli/tests/commands/test_claude.py`

**Step 1: Look at the existing pattern**

Read `packages/interfaces/sdd_cli/src/sdd_cli/commands/copilot.py` in full — mirror
its Typer/`resolve_workspace_root` conventions and its standalone-only shape (no
`--skills` flag to reconcile; the existing SDD-branded Claude path is the
pre-existing wizard-integrated `AdapterGenerator`, not a flag on this command).

**Step 2: Write the failing test**

```python
# packages/interfaces/sdd_cli/tests/commands/test_claude.py
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sdd_cli.commands.claude import app

runner = CliRunner()


def test_claude_build_writes_standalone_surface(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / "claude-standalone" / "CLAUDE.md").exists()
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_claude.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdd_cli.commands.claude'`

**Step 4: Implement the command**

```python
# packages/interfaces/sdd_cli/src/sdd_cli/commands/claude.py
"""Claude Code governance projection build commands (Soft/Standalone profile)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(
    help="Claude Code governance projection generation", invoke_without_command=True
)
console = Console()


@app.callback(invoke_without_command=True)
def claude_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_command_group("Claude", ["build"])
        raise typer.Exit(0)


@app.command("build")
def build(
    dest: Path | None = typer.Option(
        None, "--dest", help="Output directory (default: <workspace>/dist/claude-standalone)."
    ),
) -> None:
    """Build the Soft/Standalone Claude Code governance projection using real Claude Code conventions."""
    from sdd_adapters.claude import ClaudeStandaloneGenerator

    ws_root = resolve_workspace_root()
    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=ws_root, dest=dest)

    if not result.success:
        console.print(f"[red]Claude standalone build failed:[/red] {'; '.join(result.errors)}")
        raise typer.Exit(1)

    console.print(
        f"[green]Claude standalone config built[/green] ({len(result.files_written)} files)"
    )
```

**Step 5: Register the command**

In `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`, add to
`COMMAND_SPECS` (alphabetical position near `"claude"`... note: check for a naming
collision with any pre-existing `"claude"` key before adding; if one exists, this
new command group must be reconciled with it rather than silently shadowing it —
flag as a blocker if found):

```python
    "claude": CommandSpec(
        "sdd_cli.commands.claude", "Claude Code governance projection generation"
    ),
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_claude.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/claude.py packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py packages/interfaces/sdd_cli/tests/commands/test_claude.py
git commit -m "feat(sdd_cli): add 'sdd claude build --standalone' command"
```

---

### Task 6: Documentation

**Files:**
- Create: `docs/spec/guides/claude-governance-plugin.md`

**Step 1: Write the doc**

Same structure as `docs/spec/guides/copilot-governance-plugin.md`: what
Soft/Standalone means for Claude Code specifically (embedded snapshot, reduced
assurance, no network), build command, bundle contents table, canonical-source
disclaimer, and an explicit statement of Decisions D-1 and D-2 (from `proposal.md`)
so a reader understands why the plugin-bundle form and the `hooks` block were
deliberately excluded — not oversights.

**Step 2: No test — documentation only.**

**Step 3: Commit**

```bash
git add docs/spec/guides/claude-governance-plugin.md
git commit -m "docs: document the Claude Code Soft/Standalone governance projection"
```

---

### Task 7: Full test run + governance validation

**Step 1: Run the full affected test suites**

Run: `uv run pytest packages/features/sdd_adapters packages/interfaces/sdd_cli/tests/commands/test_claude.py -v`
Expected: all PASS, including pre-existing Devin/Copilot/Codex/Antigravity tests
untouched (confirms no regression).

**Step 2: Run repo-wide governance validation**

Run: `sdd governance validate` (confirm the exact command in `Makefile` first, same
caveat as the Devin/Copilot plans' equivalent task).

**Step 3: Report residual risks and unverified assumptions to the user**

Summarize in the final message (not a new file):
- `.claude/rules/*.md` loading/scoping semantics (whole-file vs. path-scoped) were
  not confirmed by the evidence note's search pass — resolve before Task 2's
  templates are considered final (see the `[NEEDS CLARIFICATION]` marker there).
- Decision D-1 (project-config form, not plugin bundle) and Decision D-2
  (permissions only, no hooks) were made by symmetry with Devin's own
  standalone/plugin split, not from an explicit user requirement — confirm both
  still hold before shipping, especially if the user later wants an installable
  Claude plugin.
- The generated bundle has not been tested inside a real Claude Code session —
  only schema-level and structural verification was done. Recommend the user copy
  `dist/claude-standalone/{CLAUDE.md,.claude}` into a real project and confirm
  Claude Code picks up the files as expected before declaring this
  production-ready.
- Check Task 5's flagged possible naming collision on the `"claude"` CLI command
  group key before registering.

No commit for this task — verification only.

---

## Execution Handoff

Plan complete and saved to
`docs/plans/2026-08-19-claude-governance-projection-soft-standalone.md`. This plan
was produced by a Strategist mission (`20260819-claude-standalone`) as a
`documentation_target` deliverable — Tasks 1-7 above are `implementation_handoff`
work and were never executed by Strategist's Sniper. Two execution options once you
want to proceed:

1. **Subagent-Driven (this session)** — dispatch a fresh subagent per task, review
   the diff between tasks, fast iteration.
2. **Parallel Session (separate)** — open a new session with the `executing-plans`
   skill, batch execution with checkpoints.

Which approach?
