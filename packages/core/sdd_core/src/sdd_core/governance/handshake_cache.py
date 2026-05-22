"""Handshake cache management and persistence."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


class HandshakeCache:
    """Manages cache and persistence for handshake state."""

    # TTL constants (D11): profile-scoped cache validity
    _TTL_CLIENT_MINUTES: int = 30
    _TTL_MASTER_MINUTES: int = 480  # 8 hours

    def __init__(
        self,
        cache_file: Path,
        cache_dir: Path,
        cache_ttl: timedelta,
        project_root: Path,
        agent_id: str,
    ):
        """Initialize cache manager."""
        self.cache_file = cache_file
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.project_root = project_root
        self.agent_id = agent_id
        self.mandates_loaded: list[str] = []
        self.spec_fingerprint: str = ""
        self.gap_status: str = ""
        self.skill_profile: str = "default"

    def load_cache(self) -> dict[str, Any] | None:
        """Load cached state if still valid."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                cache = cast(dict[str, Any], json.load(f))

            last_check = datetime.fromisoformat(cache.get("last_check", ""))
            if (datetime.now() - last_check) < self.cache_ttl:
                return cache
        except Exception as exc:
            logger.warning("Failed to load AHP cache: %s", exc)

        return None

    def extract_governance_core(self) -> dict[str, Any] | None:
        """Load governance-core.json to extract mandates and fingerprint."""
        candidates = [
            self.project_root
            / "generated"
            / "client"
            / "compiled"
            / "governance-core.json",
            self.project_root
            / "generated"
            / "master"
            / "compiled"
            / "governance-core.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        return cast(dict[str, Any], json.load(f))
                except Exception as exc:
                    logger.warning(
                        "Failed to load governance-core.json at %s: %s", candidate, exc
                    )
        return None

    def extract_mandates(self) -> list[str]:
        """Extract MANDATE IDs from governance-core.json."""
        governance_core = self.extract_governance_core()
        if not governance_core:
            return []

        return sorted(
            item["id"]
            for item in governance_core.get("items", [])
            if (
                item.get("type") == "MANDATE"
                or item.get("metadata", {}).get("type") == "MANDATE"
            )
            and "id" in item
        )

    def compute_spec_fingerprint(self) -> str:
        """Compute SHA-256 fingerprint of governance spec."""
        governance_core = self.extract_governance_core()
        if not governance_core:
            return ""

        try:
            clean = {
                k: v
                for k, v in governance_core.items()
                if k not in {"_signature", "fingerprint"}
            }
            serialized = json.dumps(clean, sort_keys=True, ensure_ascii=True)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        except Exception as exc:
            logger.warning("Failed to compute spec fingerprint: %s", exc)
            return ""

    def map_ahp_to_gap(self, ahp_state: str, confidence: float) -> str:
        """Map 5-state AHP to 3-state GAP status."""
        if ahp_state == "HEALTHY":
            return "ACTIVE"
        if ahp_state == "PARTIAL":
            return "PARTIAL"
        return "NOT_ACTIVE"

    def save_cache(
        self,
        state: str,
        checks: list[dict[str, Any]],
        confidence: float,
        skill_profile: str,
    ) -> None:
        """Save state to persistent cache with GAP fields."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            mandates_loaded = self.extract_mandates()
            spec_fingerprint = self.compute_spec_fingerprint()
            gap_status = self.map_ahp_to_gap(state, confidence)

            self.mandates_loaded = mandates_loaded
            self.spec_fingerprint = spec_fingerprint
            self.gap_status = gap_status
            self.skill_profile = skill_profile

            cache = {
                "gap_version": "1.0",
                "status": gap_status,
                "agent_id": self.agent_id,
                "spec_fingerprint": spec_fingerprint,
                "mandates_loaded": mandates_loaded,
                "skill_profile": skill_profile,
                "confidence": round(confidence, 1),
                "last_check": datetime.now().isoformat(),
                "state": state,
                "checks": checks,
            }

            if self.cache_file.exists():
                try:
                    existing = json.loads(self.cache_file.read_text(encoding="utf-8"))
                    for key, value in existing.items():
                        if key not in cache:
                            cache[key] = value
                except Exception:
                    logger.debug(
                        "Could not merge existing AHP cache state", exc_info=True
                    )

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save AHP cache: %s", exc)

    def extract_skill_profile(self) -> str:
        """Best-effort extraction of active profile from canonical .sdd/profile."""
        try:
            import configparser

            profile_path = self.project_root / ".sdd" / "profile"
            if not profile_path.exists():
                return "default"
            parser = configparser.ConfigParser()
            parser.read(profile_path)
            profile_type = parser.get("sdd", "type", fallback="").strip().lower()
            return profile_type if profile_type else "default"
        except Exception:
            return "default"

    def resolve_ttl_minutes(self) -> int:
        """Determine cache TTL based on workspace profile type (D11).

        Resolution order:
        1. pyproject.toml [tool.sdd.runtime] handshake_ttl_minutes
        2. Workspace profile type fallback (master=480, client=30)
        3. Safe default (30)

        Returns:
            Configured minutes or profile-scoped default.
        """
        # 1. Try pyproject.toml configuration
        try:
            pyproject_path = self.project_root / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                with open(pyproject_path, "rb") as f:
                    config = tomllib.load(f)
                sdd_runtime = config.get("tool", {}).get("sdd", {}).get("runtime", {})
                if "handshake_ttl_minutes" in sdd_runtime:
                    return int(sdd_runtime["handshake_ttl_minutes"])
        except (OSError, ValueError, KeyError, TypeError):  # nosec B110 — best-effort config parsing
            logger.debug(
                "Could not parse handshake_ttl_minutes from pyproject.toml",
                exc_info=True,
            )

        # 2. Fallback to profile-scoped defaults
        try:
            import configparser

            profile_path = self.project_root / ".sdd" / "profile"
            if profile_path.exists():
                parser = configparser.ConfigParser()
                parser.read(profile_path)
                profile_type = parser.get("sdd", "type", fallback="").strip().lower()
                if profile_type == "master":
                    return self._TTL_MASTER_MINUTES
        except Exception:
            logger.debug("Could not read workspace profile for TTL", exc_info=True)
        return self._TTL_CLIENT_MINUTES
