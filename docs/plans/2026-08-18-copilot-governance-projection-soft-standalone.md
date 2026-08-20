# SDD Governance Projection for GitHub Copilot (Soft/Standalone) Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Generate a self-contained, zero-SDD-mention GitHub Copilot governance
configuration (Soft/Standalone profile) from this repository's own governed markdown
sources, using only GitHub Copilot's real, currently-documented file conventions —
no invented schema, no network or external runtime dependency, reproducible
golden-tested output. This is the Copilot analogue of the existing
`DevinPluginGenerator.generate_standalone()` (see
`docs/plans/2026-08-17-devin-governance-projection-soft-standalone.md`), built to
the same criteria.

**Architecture:** New `packages/features/sdd_adapters/src/sdd_adapters/copilot/`
subpackage, alongside (not replacing) the existing `AdapterGenerator` Copilot target
(`.github/prompts/*.prompt.md`, SDD-branded, wizard-integrated). `CopilotStandaloneGenerator`
reuses `sdd_adapters/devin/_content_sources.py`'s `_load_governance_summary` and
`_load_coding_practices` unmodified — both are already generic over `output_dir:
Path` with no Devin-specific coupling. Output goes to `dist/copilot-standalone/` (a
build artifact, never scattered into the consuming project's real `.github/`),
mirroring every other `dist/*-standalone` / `dist/*-plugin` convention in this
package.

**Tech Stack:** Python 3.10+, Jinja2 (already a `sdd_adapters` dependency), pytest,
existing `sdd_adapters.devin._content_sources` functions.

---

## Context you need before starting

- Read `packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py`
  (specifically `generate_standalone()` and `_write_standalone()`) and
  `devin/_content_sources.py` first — this plan reuses both directly.
- Read `docs/spec/guides/copilot-plugin-provider-surface-evidence.md` (Task 1 of
  this plan's discovery predecessor) — the verified real Copilot file conventions
  this plan generates. Do not invent a file shape not listed there.
- Real GitHub Copilot customization surface (verified 2026-08-18):
  - `.github/copilot-instructions.md` — always-on, broadest documented surface
    (completions + Chat + PR review). This plan's primary always-on output file.
  - `.github/instructions/{topic}.instructions.md` — `applyTo` glob frontmatter;
    a file without `applyTo` behaves like `applyTo: "**"`. This plan's equivalent of
    Devin's 7 `.devin/rules/*.md` topic files.
  - **No confirmed Copilot equivalent** for Devin's `.devin/hooks.v1.json` (lifecycle
    hook) or `.devin/config.json` (declarative config). This plan does not invent
    substitutes for either — it discloses both gaps in the generated
    `.github/copilot-instructions.md` text itself.
  - Root `AGENTS.md` is also natively read by Copilot coding agent, but precedence
    against `.github/copilot-instructions.md` when both exist is undocumented as of
    this search — this plan deliberately emits `.github/copilot-instructions.md`
    only, not both (see Task 5, Decision D1).

## Non-Goals (do not implement)

- Any change to `AdapterGenerator` or `templates/adapters/copilot/*.tpl` — the
  existing SDD-branded per-skill Copilot integration is untouched.
- A `.github/hooks.json` or any other invented lifecycle-hook file — no real Copilot
  convention supports it (see evidence note § Confirmed structural gaps).
- A single declarative permissions/config JSON file — no real Copilot convention
  supports it either.
- `.github/chatmodes/*.chatmode.md` or `.github/prompts/*.prompt.md` generation in
  the standalone mode — those are explicitly-invoked, task-specific files, not
  always-on governance surface; out of scope for a first slice (candidate for a
  later plan once the always-on + path-scoped layer is proven).
- Wiring `CopilotStandaloneGenerator` into the wizard's automatic pipeline — stays
  an explicit, opt-in CLI action, same posture as both Devin generators.

---

### Task 1: Scaffold the `copilot` subpackage

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/copilot/__init__.py`
- Modify: `packages/features/sdd_adapters/src/sdd_adapters/__init__.py`

**Step 1: Create the subpackage init**

```python
# packages/features/sdd_adapters/src/sdd_adapters/copilot/__init__.py
"""Copilot standalone governance projection generation (Soft/Standalone profile)."""

from .generator import CopilotStandaloneGenerator, CopilotStandaloneResult

__all__ = ["CopilotStandaloneGenerator", "CopilotStandaloneResult"]
```

This will fail to import until Task 2 creates `generator.py` — expected, nothing
imports `sdd_adapters.copilot` yet.

**Step 2: Export from the package root**

Add `CopilotStandaloneGenerator`, `CopilotStandaloneResult` to
`sdd_adapters/__init__.py`'s imports and `__all__`, alongside the existing
`AdapterGenerator`/`DevinPluginGenerator` exports.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/copilot/__init__.py packages/features/sdd_adapters/src/sdd_adapters/__init__.py
git commit -m "feat(sdd_adapters): scaffold copilot standalone subpackage"
```

---

### Task 2: Standalone templates

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/copilot_plugin/standalone/copilot-instructions.md.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/copilot_plugin/standalone/instructions/architecture.instructions.md.tpl`
- Create: `.../instructions/git-safety.instructions.md.tpl`
- Create: `.../instructions/testing.instructions.md.tpl`
- Create: `.../instructions/generated-artifacts.instructions.md.tpl`
- Create: `.../instructions/python.instructions.md.tpl`
- Create: `.../instructions/go.instructions.md.tpl`
- Create: `.../instructions/documentation.instructions.md.tpl`

No test in this step — inert until Task 3 renders them.

**`copilot-instructions.md.tpl`** — must include, at minimum:
- A profile disclosure block equivalent to Devin's `AGENTS.md.tpl` (`policy_source:
  embedded_snapshot`, `assurance: reduced`, `external_dependencies: none`).
- An explicit "no hook mechanism, no declarative config file" disclosure, citing
  `docs/spec/guides/copilot-plugin-provider-surface-evidence.md` § Confirmed
  structural gaps, so a reader understands this is a documented, verified limitation
  — not an oversight.
- The same governance-summary rendering already proven in Devin's
  `sdd-harness-summary.md.tpl`/`sdd-soft-governance-behavior.md.tpl` (mandate count,
  guideline categories) and, when present, `sdd-coding-practices.md.tpl`'s
  anti-pattern rendering — reuse the same Jinja2 context shape
  `devin/plugin_generator.py`'s `generate()` already builds
  (`governance_fingerprint`, `mandate_count`, `mandates`, `guideline_categories`,
  `guidelines`, `anti_patterns`, `go_resolution_bypass`), so the two generators stay
  content-consistent.

**Each `{topic}.instructions.md.tpl`** — YAML frontmatter with `applyTo`:
- `architecture`, `git-safety`, `testing`, `generated-artifacts`, `documentation` →
  `applyTo: "**"` (repo-wide topics, no language scope).
- `python` → `applyTo: "**/*.py"`.
- `go` → `applyTo: "**/*.go"`.

Content of each topic file should be adapted from the corresponding
`templates/devin_plugin/standalone/rules/{topic}.md.tpl` (same subject matter,
reformatted with the `applyTo` frontmatter Copilot requires instead of Devin's rule
trigger shape).

**Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/templates/copilot_plugin/
git commit -m "feat(sdd_adapters): add copilot standalone templates"
```

---

### Task 3: `CopilotStandaloneGenerator.generate_standalone()` (TDD)

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/copilot/generator.py`
- Test: `packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py`

**Step 1: Write the failing test**

```python
# packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py
from __future__ import annotations

from pathlib import Path

from sdd_adapters.copilot.generator import CopilotStandaloneGenerator

_TOPICS = (
    "architecture", "git-safety", "testing", "generated-artifacts",
    "python", "go", "documentation",
)


def test_generate_standalone_writes_full_surface(tmp_path: Path) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True
    root = tmp_path / "dist" / "copilot-standalone"
    assert (root / ".github" / "copilot-instructions.md").exists()
    for topic in _TOPICS:
        assert (root / ".github" / "instructions" / f"{topic}.instructions.md").exists()


def test_generate_standalone_is_deterministic(tmp_path: Path) -> None:
    r1 = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    r2 = CopilotStandaloneGenerator().generate_standalone(
        output_dir=tmp_path, dest=tmp_path / "dist2"
    )

    a = (tmp_path / "dist" / "copilot-standalone" / ".github" / "copilot-instructions.md").read_text()
    b = (tmp_path / "dist2" / ".github" / "copilot-instructions.md").read_text()
    assert a == b
    assert r1.success and r2.success


def test_generate_standalone_never_touches_the_network(tmp_path: Path, monkeypatch) -> None:
    import socket

    def _blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted during standalone generation")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdd_adapters.copilot.generator'`

**Step 3: Implement `CopilotStandaloneGenerator`**

Mirror `DevinPluginGenerator.generate_standalone()` / `_write_standalone()`
structurally:

```python
# packages/features/sdd_adapters/src/sdd_adapters/copilot/generator.py
"""CopilotStandaloneGenerator: zero-SDD-mention Copilot governance projection."""

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
    Path(__file__).parent.parent / "templates" / "copilot_plugin" / "standalone"
)
_STANDALONE_RULESET_VERSION = "1.0.0"
_TOPIC_NAMES = (
    "architecture", "git-safety", "testing", "generated-artifacts",
    "python", "go", "documentation",
)


@dataclass
class CopilotStandaloneResult:
    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True
    governance_summary_digest: str = ""
    coding_practices_digest: str = ""


class CopilotStandaloneGenerator:
    """Generates a zero-SDD-mention Copilot governance projection (Soft/Standalone)."""

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
    ) -> CopilotStandaloneResult:
        result = CopilotStandaloneResult()

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

        root = Path(dest) if dest else Path(output_dir) / "dist" / "copilot-standalone"

        try:
            self._write(
                root / ".github" / "copilot-instructions.md",
                "copilot-instructions.md",
                context,
                result,
            )
            for topic in _TOPIC_NAMES:
                self._write(
                    root / ".github" / "instructions" / f"{topic}.instructions.md",
                    f"instructions/{topic}.instructions.md",
                    context,
                    result,
                )
        except Exception as e:  # defensive: partial output is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write(
        self, path: Path, template_name: str, context: dict[str, Any], result: CopilotStandaloneResult
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/copilot/generator.py packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py
git commit -m "feat(sdd_adapters): implement CopilotStandaloneGenerator.generate_standalone()"
```

---

### Task 4: End-to-end test against this repo's real governance sources

**Files:**
- Modify: `packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py`

**Step 1: Write the test**

```python
def test_generate_standalone_against_real_repo_sources(tmp_path: Path) -> None:
    # tests/ -> sdd_adapters/ -> features/ -> packages/ -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / ".sdd" / "metadata.json").exists(), (
        "sanity check: adjust the parents[] index above if the package moves"
    )

    result = CopilotStandaloneGenerator().generate_standalone(
        output_dir=repo_root, dest=tmp_path / "copilot-standalone"
    )

    assert result.success is True, result.errors
    content = (tmp_path / "copilot-standalone" / ".github" / "copilot-instructions.md").read_text()
    assert "hook" in content.lower() or "hooks" in content.lower()  # gap disclosure present
```

**Step 2: Run it**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py::test_generate_standalone_against_real_repo_sources -v`
Expected: PASS. If `parents[4]` is wrong, the sanity-check assertion fails clearly.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/tests/test_copilot_standalone_generator.py
git commit -m "test(sdd_adapters): verify copilot standalone generation against real repo governance sources"
```

---

### Task 5: CLI command — `sdd copilot build --standalone`

**Files:**
- Create: `packages/interfaces/sdd_cli/src/sdd_cli/commands/copilot.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`
- Test: `packages/interfaces/sdd_cli/tests/commands/test_copilot.py`

**Step 1: Look at the existing pattern**

Read `packages/interfaces/sdd_cli/src/sdd_cli/commands/devin.py` in full — mirror its
Typer/`resolve_workspace_root` conventions. Unlike `devin.py`, this command has no
SDD-branded sibling mode to guard against combining (no `--skills` flag; the existing
SDD-branded Copilot path is the pre-existing wizard-integrated `AdapterGenerator`,
not a flag on this command) — so `--standalone` can be the command's only behavior,
or an explicit flag kept for symmetry with `devin build`'s flag naming. Pick one and
record the decision (**Decision D2**) in this task's commit message.

**Step 2: Write the failing test**

```python
# packages/interfaces/sdd_cli/tests/commands/test_copilot.py
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sdd_cli.commands.copilot import app

runner = CliRunner()


def test_copilot_build_writes_standalone_surface(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["build", "--standalone"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / "copilot-standalone" / ".github" / "copilot-instructions.md").exists()
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_copilot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdd_cli.commands.copilot'`

**Step 4: Implement the command**

```python
# packages/interfaces/sdd_cli/src/sdd_cli/commands/copilot.py
"""Copilot governance projection build commands (Soft/Standalone profile)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(
    help="Copilot governance projection generation", invoke_without_command=True
)
console = Console()


@app.callback(invoke_without_command=True)
def copilot_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_command_group("Copilot", ["build"])
        raise typer.Exit(0)


@app.command("build")
def build(
    dest: Path | None = typer.Option(
        None, "--dest", help="Output directory (default: <workspace>/dist/copilot-standalone)."
    ),
    standalone: bool = typer.Option(
        True,
        "--standalone/--no-standalone",
        help="Build the zero-SDD-mention Soft/Standalone governance projection.",
    ),
) -> None:
    """Build a Copilot governance surface using real GitHub Copilot conventions."""
    from sdd_adapters.copilot import CopilotStandaloneGenerator

    if not standalone:
        console.print(
            "[yellow]No non-standalone Copilot build exists on this command.[/yellow] "
            "For the SDD-branded per-skill Copilot integration, use the wizard's "
            "existing generation step (AdapterGenerator), not this command."
        )
        raise typer.Exit(1)

    ws_root = resolve_workspace_root()
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=ws_root, dest=dest)

    if not result.success:
        console.print(f"[red]Copilot standalone build failed:[/red] {'; '.join(result.errors)}")
        raise typer.Exit(1)

    console.print(
        f"[green]Copilot standalone config built[/green] ({len(result.files_written)} files)"
    )
```

**Step 5: Register the command**

In `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`, add to
`COMMAND_SPECS` (alphabetical position near `"codex"`/`"devin"`):

```python
    "copilot": CommandSpec(
        "sdd_cli.commands.copilot", "Copilot governance projection generation"
    ),
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_copilot.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/copilot.py packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py packages/interfaces/sdd_cli/tests/commands/test_copilot.py
git commit -m "feat(sdd_cli): add 'sdd copilot build --standalone' command"
```

---

### Task 6: Documentation

**Files:**
- Create: `docs/spec/guides/copilot-governance-plugin.md`

**Step 1: Write the doc**

Same structure as `docs/spec/guides/devin-governance-plugin.md`: what Soft/Standalone
means for Copilot specifically (embedded snapshot, reduced assurance, no network),
build command, bundle contents table, canonical-source disclaimer, and a **Known
limitations** section stating explicitly:
- No hook mechanism equivalent to Devin's `hooks.v1.json` (see evidence note).
- No declarative config/permissions file equivalent to Devin's `config.json` (see
  evidence note).
- `.github/copilot-instructions.md` vs. root `AGENTS.md` precedence is undocumented;
  this generator deliberately emits only `.github/copilot-instructions.md` (Decision
  D1, see this plan's Context section) to avoid duplicate/conflicting always-on
  content — re-evaluate if GitHub documents precedence in the future.

**Step 2: No test — documentation only.**

**Step 3: Commit**

```bash
git add docs/spec/guides/copilot-governance-plugin.md
git commit -m "docs: document the Copilot Soft/Standalone governance projection"
```

---

### Task 7: Full test run + governance validation

**Step 1: Run the full affected test suites**

Run: `uv run pytest packages/features/sdd_adapters packages/interfaces/sdd_cli/tests/commands/test_copilot.py -v`
Expected: all PASS, including pre-existing Devin/Claude/Codex/Antigravity tests
untouched (confirms no regression).

**Step 2: Run repo-wide governance validation**

Run: `sdd governance validate` (confirm the exact command in `Makefile` first, same
caveat as the Devin plan's equivalent task).

**Step 3: Report residual risks and unverified assumptions to the user**

Summarize in the final message (not a new file):
- No confirmed Copilot equivalent for Devin's hooks/config — disclosed in the
  generated output itself, not silently dropped.
- `.github/copilot-instructions.md` vs. `AGENTS.md` precedence is unresolved
  publicly; this generator picked `.github/copilot-instructions.md` only
  (Decision D1) — revisit if GitHub documents precedence later.
- `.github/chatmodes/*.chatmode.md` directory placement was corroborated by
  secondary sources only, not a pinned first-party page — re-verify before any
  future plan emits chat-mode files.
- The generated bundle has not been tested inside a real Copilot Chat/coding-agent
  session — only schema-level and structural verification was done. Recommend the
  user copy `dist/copilot-standalone/.github/*` into a real repository's `.github/`
  and confirm Copilot picks up the instructions before declaring this
  production-ready.

No commit for this task — verification only.

---

## Execution Handoff

Plan complete and saved to
`docs/plans/2026-08-18-copilot-governance-projection-soft-standalone.md`. This plan
was produced by a Strategist mission (`20260818-copilot-standalone-plugin`) as a
`documentation_target` deliverable — Tasks 1-7 above are `implementation_handoff`
work and were never executed by Strategist's Sniper. Two execution options once you
want to proceed:

1. **Subagent-Driven (this session)** — dispatch a fresh subagent per task, review
   the diff between tasks, fast iteration.
2. **Parallel Session (separate)** — open a new session with the `executing-plans`
   skill, batch execution with checkpoints.

Which approach?
