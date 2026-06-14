"""HttpProvider — HTTP-delegated intelligence provider, external service integration."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

from sdd_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)

from ._fallbacks import (
    _degraded_analysis_result as _degraded_analysis_result_impl,
)
from ._fallbacks import (
    _deserialize_response,
)
from ._fallbacks import (
    _fallback_budget_estimate as _fallback_budget_estimate_impl,
)
from ._fallbacks import (
    _fallback_compressed_context as _fallback_compressed_context_impl,
)

logger = logging.getLogger(__name__)


class HttpProvider:
    """HTTP-delegated intelligence provider.

    Delegates analysis and compression to an external HTTP service
    configured via the SDD_INTELLIGENCE_URL environment variable.

    All public methods are async. Use ``await provider.is_available()`` to
    check reachability before calling service methods.
    """

    _degraded_analysis_result = staticmethod(_degraded_analysis_result_impl)
    _fallback_compressed_context = staticmethod(_fallback_compressed_context_impl)
    _fallback_budget_estimate = staticmethod(_fallback_budget_estimate_impl)

    def __init__(self) -> None:
        """Initialize HTTP provider with service URL from environment."""
        self._url: str | None = os.environ.get("SDD_INTELLIGENCE_URL")
        if self._url:
            self._validate_url(self._url)
        self._available: bool | None = None  # Cache availability

    @staticmethod
    def _validate_url(url: str) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"SDD_INTELLIGENCE_URL has unsupported scheme '{parsed.scheme}'. "
                "Use http:// or https://."
            )
        if parsed.scheme == "http":
            logger.warning(
                "SDD_INTELLIGENCE_URL uses plaintext HTTP; consider HTTPS for non-local endpoints."
            )

    @property
    def name(self) -> str:
        """Provider name."""
        return "http"

    @property
    def available(self) -> bool:
        """Sync availability from cache. Always False until is_available() is awaited."""
        return self._available is True

    async def is_available(self) -> bool:
        """Check if external service is available (async).

        Performs a quick health check on first call, then caches result.
        """
        if self._available is not None:
            return self._available

        if not self._url:
            self._available = False
            return False

        try:
            import httpx

            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(self._url + "/health")
                self._available = resp.status_code == 200
        except Exception as exc:
            logger.debug("HTTP provider health check failed: %s", exc)
            self._available = False

        return self._available

    async def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Delegate task analysis to HTTP service."""
        if not await self.is_available():
            return self._degraded_analysis_result()

        try:
            return cast(
                AnalysisResult,
                await self._call_service(
                    "analyze",
                    {
                        "query": task.query,
                        "path_id": task.path_id,
                        "context_bytes_loaded": task.context_bytes_loaded,
                        "context_budget_bytes": task.context_budget_bytes,
                    },
                    AnalysisResult,
                ),
            )
        except Exception as exc:
            logger.debug("HTTP analyze failed: %s", exc)
            return self._degraded_analysis_result()

    async def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Delegate context compression to HTTP service."""
        if not await self.is_available():
            return self._fallback_compressed_context(context)

        try:
            return cast(
                CompressedContext,
                await self._call_service(
                    "compress",
                    {
                        "items": context.items,
                        "query": context.query,
                        "budget_bytes": context.budget_bytes,
                    },
                    CompressedContext,
                ),
            )
        except Exception as exc:
            logger.debug("HTTP compress failed: %s", exc)
            return self._fallback_compressed_context(context)

    async def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Delegate budget estimation to HTTP service."""
        if not await self.is_available():
            return self._fallback_budget_estimate()

        try:
            return cast(
                BudgetEstimate,
                await self._call_service(
                    "estimate",
                    {
                        "query": task.query,
                        "path_id": task.path_id,
                        "context_bytes_loaded": task.context_bytes_loaded,
                    },
                    BudgetEstimate,
                ),
            )
        except Exception as exc:
            logger.debug("HTTP estimate failed: %s", exc)
            return self._fallback_budget_estimate()

    async def _call_service(
        self, operation: str, payload: dict[str, Any], result_type: type[Any]
    ) -> Any:
        """Call remote service and deserialize response."""
        import httpx

        if not self._url:
            raise RuntimeError("SDD_INTELLIGENCE_URL not set")

        url = f"{self._url}/{operation}"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            response_data: dict[str, Any] = resp.json()

        return _deserialize_response(result_type, response_data, self.name)
