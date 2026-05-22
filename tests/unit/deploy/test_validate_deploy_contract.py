from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path("tools/deploy/validate_deploy_contract.py")
    spec = importlib.util.spec_from_file_location("validate_deploy_contract", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(seed: str) -> str:
    return f"sha256:{seed * 64}"[:71]


def test_contract_success_default_policy() -> None:
    mod = _load_module()
    result = mod.validate_contract(
        target_env="staging",
        mode="contract",
        image_digest=_digest("a"),
        rollback_to="previous",
        canary_policy="10,25,50,100",
        enable_real_deploy=False,
    )
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["canary_steps"] == (10, 25, 50, 100)


def test_invalid_digest_blocks_contract() -> None:
    mod = _load_module()
    result = mod.validate_contract(
        target_env="staging",
        mode="contract",
        image_digest="sha256:deadbeef",
        rollback_to="previous",
        canary_policy="10,25,50,100",
        enable_real_deploy=False,
    )
    assert result["ok"] is False
    assert any("image_digest" in msg for msg in result["errors"])


def test_invalid_canary_blocks_contract() -> None:
    mod = _load_module()
    result = mod.validate_contract(
        target_env="production",
        mode="contract",
        image_digest=_digest("b"),
        rollback_to="previous",
        canary_policy="10,10,100",
        enable_real_deploy=False,
    )
    assert result["ok"] is False
    assert any("canary_policy" in msg for msg in result["errors"])


def test_real_mode_requires_flag() -> None:
    mod = _load_module()
    result = mod.validate_contract(
        target_env="production",
        mode="real",
        image_digest=_digest("c"),
        rollback_to=_digest("d"),
        canary_policy="10,25,50,100",
        enable_real_deploy=False,
    )
    assert result["ok"] is False
    assert any("ENABLE_REAL_DEPLOY" in msg for msg in result["errors"])


def test_real_mode_allowed_with_flag() -> None:
    mod = _load_module()
    result = mod.validate_contract(
        target_env="production",
        mode="real",
        image_digest=_digest("e"),
        rollback_to=_digest("f"),
        canary_policy="10,25,50,100",
        enable_real_deploy=True,
    )
    assert result["ok"] is True
