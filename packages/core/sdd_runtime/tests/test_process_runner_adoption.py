"""Contract tests for subprocess execution policy in runtime skills engine."""

from pathlib import Path


def test_skills_runtime_does_not_fallback_to_subprocess_run() -> None:
    executor_content = Path(
        "packages/core/sdd_runtime/src/sdd_runtime/_skill_executor.py"
    ).read_text(encoding="utf-8")
    assert "SafeProcessRunner" in executor_content
    assert "subprocess.run(" not in executor_content
