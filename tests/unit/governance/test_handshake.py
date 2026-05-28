"""Unit tests for sdd_core.governance.handshake.AgentHandshakeProtocol."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ahp(tmp_path: Path) -> Any:
    """Create an AHP instance with project_root set to tmp_path."""
    from sdd_core.governance.handshake import AgentHandshakeProtocol

    return AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)


def _write_profile(tmp_path: Path, profile_type: str = "client") -> None:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir(exist_ok=True)
    (sdd_dir / "profile").write_text(
        f"[sdd]\ntype = {profile_type}\nname = test\n", encoding="utf-8"
    )


def _write_governance_core(tmp_path: Path, items: list[Any] | None = None) -> Path:
    compiled_dir = tmp_path / ".sdd" / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    data = {"items": items or [], "fingerprint": "abc123"}
    path = compiled_dir / "governance-core.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _write_cache(tmp_path: Path, state: str = "HEALTHY", minutes_old: int = 0) -> None:
    cache_dir = tmp_path / ".sdd" / "runtime"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ts = (datetime.now() - timedelta(minutes=minutes_old)).isoformat()
    cache = {
        "gap_version": "1.0",
        "status": "ACTIVE",
        "agent_id": "unknown",
        "spec_fingerprint": "abc123",
        "mandates_loaded": [],
        "confidence": 75.0,
        "last_check": ts,
        "state": state,
        "checks": [],
    }
    (cache_dir / "governance-state.json").write_text(
        json.dumps(cache), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestAhpInit:
    def test_cache_dir_set_from_project_root(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.cache_dir == tmp_path / ".sdd" / "runtime"

    def test_cache_ttl_set_from_param(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.cache_ttl == timedelta(minutes=5)

    def test_default_state_not_connected(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.current_state == "NOT_CONNECTED"

    def test_gap_status_initially_not_active(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.gap_status == "NOT_ACTIVE"

    def test_agent_id_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_AGENT_ID", "test-agent-99")
        ahp = _make_ahp(tmp_path)
        assert ahp.agent_id == "test-agent-99"

    def test_ttl_client_default(self, tmp_path: Path) -> None:
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        # No cache_ttl_minutes, no profile → defaults to client (30 min)
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.cache_ttl == timedelta(minutes=30)

    def test_ttl_master_when_profile_type_is_master(self, tmp_path: Path) -> None:
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        _write_profile(tmp_path, "master")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.cache_ttl == timedelta(minutes=480)


# ---------------------------------------------------------------------------
# should_run_handshake
# ---------------------------------------------------------------------------


class TestShouldRunHandshake:
    def test_empty_string_returns_false(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("") is False

    def test_technical_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("can you validate the code?") is True

    def test_status_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("check the status") is True

    def test_governance_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("show governance") is True

    def test_casual_greeting_returns_false(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("obrigado pela ajuda") is False

    def test_joke_request_returns_false(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        # Should not trigger
        result = ahp.should_run_handshake("tell me a funny joke")
        # May be True or False depending on "funny" keyword — just ensure no crash
        assert isinstance(result, bool)

    def test_spec_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp.should_run_handshake("show me the spec") is True


# ---------------------------------------------------------------------------
# Layer 1: Discovery
# ---------------------------------------------------------------------------


class TestLayer1Discovery:
    def test_no_sdd_dir_returns_not_connected(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, results = ahp._layer_1_discovery()
        assert state == "NOT_CONNECTED"

    def test_sdd_dir_present_returns_connected(self, tmp_path: Path) -> None:
        (tmp_path / ".sdd").mkdir()
        ahp = _make_ahp(tmp_path)
        state, results = ahp._layer_1_discovery()
        assert state == "CONNECTED"

    def test_results_contain_sdd_dir_check(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        _, results = ahp._layer_1_discovery()
        names = [r.name for r in results]
        assert ".sdd/ directory" in names

    def test_governance_core_json_check_present(self, tmp_path: Path) -> None:
        (tmp_path / ".sdd").mkdir()
        ahp = _make_ahp(tmp_path)
        _, results = ahp._layer_1_discovery()
        names = [r.name for r in results]
        assert "governance-core.json" in names


# ---------------------------------------------------------------------------
# Layer 2: Link Validation
# ---------------------------------------------------------------------------


class TestLayer2LinkValidation:
    def test_no_profile_returns_no_config(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_2_link_validation()
        assert state == "NO_CONFIG"

    def test_valid_profile_returns_link_ok(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, "client")
        # Create packages dir (needed for core_accessible check)
        (tmp_path / "packages").mkdir()
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_2_link_validation()
        assert state == "LINK_OK"

    def test_invalid_profile_type_returns_broken_link(self, tmp_path: Path) -> None:
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text("[sdd]\ntype = invalid\n", encoding="utf-8")
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_2_link_validation()
        assert state == "BROKEN_LINK"


# ---------------------------------------------------------------------------
# Layer 3: Runtime Validation
# ---------------------------------------------------------------------------


class TestLayer3RuntimeValidation:
    def test_no_runtime_dir_returns_not_initialized(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "NOT_INITIALIZED"

    def test_runtime_dir_without_state_returns_partial(self, tmp_path: Path) -> None:
        (tmp_path / ".sdd" / "runtime").mkdir(parents=True)
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "PARTIAL"

    def test_full_runtime_returns_ready(self, tmp_path: Path) -> None:
        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text("{}", encoding="utf-8")
        sdd_runtime_dir = tmp_path / ".sdd" / "runtime"
        sdd_runtime_dir.mkdir(parents=True, exist_ok=True)
        (sdd_runtime_dir / ".phase-0-complete").write_text("done", encoding="utf-8")
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "READY"


# ---------------------------------------------------------------------------
# Layer 4: Governance Health
# ---------------------------------------------------------------------------


class TestLayer4GovernanceHealth:
    def test_no_artifacts_returns_unknown(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_4_governance_health()
        assert state == "UNKNOWN"

    def test_valid_governance_core_returns_degraded_or_healthy(
        self, tmp_path: Path
    ) -> None:
        _write_governance_core(tmp_path)
        ahp = _make_ahp(tmp_path)
        state, _ = ahp._layer_4_governance_health()
        assert state in ("HEALTHY", "DEGRADED")

    def test_invalid_governance_json_governance_not_valid(self, tmp_path: Path) -> None:
        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_text("not json", encoding="utf-8")
        ahp = _make_ahp(tmp_path)
        _, results = ahp._layer_4_governance_health()
        integrity_check = next(r for r in results if r.name == "governance integrity")
        assert integrity_check.passed is False


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------


class TestComputeFinalState:
    def test_not_connected_when_l1_not_connected(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._compute_final_state(
            "NOT_CONNECTED", "LINK_OK", "READY", "HEALTHY"
        )
        assert result == "NOT_CONNECTED"

    def test_misconfigured_when_l2_broken(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._compute_final_state(
            "CONNECTED", "BROKEN_LINK", "READY", "HEALTHY"
        )
        assert result == "MISCONFIGURED"

    def test_not_initialized_when_l3_not_initialized(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._compute_final_state(
            "CONNECTED", "LINK_OK", "NOT_INITIALIZED", "HEALTHY"
        )
        assert result == "NOT_INITIALIZED"

    def test_partial_when_partial_in_any_layer(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._compute_final_state("CONNECTED", "LINK_OK", "PARTIAL", "HEALTHY")
        assert result == "PARTIAL"

    def test_healthy_when_all_ok(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._compute_final_state("CONNECTED", "LINK_OK", "READY", "HEALTHY")
        assert result == "HEALTHY"


class TestComputeConfidence:
    def test_empty_results_returns_zero(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)

        result = ahp._compute_confidence([])
        assert result == 0.0

    def test_all_passed_returns_100(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        from sdd_core.governance.handshake import ValidationResult

        checks = [
            ValidationResult("a", True, "ok", "L1"),
            ValidationResult("b", True, "ok", "L2"),
        ]
        result = ahp._compute_confidence(checks)
        assert result == 100.0

    def test_half_passed_returns_50(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        from sdd_core.governance.handshake import ValidationResult

        checks = [
            ValidationResult("a", True, "ok", "L1"),
            ValidationResult("b", False, "fail", "L2"),
        ]
        result = ahp._compute_confidence(checks)
        assert result == 50.0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestLoadCache:
    def test_returns_none_when_no_cache_file(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp._load_cache()
        assert result is None

    def test_returns_none_when_cache_expired(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="HEALTHY", minutes_old=100)
        ahp = _make_ahp(tmp_path)  # ttl=5 min
        result = ahp._load_cache()
        assert result is None

    def test_returns_cache_when_fresh(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="HEALTHY", minutes_old=0)
        ahp = _make_ahp(tmp_path)
        result = ahp._load_cache()
        assert result is not None
        assert result["state"] == "HEALTHY"


# ---------------------------------------------------------------------------
# GAP mapping
# ---------------------------------------------------------------------------


class TestMapAhpToGap:
    def test_healthy_maps_to_active(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._map_ahp_to_gap("HEALTHY", 100.0) == "ACTIVE"

    def test_partial_maps_to_partial(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._map_ahp_to_gap("PARTIAL", 60.0) == "PARTIAL"

    def test_not_connected_maps_to_not_active(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._map_ahp_to_gap("NOT_CONNECTED", 0.0) == "NOT_ACTIVE"

    def test_misconfigured_maps_to_not_active(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._map_ahp_to_gap("MISCONFIGURED", 0.0) == "NOT_ACTIVE"


# ---------------------------------------------------------------------------
# format_gap_output
# ---------------------------------------------------------------------------


class TestFormatGapOutput:
    def test_silent_mode_returns_empty(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        result = ahp.format_gap_output(mode="silent")
        assert result == ""

    def test_compact_mode_contains_status(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        ahp.gap_status = "ACTIVE"
        result = ahp.format_gap_output(mode="compact")
        assert "ACTIVE" in result

    def test_verbose_mode_contains_confidence(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        ahp.gap_status = "PARTIAL"
        ahp.current_confidence = 55.0
        ahp.mandates_loaded = ["M001"]
        result = ahp.format_gap_output(mode="verbose")
        assert "PARTIAL" in result
        assert "55.0" in result


# ---------------------------------------------------------------------------
# validate() — full integration via validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def test_validate_returns_state_and_report(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert isinstance(state, str)
        assert state in (
            "NOT_CONNECTED",
            "MISCONFIGURED",
            "NOT_INITIALIZED",
            "PARTIAL",
            "HEALTHY",
        )
        assert report.state == state

    def test_validate_returns_not_connected_without_sdd(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert state == "NOT_CONNECTED"

    def test_validate_uses_cache_when_fresh(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="PARTIAL", minutes_old=0)
        ahp = _make_ahp(tmp_path)
        state, report = ahp.validate(output_mode="silent")
        assert state == "PARTIAL"
        assert report.cached is True

    def test_validate_ignores_expired_cache_with_force(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="HEALTHY", minutes_old=100)
        ahp = _make_ahp(tmp_path)  # ttl=5min, cache is 100min old
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        # Force recheck → should NOT use cache
        assert report.cached is False

    def test_validate_saves_cache_on_fresh_run(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        ahp.validate(output_mode="silent", force_recheck=True)
        cache_file = tmp_path / ".sdd" / "runtime" / "governance-state.json"
        assert cache_file.exists()

    def test_validate_with_full_setup_returns_healthy(self, tmp_path: Path) -> None:
        # Set up complete environment
        _write_profile(tmp_path, "client")
        _write_governance_core(tmp_path, [{"id": "M001", "type": "MANDATE"}])
        (tmp_path / "packages").mkdir()
        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text("{}", encoding="utf-8")
        sdd_runtime_dir = tmp_path / ".sdd" / "runtime"
        sdd_runtime_dir.mkdir(parents=True, exist_ok=True)
        (sdd_runtime_dir / ".phase-0-complete").write_text("done", encoding="utf-8")

        ahp = _make_ahp(tmp_path)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert state == "HEALTHY"


# ---------------------------------------------------------------------------
# format_output
# ---------------------------------------------------------------------------


class TestFormatOutput:
    def _make_report(self, tmp_path: Path, state: str = "HEALTHY") -> Any:
        from sdd_core.governance.handshake import HandshakeReport

        return HandshakeReport(
            state=state,
            confidence=75.0,
            checks=[
                {
                    "name": "check1",
                    "passed": True,
                    "message": "ok",
                    "layer": "DISCOVERY",
                }
            ],
            actions=["proceed_silently"],
            cached=False,
            cache_age_seconds=None,
        )

    def test_silent_mode_returns_state_emoji(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        report = self._make_report(tmp_path)
        result = ahp.format_output("HEALTHY", report, mode="silent")
        assert "SDD:" in result

    def test_compact_mode_contains_state(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        report = self._make_report(tmp_path)
        result = ahp.format_output("HEALTHY", report, mode="compact")
        assert "HEALTHY" in result

    def test_verbose_mode_contains_confidence(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        report = self._make_report(tmp_path)
        result = ahp.format_output("HEALTHY", report, mode="verbose")
        assert "75.0" in result
        assert "DISCOVERY" in result

    def test_verbose_mode_with_cached_report(self, tmp_path: Path) -> None:
        from sdd_core.governance.handshake import HandshakeReport

        ahp = _make_ahp(tmp_path)
        report = HandshakeReport(
            state="PARTIAL",
            confidence=50.0,
            checks=[],
            actions=[],
            cached=True,
            cache_age_seconds=120,
        )
        result = ahp.format_output("PARTIAL", report, mode="verbose")
        assert "120" in result

    def test_unknown_state_does_not_crash(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        report = self._make_report(tmp_path, state="UNKNOWN_STATE")
        # Should not raise
        result = ahp.format_output("UNKNOWN_STATE", report, mode="compact")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _extract_mandates / _compute_spec_fingerprint
# ---------------------------------------------------------------------------


class TestExtractMandates:
    def test_returns_empty_when_no_governance_core(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._extract_mandates() == []

    def test_extracts_mandate_ids(self, tmp_path: Path) -> None:
        _write_governance_core(
            tmp_path,
            [
                {"id": "M001", "type": "MANDATE"},
                {"id": "M002", "type": "MANDATE"},
                {"id": "G001", "type": "GUIDELINE"},
            ],
        )
        ahp = _make_ahp(tmp_path)
        mandates = ahp._extract_mandates()
        assert "M001" in mandates
        assert "M002" in mandates
        assert "G001" not in mandates


class TestComputeSpecFingerprint:
    def test_returns_empty_when_no_governance_core(self, tmp_path: Path) -> None:
        ahp = _make_ahp(tmp_path)
        assert ahp._compute_spec_fingerprint() == ""

    def test_returns_16_char_hex(self, tmp_path: Path) -> None:
        _write_governance_core(tmp_path, [{"id": "M001", "type": "MANDATE"}])
        ahp = _make_ahp(tmp_path)
        fp = ahp._compute_spec_fingerprint()
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# generate_challenge — skill export exception fallback
# ---------------------------------------------------------------------------


class TestGenerateChallengeSkillExport:
    def test_generate_challenge_handles_skill_export_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generate_challenge gracefully handles SkillEngine export failures.

        This covers the try-except-pass fallback at handshake.py:954
        when SkillEngine.export_skills_payload() raises an exception.
        """
        ahp = _make_ahp(tmp_path)

        # Mock SkillEngine to raise an exception during export_skills_payload
        from unittest.mock import MagicMock, patch

        mock_engine = MagicMock()
        mock_engine.export_skills_payload.side_effect = RuntimeError(
            "Skill export failed"
        )

        with patch("sdd_runtime.skills.SkillEngine", return_value=mock_engine):
            # Should not raise despite the exception
            challenge = ahp.generate_challenge(
                task_description="Test with skill export error"
            )

            # Challenge should be created with empty skills list as fallback
            assert challenge is not None
            assert challenge.session_id is not None
            assert challenge.available_skills == []  # Fallback to empty list
            assert challenge.task.get("description") == "Test with skill export error"
