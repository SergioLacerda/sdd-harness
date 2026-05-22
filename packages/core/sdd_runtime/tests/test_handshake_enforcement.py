import json
from pathlib import Path

from sdd_runtime.skills import SkillEngine

from sdd_core.governance.handshake import AgentHandshakeProtocol


def test_skill_enforcement_blocks_unauthorized_skill(tmp_path: Path):
    # Setup temporary project root
    project_root = tmp_path
    ai_dir = project_root / ".sdd" / "runtime"
    ai_dir.mkdir(parents=True)

    # Create a handshake response that DOES NOT include 'sdd-diagnose'
    handshake_file = ai_dir / "handshake-response.json"
    response_data = {
        "agent_id": "test-agent",
        "understood_mandates": ["M001"],
        "skills_to_use": ["sdd-review-architecture"],  # 'sdd-diagnose' is missing
        "plan": {},
        "compliance_declaration": "test",
        "acknowledged_signature": True,
    }
    handshake_file.write_text(json.dumps(response_data), encoding="utf-8")

    engine = SkillEngine()

    # Execution should be blocked
    result = engine.run_skill("sdd-diagnose", project_root=project_root)

    assert result.policy_result == "unauthorized"
    assert "was not declared in the initial handshake" in result.reason
    assert result.exit_code == 1


def test_skill_enforcement_allows_authorized_skill(tmp_path: Path):
    # Setup temporary project root
    project_root = tmp_path
    ai_dir = project_root / ".sdd" / "runtime"
    ai_dir.mkdir(parents=True)

    # Create a handshake response that DOES include 'sdd-diagnose'
    handshake_file = ai_dir / "handshake-response.json"
    response_data = {
        "agent_id": "test-agent",
        "understood_mandates": ["M001"],
        "skills_to_use": ["sdd-diagnose"],
        "plan": {},
        "compliance_declaration": "test",
        "acknowledged_signature": True,
    }
    handshake_file.write_text(json.dumps(response_data), encoding="utf-8")

    engine = SkillEngine()

    # Execution should be allowed (policy_result will be 'executed' or 'fallback_cli' if tool missing)
    result = engine.run_skill("sdd-diagnose", project_root=project_root)

    assert result.policy_result != "unauthorized"


def test_handshake_challenge_generation():
    ahp = AgentHandshakeProtocol()
    challenge = ahp.generate_challenge(task_description="Unit Test")

    assert challenge.session_id is not None
    assert isinstance(challenge.active_mandates, list)
    assert all(
        isinstance(mandate_id, str) and mandate_id.startswith("M")
        for mandate_id in challenge.active_mandates
    )
    assert isinstance(challenge.available_skills, list)
    assert challenge.task.get("description") == "Unit Test"

    # Signature status is environment-dependent.
    assert challenge.signature_status in [
        "none",
        "valid",
        "invalid",
        "mixed",
        "verified",
    ]
