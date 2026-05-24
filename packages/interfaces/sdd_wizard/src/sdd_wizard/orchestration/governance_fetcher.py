"""Bootstrap fetcher for compiled governance defaults from GitHub Releases."""

from __future__ import annotations

import contextlib
import json
import time
import urllib.request
import uuid
from pathlib import Path

import structlog

_OWNER = "SergioLacerda"
_REPO = "sdd-harness"
_FILES = ("governance-core.json", "governance-client.json")
_REQUIRED_FIELDS = {"version", "items"}

logger = structlog.get_logger(__name__)


def get_cli_version() -> str:
    """Return the installed sdd-cli version, or 'unknown' if not resolvable."""
    try:
        from importlib.metadata import version

        return version("sdd-cli")
    except Exception:
        return "unknown"


def _download_file(url: str, dest: Path) -> bool:
    if not url.startswith("https://"):
        return False
    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310  # nosec B310
        return True
    except Exception:
        return False


def _validate_governance_file(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and _REQUIRED_FIELDS.issubset(data.keys())
    except Exception:
        return False


def fetch_compiled_defaults(version: str, dest: Path) -> tuple[bool, str]:
    """Download governance-core.json and governance-client.json into dest.

    Returns (success, source) where source is one of:
      'versioned_release', 'latest_release', or 'failed'.

    Integrity contract: if either file fails validation the function cleans
    up any partially-downloaded files and returns (False, 'failed').
    """
    base = f"https://github.com/{_OWNER}/{_REPO}/releases/download"
    latest_base = f"https://github.com/{_OWNER}/{_REPO}/releases/latest/download"

    dest.mkdir(parents=True, exist_ok=True)

    trace_id = str(uuid.uuid4())
    start = time.monotonic()
    source = "versioned_release"
    downloaded: list[Path] = []

    logger.info(
        "wizard.bootstrap.compiled_defaults.fetch.started",
        trace_id=trace_id,
        installed_version=version,
    )

    for filename in _FILES:
        versioned_url = f"{base}/v{version}/{filename}"
        fallback_url = f"{latest_base}/{filename}"
        dest_path = dest / filename

        if _download_file(versioned_url, dest_path):
            pass
        elif _download_file(fallback_url, dest_path):
            source = "latest_release"
        else:
            _cleanup(downloaded)
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "wizard.bootstrap.compiled_defaults.fetch.failed",
                trace_id=trace_id,
                installed_version=version,
                source="failed",
                latency_ms=latency_ms,
            )
            return False, "failed"

        if not _validate_governance_file(dest_path):
            dest_path.unlink(missing_ok=True)
            _cleanup(downloaded)
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "wizard.bootstrap.compiled_defaults.fetch.failed",
                trace_id=trace_id,
                installed_version=version,
                source=source,
                latency_ms=latency_ms,
                reason="invalid_json_or_shape",
            )
            return False, "failed"

        downloaded.append(dest_path)

    latency_ms = int((time.monotonic() - start) * 1000)

    if source == "latest_release":
        logger.warning(
            "wizard.bootstrap.compiled_defaults.fetch.fallback_latest",
            trace_id=trace_id,
            installed_version=version,
            source=source,
            latency_ms=latency_ms,
        )
    else:
        logger.info(
            "wizard.bootstrap.compiled_defaults.fetch.succeeded",
            trace_id=trace_id,
            installed_version=version,
            source=source,
            latency_ms=latency_ms,
        )

    return True, source


def _cleanup(paths: list[Path]) -> None:
    for p in paths:
        with contextlib.suppress(OSError):
            p.unlink()
