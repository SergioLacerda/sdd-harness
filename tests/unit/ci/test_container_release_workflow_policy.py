from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTAINER_RELEASE_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "container-release.yml"
)


def _load_workflow(path: Path) -> dict:
    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_constructor(
        "tag:yaml.org,2002:bool",
        lambda loader, node: loader.construct_scalar(node),
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


def test_container_release_verifies_release_success_before_publishing() -> None:
    """container-release.yml can publish an image via manual workflow_dispatch
    independently of release.yml. Without a cross-check, that publish could
    target a tag whose release.yml build never succeeded. A GitHub Release only
    exists once release.yml's `release` job has completed, so checking for one
    is a reliable proxy for "the release build succeeded" — and it must run
    before any GHCR login/push/sign step."""
    workflow = _load_workflow(CONTAINER_RELEASE_WORKFLOW)
    steps = workflow["jobs"]["build-scan-sign-push"]["steps"]
    step_names = [step.get("name") for step in steps]
    assert "Verify a successful release.yml run exists for this tag" in step_names

    verify_index = step_names.index(
        "Verify a successful release.yml run exists for this tag"
    )
    login_index = step_names.index("Login to GHCR (retry)")
    assert verify_index < login_index, (
        "the release-success check must run before GHCR login/publish steps"
    )


def test_container_release_gate_only_applies_to_tag_publishes() -> None:
    """A workflow_dispatch publish from a branch (not a tag) has no
    corresponding release.yml run to check against by design — the gate must
    only fire for tag-triggered publishes, not silently block branch-based
    test image publishes."""
    workflow = _load_workflow(CONTAINER_RELEASE_WORKFLOW)
    steps = workflow["jobs"]["build-scan-sign-push"]["steps"]
    verify_step = next(
        step
        for step in steps
        if step.get("name") == "Verify a successful release.yml run exists for this tag"
    )
    assert "startsWith(github.ref, 'refs/tags/')" in verify_step["if"]
