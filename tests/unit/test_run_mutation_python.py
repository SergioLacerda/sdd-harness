from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tools.testing import run_mutation_python

pytestmark = pytest.mark.unit


def test_create_workspace_link_uses_symlink_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, bool]] = []

    def fake_symlink_to(self: Path, target: Path, target_is_directory: bool) -> None:
        calls.append((target, target_is_directory))

    monkeypatch.setattr(Path, "symlink_to", fake_symlink_to)

    target = tmp_path / "target"
    link = tmp_path / "link"
    created = run_mutation_python._create_workspace_link(link, target)

    assert created.kind == "symlink"
    assert created.path == link
    assert calls == [(target, True)]


def test_create_workspace_link_falls_back_to_windows_junction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def raise_privilege_error(
        self: Path, target: Path, target_is_directory: bool
    ) -> None:
        exc = OSError("missing privilege")
        exc.winerror = 1314  # type: ignore[attr-defined]
        raise exc

    run = Mock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(run_mutation_python.sys, "platform", "win32")
    monkeypatch.setattr(Path, "symlink_to", raise_privilege_error)
    monkeypatch.setattr(run_mutation_python.subprocess, "run", run)

    target = tmp_path / "target"
    link = tmp_path / "link"
    created = run_mutation_python._create_workspace_link(link, target)

    assert created.kind == "junction"
    run.assert_called_once_with(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        cwd=link.parent,
        capture_output=True,
        text=True,
    )


def test_create_workspace_link_reraises_unexpected_oserror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def raise_unexpected(self: Path, target: Path, target_is_directory: bool) -> None:
        raise OSError("boom")

    monkeypatch.setattr(Path, "symlink_to", raise_unexpected)

    with pytest.raises(OSError, match="boom"):
        run_mutation_python._create_workspace_link(tmp_path / "link", tmp_path)
