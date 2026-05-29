"""Token economy metrics aggregation and Prometheus text format exposition.

Zero-dependency: stdlib only. Thread-safe collectors for in-process token/cost
tracking and Prometheus text-format rendering (version 0.0.4).

Usage::

    from sdd_runtime.metrics import TokenEconomyCollector, PrometheusTextRenderer
    from sdd_runtime.reader import TelemetryReader
    from pathlib import Path

    # Replay JSONL to build metrics
    reader = TelemetryReader(Path(".sdd/runtime/compliance-events.jsonl"))
    collector = TokenEconomyCollector.from_reader(reader)
    snap = collector.snapshot()

    # Render as Prometheus text format
    prometheus_text = PrometheusTextRenderer().render(snap)

    # Ingest live events
    collector.ingest(runtime_event)
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .reader import TelemetryReader
    from .telemetry import RuntimeEvent


def _load_token_budget_config() -> dict[str, Any]:
    """Load token budget configuration from pyproject.toml or environment.

    Resolution order:
    1. Environment variables (SDD_TOKEN_BUDGET_CEILING, SDD_CONTEXT_COMPRESSION_THRESHOLD, SDD_CONTEXT_COMPRESSION_TARGET)
    2. pyproject.toml [tool.sdd.runtime] configuration
    3. Default values

    Returns:
        Dict with keys: token_budget_ceiling, context_compression_threshold, context_compression_target
    """
    # Environment variable overrides
    if os.environ.get("SDD_TOKEN_BUDGET_CEILING"):
        ceiling = int(os.environ.get("SDD_TOKEN_BUDGET_CEILING", "100000"))
    else:
        ceiling = 100000

    if os.environ.get("SDD_CONTEXT_COMPRESSION_THRESHOLD"):
        threshold = float(os.environ.get("SDD_CONTEXT_COMPRESSION_THRESHOLD", "70"))
    else:
        threshold = 70.0

    if os.environ.get("SDD_CONTEXT_COMPRESSION_TARGET"):
        target = float(os.environ.get("SDD_CONTEXT_COMPRESSION_TARGET", "50"))
    else:
        target = 50.0

    # Try to load from pyproject.toml if environment variables not set
    pyproject_path = Path.cwd() / "pyproject.toml"
    if pyproject_path.exists() and not os.environ.get("SDD_TOKEN_BUDGET_CEILING"):
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[import-not-found]

            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            sdd_runtime = config.get("tool", {}).get("sdd", {}).get("runtime", {})
            ceiling = sdd_runtime.get("token_budget_ceiling", ceiling)
            threshold = sdd_runtime.get("context_compression_threshold", threshold)
            target = sdd_runtime.get("context_compression_target", target)
        except Exception:  # nosec B110
            # If pyproject.toml reading fails, use defaults
            pass

    return {
        "token_budget_ceiling": ceiling,
        "context_compression_threshold": threshold,
        "context_compression_target": target,
    }


@dataclass
class ModelMetrics:
    """Per-model token and cost accumulators."""

    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    call_count: int = 0


@dataclass
class EconomySnapshot:
    """Point-in-time snapshot of aggregated token economy metrics.

    Thread-safe snapshot captured from TokenEconomyCollector.snapshot().
    All fields are immutable after creation.
    """

    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens_total: int = 0
    total_cost_usd: float = 0.0
    total_calls: int = 0
    budget_utilization_pct: float = 0.0
    warn_count: int = 0
    breach_count: int = 0
    retry_cap_count: int = 0
    per_model: dict[str, ModelMetrics] = field(default_factory=dict)


class TokenEconomyCollector:
    """In-process accumulator for token economy RuntimeEvents.

    Thread-safe; uses a single RLock for all mutations.
    Can be populated from a TelemetryReader (JSONL replay) or
    by calling ingest(event) on each live RuntimeEvent.

    The collector filters and processes only relevant events:
      - economy.token.consume → increments token/cost counters and per-model tracking
      - economy.budget.warn* → increments warn_count
      - economy.budget.breach* → increments breach_count
      - economy.retry.cap.reached → increments retry_cap_count
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot = EconomySnapshot()
        self._budget_config = _load_token_budget_config()

    def ingest(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Update internal counters from a single RuntimeEvent or dict.

        No-op on irrelevant event types. Acquires lock for all mutations.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation (e.g., from JSONL).
            Must have fields: event, tokens_input, tokens_output, tokens_total,
            budget_utilization_pct, details (dict).
        """
        # Normalize to dict interface
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        event_type = event_dict.get("event", "")

        with self._lock:
            # Process economy.token.consume events
            if event_type == "economy.token.consume":
                tokens_in = event_dict.get("tokens_input") or 0
                tokens_out = event_dict.get("tokens_output") or 0
                tokens_tot = event_dict.get("tokens_total") or 0

                self._snapshot.total_tokens_input += tokens_in
                self._snapshot.total_tokens_output += tokens_out
                self._snapshot.total_tokens_total += tokens_tot
                self._snapshot.total_calls += 1

                # Track per-model metrics
                details = event_dict.get("details", {})
                if isinstance(details, dict):
                    model = details.get("model", "unknown")
                    cost = details.get("cost_usd", 0.0)

                    if model not in self._snapshot.per_model:
                        self._snapshot.per_model[model] = ModelMetrics()

                    m = self._snapshot.per_model[model]
                    m.tokens_input += tokens_in
                    m.tokens_output += tokens_out
                    m.tokens_total += tokens_tot
                    m.cost_usd += cost
                    m.call_count += 1

                    self._snapshot.total_cost_usd += cost

                # Calculate budget utilization percentage from config ceiling
                budget_ceiling = self._budget_config.get("token_budget_ceiling", 100000)
                if budget_ceiling > 0:
                    self._snapshot.budget_utilization_pct = (
                        self._snapshot.total_tokens_total / budget_ceiling
                    ) * 100
                else:
                    self._snapshot.budget_utilization_pct = 0.0

            # Process budget warn events
            elif event_type in (
                "economy.budget.warn",
                "economy.budget.warn.tokens",
                "economy.budget.warn.usd",
            ):
                self._snapshot.warn_count += 1

            # Process budget breach events
            elif event_type in (
                "economy.budget.breach",
                "economy.budget.breach.tokens",
                "economy.budget.breach.usd",
            ):
                self._snapshot.breach_count += 1

            # Process retry cap reached events
            elif event_type == "economy.retry.cap.reached":
                self._snapshot.retry_cap_count += 1

    @classmethod
    def from_reader(cls, reader: TelemetryReader) -> TokenEconomyCollector:
        """Build a collector by replaying all relevant events from a TelemetryReader.

        Iterates over all economy.token.consume, economy.budget.warn*, economy.budget.breach*,
        and economy.retry.cap.reached events and calls ingest() on each.

        Parameters
        ----------
        reader:
            An initialized TelemetryReader pointing to a JSONL events file.

        Returns
        -------
        TokenEconomyCollector with aggregated state from all events.
        """
        collector = cls()

        # Iterate all events and filter for relevant types
        for evt in reader.list_events():
            event_type = evt.get("event", "")
            if (
                event_type == "economy.token.consume"
                or event_type.startswith("economy.budget.warn")
                or event_type.startswith("economy.budget.breach")
                or event_type == "economy.retry.cap.reached"
            ):
                collector.ingest(evt)

        return collector

    def snapshot(self) -> EconomySnapshot:
        """Return a copy of the current aggregated state.

        Thread-safe; acquires lock for the entire copy operation.

        Returns
        -------
        EconomySnapshot with point-in-time values. Safe to share/serialize.
        """
        with self._lock:
            # Deep copy per_model dict
            per_model_copy = {
                model: ModelMetrics(
                    tokens_input=m.tokens_input,
                    tokens_output=m.tokens_output,
                    tokens_total=m.tokens_total,
                    cost_usd=m.cost_usd,
                    call_count=m.call_count,
                )
                for model, m in self._snapshot.per_model.items()
            }
            return EconomySnapshot(
                total_tokens_input=self._snapshot.total_tokens_input,
                total_tokens_output=self._snapshot.total_tokens_output,
                total_tokens_total=self._snapshot.total_tokens_total,
                total_cost_usd=self._snapshot.total_cost_usd,
                total_calls=self._snapshot.total_calls,
                budget_utilization_pct=self._snapshot.budget_utilization_pct,
                warn_count=self._snapshot.warn_count,
                breach_count=self._snapshot.breach_count,
                retry_cap_count=self._snapshot.retry_cap_count,
                per_model=per_model_copy,
            )

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._snapshot = EconomySnapshot()


class PrometheusTextRenderer:
    """Render an EconomySnapshot as Prometheus text exposition format.

    Produces the canonical text format (version 0.0.4) as a UTF-8 string.
    No external dependencies. Complies with OpenMetrics specification.

    Metric families:
      - sdd_tokens_input_total (counter)
      - sdd_tokens_output_total (counter)
      - sdd_tokens_total_total (counter)
      - sdd_cost_usd_total (counter)
      - sdd_llm_calls_total (counter)
      - sdd_budget_utilization_pct (gauge)
      - sdd_budget_warn_total (counter)
      - sdd_budget_breach_total (counter)
      - sdd_retry_cap_total (counter)
      - sdd_tokens_by_model_input_total (counter with model label)
      - sdd_tokens_by_model_output_total (counter with model label)

    Usage::

        renderer = PrometheusTextRenderer()
        prometheus_text = renderer.render(snapshot)
        # Use as HTTP response body with Content-Type: text/plain; version=0.0.4
    """

    def render(self, snapshot: EconomySnapshot) -> str:
        """Return the full Prometheus text exposition payload as a str.

        Parameters
        ----------
        snapshot:
            An EconomySnapshot to render.

        Returns
        -------
        Complete Prometheus text format (version 0.0.4) as UTF-8 string.
        """
        lines: list[str] = []

        # Helper: add metric line
        def add_metric(
            name: str,
            value: float | int,
            help_text: str = "",
            metric_type: str = "gauge",
            labels: dict[str, str] | None = None,
        ) -> None:
            if help_text:
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {metric_type}")
            lines.append(self._metric_line(name, value, labels))

        # Global counters
        add_metric(
            "sdd_tokens_input_total",
            snapshot.total_tokens_input,
            help_text="Total input tokens consumed across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_tokens_output_total",
            snapshot.total_tokens_output,
            help_text="Total output tokens consumed across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_tokens_total_total",
            snapshot.total_tokens_total,
            help_text="Total tokens (input + output) across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_cost_usd_total",
            round(snapshot.total_cost_usd, 4),
            help_text="Estimated USD cost of all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_llm_calls_total",
            snapshot.total_calls,
            help_text="Total number of LLM calls recorded",
            metric_type="counter",
        )
        add_metric(
            "sdd_budget_utilization_pct",
            round(snapshot.budget_utilization_pct, 2),
            help_text="Current budget utilization percentage (latest observed)",
            metric_type="gauge",
        )
        add_metric(
            "sdd_budget_warn_total",
            snapshot.warn_count,
            help_text="Number of budget warn events (>90% utilization)",
            metric_type="counter",
        )
        add_metric(
            "sdd_budget_breach_total",
            snapshot.breach_count,
            help_text="Number of budget breach events (>=100% utilization)",
            metric_type="counter",
        )
        add_metric(
            "sdd_retry_cap_total",
            snapshot.retry_cap_count,
            help_text="Number of retry ceiling breach events",
            metric_type="counter",
        )

        # Per-model metrics
        if snapshot.per_model:
            lines.append(
                "# HELP sdd_tokens_by_model_input_total Input tokens per model"
            )
            lines.append("# TYPE sdd_tokens_by_model_input_total counter")
            for model, metrics in sorted(snapshot.per_model.items()):
                lines.append(
                    self._metric_line(
                        "sdd_tokens_by_model_input_total",
                        metrics.tokens_input,
                        labels={"model": model},
                    )
                )

            lines.append(
                "# HELP sdd_tokens_by_model_output_total Output tokens per model"
            )
            lines.append("# TYPE sdd_tokens_by_model_output_total counter")
            for model, metrics in sorted(snapshot.per_model.items()):
                lines.append(
                    self._metric_line(
                        "sdd_tokens_by_model_output_total",
                        metrics.tokens_output,
                        labels={"model": model},
                    )
                )

            lines.append(
                "# HELP sdd_tokens_by_model_total_total Total tokens (input+output) per model"
            )
            lines.append("# TYPE sdd_tokens_by_model_total_total counter")
            for model, metrics in sorted(snapshot.per_model.items()):
                lines.append(
                    self._metric_line(
                        "sdd_tokens_by_model_total_total",
                        metrics.tokens_total,
                        labels={"model": model},
                    )
                )

            lines.append("# HELP sdd_cost_usd_by_model_total USD cost per model")
            lines.append("# TYPE sdd_cost_usd_by_model_total counter")
            for model, metrics in sorted(snapshot.per_model.items()):
                lines.append(
                    self._metric_line(
                        "sdd_cost_usd_by_model_total",
                        round(metrics.cost_usd, 4),
                        labels={"model": model},
                    )
                )

            lines.append(
                "# HELP sdd_llm_calls_by_model_total Number of LLM calls per model"
            )
            lines.append("# TYPE sdd_llm_calls_by_model_total counter")
            for model, metrics in sorted(snapshot.per_model.items()):
                lines.append(
                    self._metric_line(
                        "sdd_llm_calls_by_model_total",
                        metrics.call_count,
                        labels={"model": model},
                    )
                )

        return "\n".join(lines) + "\n"

    def _metric_line(
        self,
        name: str,
        value: float | int,
        labels: dict[str, str] | None = None,
    ) -> str:
        """Format a single metric line with optional label set.

        Follows Prometheus text format 0.0.4: metric_name{label="val",...} value

        Parameters
        ----------
        name:
            Metric name (e.g., "sdd_tokens_input_total").
        value:
            Numeric value (int or float).
        labels:
            Optional dict of label name -> label value. Values are escaped.

        Returns
        -------
        Single line of Prometheus text format, no trailing newline.
        """
        label_str = ""
        if labels:
            label_parts = []
            for k, v in sorted(labels.items()):
                # Escape: \, ", \n in label values
                escaped = (
                    v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                )
                label_parts.append(f'{k}="{escaped}"')
            label_str = "{" + ",".join(label_parts) + "}"

        return f"{name}{label_str} {value}"
