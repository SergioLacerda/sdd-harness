from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.utils import sdd_authority as authority_mod


def test_resolve_workspace_root_prefers_explicit_root(tmp_path: Path) -> None:
    assert authority_mod.resolve_workspace_root(tmp_path) == tmp_path.resolve()


def test_workspace_root_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(tmp_path))
    assert authority_mod._workspace_root_from_env() == tmp_path.resolve()


def test_workspace_root_from_env_returns_none_when_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)
    assert authority_mod._workspace_root_from_env() is None


def test_repo_root_prefers_workspace_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "sdd_core.utils.environment.find_workspace_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "sdd_core.utils.environment.detect_repo_root", lambda: tmp_path / "repo"
    )
    assert authority_mod._repo_root() == tmp_path


def test_resolve_workspace_root_uses_env_then_workspace_then_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_root = tmp_path / "env"
    ws_root = tmp_path / "ws"
    repo_root = tmp_path / "repo"
    monkeypatch.setattr(authority_mod, "_workspace_root_from_env", lambda: env_root)
    assert authority_mod.resolve_workspace_root() == env_root

    monkeypatch.setattr(authority_mod, "_workspace_root_from_env", lambda: None)
    monkeypatch.setattr(
        "sdd_core.utils.environment.find_workspace_root", lambda: ws_root
    )
    assert authority_mod.resolve_workspace_root() == ws_root.resolve()

    monkeypatch.setattr("sdd_core.utils.environment.find_workspace_root", lambda: None)
    monkeypatch.setattr(authority_mod, "_repo_root", lambda: repo_root)
    assert authority_mod.resolve_workspace_root() == repo_root.resolve()


def test_enforce_path_policy_allows_extraordinary_audit(tmp_path: Path) -> None:
    req = tmp_path / "outside"
    assert (
        authority_mod.enforce_path_policy(
            req, workspace_root=tmp_path, mode="extraordinary_audit"
        )
        == req.resolve()
    )


def test_enforce_path_policy_rejects_invalid_mode(tmp_path: Path) -> None:
    with pytest.raises(authority_mod.PathPolicyViolation) as excinfo:
        authority_mod.enforce_path_policy(
            tmp_path, workspace_root=tmp_path, mode="weird"
        )
    assert excinfo.value.as_dict()["code"] == authority_mod.POLICY_ERR_CODE


def test_enforce_path_policy_allows_generated_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    ws = repo / "generated" / "client-a"
    req = ws / ".sdd" / "compiled"
    req.mkdir(parents=True)
    monkeypatch.setattr(authority_mod, "_repo_root", lambda: repo)
    assert authority_mod.enforce_path_policy(req, workspace_root=ws) == req.resolve()


def test_enforce_path_policy_rejects_generated_workspace_read_outside_generated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    ws = repo / "generated" / "client-a"
    req = repo / "other"
    req.mkdir(parents=True)
    monkeypatch.setattr(authority_mod, "_repo_root", lambda: repo)
    with pytest.raises(authority_mod.PathPolicyViolation):
        authority_mod.enforce_path_policy(req, workspace_root=ws)


def test_enforce_path_policy_rejects_path_outside_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    ws = repo
    (ws / ".sdd").mkdir(parents=True)
    req = tmp_path / "outside"
    req.mkdir(parents=True)
    monkeypatch.setattr(authority_mod, "_repo_root", lambda: repo)
    with pytest.raises(authority_mod.PathPolicyViolation):
        authority_mod.enforce_path_policy(req, workspace_root=ws)


def test_relative_and_temp_helpers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "base"
    child = base / "child"
    child.mkdir(parents=True)
    assert authority_mod._is_relative_to(child, base) is True
    assert authority_mod._is_relative_to(base, child) is False
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    assert authority_mod._is_within_system_temp(child) is True


def test_is_within_system_temp_handles_resolution_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "tempfile.gettempdir", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert authority_mod._is_within_system_temp(tmp_path) is False


def test_authority_paths_use_resolved_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        authority_mod, "resolve_workspace_root", lambda root=None: tmp_path
    )
    assert authority_mod.compiled_active_dir() == tmp_path / ".sdd" / "compiled"
    assert authority_mod.source_semantic_dir() == tmp_path / ".sdd" / "source"
    assert authority_mod.profile_active_path() == tmp_path / ".sdd" / "profile"
