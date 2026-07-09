"""Tests for the sdd-compile binary resolver."""

from __future__ import annotations

import pytest

from sdd_core.utils import compiler_runner
from sdd_core.utils.compiler_runner import CompilerRunnerError


def test_fetch_release_binary_error_names_standalone_remediation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing release assets should explain the standalone install fix path."""

    monkeypatch.setattr(compiler_runner, "_download", lambda _url: None)

    with pytest.raises(CompilerRunnerError) as exc_info:
        compiler_runner._fetch_release_binary("1.0.0", "sdd-compile-linux-amd64")

    message = str(exc_info.value)
    assert "No sdd-compile release binary found for version 1.0.0" in message
    assert "asset sdd-compile-linux-amd64" in message
    assert "tried tags v1.0.0 and V1.0.0" in message
    assert "Standalone installs need a release asset" in message
    assert "SDD_COMPILE_BIN" in message
