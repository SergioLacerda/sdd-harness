"""Drift detection — classify and surface governance state mismatches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import CompiledArtifact
    from .session import SessionState

# Canonical drift taxonomy (§12.5 of the improvement plan).
DRIFT_NONE = "none"
DRIFT_SPEC = "spec_drift"  # source changed, artifact not recompiled
DRIFT_PROFILE = "profile_drift"  # runtime profile ≠ expected (master/client mismatch)
DRIFT_SESSION = "session_drift"  # cached session bound to a stale artifact fingerprint
DRIFT_POLICY = "policy_drift"  # policy-set version mismatch
DRIFT_MISSING = "missing_fingerprint"
DRIFT_MISMATCH = "fingerprint_mismatch"

# Deterministic remediation commands per drift type.
_REMEDIATION: dict[str, str] = {
    DRIFT_NONE: "",
    DRIFT_SPEC: "sdd governance compile",
    DRIFT_PROFILE: "sdd governance validate --profile <expected>",
    DRIFT_SESSION: "sdd runtime reset-session",
    DRIFT_POLICY: "sdd governance compile --force",
    DRIFT_MISSING: "sdd governance compile",
    DRIFT_MISMATCH: "sdd governance compile",
}


@dataclass
class DriftReport:
    """Result of a drift detection operation."""

    drift_detected: bool
    drift_type: str
    remediation_command: str = ""
    details: str = ""

    @property
    def is_clean(self) -> bool:
        """Is Clean."""
        return not self.drift_detected


class DriftDetector:
    """Detects runtime drift between session state and compiled artifact.

    Two entry points:
    - :meth:`detect` — low-level fingerprint comparison (backward-compatible).
    - :meth:`classify` — full semantic drift classification using typed objects.
    """

    def detect(
        self, *, session_fingerprint: str, artifact_fingerprint: str
    ) -> DriftReport:
        """Fingerprint-level drift check (backward-compatible)."""
        if not session_fingerprint or not artifact_fingerprint:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_MISSING,
                remediation_command=_REMEDIATION[DRIFT_MISSING],
                details="One or both fingerprints are empty.",
            )
        if session_fingerprint != artifact_fingerprint:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_MISMATCH,
                remediation_command=_REMEDIATION[DRIFT_MISMATCH],
                details=(
                    f"Session fingerprint '{session_fingerprint}' does not match "
                    f"artifact fingerprint '{artifact_fingerprint}'."
                ),
            )
        return DriftReport(drift_detected=False, drift_type=DRIFT_NONE)

    def classify(
        self,
        *,
        session: SessionState,
        artifact: CompiledArtifact,
        current_profile: str,
    ) -> DriftReport:
        """Full semantic drift classification across all four drift axes.

        Checks are applied in priority order; the first detected drift wins.
        """
        # 1. Profile drift — runtime profile ≠ artifact profile.
        if artifact.profile and current_profile and artifact.profile != current_profile:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_PROFILE,
                remediation_command=_REMEDIATION[DRIFT_PROFILE].replace(
                    "<expected>", artifact.profile
                ),
                details=(
                    f"Current profile '{current_profile}' does not match "
                    f"artifact profile '{artifact.profile}'."
                ),
            )

        # 2. Session drift — session bound to a different artifact fingerprint.
        report = self.detect(
            session_fingerprint=session.artifact_fingerprint,
            artifact_fingerprint=artifact.fingerprint,
        )
        if report.drift_detected:
            if report.drift_type == DRIFT_MISMATCH:
                return DriftReport(
                    drift_detected=True,
                    drift_type=DRIFT_SESSION,
                    remediation_command=_REMEDIATION[DRIFT_SESSION],
                    details=report.details,
                )
            return report  # DRIFT_MISSING — propagate as-is

        # 3. Policy drift — schema version mismatch between session and artifact.
        if session.schema_version != artifact.schema_version:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_POLICY,
                remediation_command=_REMEDIATION[DRIFT_POLICY],
                details=(
                    f"Session schema_version '{session.schema_version}' does not match "
                    f"artifact schema_version '{artifact.schema_version}'."
                ),
            )

        return DriftReport(drift_detected=False, drift_type=DRIFT_NONE)
