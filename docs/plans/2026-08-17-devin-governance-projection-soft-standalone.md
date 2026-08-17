# SDD Governance Projection for Devin (Soft/Standalone) Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Generate a self-contained, distributable Devin plugin bundle (Soft/Standalone profile) from the SDD Harness's canonical `.sdd/skills/` registry, with no network or external runtime dependency, reduced-assurance disclosure, and reproducible golden-tested output.

**Architecture:** Extend the existing `packages/features/sdd_adapters` package (which already generates per-skill adapter files for Claude/Codex/Copilot/Antigravity via `AdapterGenerator`) with a new, independent `DevinPluginGenerator`. Unlike the four existing targets — which each write one flat file per skill directly into the *consuming* project root (`.claude/commands/`, `.codex/skills/`, etc.) — Devin's governance surface is a **distributable plugin bundle** (`.devin-plugin/plugin.json` + `AGENTS.md` + `skills/{name}/SKILL.md` + `hooks.json` + `metadata/provenance.json`), matching the real Devin CLI plugin schema verified against `docs.devin.ai/cli/extensibility/*` on 2026-08-17. It is generated into `dist/devin-plugin/` (a build output, not scattered into the project like the other four targets) and reuses the existing `SkillLoader` to read `.sdd/skills/registry.json`. Hard/Connected mode, the SDD↔Devin handshake protocol, and the general per-skill single-file adapter convention are explicitly out of scope — see Non-Goals.

**Tech Stack:** Python 3.10+, Jinja2 (already a `sdd_adapters` dependency), pytest, existing `sdd_adapters.skill_loader.SkillLoader`.

---

## Context you need before starting

- Read `packages/features/sdd_adapters/src/sdd_adapters/adapter_generator.py`, `skill_loader.py`, and `template_renderer.py` first — this plan extends that package, it does not create a new one.
- The canonical skill data lives at `.sdd/skills/registry.json` + `.sdd/skills/{name}/skill.yaml` at the **repo root** of whatever project is being built (for this repo, that's `sdd-harness`'s own root `.sdd/` — this is dogfooding, not a special case; see `SkillLoader.load_skills`).
- Real Devin CLI schema (verified 2026-08-17 against `docs.devin.ai/cli/extensibility/plugins/overview`, `.../configuration`, `.../rules`, `.../hooks/overview`):
  - Plugin bundle layout: `.devin-plugin/plugin.json` (manifest), `AGENTS.md` (always-on rule), `rules/`, `skills/{name}/SKILL.md`, `hooks.json`, `.mcp.json`, `agents/`.
  - `plugin.json` fields: `name` (required), `version`, `description`, `author{name,email}`, `homepage`, `repository`, `license`, `keywords`, `skills` (path list, default `skills/`), `mcpServers`, `requiredPlugins`, `optionalPlugins`, `forbiddenPlugins`.
  - `SKILL.md` frontmatter: `name`, `description`, `allowed-tools` (list), `triggers` (user/model — Devin's exact sub-shape for this field is not fully documented publicly as of 2026-08-17; we render it as a flat list, which is a conservative, forward-compatible superset — flag this as a residual assumption in the docs task).
  - `hooks.json` (or project-level `.devin/hooks.v1.json`): top-level keys **are** event names directly (no wrapper key). Confirmed event: `SessionStart`. Hook entry: `{"hooks": [{"type": "command", "command": "...", "timeout": N}]}`. A `command`-type hook receives JSON on stdin and may return `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": "..."}}` on stdout to inject text into the agent's context.
- This plan deliberately does **not** touch `.sdd/commands/registry.json` — Devin's `SKILL.md` files are themselves the slash-invocable unit (the directory name under `skills/` is the invocation slug), so there is no separate "command routing" layer to project for Devin the way there is for Claude/Codex/Copilot.

## Non-Goals (do not implement)

- Hard/Connected mode, SDD Harness probe/handshake, or any new SDD external protocol — that requires a separate RFC per `docs/spec/guides/RFC_PROCESS.md` (see `analysis.md` R-004 / U-004 in `.analysis/refined/20260817-devin-governance-projection-refinement/`).
- Adding "devin" to `.sdd/commands/registry.json` targets.
- Wiring `DevinPluginGenerator` into the wizard's automatic `Phase456Generator` pipeline (the other four targets run automatically on every `sdd init`; Devin plugin generation stays an explicit, opt-in CLI action for this first slice).
- CI/release automation for publishing the plugin bundle.

---

### Task 1: Record Devin provider-surface verification evidence

**Files:**
- Create: `docs/spec/guides/devin-plugin-provider-surface-evidence.md`

**Step 1: Write the evidence note**

```markdown
# Devin Plugin Provider Surface — Verification Evidence

**Verified:** 2026-08-17
**Verified by:** live web search + fetch against `docs.devin.ai` (no pinned local fixture existed prior to this note).

## Sources

- https://docs.devin.ai/cli/extensibility/plugins/overview — plugin manifest schema, directory layout, install sources.
- https://docs.devin.ai/cli/extensibility/configuration — `.devin/config.json`, `.devin/config.local.json`, permissions syntax.
- https://docs.devin.ai/cli/extensibility/rules — `AGENTS.md` / rules discovery and precedence.
- https://docs.devin.ai/cli/extensibility/hooks/overview — `hooks.v1.json` / `hooks.json` schema, event names, stdin/stdout contract.
- https://docs.devin.ai/cli/extensibility/skills/creating-skills — `SKILL.md` frontmatter.

## Confirmed plugin bundle shape

\`\`\`text
my-plugin/
├── .devin-plugin/
│   └── plugin.json     # primary manifest (fallback: .claude-plugin/plugin.json, root plugin.json)
├── AGENTS.md            # always-on rule
├── rules/               # optional, triggered rules
├── agents/              # optional, custom subagents
├── hooks.json           # optional, lifecycle hooks
├── .mcp.json            # optional, MCP servers
└── skills/
    └── {name}/SKILL.md
\`\`\`

## Confirmed hooks.json schema

Top-level keys are event names directly. Confirmed events: `PreToolUse`, `PostToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`. Hook type is `command` (shell) or `prompt` (LLM). Command hooks receive `{hook_event_name, tool_name, tool_input, session_id, prompt_id}` on stdin and may write `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": "..."}}` to stdout. Exit code `2` blocks.

## Residual risk / unverified detail

- The exact sub-schema of `SKILL.md`'s `triggers` frontmatter field (user vs. model trigger split) is not fully documented publicly as of this date. This implementation renders `triggers` as a flat YAML list, a conservative superset that should remain forward-compatible. Re-verify before the next plugin schema version bump.
- Plugin update/version-resolution semantics (`devin plugins update`) are only partially documented; not relied upon by this implementation, which produces an unpublished local bundle only.
```

**Step 2: No test for this task (documentation-only). Move on.**

---

### Task 2: Scaffold the `devin` subpackage

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/devin/__init__.py`
- Modify: `packages/features/sdd_adapters/src/sdd_adapters/__init__.py`

**Step 1: Create the subpackage init**

```python
# packages/features/sdd_adapters/src/sdd_adapters/devin/__init__.py
"""Devin plugin bundle generation (Soft/Standalone profile)."""

from .plugin_generator import DevinPluginGenerator, DevinPluginResult

__all__ = ["DevinPluginGenerator", "DevinPluginResult"]
```

This will fail to import until Task 3 creates `plugin_generator.py` — that's expected and fine, nothing imports `sdd_adapters.devin` yet.

**Step 2: Export from the package root**

Edit `packages/features/sdd_adapters/src/sdd_adapters/__init__.py`:

```python
"""Multi-agent adapter generation from SDD skills and commands."""

from .adapter_generator import AdapterGenerator, AdapterResult
from .devin import DevinPluginGenerator, DevinPluginResult

__all__ = [
    "AdapterGenerator",
    "AdapterResult",
    "DevinPluginGenerator",
    "DevinPluginResult",
]
```

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/devin/__init__.py packages/features/sdd_adapters/src/sdd_adapters/__init__.py
git commit -m "feat(sdd_adapters): scaffold devin plugin subpackage"
```

---

### Task 3: Policy digest helper (TDD)

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py`
- Test: `packages/features/sdd_adapters/tests/test_devin_plugin_generator.py`

**Step 1: Write the failing test**

```python
# packages/features/sdd_adapters/tests/test_devin_plugin_generator.py
"""Tests for DevinPluginGenerator (Soft/Standalone Devin plugin bundle)."""

from __future__ import annotations

from sdd_adapters.devin.plugin_generator import _policy_digest


def test_policy_digest_is_deterministic_and_order_independent() -> None:
    skills_a = [{"name": "b", "risk_score": "low"}, {"name": "a", "risk_score": "high"}]
    skills_b = [{"name": "a", "risk_score": "high"}, {"name": "b", "risk_score": "low"}]

    digest_a = _policy_digest(skills_a)
    digest_b = _policy_digest(skills_b)

    assert digest_a != digest_b  # dict order inside json.dumps(sort_keys=True) is stable per-item, list order matters
    assert len(digest_a) == 64
```

Wait — reconsider: `json.dumps(list, sort_keys=True)` sorts *dict keys*, not list element order. `skills_a` and `skills_b` differ only in list order, so their digests **will** differ unless the caller sorts the list first. `DevinPluginGenerator.generate()` will sort by name before calling `_policy_digest`, so `_policy_digest` itself is order-sensitive by design (it's a pure function over whatever list it's given). Fix the test to assert that directly:

```python
def test_policy_digest_is_deterministic_for_same_input() -> None:
    skills = [{"name": "a", "risk_score": "high"}, {"name": "b", "risk_score": "low"}]

    assert _policy_digest(skills) == _policy_digest(skills)
    assert len(_policy_digest(skills)) == 64


def test_policy_digest_changes_with_content() -> None:
    skills_a = [{"name": "a", "risk_score": "low"}]
    skills_b = [{"name": "a", "risk_score": "high"}]

    assert _policy_digest(skills_a) != _policy_digest(skills_b)
```

Use this second version — replace the first draft in the file with these two tests.

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sdd_adapters.devin.plugin_generator'`

**Step 3: Write minimal implementation**

```python
# packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py
"""DevinPluginGenerator: builds a self-contained SDD governance plugin bundle for Devin (Soft/Standalone profile)."""

from __future__ import annotations

import hashlib
import json
import stat
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py packages/features/sdd_adapters/tests/test_devin_plugin_generator.py
git commit -m "feat(sdd_adapters): add deterministic policy digest for devin plugin"
```

---

### Task 4: Devin plugin templates

**Files:**
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/plugin.json.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/AGENTS.md.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/SKILL.md.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/hooks.json.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/provenance.json.tpl`
- Create: `packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/session-start-assurance.sh.tpl`

No test in this step — these are inert files until Task 5 renders them. Write them exactly as follows.

**`plugin.json.tpl`**

```jinja2
{
  "name": "sdd-governance-devin",
  "version": "{{ plugin_version }}",
  "description": "SDD Harness governance projection for Devin (Soft/Standalone profile).",
  "author": {
    "name": "SDD Harness",
    "email": "sergio.lacerda.vieira@gmail.com"
  },
  "homepage": "https://github.com/SergioLacerda/sdd-harness",
  "repository": "https://github.com/SergioLacerda/sdd-harness.git",
  "license": "MIT",
  "keywords": ["sdd", "governance", "devin-plugin", "soft-standalone"],
  "skills": ["skills"]
}
```

**`AGENTS.md.tpl`**

```jinja2
# SDD Governance Projection for Devin

Profile: **Soft/Standalone**
Provider: `devin`
Plugin version: `{{ plugin_version }}`
Policy digest (embedded snapshot): `sha256:{{ policy_digest }}`
Source revision: `{{ source_revision }}`
Built at: `{{ built_at }}`

## Assurance disclosure

This plugin ships an embedded snapshot of SDD Harness governance skills. It has **not** verified a live SDD Harness connection for this session.

- `policy_source: embedded_snapshot`
- `assurance: reduced`
- `external_dependencies: none`

Soft/Standalone assurance is never equivalent to a connected Hard/Connected SDD Harness session. Do not represent this plugin's governance as equivalent to a live-verified SDD policy.

## Precedence order

1. Provider or organization safety controls (Devin's own permissions/config).
2. Connected SDD hard policy (not active in this profile).
3. Project canonical policy (this project's own `.sdd/`, if present).
4. Embedded SDD snapshot (this plugin's `skills/`).
5. Provider local rules (`.devin/config.json`, project `AGENTS.md`, `rules/`).
6. User task instructions.

## Skill discovery

Skills embedded in this plugin are listed under `skills/`. Each skill file documents its own allowed CLI commands and risk score. Do not invent commands beyond what a skill file declares.

## Canonical source

This plugin is a generated projection. It is **not** the canonical governance source. Canonical SDD Harness policy lives in the `.sdd/` directory of the SDD Harness project this plugin was compiled from — see `metadata/provenance.json` for the exact source revision.
```

**`SKILL.md.tpl`**

```jinja2
---
name: {{ skill.name }}
description: {{ skill.description }}
allowed-tools:
{% for cmd in skill.allowed_tools | default([], true) %}
  - {{ cmd }}
{% endfor %}
triggers:
{% for t in skill.triggers | default([], true) %}
  - {{ t }}
{% endfor %}
---

# {{ skill.name }}

Source of truth: `.sdd/skills/{{ skill.name }}/skill.yaml` in the SDD Harness repository this plugin was generated from.

## When to use

{% for t in skill.when_to_use | default([], true) %}
- {{ t }}
{% endfor %}

## Profile disclosure

This plugin operates in **Soft/Standalone** profile: `policy_source=embedded_snapshot`, `assurance=reduced`, `external_dependencies=none`. The embedded snapshot may drift from the canonical SDD Harness source between plugin releases. Do not treat this file as authoritative if a connected SDD Harness promotes this session to Hard/Connected profile.

## Required steps

1. Confirm this skill (`{{ skill.name }}`) is listed under `skills/` of this plugin.
2. Follow the steps below using only the allowed CLI commands.
3. Report `policy_result` and any governance fields verbatim.

## Allowed CLI

{% for cmd in skill.allowed_tools | default([], true) %}
- `{{ cmd }}`
{% endfor %}

## Risk

`{{ skill.risk_score | default("controlled", true) }}`
```

**`hooks.json.tpl`**

```jinja2
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "./hooks/session-start-assurance.sh",
          "timeout": 5
        }
      ]
    }
  ]
}
```

**`provenance.json.tpl`**

```jinja2
{
  "plugin_version": "{{ plugin_version }}",
  "compiler_version": "{{ compiler_version }}",
  "governance_schema_version": "{{ schema_version }}",
  "source_revision": "{{ source_revision }}",
  "built_at": "{{ built_at }}",
  "embedded_policy_digest": "sha256:{{ policy_digest }}",
  "active_policy_digest": null,
  "profile": "soft",
  "provider": "devin",
  "compatibility_relationship": "not_applicable_soft_profile"
}
```

**`session-start-assurance.sh.tpl`**

```jinja2
#!/bin/sh
# Generated by sdd_adapters DevinPluginGenerator. Do not edit by hand.
cat <<'JSON'
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "SDD GOVERNANCE PROJECTION (devin) | profile=soft | policy_source=embedded_snapshot | assurance=reduced | external_dependencies=none | plugin_version={{ plugin_version }} | policy_digest={{ policy_digest }}"}}
JSON
```

**Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/templates/devin_plugin/
git commit -m "feat(sdd_adapters): add devin plugin bundle templates"
```

---

### Task 5: `DevinPluginGenerator.generate()` orchestration (TDD)

**Files:**
- Modify: `packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py`
- Modify: `packages/features/sdd_adapters/tests/test_devin_plugin_generator.py`

**Step 1: Write the failing test**

Append to the test file:

```python
import json
from pathlib import Path

import pytest
import yaml

from sdd_adapters.devin.plugin_generator import DevinPluginGenerator


def _write_skill(sdd_dir: Path, name: str, **overrides: object) -> None:
    skills_dir = sdd_dir / "skills" / name
    skills_dir.mkdir(parents=True)
    base = {
        "name": name,
        "description": f"{name} description.",
        "when_to_use": ["testing"],
        "allowed_tools": [f"sdd {name}"],
        "triggers": [name],
        "risk_score": "low",
    }
    base.update(overrides)
    (skills_dir / "skill.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
    registry_path = sdd_dir / "skills" / "registry.json"
    registry = {"skills": []}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["skills"].append({"name": name})
    registry_path.write_text(json.dumps(registry), encoding="utf-8")


def test_generate_writes_full_plugin_bundle(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")
    _write_skill(sdd_dir, "beta")

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path,
        source_revision="deadbeef",
        built_at="2026-08-17T00:00:00+00:00",
    )

    assert result.success is True
    bundle = tmp_path / "dist" / "devin-plugin"
    assert (bundle / ".devin-plugin" / "plugin.json").exists()
    assert (bundle / "AGENTS.md").exists()
    assert (bundle / "hooks.json").exists()
    assert (bundle / "metadata" / "provenance.json").exists()
    assert (bundle / "hooks" / "session-start-assurance.sh").exists()
    assert (bundle / "skills" / "alpha" / "SKILL.md").exists()
    assert (bundle / "skills" / "beta" / "SKILL.md").exists()

    plugin_json = json.loads((bundle / ".devin-plugin" / "plugin.json").read_text())
    assert plugin_json["name"] == "sdd-governance-devin"

    provenance = json.loads((bundle / "metadata" / "provenance.json").read_text())
    assert provenance["source_revision"] == "deadbeef"
    assert provenance["profile"] == "soft"
    assert provenance["embedded_policy_digest"] == f"sha256:{result.policy_digest}"

    hook_script = bundle / "hooks" / "session-start-assurance.sh"
    assert hook_script.stat().st_mode & 0o111  # executable bits set


def test_generate_is_deterministic_for_same_input(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")

    r1 = DevinPluginGenerator().generate(
        output_dir=tmp_path, source_revision="x", built_at="2026-08-17T00:00:00+00:00"
    )
    r2 = DevinPluginGenerator().generate(
        output_dir=tmp_path, source_revision="x", built_at="2026-08-17T00:00:00+00:00"
    )

    assert r1.policy_digest == r2.policy_digest


def test_generate_reports_error_when_no_skills(tmp_path: Path) -> None:
    result = DevinPluginGenerator().generate(output_dir=tmp_path)

    assert result.success is False
    assert result.errors
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py -v`
Expected: FAIL — `DevinPluginGenerator` has no `generate` method yet (AttributeError).

**Step 3: Implement `DevinPluginGenerator`**

Append to `plugin_generator.py`:

```python
class DevinPluginGenerator:
    """Generates a Soft/Standalone SDD governance plugin bundle for Devin."""

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
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
            result.errors.append(f"No skills found under {sdd_dir / 'skills' / 'registry.json'}")
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
            self._write(bundle_root / ".devin-plugin" / "plugin.json", "plugin.json", context, result)
            self._write(bundle_root / "AGENTS.md", "AGENTS.md", context, result)
            self._write(bundle_root / "hooks.json", "hooks.json", context, result)
            self._write(bundle_root / "metadata" / "provenance.json", "provenance.json", context, result)
            hook_script = self._write(
                bundle_root / "hooks" / "session-start-assurance.sh",
                "session-start-assurance.sh",
                context,
                result,
            )
            hook_script.chmod(hook_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

            for skill in skills_sorted:
                skill_dir = bundle_root / "skills" / skill.get("name", "unknown")
                skill_dir.mkdir(parents=True, exist_ok=True)
                self._write(skill_dir / "SKILL.md", "SKILL.md", {**context, "skill": skill}, result)

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
        self, path: Path, template_name: str, context: dict[str, Any], result: DevinPluginResult
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add packages/features/sdd_adapters/src/sdd_adapters/devin/plugin_generator.py packages/features/sdd_adapters/tests/test_devin_plugin_generator.py
git commit -m "feat(sdd_adapters): implement DevinPluginGenerator.generate()"
```

---

### Task 6: No-network / no-harness acceptance test

**Files:**
- Modify: `packages/features/sdd_adapters/tests/test_devin_plugin_generator.py`

**Step 1: Write the failing (well, currently-vacuous) test**

```python
def test_generate_never_touches_the_network(tmp_path: Path, monkeypatch) -> None:
    import socket

    sdd_dir = tmp_path / ".sdd"
    _write_skill(sdd_dir, "alpha")

    def _blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted during Soft/Standalone generation")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = DevinPluginGenerator().generate(
        output_dir=tmp_path, built_at="2026-08-17T00:00:00+00:00"
    )

    assert result.success is True
```

**Step 2: Run it**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py::test_generate_never_touches_the_network -v`
Expected: PASS immediately — `generate()` never opens a socket. This test exists to catch *future* regressions (e.g. someone adding a version-check HTTP call), not to drive new production code. That's fine — not every test in a TDD flow needs a red phase when it's asserting an existing negative property.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/tests/test_devin_plugin_generator.py
git commit -m "test(sdd_adapters): assert devin plugin generation never touches the network"
```

---

### Task 7: End-to-end test against this repo's real `.sdd/skills/`

**Files:**
- Modify: `packages/features/sdd_adapters/tests/test_devin_plugin_generator.py`

**Step 1: Write the test**

This proves the generator works against the actual 10-skill registry in this repo, without golden-matching exact content (which would churn every time a skill description changes).

```python
def test_generate_against_real_repo_registry(tmp_path: Path) -> None:
    # Repo root: tests/ -> sdd_adapters/ -> features/ -> packages/ -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / ".sdd" / "skills" / "registry.json").exists(), (
        "sanity check: adjust the parents[] index above if the package moves"
    )

    result = DevinPluginGenerator().generate(
        output_dir=repo_root,
        dest=tmp_path / "devin-plugin",
        built_at="2026-08-17T00:00:00+00:00",
    )

    assert result.success is True, result.errors
    skill_dirs = sorted(p.name for p in (tmp_path / "devin-plugin" / "skills").iterdir())
    assert "sdd-ask" in skill_dirs
    assert len(skill_dirs) >= 10
    assert len(result.policy_digest) == 64
```

**Step 2: Run it**

Run: `uv run pytest packages/features/sdd_adapters/tests/test_devin_plugin_generator.py::test_generate_against_real_repo_registry -v`
Expected: PASS. If the `parents[4]` index is wrong you'll get a clear assertion failure on the sanity check line, not a confusing path error — adjust the index and rerun.

**Step 3: Commit**

```bash
git add packages/features/sdd_adapters/tests/test_devin_plugin_generator.py
git commit -m "test(sdd_adapters): verify devin plugin generation against real skill registry"
```

---

### Task 8: CLI command — `sdd adapters devin build`

**Files:**
- Create: `packages/interfaces/sdd_cli/src/sdd_cli/commands/devin.py`
- Modify: `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`
- Test: `packages/interfaces/sdd_cli/tests/commands/test_devin.py` (create the `commands/` subdir if it doesn't already exist — check first with `ls packages/interfaces/sdd_cli/tests/`)

**Step 1: Look at the existing pattern**

Read `packages/interfaces/sdd_cli/src/sdd_cli/commands/plugin.py` in full and `packages/interfaces/sdd_cli/src/sdd_cli/utils/sdd_authority.py` (for `resolve_workspace_root`) before writing this task — mirror their Typer/`resolve_workspace_root` conventions exactly.

**Step 2: Write the failing test**

```python
# packages/interfaces/sdd_cli/tests/commands/test_devin.py
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sdd_cli.commands.devin import app

runner = CliRunner()


def test_devin_build_writes_plugin_bundle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    sdd_dir = tmp_path / ".sdd" / "skills"
    skill_dir = sdd_dir / "alpha"
    skill_dir.mkdir(parents=True)
    (sdd_dir / "registry.json").write_text(json.dumps({"skills": [{"name": "alpha"}]}))
    (skill_dir / "skill.yaml").write_text("name: alpha\ndescription: test skill\n")

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / "devin-plugin" / "AGENTS.md").exists()
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_devin.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdd_cli.commands.devin'`

**Step 4: Implement the command**

```python
# packages/interfaces/sdd_cli/src/sdd_cli/commands/devin.py
"""Devin plugin build commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sdd_cli.services.command_group_output import show_command_group
from sdd_cli.utils.sdd_authority import resolve_workspace_root

app = typer.Typer(help="Devin governance plugin generation", invoke_without_command=True)
console = Console()


@app.callback(invoke_without_command=True)
def devin_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_command_group("Devin", ["build"])
        raise typer.Exit(0)


@app.command("build")
def build(
    dest: Path = typer.Option(
        None, "--dest", help="Bundle output directory (default: <workspace>/dist/devin-plugin)."
    ),
) -> None:
    """Build the Soft/Standalone Devin governance plugin bundle from .sdd/skills/."""
    from sdd_adapters.devin import DevinPluginGenerator

    ws_root = resolve_workspace_root()
    result = DevinPluginGenerator().generate(output_dir=ws_root, dest=dest)

    if not result.success:
        console.print(f"[red]Devin plugin build failed:[/red] {'; '.join(result.errors)}")
        raise typer.Exit(1)

    console.print(f"[green]Devin plugin built[/green] ({len(result.files_written)} files, "
                  f"policy_digest=sha256:{result.policy_digest[:12]}...)")
```

Note: check `resolve_workspace_root`'s exact signature in `sdd_authority.py` before using it — it may require a `Path` argument or a Typer context; adjust the call to match, this snippet assumes a no-arg call resolving from `Path.cwd()`.

**Step 5: Register the command**

In `packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py`, add to `COMMAND_SPECS` (alphabetical position near `"doctor"`/`"docs"` or wherever fits the existing ordering):

```python
    "devin": CommandSpec(
        "sdd_cli.commands.devin", "Devin governance plugin generation"
    ),
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest packages/interfaces/sdd_cli/tests/commands/test_devin.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add packages/interfaces/sdd_cli/src/sdd_cli/commands/devin.py packages/interfaces/sdd_cli/src/sdd_cli/_command_specs.py packages/interfaces/sdd_cli/tests/commands/test_devin.py
git commit -m "feat(sdd_cli): add 'sdd devin build' command for the Soft/Standalone plugin bundle"
```

---

### Task 9: Documentation

**Files:**
- Create: `docs/spec/guides/devin-governance-plugin.md`

**Step 1: Write the doc**

```markdown
# SDD Governance Projection for Devin

Generates a self-contained, distributable Devin plugin bundle from this repository's
`.sdd/skills/` registry, in **Soft/Standalone** profile.

## What Soft/Standalone means

- Works without SDD Harness, without network, without any runtime Python/Go/Node dependency.
- Reports `policy_source=embedded_snapshot` and `assurance=reduced` — both in `AGENTS.md`
  (always loaded) and via a `SessionStart` hook that injects the same disclosure into the
  agent's context at session start.
- Is never represented as equivalent to a connected, Hard/Connected SDD Harness session.

Hard/Connected mode (a live SDD Harness probe/handshake) is **not implemented**. It requires
a separate RFC — see `docs/spec/guides/RFC_PROCESS.md` — because it would introduce a new SDD
external integration protocol.

## Build

\`\`\`bash
sdd devin build
# or, from Python:
# DevinPluginGenerator().generate(output_dir=<repo_root>)
\`\`\`

Output: `dist/devin-plugin/` (not committed to source control — treat like any other build
artifact and add it to `.gitignore` if you commit generated output elsewhere in this project).

## Install into Devin

\`\`\`bash
devin plugins install ./dist/devin-plugin
\`\`\`

## Bundle contents

| Path | Role |
|---|---|
| `.devin-plugin/plugin.json` | Plugin manifest (name, version, license, skill paths) |
| `AGENTS.md` | Always-on assurance/precedence disclosure |
| `skills/{name}/SKILL.md` | One per canonical SDD skill in `.sdd/skills/registry.json` |
| `hooks.json` + `hooks/session-start-assurance.sh` | Injects the Soft/Standalone disclosure into every session |
| `metadata/provenance.json` | Plugin version, compiler version, source revision, embedded policy digest, profile |

## Canonical source

This plugin is a generated projection, never a policy source. Canonical SDD governance stays
in this repository's `.sdd/`. See `metadata/provenance.json` in a built bundle for the exact
source revision it was generated from.

## Known limitations

- `SKILL.md`'s `triggers` frontmatter sub-schema is rendered as a flat list — Devin's exact
  user/model trigger split was not fully documented publicly as of 2026-08-17. Re-verify
  against `docs.devin.ai/cli/extensibility/skills/creating-skills` before the next schema bump.
  See `docs/spec/guides/devin-plugin-provider-surface-evidence.md`.
- Hard/Connected mode is out of scope (see above).
```

**Step 2: No test — documentation only.**

**Step 3: Commit**

```bash
git add docs/spec/guides/devin-governance-plugin.md
git commit -m "docs: document the Devin Soft/Standalone governance plugin"
```

---

### Task 10: Full package test run + governance validation

**Step 1: Run the full `sdd_adapters` and `sdd_cli` test suites**

Run: `uv run pytest packages/features/sdd_adapters packages/interfaces/sdd_cli/tests/commands/test_devin.py -v`
Expected: all PASS, including the pre-existing Claude/Codex/Copilot/Antigravity tests (untouched — this confirms no regression).

**Step 2: Run repo-wide governance validation**

Run: `sdd governance validate` (or whatever the project's standard pre-commit governance check is — confirm the exact command in `Makefile` under a `governance` or `validate` target before running).

**Step 3: Report residual risks and unverified assumptions to the user**

Summarize in your final message to the user (not a new file):
- `SKILL.md` `triggers` sub-schema is a best-effort flat-list mapping (see Task 9's Known Limitations).
- Hard/Connected is fully out of scope; U-004/R-004 from the original refined demand remain open and would need a separate RFC.
- The plugin bundle has not been installed into a real Devin CLI session — only schema-level and structural verification was done. Recommend the user (or a follow-up task) run `devin plugins install ./dist/devin-plugin` against an actual Devin CLI installation before declaring this production-ready.

No commit for this task — it's verification only.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-08-17-devin-governance-projection-soft-standalone.md`. Two execution options:

1. **Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review the diff between tasks, fast iteration.
2. **Parallel Session (separate)** — open a new session with the `executing-plans` skill, batch execution with checkpoints.

Which approach?
