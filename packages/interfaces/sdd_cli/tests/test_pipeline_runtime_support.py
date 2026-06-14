"""Tests for `check_budget_zone_and_compress` budget-zone heuristics."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.commands._ask_backend._pipeline_runtime_support import (
    check_budget_zone_and_compress,
)

_LOGGER = logging.getLogger("test.pipeline_runtime_support")


def test_unknown_path_id_returns_input_bytes_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_PATH_ID", raising=False)

    result_bytes, compression_ratio = check_budget_zone_and_compress(
        "query",
        12345,
        5,
        prefer_full_summary_fn=lambda: False,
        logger=_LOGGER,
    )

    assert result_bytes == 12345
    assert compression_ratio is None


def test_green_zone_below_yellow_threshold_skips_compression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_PATH_ID", "A")

    # 10000 bytes / 40960 (PATH A budget) ≈ 24% < 70% YELLOW threshold.
    result_bytes, compression_ratio = check_budget_zone_and_compress(
        "query",
        10000,
        5,
        prefer_full_summary_fn=lambda: False,
        logger=_LOGGER,
    )

    assert result_bytes == 10000
    assert compression_ratio is None


def test_yellow_zone_applies_compression_from_context_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_PATH_ID", "A")

    # 32768 bytes / 40960 (PATH A budget) == 80%, inside [70, 100) YELLOW zone.
    fake_result = MagicMock(compression_ratio=0.5, bytes_loaded=1000)
    fake_loader = MagicMock()
    fake_loader.load_result.return_value = fake_result

    with patch("sdd_runtime.context.ContextLoader", return_value=fake_loader):
        result_bytes, compression_ratio = check_budget_zone_and_compress(
            "query",
            32768,
            5,
            prefer_full_summary_fn=lambda: False,
            logger=_LOGGER,
        )

    assert result_bytes == 1000
    assert compression_ratio == 0.5
    fake_loader.load_result.assert_called_once()


def test_yellow_zone_context_loader_failure_keeps_original_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_PATH_ID", "A")

    with patch(
        "sdd_runtime.context.ContextLoader",
        side_effect=RuntimeError("boom"),
    ):
        result_bytes, compression_ratio = check_budget_zone_and_compress(
            "query",
            32768,
            5,
            prefer_full_summary_fn=lambda: False,
            logger=_LOGGER,
        )

    assert result_bytes == 32768
    assert compression_ratio is None


def test_budget_lookup_failure_falls_back_to_original_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sdd_runtime.telemetry as telemetry

    monkeypatch.setenv("SDD_PATH_ID", "A")
    monkeypatch.setitem(telemetry._PATH_BUDGET_BYTES, "A", 0)

    result_bytes, compression_ratio = check_budget_zone_and_compress(
        "query",
        32768,
        5,
        prefer_full_summary_fn=lambda: False,
        logger=_LOGGER,
    )

    assert result_bytes == 32768
    assert compression_ratio is None
