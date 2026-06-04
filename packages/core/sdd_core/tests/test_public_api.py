"""Tests for the sdd_core package public API boundary."""

from __future__ import annotations

import importlib

import pytest

import sdd_core

pytestmark = pytest.mark.unit


def test_public_api_lazy_exports_resolve() -> None:
    assert (
        sdd_core.DeploymentManager
        is importlib.import_module("sdd_core.deployment_manager").DeploymentManager
    )
    assert (
        sdd_core.GovernanceOrchestrator
        is importlib.import_module(
            "sdd_core.governance_orchestrator"
        ).GovernanceOrchestrator
    )


def test_public_api_missing_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        sdd_core.__getattr__("missing")
