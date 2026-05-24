from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def test_mandate_index_registers_m010() -> None:
    content = _read("docs/spec/canonical/core/mandates/INDEX.md")
    assert "M010" in content
    assert "M010_DELIVERY_HYGIENE.md" in content


def test_m010_declares_hard_enforcement_and_blocked_failure() -> None:
    content = _read("docs/spec/canonical/core/mandates/M010_DELIVERY_HYGIENE.md")
    assert "**Enforcement:** HARD" in content
    assert "delivery is `BLOCKED`" in content
    assert "ruff check --fix ." in content


def test_p004_includes_remediation_first_pipeline() -> None:
    content = _read(
        "docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md"
    )
    assert "Remediation-First Pipeline (Strict)" in content
    assert "ruff check --fix ." in content
    assert "re-run after auto-fix" in content


def test_entrypoint_and_dod_include_strict_hygiene_steps() -> None:
    entrypoint = _read("docs/runtime/protocols/AGENT_ENTRYPOINT.md")
    dod = _read("docs/spec/canonical/specifications/definition_of_done.md")
    assert "ruff check --fix ." in entrypoint
    assert "Revalidação pós auto-fix" in entrypoint
    assert "Strict Auto-Fix Hygiene (Mandatory)" in dod
    assert "delivery is BLOCKED" in dod
