"""Tests for HandshakeChallenge module (M015 bidirectional protocol)."""

import json
from unittest.mock import patch

from sdd_core.governance.handshake_challenge import HandshakeChallenge
from sdd_core.governance.handshake_models import HandshakeRequest


class TestGenerateChallenge:
    """Test HandshakeChallenge.generate_challenge() method."""

    def test_generate_challenge_returns_handshake_request(self, tmp_path):
        """Verify generate_challenge returns a HandshakeRequest object."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge(
            task_description="Test Task",
            task_type="test",
            mandates_loaded=["mandate1", "mandate2"],
        )

        assert isinstance(request, HandshakeRequest)
        assert request.session_id.startswith("sess_")
        assert request.task["description"] == "Test Task"
        assert request.task["type"] == "test"
        assert request.active_mandates == ["mandate1", "mandate2"]

    def test_generate_challenge_includes_signature_status(self, tmp_path):
        """Verify generate_challenge includes signature_status field."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge()

        assert hasattr(request, "signature_status")
        assert request.signature_status in {"verified", "none"}

    def test_generate_challenge_skill_engine_import_failure_non_fatal(self, tmp_path):
        """Verify generate_challenge handles missing SkillEngine gracefully."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        with patch(
            "sdd_runtime.skills.SkillEngine", side_effect=ImportError("No module")
        ):
            request = challenge.generate_challenge()

        assert isinstance(request, HandshakeRequest)
        assert request.available_skills == []  # Empty when SkillEngine fails


class TestCompleteHandshake:
    """Test HandshakeChallenge.complete_handshake() method."""

    def test_complete_handshake_writes_response_file(self, tmp_path):
        """Verify complete_handshake persists response to file."""
        cache_dir = tmp_path / ".sdd" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        response_data = {
            "agent_id": "claude-agent",
            "understood_mandates": ["m1", "m2"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": True,
        }
        challenge.complete_handshake(response_data)

        assert response_file.exists()
        written_data = json.loads(response_file.read_text(encoding="utf-8"))
        assert written_data["agent_id"] == "claude-agent"
        assert written_data["skills_to_use"] == ["skill1"]

    def test_complete_handshake_fills_missing_timestamp(self, tmp_path):
        """Verify complete_handshake adds timestamp if missing."""
        cache_dir = tmp_path / ".sdd" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        response_data = {
            "agent_id": "claude-agent",
            "understood_mandates": [],
            "skills_to_use": [],
            "acknowledged_signature": False,
            "timestamp": "",
        }

        result = challenge.complete_handshake(response_data)

        assert result.timestamp != ""
        written_data = json.loads(response_file.read_text(encoding="utf-8"))
        assert written_data["timestamp"] != ""


class TestHandshakeResponse:
    """Test HandshakeChallenge.get_handshake_response() and is_handshake_valid()."""

    def test_get_handshake_response_returns_none_when_missing(self, tmp_path):
        """Verify get_handshake_response returns None when response file doesn't exist."""
        cache_dir = tmp_path / ".sdd" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        result = challenge.get_handshake_response()

        assert result is None

    def test_is_handshake_valid_returns_false_when_missing(self, tmp_path):
        """Verify is_handshake_valid returns False when response file doesn't exist."""
        cache_dir = tmp_path / ".sdd" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        result = challenge.is_handshake_valid()

        assert result is False


class TestSignatureStatus:
    """Test HandshakeChallenge._resolve_signature_status() method."""

    def test_signature_status_returns_none_when_no_env_var(self, tmp_path, monkeypatch):
        """Verify _resolve_signature_status returns 'none' when SDD_SIGNATURE_MODE not set."""
        monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        status = challenge._resolve_signature_status()

        assert status == "none"

    def test_signature_status_returns_none_when_no_sig_files(
        self, tmp_path, monkeypatch
    ):
        """Verify _resolve_signature_status returns 'none' when no .sig files exist."""
        monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        status = challenge._resolve_signature_status()

        assert status == "none"

    def test_signature_status_returns_verified_when_sig_exists(
        self, tmp_path, monkeypatch
    ):
        """Verify _resolve_signature_status returns 'verified' when .sig file exists."""
        monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")

        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True, exist_ok=True)

        gov_file = compiled_dir / "governance-core.json"
        gov_file.write_text("{}", encoding="utf-8")

        sig_file = gov_file.with_suffix(gov_file.suffix + ".sig")
        sig_file.write_text("signature", encoding="utf-8")

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".sdd" / "runtime",
            response_file=tmp_path / ".sdd" / "runtime" / "response.json",
        )

        status = challenge._resolve_signature_status()

        assert status == "verified"
