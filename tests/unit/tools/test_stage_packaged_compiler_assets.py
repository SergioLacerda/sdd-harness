from __future__ import annotations

from pathlib import Path

import pytest

from tools.release import stage_packaged_compiler_assets as stage
from tools.release.validate_release_assets import REQUIRED_COMPILER_ASSETS


def _write_dist(root: Path) -> Path:
    dist = root / "dist"
    dist.mkdir()
    for asset in REQUIRED_COMPILER_ASSETS:
        (dist / asset).write_bytes(f"payload:{asset}".encode())
    return dist


def test_stage_packaged_compiler_assets_copies_required_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = _write_dist(tmp_path)
    target = tmp_path / "package" / "_native"
    monkeypatch.setattr(stage, "PACKAGE_NATIVE_DIR", target)

    stage.stage_packaged_compiler_assets(dist)

    assert sorted(path.name for path in target.iterdir()) == sorted(
        REQUIRED_COMPILER_ASSETS
    )
    assert (target / "sdd-compile-linux-amd64").read_bytes() == (
        dist / "sdd-compile-linux-amd64"
    ).read_bytes()


def test_stage_packaged_compiler_assets_fails_when_asset_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = _write_dist(tmp_path)
    (dist / "sdd-compile-linux-amd64").unlink()
    monkeypatch.setattr(stage, "PACKAGE_NATIVE_DIR", tmp_path / "_native")

    with pytest.raises(SystemExit, match="sdd-compile-linux-amd64"):
        stage.stage_packaged_compiler_assets(dist)
