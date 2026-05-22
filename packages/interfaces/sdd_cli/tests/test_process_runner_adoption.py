"""Contract tests for process runner adoption in CLI command modules."""

from pathlib import Path


def test_tools_command_uses_safe_process_runner_not_subprocess() -> None:
    content = Path(
        "packages/interfaces/sdd_cli/src/sdd_cli/commands/tools.py"
    ).read_text(encoding="utf-8")
    assert "SafeProcessRunner" in content
    assert "subprocess.run(" not in content
