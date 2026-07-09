"""Phase timer helper for `sdd ask` trace-route instrumentation.

Records wall-clock timing for named pipeline phases without changing the
behavior of the phases themselves. See
.analysis/refined/sdd-ask-traceroute-20260709/design.md for the event model
this feeds into.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PhaseRecord:
    """A single measured phase in an `sdd ask` invocation."""

    phase_id: str
    latency_domain: str
    duration_ms: int
    start_ts: str
    end_ts: str
    measurement_quality: str = "measured"
    observed_by: str = "sdd_cli"
    failed: bool = False


@dataclass
class PhaseTimer:
    """Collects `PhaseRecord`s for the phases of one `sdd ask` invocation."""

    _records: list[PhaseRecord] = field(default_factory=list)

    @contextmanager
    def phase(
        self,
        phase_id: str,
        *,
        latency_domain: str,
        measurement_quality: str = "measured",
        observed_by: str = "sdd_cli",
    ) -> Iterator[None]:
        start_mono = time.monotonic()
        start_ts = _utc_now_iso()
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            end_ts = _utc_now_iso()
            duration_ms = int((time.monotonic() - start_mono) * 1000)
            self._records.append(
                PhaseRecord(
                    phase_id=phase_id,
                    latency_domain=latency_domain,
                    duration_ms=duration_ms,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    measurement_quality=measurement_quality,
                    observed_by=observed_by,
                    failed=failed,
                )
            )

    def records(self) -> list[PhaseRecord]:
        return list(self._records)

    def phase_total_ms(self) -> int:
        return sum(r.duration_ms for r in self._records)

    def unattributed_ms(self, *, session_duration_ms: int) -> int:
        return max(0, session_duration_ms - self.phase_total_ms())
