"""Tests for sdd_cli.services.governance_scoring_output."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from sdd_cli.services.governance_scoring_output import (
    render_governance_adherence_output,
    render_governance_score_output,
    run_governance_adherence_cmd,
    run_governance_score,
    run_governance_score_cmd,
)
from sdd_core.utils.environment import ProfileContext, WorkspaceNotInitializedError


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestRenderGovernanceScoreOutput:
    def test_verbose_table_above_threshold(self) -> None:
        checks = [("check a", True, 50), ("check b", False, 50)]
        render_governance_score_output(
            checks=checks,
            final_score=50,
            threshold=50,
            verbose=True,
            console=_console(),
        )

    def test_non_verbose_above_threshold(self) -> None:
        render_governance_score_output(
            checks=[], final_score=80, threshold=50, verbose=False, console=_console()
        )

    def test_below_threshold_raises_exit(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            render_governance_score_output(
                checks=[],
                final_score=40,
                threshold=50,
                verbose=False,
                console=_console(),
            )
        assert exc_info.value.exit_code == 1


class TestRenderGovernanceAdherenceOutput:
    _RESULT = {
        "score": 80,
        "details": {
            "behavioral_score": 40,
            "allows": 10,
            "warns": 1,
            "blocks": 0,
            "structural_score": 25,
            "structural_status": "ok",
            "freshness_score": 15,
            "freshness_status": "fresh",
        },
    }

    def test_verbose_table_above_threshold(self) -> None:
        render_governance_adherence_output(
            result=self._RESULT,
            threshold=50,
            window=24,
            verbose=True,
            console=_console(),
        )

    def test_non_verbose_above_threshold(self) -> None:
        render_governance_adherence_output(
            result=self._RESULT,
            threshold=50,
            window=24,
            verbose=False,
            console=_console(),
        )

    def test_below_threshold_raises_exit(self) -> None:
        result = {**self._RESULT, "score": 10}
        with pytest.raises(typer.Exit) as exc_info:
            render_governance_adherence_output(
                result=result,
                threshold=50,
                window=24,
                verbose=False,
                console=_console(),
            )
        assert exc_info.value.exit_code == 1


class _FakeAHPReport:
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence


class _FakeAHP:
    def __init__(
        self, project_root: Path | None = None, cache_ttl_minutes: int | None = None
    ) -> None:
        self.project_root = project_root
        self._confidence = _AHP_CONFIDENCE

    def validate(self, output_mode: str = "silent", force_recheck: bool = False):
        return ("HEALTHY", _FakeAHPReport(confidence=self._confidence))


_AHP_CONFIDENCE = 80.0


class TestRunGovernanceScore:
    def test_all_checks_pass_with_artifact_fingerprint(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        fingerprint = "0123456789abcdef" + "extra"
        artifact.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash=fingerprint[:16],
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=profile_ctx
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=80, console=_console()
            )

        assert captured["final_score"] == 100
        assert all(passed for _, passed, _ in captured["checks"])

    def test_profile_not_initialized(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text(json.dumps({"fingerprint": "abc"}), encoding="utf-8")

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile",
                side_effect=WorkspaceNotInitializedError("not initialized"),
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label[".sdd/profile valid"] is False
        assert checks_by_label["core_hash matches artifact"] is False
        # profile (30) fails, artifacts (30) + AHP (20) pass => 50/100
        assert captured["final_score"] == 50

    def test_artifacts_missing(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()  # no governance-core.json written

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash="0123456789abcdef",
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=profile_ctx
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label["governance artifacts compiled"] is False
        assert checks_by_label["core_hash matches artifact"] is False
        # profile (30) + AHP (20) pass, artifacts (30) fails => 50/100
        assert captured["final_score"] == 50

    def test_low_ahp_confidence(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 30.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        fingerprint = "0123456789abcdef" + "extra"
        artifact.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash=fingerprint[:16],
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=profile_ctx
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        finally_label = next(
            label for label, _, _ in captured["checks"] if label.startswith("AHP")
        )
        assert "30.0%" in finally_label
        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert (
            checks_by_label[
                next(lbl for lbl in checks_by_label if lbl.startswith("AHP"))
            ]
            is False
        )
        # profile (30) + artifacts (30) + hash (20) pass, AHP (20) fails => 80/100
        assert captured["final_score"] == 80

    def test_hash_backward_compatibility(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        # No "fingerprint" key -> backward-compatibility branch computes sha256
        artifact_data = {"items": ["a", "b"]}
        artifact.write_text(json.dumps(artifact_data), encoding="utf-8")

        computed = hashlib.sha256(
            json.dumps(artifact_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash=computed,
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=profile_ctx
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label["core_hash matches artifact"] is True
        assert captured["final_score"] == 100

    def test_hash_check_exception_is_caught(self, tmp_path: Path) -> None:
        global _AHP_CONFIDENCE
        _AHP_CONFIDENCE = 80.0

        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text("not valid json", encoding="utf-8")

        profile_ctx = ProfileContext(
            type="client",
            name="test-ws",
            workspace_id="ws1",
            core_hash="0123456789abcdef",
            root=tmp_path,
        )

        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=profile_ctx
            ),
            patch(
                "sdd_cli.utils.sdd_authority.compiled_active_dir",
                return_value=compiled_dir,
            ),
            patch("sdd_core.governance.handshake.AgentHandshakeProtocol", _FakeAHP),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_score_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_score(
                ws_root=tmp_path, verbose=False, threshold=50, console=_console()
            )

        checks_by_label = {label: passed for label, passed, _ in captured["checks"]}
        assert checks_by_label["core_hash matches artifact"] is False


class TestRunGovernanceScoreCmd:
    def test_no_workspace_exits_1(self) -> None:
        with (
            patch(
                "sdd_cli.utils.sdd_authority.resolve_workspace_root", return_value=None
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_governance_score_cmd(verbose=False, threshold=50, console=_console())
        assert exc_info.value.exit_code == 1

    def test_resolves_workspace_and_delegates(self, tmp_path: Path) -> None:
        captured: dict = {}

        def _capture_run(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_cli.utils.sdd_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.utils.sdd_authority.enforce_path_policy",
                side_effect=lambda root, **_: root,
            ),
            patch(
                "sdd_cli.services.governance_scoring_output.run_governance_score",
                side_effect=_capture_run,
            ),
        ):
            run_governance_score_cmd(verbose=True, threshold=70, console=_console())

        assert captured["ws_root"] == tmp_path
        assert captured["verbose"] is True
        assert captured["threshold"] == 70


class TestRunGovernanceAdherenceCmd:
    def test_success_renders_result(self, tmp_path: Path) -> None:
        result = {
            "score": 80,
            "details": {
                "behavioral_score": 40,
                "allows": 10,
                "warns": 1,
                "blocks": 0,
                "structural_score": 25,
                "structural_status": "ok",
                "freshness_score": 15,
                "freshness_status": "fresh",
            },
        }
        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "sdd_cli.utils.sdd_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_core.governance.compliance.compute_governance_adherence",
                return_value=result,
            ),
            patch(
                "sdd_cli.services.governance_scoring_output.render_governance_adherence_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_adherence_cmd(
                verbose=False, threshold=50, window=24, console=_console()
            )

        assert captured["result"] == result
        assert captured["threshold"] == 50
        assert captured["window"] == 24

    def test_exception_exits_1(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.utils.sdd_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_core.governance.compliance.compute_governance_adherence",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_governance_adherence_cmd(
                verbose=False, threshold=50, window=24, console=_console()
            )
        assert exc_info.value.exit_code == 1
