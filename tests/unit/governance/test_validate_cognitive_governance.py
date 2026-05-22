from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path("tools/governance/validate_cognitive_governance.py")
    spec = importlib.util.spec_from_file_location("validate_cognitive_governance", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "docs/runtime/protocols/AGENT_ENTRYPOINT.md", "# entry\n")
    _write(
        tmp_path / "docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md", "# protocol\n"
    )
    _write(
        tmp_path / "docs/runtime/AGENT_ENTRYPOINT.md",
        "compatibilidade\ndocs/runtime/protocols/AGENT_ENTRYPOINT.md\n",
    )
    _write(
        tmp_path / "docs/runtime/AGENT_RUNTIME_PROTOCOL.md",
        "compatibilidade\ndocs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md\n",
    )
    _write(
        tmp_path / "tools/governance/cognitive_governance_allowlist.json",
        '{"allowlist": []}\n',
    )

    base_contract = """# X\n## Objective\nA\n## MUST\n- x\n## MUST NOT\n- y\n## INVALID\n- z\n## Escalation/Recovery\n- r\n"""

    for name in (
        "CONVERGENCE_GOVERNANCE.md",
        "TEST_GOVERNANCE.md",
        "RETRIEVAL_BEFORE_REASONING.md",
        "BOUNDED_REASONING.md",
    ):
        _write(tmp_path / "docs/spec/canonical/core/cognition" / name, base_contract)

    _write(
        tmp_path / "docs/runtime/paths/PATH_A_BUGFIX.md",
        "# PATH A\n## Cognitive Objective\nScope\n",
    )
    return tmp_path


def test_validator_passes_on_valid_layout(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _make_repo(tmp_path)
    report = mod.validate(repo)
    assert report["ok"] is True


def test_validator_fails_when_must_not_missing(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _make_repo(tmp_path)
    bad = repo / "docs/spec/canonical/core/cognition/TEST_GOVERNANCE.md"
    bad.write_text("# X\n## Objective\nA\n", encoding="utf-8")
    report = mod.validate(repo)
    assert report["ok"] is False
    assert any(v["code"] == "missing-section" for v in report["violations"])


def test_validator_fails_on_broken_link(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _make_repo(tmp_path)
    target = repo / "docs/spec/canonical/core/cognition/CONVERGENCE_GOVERNANCE.md"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n[bad](./missing.md)\n",
        encoding="utf-8",
    )
    report = mod.validate(repo)
    assert report["ok"] is False
    assert any(v["code"] == "broken-link" for v in report["violations"])


def test_validator_fails_when_path_missing_objective(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _make_repo(tmp_path)
    path_doc = repo / "docs/runtime/paths/PATH_A_BUGFIX.md"
    path_doc.write_text("# PATH A\n", encoding="utf-8")
    report = mod.validate(repo)
    assert report["ok"] is False
    assert any(v["code"] == "missing-cognitive-objective" for v in report["violations"])
