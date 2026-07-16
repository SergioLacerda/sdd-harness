from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
RELEASE_DRY_RUN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-dry-run.yml"


def _load_workflow(path: Path) -> dict:
    # YAML parses the bare `on:` workflow key as boolean True; force text keys.
    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_constructor(
        "tag:yaml.org,2002:bool",
        lambda loader, node: loader.construct_scalar(node),
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


def _jobs(workflow: dict) -> dict:
    return workflow["jobs"]


def _step_run_block(steps: list[dict], name: str) -> str:
    step = next(step for step in steps if step.get("name") == name)
    return step.get("run", "")


def test_release_workflow_has_windows_install_smoke_lane() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    jobs = _jobs(workflow)
    assert "release-install-smoke" in jobs

    smoke = jobs["release-install-smoke"]
    matrix_os = smoke["strategy"]["matrix"]["os"]
    assert "windows-latest" in matrix_os
    assert "ubuntu-latest" in matrix_os


def test_release_workflow_is_tag_driven_and_accepts_uppercase_v() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    tags = workflow["on"]["push"]["tags"]
    assert "v*.*.*" in tags
    assert "V*.*.*" in tags

    validate_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["validate"]["steps"]
    )
    assert "^[vV][0-9]+" in validate_steps
    assert "setuptools_scm" not in validate_steps
    assert "tools/release/resolve_vcs_version.py" in validate_steps


def test_release_build_syncs_versions_from_git_tag() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    build_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["build"]["steps"]
    )
    assert 'VERSION="${VERSION#V}"' in build_steps
    assert "tools/release/sync_versions.py" in build_steps
    assert "steps.version.outputs.tag" in build_steps


def test_release_verify_step_checks_sdd_cli_via_built_wheel() -> None:
    """sdd_cli is now dynamically versioned (hatch-vcs) and has no static
    `version = "..."` line for the verify step to grep. The verify step must
    skip dynamic-version packages instead of failing on them, and the actual
    sdd_cli version must be confirmed after the build, via the built wheel
    filename."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    verify_step = _step_run_block(build_steps, "Verify all package versions match tag")
    build_step = _step_run_block(build_steps, "Build packages")

    assert "dynamic" in verify_step
    assert "version" in verify_step
    assert "dist/sdd_cli-" in build_step


def test_release_dry_run_syncs_versions_from_git_tag() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    dry_run_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["dry-run"]["steps"]
    )
    assert "^[vV][0-9]+" in dry_run_steps
    assert 'VERSION="${VERSION#V}"' in dry_run_steps
    assert 'tools/release/sync_versions.py "$TAG"' in dry_run_steps


def test_release_workflows_use_canonical_governance_compile_command() -> None:
    workflows = [
        (RELEASE_WORKFLOW, "build"),
        (RELEASE_DRY_RUN_WORKFLOW, "dry-run"),
    ]

    for path, job_name in workflows:
        workflow = _load_workflow(path)
        steps = "\n".join(
            step.get("run", "") for step in _jobs(workflow)[job_name]["steps"]
        )
        assert "uv run python -m sdd_cli governance compile --profile client" in steps
        assert "uv run python -m sdd_cli compile" not in steps
        assert "cp generated/client/build/governance-core.json" in steps
        assert "mkdir -p generated/client/build/final-template/.sdd" in steps


def test_release_workflow_smoke_install_uses_local_dist_only() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    smoke = _jobs(workflow)["release-install-smoke"]
    install_steps = "\n".join(
        step.get("run", "") for step in smoke["steps"] if "run" in step
    )
    assert "--no-index" in install_steps
    assert "--find-links dist" in install_steps


def test_release_workflows_build_cross_platform_runtime_wheelhouse() -> None:
    workflows = [
        (RELEASE_WORKFLOW, "build"),
        (RELEASE_DRY_RUN_WORKFLOW, "dry-run"),
    ]

    for path, job_name in workflows:
        workflow = _load_workflow(path)
        steps = "\n".join(
            step.get("run", "") for step in _jobs(workflow)[job_name]["steps"]
        )
        assert "--platform manylinux2014_x86_64" in steps
        assert "--platform win_amd64" in steps
        assert "--python-version 312" in steps
        assert "--find-links dist" in steps
        assert "dist/sdd_cli-*.whl" in steps
        assert '"colorama>=0.4.6"' in steps


def test_release_job_depends_on_install_smoke() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    jobs = _jobs(workflow)
    assert jobs["release"]["needs"] == "release-install-smoke"


def test_release_dry_run_has_windows_install_smoke_lane() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    jobs = _jobs(workflow)
    assert "release-install-smoke" in jobs

    smoke = jobs["release-install-smoke"]
    matrix_os = smoke["strategy"]["matrix"]["os"]
    assert "windows-latest" in matrix_os
    assert "ubuntu-latest" in matrix_os
    assert smoke["needs"] == "dry-run"


def test_release_workflow_permissions_are_job_scoped() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)

    top_level_permissions = workflow.get("permissions") or {}
    assert top_level_permissions.get("contents") != "write"
    assert top_level_permissions.get("id-token") != "write"

    jobs = _jobs(workflow)
    for job_name in ("validate", "build", "release-install-smoke"):
        job_permissions = jobs[job_name].get("permissions") or {}
        assert job_permissions.get("contents") != "write"
        assert job_permissions.get("id-token") != "write"

    assert jobs["release"]["permissions"]["contents"] == "write"
    assert jobs["provenance"]["permissions"]["id-token"] == "write"


def test_release_signing_step_is_blocking() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    release_steps = _jobs(workflow)["release"]["steps"]
    sign_step = next(
        step
        for step in release_steps
        if "sigstore/gh-action-sigstore-python" in step.get("uses", "")
    )
    assert "continue-on-error" not in sign_step


def test_release_signing_uses_real_sigstore_action_with_oidc_permission() -> None:
    """The signing action must be a real, resolvable action (not a placeholder),
    and the job must request the OIDC token it needs for keyless signing."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    release_job = _jobs(workflow)["release"]
    sign_step = next(
        step
        for step in release_job["steps"]
        if "sigstore/gh-action-sigstore-python" in step.get("uses", "")
    )
    assert "@5b79a39c381910c090341a2c9b0bf022c8b387e1" in sign_step["uses"]
    assert release_job["permissions"]["id-token"] == "write"
