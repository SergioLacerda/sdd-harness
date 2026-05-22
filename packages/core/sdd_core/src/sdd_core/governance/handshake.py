"""
SDD Architecture - Agent Handshake Protocol (AHP) v1.1

Implicit context validation protocol executed before technical responses.

Design Principles:
- Semantic: Runs only when appropriate (technical context)
- Smart: Caches state, avoids redundant checks
- Agnostic: Works for any governed system (not SDD-specific)
- Non-intrusive: 3 output modes (silent/compact/verbose)
- State-based: 5-state machine with clear transitions

4-Layer Validation:
    1. DISCOVERY       -> Is governance present?
    2. LINK_VALIDATION -> Are connections valid?
    3. RUNTIME         -> Is it operational?
    4. GOVERNANCE      -> Is it healthy?

5-State Machine:
    NOT_CONNECTED      -> No governance found
    MISCONFIGURED      -> Found but broken
    NOT_INITIALIZED    -> Found but not setup
    PARTIAL            -> Runtime incomplete
    HEALTHY            -> Everything OK
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from .handshake_cache import HandshakeCache
from .handshake_challenge import HandshakeChallenge
from .handshake_formatter import HandshakeFormatter
from .handshake_models import HandshakeReport, HandshakeRequest, HandshakeResponse
from .handshake_telemetry import HandshakeTelemetry
from .handshake_validator import GovernanceValidator, ValidationResult
from .semantic_trigger import SemanticTrigger

__all__ = [
    "AgentHandshakeProtocol",
    "HandshakeRequest",
    "ValidationResult",
    "HandshakeReport",
    "HandshakeResponse",
]

# ========== DATA MODELS ==========


class AgentHandshakeProtocol:
    """
    Agent Handshake Protocol - Smart context validation engine.

    Validates system state before technical operations without being intrusive.
    Caches results to avoid redundant checks and supports 3 output modes.
    """

    # State definitions
    STATES = {
        "NOT_CONNECTED": {"emoji": "X", "description": "No governance detected"},
        "MISCONFIGURED": {"emoji": "!", "description": "Governance broken/invalid"},
        "NOT_INITIALIZED": {
            "emoji": "!",
            "description": "Setup incomplete (PHASE 0 needed)",
        },
        "PARTIAL": {"emoji": "~", "description": "Runtime incomplete"},
        "HEALTHY": {"emoji": "+", "description": "Fully operational"},
    }

    # Recommended actions per state
    ACTIONS = {
        "NOT_CONNECTED": ["proceed_normally"],
        "MISCONFIGURED": ["warn_user", "suggest_review"],
        "NOT_INITIALIZED": ["suggest_phase_0_setup"],
        "PARTIAL": ["suggest_fix"],
        "HEALTHY": ["proceed_silently"],
    }

    def __init__(
        self,
        project_root: Path | None = None,
        cache_ttl_minutes: int | None = None,
    ):
        """
        Initialize handshake protocol.

        Args:
            project_root: Project root directory (auto-detected if None).
            cache_ttl_minutes: Cache validity in minutes. When None (default),
                                TTL is derived from profile type: client=30min,
                                master=480min (8h).
        """
        self.project_root = project_root or self._find_project_root()
        self.cache_dir = self.project_root / ".sdd" / "runtime"
        self.cache_file = self.cache_dir / "governance-state.json"
        self.response_file = self.cache_dir / "handshake-response.json"

        if cache_ttl_minutes is not None:
            self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        else:
            # Need to create cache instance temporarily to resolve TTL
            temp_cache = HandshakeCache(
                self.cache_file,
                self.cache_dir,
                timedelta(minutes=30),
                self.project_root,
                "",
            )
            self.cache_ttl = timedelta(minutes=temp_cache.resolve_ttl_minutes())

        self.validation_results: list[dict[str, Any]] = []
        self.current_state = "NOT_CONNECTED"
        self.current_confidence = 0.0

        # GAP (Governance Activation Protocol) v1.0 fields
        self.gap_status = "NOT_ACTIVE"  # ACTIVE | PARTIAL | NOT_ACTIVE
        # A5 fix: inject agent_id via SDD_AGENT_ID env var
        self.agent_id: str = os.environ.get("SDD_AGENT_ID", "unknown")
        self.spec_fingerprint = ""
        self.mandates_loaded: list[str] = []
        self.skill_profile = "default"

        # Initialize delegated instances
        self._validator = GovernanceValidator(self.project_root)
        self._cache = HandshakeCache(
            self.cache_file,
            self.cache_dir,
            self.cache_ttl,
            self.project_root,
            self.agent_id,
        )
        self._formatter = HandshakeFormatter()
        self._trigger = SemanticTrigger()
        self._challenge = HandshakeChallenge(
            self.agent_id, self.project_root, self.cache_dir, self.response_file
        )
        self._telemetry = HandshakeTelemetry()

    def _find_project_root(self) -> Path:
        """Find project root directory."""
        current = Path.cwd()
        if current.name == "packages":
            return current.parent

        for parent in [current, *list(current.parents)]:
            if (parent / "packages").exists():
                return parent

        return current

    # ========== SEMANTIC TRIGGERING ==========

    def should_run_handshake(self, user_input: str) -> bool:
        """
        Detect if user input is technical/contextual.

        Returns True if handshake should run automatically.
        """
        return self._trigger.should_run_handshake(user_input)

    # ========== 4-LAYER VALIDATION ==========

    def _layer_1_discovery(self) -> tuple[str, list[ValidationResult]]:
        """Delegate to validator."""
        return self._validator.layer_1_discovery()

    def _layer_2_link_validation(self) -> tuple[str, list[ValidationResult]]:
        """Delegate to validator."""
        return self._validator.layer_2_link_validation()

    def _layer_3_runtime_validation(self) -> tuple[str, list[ValidationResult]]:
        """Delegate to validator."""
        return self._validator.layer_3_runtime_validation()

    def _layer_4_governance_health(self) -> tuple[str, list[ValidationResult]]:
        """Delegate to validator."""
        return self._validator.layer_4_governance_health()

    # ========== STATE MACHINE ==========

    def _compute_final_state(self, l1: str, l2: str, l3: str, l4: str) -> str:
        """Delegate to validator."""
        return self._validator.compute_final_state(l1, l2, l3, l4)

    def _compute_confidence(self, all_results: list[ValidationResult]) -> float:
        """Delegate to validator."""
        return self._validator.compute_confidence(all_results)

    # ========== PERSISTENCE ==========

    def _load_cache(self) -> dict[str, Any] | None:
        """Delegate to cache manager."""
        return self._cache.load_cache()

    def _extract_governance_core(self) -> dict[str, Any] | None:
        """Delegate to cache manager."""
        return self._cache.extract_governance_core()

    def _extract_mandates(self) -> list[str]:
        """Delegate to cache manager."""
        return self._cache.extract_mandates()

    def _compute_spec_fingerprint(self) -> str:
        """Delegate to cache manager."""
        return self._cache.compute_spec_fingerprint()

    def _map_ahp_to_gap(self, ahp_state: str, confidence: float) -> str:
        """Delegate to cache manager."""
        return self._cache.map_ahp_to_gap(ahp_state, confidence)

    def _save_cache(
        self, state: str, checks: list[dict[str, Any]], confidence: float
    ) -> None:
        """Save state to persistent cache with GAP fields."""
        # Update skill profile before saving
        self.skill_profile = self._cache.extract_skill_profile()
        self._cache.save_cache(state, checks, confidence, self.skill_profile)

        # Sync back to self
        self.mandates_loaded = self._cache.mandates_loaded
        self.spec_fingerprint = self._cache.spec_fingerprint
        self.gap_status = self._cache.gap_status

    def _extract_skill_profile(self) -> str:
        """Delegate to cache manager."""
        return self._cache.extract_skill_profile()

    def _emit_governance_event(self, final_state: str, confidence: float) -> None:
        """Emit GOVERNANCE_CHECKED telemetry event. Failure is non-blocking.

        Delegates to HandshakeTelemetry.
        """
        self._telemetry.emit(
            self.agent_id,
            final_state,
            confidence,
            self.project_root,
            self.gap_status,
            self.skill_profile,
            self.spec_fingerprint,
            self.mandates_loaded,
        )

    def _resolve_signature_status(self) -> str:
        """Resolve signature status by checking for signed governance artifacts.

        Delegates to HandshakeChallenge.
        """
        return self._challenge._resolve_signature_status()

    # ========== GAP FORMATTING ==========

    def format_gap_output(
        self, mode: Literal["silent", "compact", "verbose"] = "compact"
    ) -> str:
        """Format Governance Activation Protocol status."""
        self._formatter.gap_status = self.gap_status
        self._formatter.mandates_loaded = self.mandates_loaded
        self._formatter.current_confidence = self.current_confidence
        return self._formatter.format_gap_output(mode=mode)

    def format_combined_output(
        self,
        state: str,
        report: HandshakeReport,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Format combined AHP + GAP output."""
        self._formatter.gap_status = self.gap_status
        self._formatter.mandates_loaded = self.mandates_loaded
        self._formatter.current_confidence = self.current_confidence
        return self._formatter.format_combined_output(state, report, mode=mode)

    # ========== PUBLIC API ==========

    def validate(
        self,
        output_mode: Literal["silent", "compact", "verbose"] = "compact",
        force_recheck: bool = False,
    ) -> tuple[str, HandshakeReport]:
        """Execute full handshake protocol."""
        if not force_recheck:
            cache = self._load_cache()
            if cache:
                if "gap_version" in cache:
                    self.gap_status = cache.get("status", "NOT_ACTIVE")
                    self.agent_id = cache.get("agent_id", self.agent_id)
                    self.spec_fingerprint = cache.get("spec_fingerprint", "")
                    self.mandates_loaded = cache.get("mandates_loaded", [])
                    self.skill_profile = cache.get("skill_profile", "default")
                else:
                    self.mandates_loaded = self._extract_mandates()
                    self.spec_fingerprint = self._compute_spec_fingerprint()
                    self.gap_status = self._map_ahp_to_gap(
                        cache.get("state", "NOT_CONNECTED"), cache.get("confidence", 0)
                    )

                self.current_confidence = cache.get("confidence", 0)

                report = HandshakeReport(
                    state=cache["state"],
                    confidence=cache["confidence"],
                    checks=[],
                    actions=self.ACTIONS.get(cache["state"], []),
                    cached=True,
                    cache_age_seconds=int(
                        (
                            datetime.now() - datetime.fromisoformat(cache["last_check"])
                        ).total_seconds()
                    ),
                )
                return cache["state"], report

        l1_state, l1_results = self._layer_1_discovery()
        l2_state, l2_results = self._layer_2_link_validation()
        l3_state, l3_results = self._layer_3_runtime_validation()
        l4_state, l4_results = self._layer_4_governance_health()

        all_results = l1_results + l2_results + l3_results + l4_results
        final_state = self._compute_final_state(l1_state, l2_state, l3_state, l4_state)
        confidence = self._compute_confidence(all_results)

        self.mandates_loaded = self._extract_mandates()
        self.spec_fingerprint = self._compute_spec_fingerprint()
        self.gap_status = self._map_ahp_to_gap(final_state, confidence)
        self.current_confidence = confidence

        checks = [asdict(r) for r in all_results]
        self._save_cache(final_state, checks, confidence)

        # A3: emit GOVERNANCE_CHECKED compliance event (non-blocking)
        self._emit_governance_event(final_state, confidence)

        report = HandshakeReport(
            state=final_state,
            confidence=round(confidence, 1),
            checks=checks,
            actions=self.ACTIONS.get(final_state, []),
            cached=False,
            cache_age_seconds=None,
        )
        return final_state, report

    # ========== BIDIRECTIONAL HANDSHAKE (M015) ==========

    def complete_handshake(self, response_data: dict[str, Any]) -> HandshakeResponse:
        """Finalize the bidirectional handshake by recording the agent's response.

        Delegates to HandshakeChallenge.
        """
        return self._challenge.complete_handshake(response_data)

    def generate_challenge(
        self, task_description: str = "General Task", task_type: str = "other"
    ) -> HandshakeRequest:
        """Generate a formal Handshake Request challenge (M015).

        Delegates to HandshakeChallenge.
        """
        return self._challenge.generate_challenge(
            task_description,
            task_type,
            self.mandates_loaded or self._extract_mandates(),
        )

    def get_handshake_response(self) -> HandshakeResponse | None:
        """Retrieve the currently active handshake response.

        Delegates to HandshakeChallenge.
        """
        return self._challenge.get_handshake_response()

    def is_handshake_valid(self, strict: bool = False) -> bool:
        """Check if a valid handshake exists and meets security requirements.

        Delegates to HandshakeChallenge.
        """
        return self._challenge.is_handshake_valid(strict)

    # ========== OUTPUT FORMATTING ==========

    def format_output(
        self,
        state: str,
        report: HandshakeReport,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Delegate to formatter."""
        return self._formatter.format_output(state, report, mode=mode)
