from __future__ import annotations

import json
from pathlib import Path

from sdd_cli.services.ask_governance import (
    _compiled_candidates,
    load_compiled_governance,
)


def _mk_compiled_artifact(compiled_dir: Path) -> None:
    compiled_dir.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": "abcd1234ef", "mandates": [{"id": "M001"}]}
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_compiled_candidates_only_returns_active_dir(tmp_path: Path) -> None:
    active = tmp_path / "generated" / "client" / "compiled" / "active"
    candidates = _compiled_candidates(tmp_path, compiled_active_dir_fn=lambda _: active)
    assert candidates == [active]
    assert (tmp_path / ".sdd" / "compiled") not in candidates


def test_load_compiled_governance_does_not_use_legacy_extra_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "sdd_cli.services.ask_governance.load_governance_via_runtime",
        lambda *args, **kwargs: None,
    )
    active = tmp_path / "missing-active-dir"
    legacy = tmp_path / ".sdd" / "compiled"
    _mk_compiled_artifact(legacy)

    source, fingerprint, mandates_count, *_ = load_compiled_governance(
        tmp_path,
        compiled_active_dir_fn=lambda _: active,
    )
    assert source == "none"
    assert fingerprint == ""
    assert mandates_count == 0


def test_load_compiled_governance_reads_from_active_dir(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "sdd_cli.services.ask_governance.load_governance_via_runtime",
        lambda *args, **kwargs: None,
    )
    active = tmp_path / "generated" / "client" / "compiled" / "active"
    _mk_compiled_artifact(active)

    source, fingerprint, mandates_count, *_ = load_compiled_governance(
        tmp_path,
        compiled_active_dir_fn=lambda _: active,
    )
    assert source == "compiled"
    assert fingerprint
    assert mandates_count == 1
