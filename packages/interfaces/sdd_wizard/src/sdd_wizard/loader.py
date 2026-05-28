"""
SDD v3.0 Wizard - Load and deserialize compiled artifacts
"""

import json
from pathlib import Path
from typing import Any, cast

from sdd_core.utils.environment import get_sdd_paths


class ArtifactLoader:
    """Load all artifacts needed for wizard orchestration"""

    def __init__(self, repo_root: Path | None = None):
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths

        # Use generated docs-meta artifacts as source of truth for wizard input.
        self.source_dir = paths.get("docs_meta", paths["client_build"] / "docs-meta")
        self.master_compiled = paths["master_compiled"]
        self.client_compiled = paths["client_compiled"]

    def load_source_mandate(self) -> str:
        """Load SOURCE mandate.spec (text DSL)"""
        mandate_file = self.source_dir / "mandate.spec"
        if not mandate_file.exists():
            raise FileNotFoundError(f"mandate.spec not found at {mandate_file}")
        return mandate_file.read_text(encoding="utf-8")

    def load_source_guidelines(self) -> str:
        """Load SOURCE guidelines.dsl (text DSL)"""
        guidelines_file = self.source_dir / "guidelines.dsl"
        if not guidelines_file.exists():
            raise FileNotFoundError(f"guidelines.dsl not found at {guidelines_file}")
        return guidelines_file.read_text(encoding="utf-8")

    def load_compiled_mandate(self) -> dict[str, Any]:
        """Load COMPILED governance core (JSON or msgpack)"""
        # Standardized path: master_compiled/governance-core.compiled.msgpack
        mandate_msgpack = self.master_compiled / "governance-core.compiled.msgpack"
        mandate_json = self.master_compiled / "governance-core.json"

        # Try .msgpack first (Framework priority)
        if mandate_msgpack.exists():
            # Use sdd_core.utils.loader if possible for binary parsing
            from sdd_core.utils.loader import GovernanceLoader

            loader = GovernanceLoader()
            return loader.load_compiled_binary(mandate_msgpack)

        # Try .json fallback
        if mandate_json.exists():
            return cast(
                dict[str, Any], json.loads(mandate_json.read_text(encoding="utf-8"))
            )

        raise FileNotFoundError(
            "Compiled governance core not found in standardized hierarchy.\n"
            "Run: sdd governance compile to regenerate. Expected at .sdd/compiled/\n"
        )

    def load_compiled_guidelines(self) -> dict[str, Any]:
        """Load COMPILED guidelines template (JSON or msgpack)"""
        guidelines_msgpack = (
            self.master_compiled / "governance-client-template.compiled.msgpack"
        )
        guidelines_json = self._resolve_metadata(
            self.master_compiled, "metadata-client-template.json"
        )

        # Try .msgpack first
        if guidelines_msgpack.exists():
            from sdd_core.utils.loader import GovernanceLoader

            loader = GovernanceLoader()
            return loader.load_compiled_binary(guidelines_msgpack)

        # Try .json fallback
        if guidelines_json.exists():
            return cast(
                dict[str, Any], json.loads(guidelines_json.read_text(encoding="utf-8"))
            )

        raise FileNotFoundError(
            "Compiled guidelines template not found in standardized hierarchy."
        )

    def load_metadata(self) -> dict[str, Any]:
        """Load metadata-core.json with audit trail"""
        metadata_file = self._resolve_metadata(
            self.master_compiled, "metadata-core.json"
        )
        if not metadata_file.exists():
            raise FileNotFoundError(f"metadata-core.json not found at {metadata_file}")

        return cast(
            dict[str, Any], json.loads(metadata_file.read_text(encoding="utf-8"))
        )

    def _resolve_metadata(self, base: Path, filename: str) -> Path:
        preferred = base / "audit" / filename
        if preferred.exists():
            return preferred
        return base / filename

    def load_all(self) -> dict[str, Any]:
        """Load all artifacts (for wizard orchestration)"""
        return {
            "source": {
                "mandate": self.load_source_mandate(),
                "guidelines": self.load_source_guidelines(),
            },
            "compiled": {
                "mandate": self.load_compiled_mandate(),
                "guidelines": self.load_compiled_guidelines(),
            },
            "metadata": self.load_metadata(),
        }


def load_artifacts_safe(
    repo_root: Path | None = None,
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Safely load all artifacts with error handling

    Returns:
        (success: bool, data: dict, errors: list)
    """
    loader = ArtifactLoader(repo_root)
    errors = []

    try:
        data = loader.load_all()
        return (True, data, [])
    except FileNotFoundError as e:
        errors.append(f"File not found: {e}")
        return (False, {}, errors)
    except json.JSONDecodeError as e:
        errors.append(f"JSON decode error: {e}")
        return (False, {}, errors)
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return (False, {}, errors)
