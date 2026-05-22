from __future__ import annotations

from pathlib import Path

import pytest

from sdd_compiler import integrate as integrate_module

pytestmark = pytest.mark.unit


def _fake_paths(root: Path) -> dict[str, Path]:
    generated = root / "generated"
    return {
        "root": root,
        "generated": generated,
        "master": generated / "master",
        "master_compiled": generated / "master" / "compiled",
        "master_build": generated / "master" / "build",
        "master_context": generated / "master" / "context",
        "client": generated / "client",
        "client_compiled": generated / "client" / "compiled",
        "client_build": generated / "client" / "build",
        "client_context": generated / "client" / "context",
        "docs_meta": generated / "client" / "build" / "docs-meta",
        "source_spec": generated / "client" / "build" / "docs-meta",
        "packages": root / "packages",
        "core_pkg": root / "packages" / "core" / "sdd_core",
        "tools": root / "tools",
        "scripts": root / "scripts",
        "compiler_output": generated / "master" / "compiled",
        "wizard_runtime": generated / "client" / "compiled",
    }


def test_run_detailed_reports_phase_and_uses_emitter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        integrate_module, "get_sdd_paths", lambda: _fake_paths(tmp_path)
    )
    messages: list[str] = []
    integrator = integrate_module.SDDIntegrator(emitter=messages.append)

    result = integrator.run_detailed()

    assert result["ok"] is False
    assert result["phase"] == "validate_paths"
    assert result["verification"] is None
    assert any("Missing required files" in message for message in messages)
