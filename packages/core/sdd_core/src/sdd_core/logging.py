"""Central structlog configuration for all sdd_* packages.

Call ``configure_logging()`` once at process startup (CLI entrypoint or
``__main__``).  All packages obtain a logger via::

    import structlog
    logger = structlog.get_logger(__name__)

No package configures structlog directly — they rely on this module.

Output format
-------------
- JSON when ``SDD_ENV=production`` or stdout is not a TTY.
- ConsoleRenderer (human-readable, coloured) otherwise.
"""

from __future__ import annotations

import logging
import os
import sys

import structlog

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog for the current process.

    Idempotent — safe to call multiple times; only the first call takes effect.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    is_production = os.environ.get("SDD_ENV", "").lower() == "production"
    is_tty = sys.stdout.isatty()
    use_json = is_production or not is_tty

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if use_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
