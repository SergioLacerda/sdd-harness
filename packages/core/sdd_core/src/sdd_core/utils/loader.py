"""Governance loading and template generation utilities."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import msgpack

from sdd_core.utils.environment import get_sdd_paths


class GovernanceLoader:
    """Load and manage governance artifacts at runtime"""

    def __init__(self, compiled_dir: str | None = None):
        """Initialize loader

        Args:
            compiled_dir: Path to compiled directory.
                         If None, uses standardized paths.
        """
        paths = get_sdd_paths()
        if compiled_dir is None:
            try:
                from sdd_core.utils.environment import resolve_profile

                active_profile = resolve_profile().type
                self.compiled_dir = (
                    paths["master_compiled"]
                    if active_profile == "master"
                    else paths["client_compiled"]
                )
            except Exception:
                self.compiled_dir = paths["master_compiled"]
        else:
            self.compiled_dir = Path(compiled_dir)

        self.packages_data: dict[str, Any] | None = None
        self._client_data: dict[str, Any] | None = None
        self.packages_metadata: dict[str, Any] | None = None
        self._client_metadata: dict[str, Any] | None = None
        # A2: track which format was actually loaded
        self._core_context_source: str = "none"  # "msgpack" | "json" | "none"

    def _require_core_data(self) -> dict[str, Any]:
        if self.packages_data is None:
            self.load_core()
        assert self.packages_data is not None
        return self.packages_data

    def _require_client_data(self) -> dict[str, Any]:
        if self._client_data is None:
            self.load_client()
        assert self._client_data is not None
        return self._client_data

    def _require_core_metadata(self) -> dict[str, Any]:
        if self.packages_metadata is None:
            self._load_metadata_only()
        assert self.packages_metadata is not None
        return self.packages_metadata

    def _require_client_metadata(self) -> dict[str, Any]:
        if self._client_metadata is None:
            self._load_metadata_only()
        assert self._client_metadata is not None
        return self._client_metadata

    def load_all(self) -> dict[str, Any]:
        """Load all governance artifacts"""
        core_data = self.load_core()
        client_data = self.load_client()

        if not self._validate_integrity():
            raise RuntimeError("Governance integrity validation failed")

        core_metadata = self._require_core_metadata()
        client_metadata = self._require_client_metadata()

        return {
            "status": "loaded",
            "core_items": len(core_data.get("items", [])),
            "client_items": len(client_data.get("items", [])),
            "core_fingerprint": core_metadata.get("fingerprint"),
            "client_fingerprint": client_metadata.get("fingerprint"),
            # A2: surface which format was used to load core governance
            "context_source": self._core_context_source,
        }

    def load_core(self) -> dict[str, Any]:
        """Load core governance (immutable)"""
        msgpack_file = self.compiled_dir / "governance-core.compiled.msgpack"
        metadata_file = self._resolve_existing_metadata_path("metadata-core.json")

        if not msgpack_file.exists():
            raise FileNotFoundError(f"Core msgpack not found: {msgpack_file}")

        with open(msgpack_file, "rb") as f:
            self.packages_data = msgpack.unpackb(f.read(), raw=False)

        with open(metadata_file, encoding="utf-8", errors="strict") as f:
            self.packages_metadata = json.load(f)

        self._core_context_source = "msgpack"
        return self.packages_data

    def load_client(self, client_dir: Path | None = None) -> dict[str, Any]:
        """Load client governance"""
        base_dir = client_dir or self.compiled_dir
        msgpack_file = base_dir / "governance-client-template.compiled.msgpack"
        metadata_file = self._resolve_existing_metadata_path(
            "metadata-client-template.json", base_dir
        )

        if not msgpack_file.exists() and client_dir:
            # Fall back to the default compiled_dir (profile-aware) if not in client_dir
            base_dir = self.compiled_dir
            msgpack_file = base_dir / "governance-client-template.compiled.msgpack"
            metadata_file = self._resolve_existing_metadata_path(
                "metadata-client-template.json", base_dir
            )

        if not msgpack_file.exists():
            raise FileNotFoundError(f"Client msgpack not found: {msgpack_file}")

        with open(msgpack_file, "rb") as f:
            self._client_data = msgpack.unpackb(f.read(), raw=False)

        with open(metadata_file, encoding="utf-8", errors="strict") as f:
            self._client_metadata = json.load(f)

        return self._client_data

    def get_all_items(self) -> list[dict[str, Any]]:
        """Get all governance items (core + client merged)"""
        core_items = cast(
            list[dict[str, Any]], self._require_core_data().get("items", [])
        )
        client_items = cast(
            list[dict[str, Any]], self._require_client_data().get("items", [])
        )
        return core_items + client_items

    def get_items_by_type(self, item_type: str) -> list[dict[str, Any]]:
        """Get items by type"""
        items = self.get_all_items()
        item_type_upper = item_type.upper()
        return [
            item for item in items if item.get("type", "").upper() == item_type_upper
        ]

    def load_compiled_binary(self, filepath: Path) -> dict[str, Any]:
        """Load compiled msgpack binary"""
        if not filepath.exists():
            raise FileNotFoundError(f"Binary file not found: {filepath}")

        with open(filepath, "rb") as f:
            return cast(dict[str, Any], msgpack.unpackb(f.read(), raw=False))

    def get_fingerprints(self) -> dict[str, str]:
        """Get core and client fingerprints"""
        return {
            "core": str(self._require_core_metadata().get("fingerprint", "")),
            "client": str(self._require_client_metadata().get("fingerprint", "")),
            "salt": str(self._require_client_metadata().get("fingerprint_salt", "")),
        }

    def _load_metadata_only(self) -> None:
        """Load only metadata"""
        with open(
            self._resolve_existing_metadata_path("metadata-core.json"),
            encoding="utf-8",
            errors="strict",
        ) as f:
            self.packages_metadata = json.load(f)
        with open(
            self._resolve_existing_metadata_path("metadata-client-template.json"),
            encoding="utf-8",
            errors="strict",
        ) as f:
            self._client_metadata = json.load(f)

    def _resolve_metadata_path(
        self, filename: str, base_dir: Path | None = None
    ) -> Path:
        """Resolve canonical metadata path in compiled/audit/."""
        root = base_dir or self.compiled_dir
        return root / "audit" / filename

    def _resolve_existing_metadata_path(
        self, filename: str, base_dir: Path | None = None
    ) -> Path:
        """Resolve existing metadata path with legacy root fallback."""
        canonical = self._resolve_metadata_path(filename, base_dir)
        if canonical.exists():
            return canonical
        root = base_dir or self.compiled_dir
        return root / filename

    def _validate_integrity(self) -> bool:
        """Validate governance integrity"""
        fps = self.get_fingerprints()

        checks = [
            fps["core"] != "",
            fps["client"] != "",
            (
                fps["core"] == fps["salt"] if fps["salt"] else True
            ),  # Allow empty salt if not present
            fps["core"] != fps["client"],
            len(self._require_core_data().get("items", [])) > 0,
        ]
        return all(checks)


class TemplateGenerator:
    """Generate customization templates from governance"""

    def __init__(self, loader: GovernanceLoader) -> None:
        self.loader = loader

    def generate_basic_template(self) -> dict[str, Any]:
        """Generate basic customization template"""
        client_items = self.loader.load_client().get("items", [])

        template = {
            "version": "3.0",
            "type": "customization-template",
            "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "customizations": self._prepare_items(client_items),
        }
        return template

    def _prepare_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": i.get("id"),
                "title": i.get("title"),
                "type": i.get("type"),
                "customizable": i.get("customizable", False),
            }
            for i in items
        ]
