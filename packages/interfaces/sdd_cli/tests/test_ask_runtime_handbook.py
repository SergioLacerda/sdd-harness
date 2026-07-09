"""Tests for runtime handbook consultation in `sdd ask` snapshots."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from sdd_cli.commands._ask_backend._pipeline import build_governed_ask_snapshot


def _write_runtime_handbook(root: Path) -> None:
    handbook_dir = root / ".sdd" / "source" / "handbook"
    item_path = handbook_dir / "context-loading" / "context-flow.yaml"
    item_path.parent.mkdir(parents=True)
    item_path.write_text(
        yaml.safe_dump(
            {
                "id": "HBK-CONTEXT-LOADING",
                "title": "Context Flow",
                "source_doc": "docs/cognition/context-loading/context_flow.md",
                "mandate_refs": ["M003", "M005"],
                "task_types": ["planning", "implementation", "diagnosis"],
                "operation_phases": ["context_loading", "planning"],
                "load_policy": {"mode": "selective", "max_tokens": 700},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (handbook_dir / "index.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1",
                "items": [
                    {
                        "id": "HBK-CONTEXT-LOADING",
                        "title": "Context Flow",
                        "source_doc": "docs/cognition/context-loading/context_flow.md",
                        "runtime_doc": ".sdd/source/handbook/context-loading/context-flow.yaml",
                        "mandate_refs": ["M003", "M005"],
                        "task_types": ["planning", "implementation", "diagnosis"],
                        "operation_phases": ["context_loading", "planning"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_build_governed_ask_snapshot_adds_runtime_handbook_match(
    tmp_path: Path,
) -> None:
    _write_runtime_handbook(tmp_path)
    with (
        patch("sdd_cli.commands._ask_backend._guard_handshake"),
        patch(
            "sdd_cli.commands._ask_backend._load_compiled_governance",
            return_value=("compiled", "fp-1", 16, True, False, "", "verified"),
        ),
        patch(
            "sdd_cli.commands._ask_backend._runtime_drift_check",
            return_value=False,
        ),
        patch(
            "sdd_cli.commands._ask_backend._root_seed_drift_check",
            return_value=False,
        ),
        patch(
            "sdd_cli.commands._ask_backend._pipeline._collect_learning_signals",
            return_value={},
        ),
    ):
        snapshot = build_governed_ask_snapshot(
            query="plan implementation",
            skill=None,
            organize_used=False,
            workspace_root=tmp_path,
        )

    lookup = snapshot["handbook_lookup"]
    assert lookup["status"] == "matched"
    assert lookup["diagnostic"] == "handbook_match=1"
    assert lookup["matches"][0]["id"] == "HBK-CONTEXT-LOADING"
