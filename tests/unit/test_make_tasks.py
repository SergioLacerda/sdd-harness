from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_tasks_module():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tools.maintenance import make_tasks

    return make_tasks


pytestmark = pytest.mark.unit


def test_semver_key_sorts_numeric_prefixes() -> None:
    make_tasks = _make_tasks_module()
    tags = ["v1.10.0", "v1.2.9", "v2.0.0", "v1.2.10"]
    assert sorted(tags, key=make_tasks._semver_key) == [
        "v1.2.9",
        "v1.2.10",
        "v1.10.0",
        "v2.0.0",
    ]


def test_clean_removes_build_and_caches(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    (tmp_path / "build").mkdir()
    pycache = tmp_path / "a" / "__pycache__"
    pycache.mkdir(parents=True)
    (tmp_path / "a" / "b.pyc").write_text("x", encoding="utf-8")

    with patch.object(make_tasks, "REPO_ROOT", tmp_path):
        assert make_tasks.run_clean() == 0

    assert not (tmp_path / "build").exists()
    assert not pycache.exists()
    assert not (tmp_path / "a" / "b.pyc").exists()


def test_release_dry_run_runs_tests_wrapper() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_read_project_version", return_value="1.2.3"),
        patch.object(make_tasks, "run_test", return_value=0) as run_test,
        patch("sdd_core.utils.process.SafeProcessRunner.run") as runner_run,
    ):
        runner_run.return_value.returncode = 0
        runner_run.return_value.stdout = "v1.0.0\nv1.1.0\n"
        runner_run.return_value.stderr = ""
        assert make_tasks.run_release_dry_run() == 0
        run_test.assert_called_once_with(["--no-coverage"])
