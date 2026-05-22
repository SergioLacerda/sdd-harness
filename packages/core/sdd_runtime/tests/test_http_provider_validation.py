"""Tests for HttpProvider URL validation and async availability."""

from __future__ import annotations

import pytest
from sdd_runtime.providers.http_provider import HttpProvider


def test_file_scheme_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """file:// scheme is rejected at construction time."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "file:///etc/passwd")
    with pytest.raises(ValueError, match="unsupported scheme 'file'"):
        HttpProvider()


def test_ftp_scheme_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """ftp:// scheme is rejected at construction time."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "ftp://example.com/data")
    with pytest.raises(ValueError, match="unsupported scheme 'ftp'"):
        HttpProvider()


def test_http_localhost_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """http:// URL is accepted but emits a warning."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "http://localhost:8080")
    import logging

    with caplog.at_level(logging.WARNING, logger="sdd_runtime.providers.http_provider"):
        provider = HttpProvider()
    assert provider._url == "http://localhost:8080"
    assert any("plaintext HTTP" in r.message for r in caplog.records)


def test_https_accepted_no_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """https:// URL is accepted without any warning."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://service.internal")
    import logging

    with caplog.at_level(logging.WARNING, logger="sdd_runtime.providers.http_provider"):
        provider = HttpProvider()
    assert provider._url == "https://service.internal"
    assert not any("plaintext" in r.message for r in caplog.records)


def test_unset_url_skips_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SDD_INTELLIGENCE_URL is unset, no validation runs."""
    monkeypatch.delenv("SDD_INTELLIGENCE_URL", raising=False)
    provider = HttpProvider()
    assert provider._url is None


@pytest.mark.asyncio
async def test_is_available_false_when_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_available() returns False when no URL configured."""
    monkeypatch.delenv("SDD_INTELLIGENCE_URL", raising=False)
    provider = HttpProvider()
    assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_available() returns False when health check fails."""
    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://nonexistent.internal")
    provider = HttpProvider()
    result = await provider.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_analyze_task_returns_degraded_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """analyze_task returns degraded result when service unreachable."""
    from unittest.mock import AsyncMock, patch

    from sdd_runtime.intelligence import TaskContext

    monkeypatch.setenv("SDD_INTELLIGENCE_URL", "https://nonexistent.internal")
    provider = HttpProvider()

    with patch.object(provider, "is_available", new=AsyncMock(return_value=False)):
        task = TaskContext(
            query="test",
            path_id="A",
            context_bytes_loaded=0,
            context_budget_bytes=100_000,
        )
        result = await provider.analyze_task(task)

    assert result.provider == "http"
    assert result.task_class == "unknown"
