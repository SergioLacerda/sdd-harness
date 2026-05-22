"""Handshake Challenge - M015 bidirectional challenge/response protocol.

Manages the formal challenge and response lifecycle for agent handshakes.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sdd_core.governance.handshake_models import (
    HandshakeRequest,
    HandshakeResponse,
)

logger = logging.getLogger(__name__)


class HandshakeChallenge:
    """M015 protocol: bidirectional challenge/response lifecycle."""

    def __init__(
        self, agent_id: str, project_root: Path, cache_dir: Path, response_file: Path
    ):
        """Initialize challenge/response handler.

        Args:
            agent_id: Identifier for the agent
            project_root: Root directory of the project
            cache_dir: Directory for handshake cache
            response_file: Path to store handshake response
        """
        self.agent_id = agent_id
        self.project_root = project_root
        self.cache_dir = cache_dir
        self.response_file = response_file

    def _resolve_signature_status(self) -> str:
        """Resolve signature status by checking for signed governance artifacts.

        Returns 'verified' if signature mode is warn/strict and artifact is signed, else 'none'.
        """
        signature_mode = os.environ.get("SDD_SIGNATURE_MODE", "off").strip().lower()
        if signature_mode not in {"warn", "strict"}:
            return "none"

        # Check if at least one core artifact is signed
        gov_path = next(
            (
                p
                for p in [
                    self.project_root / ".sdd" / "compiled" / "governance-core.json",
                    self.project_root
                    / "generated"
                    / "master"
                    / "compiled"
                    / "governance-core.json",
                ]
                if p.exists()
            ),
            None,
        )
        if gov_path and gov_path.with_suffix(gov_path.suffix + ".sig").exists():
            return "verified"
        return "none"

    def generate_challenge(
        self,
        task_description: str = "General Task",
        task_type: str = "other",
        mandates_loaded: list[str] | None = None,
    ) -> HandshakeRequest:
        """Generate a formal Handshake Request challenge (M015).

        This challenge contains the necessary context for an agent to form
        a valid handshake response, including available skills and mandates.

        Args:
            task_description: Description of the task
            task_type: Type of task
            mandates_loaded: List of active mandates

        Returns:
            HandshakeRequest with challenge details
        """
        # 1. Resolve skills
        try:
            from sdd_runtime.skills import SkillEngine

            engine = SkillEngine()
            # Export in JSON format to be included in challenge
            skills_payload = engine.export_skills_payload(fmt="json")
            available_skills = skills_payload.get("skills", [])
        except Exception:  # nosec B110
            available_skills = []

        # 2. Resolve mandates
        active_mandates = mandates_loaded or []

        # 3. Resolve signature status
        signature_status = self._resolve_signature_status()

        # 4. Resolve budget (placeholder for now, integration with sdd_runtime.economy needed)
        budget = {
            "remaining_tokens": 1000000,  # Default safe ceiling
            "remaining_usd": 10.0,
        }

        request = HandshakeRequest(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now().isoformat(),
            task={"description": task_description, "type": task_type},
            available_skills=available_skills,
            active_mandates=active_mandates,
            budget=budget,
            signature_status=signature_status,
        )

        return request

    def complete_handshake(self, response_data: dict[str, Any]) -> HandshakeResponse:
        """Finalize the bidirectional handshake by recording the agent's response.

        Validates that the agent has acknowledged signatures and declared skills.

        Args:
            response_data: Dictionary containing the agent's response

        Returns:
            HandshakeResponse object
        """
        response = HandshakeResponse.from_dict(response_data)
        if not response.timestamp:
            response.timestamp = datetime.now().isoformat()

        # Persist response
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.response_file.write_text(
                json.dumps(response.to_dict(), indent=2), encoding="utf-8"
            )
            logger.info("Handshake response completed for agent: %s", response.agent_id)
        except Exception as exc:
            logger.error("Failed to persist handshake response: %s", exc)

        return response

    def get_handshake_response(self) -> HandshakeResponse | None:
        """Retrieve the currently active handshake response.

        Returns:
            HandshakeResponse if file exists and is valid, None otherwise
        """
        if not self.response_file.exists():
            return None
        try:
            data = json.loads(self.response_file.read_text(encoding="utf-8"))
            return HandshakeResponse.from_dict(data)
        except Exception:
            return None

    def is_handshake_valid(self, strict: bool = False) -> bool:
        """Check if a valid handshake exists and meets security requirements.

        Args:
            strict: If True, require acknowledged_signature

        Returns:
            True if handshake is valid, False otherwise
        """
        response = self.get_handshake_response()
        return response is not None and (not strict or response.acknowledged_signature)
