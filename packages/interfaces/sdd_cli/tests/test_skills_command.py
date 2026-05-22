from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def _load_json_output(raw: str) -> dict:
    # Some environments emit a governance soft preface line before JSON output.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_skills_list_json_contract() -> None:
    result = runner.invoke(app, ["--json", "skills", "list"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills list"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["state"] == "ok"
    assert data["policy_result"] == "listed"
    assert data["exit_code"] == 0
    assert isinstance(data["skills"], list)


def test_skills_describe_existing() -> None:
    result = runner.invoke(app, ["--json", "skills", "describe", "diagnose"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills describe"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["skill"] == "diagnose"
    assert data["definition"]["schema_version"] == "1.1.0"


def test_skills_describe_missing() -> None:
    result = runner.invoke(app, ["--json", "skills", "describe", "does-not-exist"])
    assert result.exit_code == 1
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills describe"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "missing_skill"


def test_skills_run_dry_run_json() -> None:
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = runner.invoke(app, ["--json", "skills", "run", "validate-governance"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills run"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "planned"
    assert data["exit_code"] == 0
    assert data["governance_footer"].startswith("SDD GOVERNANCE:")


def test_skills_run_text_appends_governance_footer() -> None:
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = runner.invoke(app, ["skills", "run", "validate-governance"])
    assert result.exit_code == 0, result.output
    assert "SDD GOVERNANCE: drift=" in result.output


def test_skills_export_openai_json() -> None:
    result = runner.invoke(app, ["--json", "skills", "export", "--format", "openai"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills export"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "exported"
    assert data["payload"]["format"] == "openai"
    assert isinstance(data["payload"]["tools"], list)


def test_skills_run_execute_json_includes_command_results() -> None:
    fake_result = MagicMock()
    fake_result.state = "ok"
    fake_result.profile = "default"
    fake_result.skill = "validate-governance"
    fake_result.policy_result = "executed"
    fake_result.reason = "runtime execution completed"
    fake_result.exit_code = 0
    fake_result.governance_footer = (
        "SDD GOVERNANCE: drift=none | governance=ok | profile=default"
    )
    fake_result.fallback = ["sdd governance validate"]
    fake_result.command_results = [
        {
            "command": "sdd governance validate",
            "status": "ok",
            "exit_code": 0,
            "error": "",
        }
    ]
    fake_result.artifacts = {"gate_decision": {"decision": "allow"}}

    with patch(
        "sdd_cli.commands.skills.SkillEngine.run_skill", return_value=fake_result
    ):
        result = runner.invoke(
            app,
            ["--json", "skills", "run", "validate-governance", "--execute"],
        )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills run"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "executed"
    assert data["command_results"][0]["command"] == "sdd governance validate"
    assert data["artifacts"]["gate_decision"]["decision"] == "allow"


def test_skills_run_correct_denied_when_pipeline_enforcement_enabled() -> None:
    with patch.dict("os.environ", {"SDD_ENFORCE_PIPELINE_CORRECT": "1"}):
        result = runner.invoke(app, ["--json", "skills", "run", "sdd-correct"])
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills run"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "denied"
    assert data["reason"] == "pipeline_required_for_sdd_correct"


def test_skills_full_bootstrap_json_missing_governance_uses_canonical_error(
    tmp_path,
) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
        patch(
            "sdd_cli.commands.skills.validate_governance_path",
            return_value=False,
        ),
    ):
        result = runner.invoke(app, ["--json", "skills", "--full-bootstrap"])

    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills full-bootstrap"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "missing_governance_artifacts"


def test_skills_learning_candidates_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
    ):
        result = runner.invoke(app, ["--json", "skills", "learning-candidates"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-candidates"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "learning_candidates_listed"
    assert isinstance(data["candidates"], list)


def test_skills_learning_approve_and_rules_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
    ):
        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "rule-candidates.json").write_text(
            json.dumps(
                {
                    "candidates": [
                        {
                            "candidate_id": "rc-1",
                            "pattern": "h|r",
                            "proposed_guardrail": "g",
                            "risk_level": "medium",
                            "expected_impact": "reduce_rework",
                            "evidence_refs": ["e"],
                            "source_count": 2,
                            "created_at": "2026-01-01T00:00:00+00:00",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        approve = runner.invoke(
            app,
            [
                "--json",
                "skills",
                "learning-approve",
                "rc-1",
                "--reviewer",
                "human",
                "--rationale",
                "looks good",
                "--ttl-days",
                "30",
            ],
        )
        assert approve.exit_code == 0, approve.output
        payload = _load_json_output(approve.output)
        assert payload["status"] == "ok"
        assert payload["command"] == "skills learning-approve"
        assert payload["ok"] is True
        assert payload["error"] is None
        assert isinstance(payload["data"], dict)
        data = _payload_data(payload)
        assert data["policy_result"] == "rule_approved"

        rules = runner.invoke(app, ["--json", "skills", "learning-rules"])
        assert rules.exit_code == 0, rules.output
        rules_payload = _load_json_output(rules.output)
        assert rules_payload["status"] == "ok"
        assert rules_payload["command"] == "skills learning-rules"
        assert rules_payload["ok"] is True
        assert rules_payload["error"] is None
        assert isinstance(rules_payload["data"], dict)
        rules_data = _payload_data(rules_payload)
        assert rules_data["policy_result"] == "active_rules_listed"
        assert isinstance(rules_data["rules"], list)


def test_skills_learning_impact_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "skills",
                "learning-impact",
                "rr-1",
                "--rework-delta",
                "-0.1",
                "--false-block-rate",
                "0.2",
                "--escalation-delta",
                "0.05",
            ],
        )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-impact"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "rule_impact_recorded"


def test_skills_learning_status_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
    ):
        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "rule-candidates.json").write_text(
            json.dumps({"candidates": [{"candidate_id": "rc-1"}]}), encoding="utf-8"
        )
        (runtime_dir / "rule-registry.json").write_text(
            json.dumps(
                {
                    "rules": [
                        {"rule_id": "rr-1", "status": "active"},
                        {"rule_id": "rr-2", "status": "rolled_back"},
                        {"rule_id": "rr-3", "status": "expired"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (runtime_dir / "rule-impact.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "rule_id": "rr-1",
                            "rework_delta": -0.2,
                            "false_block_rate": 0.1,
                            "escalation_delta": 0.05,
                            "rollback_flag": False,
                            "timestamp": "2099-01-01T00:00:00+00:00",
                        }
                    ),
                    json.dumps(
                        {
                            "rule_id": "rr-2",
                            "rework_delta": 0.3,
                            "false_block_rate": 0.2,
                            "escalation_delta": 0.1,
                            "rollback_flag": True,
                            "timestamp": "2099-01-01T00:00:00+00:00",
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["--json", "skills", "learning-status"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-status"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "learning_status_loaded"
    status = data["status"]
    assert status["candidates_total"] == 1
    assert status["rules_active"] == 1
    assert status["rules_rolled_back"] == 1
    assert status["rules_expired"] == 1
    assert "kpi_rework_reduction_pct_recent" in status


def test_skills_regenerate_seeds_invokes_full_bootstrap_mode() -> None:
    with patch("sdd_cli.commands.skills._run_full_bootstrap") as bootstrap:
        result = runner.invoke(app, ["skills", "--regenerate-seeds"])
    assert result.exit_code == 0, result.output
    bootstrap.assert_called_once_with(regenerate_seeds=True, dry_run=False)


def test_skills_regenerate_seeds_dry_run_invokes_full_bootstrap_mode() -> None:
    with patch("sdd_cli.commands.skills._run_full_bootstrap") as bootstrap:
        result = runner.invoke(app, ["skills", "--regenerate-seeds", "--dry-run"])
    assert result.exit_code == 0, result.output
    bootstrap.assert_called_once_with(regenerate_seeds=True, dry_run=True)


def test_skills_dry_run_requires_regenerate_seeds() -> None:
    result = runner.invoke(app, ["skills", "--dry-run"])
    assert result.exit_code == 2, result.output
    assert "--dry-run requires --regenerate-seeds" in result.output


def test_skills_full_bootstrap_json_uses_canonical_envelope(tmp_path) -> None:
    class _Summary:
        commands = {"added": 0, "removed": 0, "unchanged": 1}
        skills = {"added": 0, "removed": 0, "unchanged": 1}

        def as_json(self):
            return {
                "commands": self.commands,
                "skills": self.skills,
                "drift_detected": False,
            }

    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
        patch(
            "sdd_cli.commands.skills.validate_governance_path",
            return_value=True,
        ),
        patch(
            "sdd_cli.commands.skills.load_governance_config",
            return_value={"items": [{"id": "M001"}]},
        ),
        patch(
            "sdd_cli.commands.skills.generate_agent_seeds",
            return_value=[("copilot", tmp_path / "seed.md", "ok")],
        ),
        patch(
            "sdd_cli.commands.skills.generate_agent_instruction_files",
            return_value=[],
        ),
        patch(
            "sdd_cli.commands.skills.generate_agent_prompt_commands",
            return_value=[],
        ),
        patch(
            "sdd_cli.commands.skills.generate_skills_registry",
            return_value={"skill_count": 1},
        ),
        patch(
            "sdd_cli.commands.skills.generate_commands_registry",
            return_value={"command_count": 1},
        ),
        patch(
            "sdd_cli.commands.skills.reconcile_registries",
            return_value=_Summary(),
        ),
        patch(
            "sdd_cli.commands.skills.generate_skill_index",
            return_value={"skill_count": 1},
        ),
        patch(
            "sdd_cli.commands.skills.generate_cli_commands_index",
            return_value={"command_count": 1},
        ),
        patch("sdd_cli.commands.skills._generate_adapters", return_value=(2, None)),
    ):
        result = runner.invoke(app, ["--json", "skills", "--full-bootstrap"])

    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills full-bootstrap"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "skills_full_bootstrap_completed"


def test_skills_list_json_uses_canonical_data_payload(monkeypatch) -> None:
    result = runner.invoke(app, ["--json", "skills", "list"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills list"
    assert payload["ok"] is True
    assert payload["data"]["policy_result"] == "listed"
    assert "policy_result" not in payload


def test_reconcile_root_seed_artifacts_prunes_stale_files(tmp_path) -> None:
    from sdd_cli.commands.skills import _reconcile_root_seed_artifacts

    commands_registry = tmp_path / ".sdd" / "commands"
    skills_registry = tmp_path / ".sdd" / "skills"
    commands_registry.mkdir(parents=True, exist_ok=True)
    skills_registry.mkdir(parents=True, exist_ok=True)
    (commands_registry / "registry.json").write_text(
        json.dumps(
            {
                "commands": [
                    {"id": "sdd-ask"},
                    {"id": "sdd-ask-full"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (skills_registry / "registry.json").write_text(
        json.dumps({"skills": [{"name": "sdd-ask"}, {"name": "sdd-diagnose"}]}),
        encoding="utf-8",
    )

    prompts = tmp_path / ".github" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    (prompts / "sdd-ask.prompt.md").write_text("ok", encoding="utf-8")
    (prompts / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

    codex_skills = tmp_path / ".codex" / "skills"
    codex_skills.mkdir(parents=True, exist_ok=True)
    (codex_skills / "sdd-ask-full.prompt.md").write_text("ok", encoding="utf-8")
    (codex_skills / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

    claude_cmds = tmp_path / ".claude" / "commands"
    claude_cmds.mkdir(parents=True, exist_ok=True)
    (claude_cmds / "sdd-ask.md").write_text("ok", encoding="utf-8")
    (claude_cmds / "sdd-legacy.md").write_text("stale", encoding="utf-8")

    gemini_skills = tmp_path / ".gemini" / "antigravity" / "skills"
    gemini_skills.mkdir(parents=True, exist_ok=True)
    (gemini_skills / "sdd-ask").mkdir()
    (gemini_skills / "sdd-governance").mkdir()
    (gemini_skills / "sdd-legacy").mkdir()
    stats = _reconcile_root_seed_artifacts(tmp_path)

    assert stats["deleted"] == 4
    assert (prompts / "sdd-legacy.prompt.md").exists() is False
    assert (codex_skills / "sdd-legacy.prompt.md").exists() is False
    assert (claude_cmds / "sdd-legacy.md").exists() is False
    assert (gemini_skills / "sdd-legacy").exists() is False
    assert (gemini_skills / "sdd-governance").exists() is True


def test_reconcile_root_seed_artifacts_dry_run_does_not_delete(tmp_path) -> None:
    from sdd_cli.commands.skills import _reconcile_root_seed_artifacts

    commands_registry = tmp_path / ".sdd" / "commands"
    skills_registry = tmp_path / ".sdd" / "skills"
    commands_registry.mkdir(parents=True, exist_ok=True)
    skills_registry.mkdir(parents=True, exist_ok=True)
    (commands_registry / "registry.json").write_text(
        json.dumps({"commands": [{"id": "sdd-ask"}]}),
        encoding="utf-8",
    )
    (skills_registry / "registry.json").write_text(
        json.dumps({"skills": [{"name": "sdd-ask"}]}),
        encoding="utf-8",
    )
    prompts = tmp_path / ".github" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    stale = prompts / "sdd-legacy.prompt.md"
    stale.write_text("stale", encoding="utf-8")

    stats = _reconcile_root_seed_artifacts(tmp_path, dry_run=True)
    assert stats["would_delete"] == 1
    assert stats["deleted"] == 0
    assert stale.exists() is True


def test_reconcile_root_seed_artifacts_fails_without_registries(tmp_path) -> None:
    from sdd_cli.commands.skills import _reconcile_root_seed_artifacts

    with pytest.raises(FileNotFoundError):
        _reconcile_root_seed_artifacts(tmp_path)


def test_skills_run_correct_blocked_text_mode(monkeypatch) -> None:
    monkeypatch.setenv("SDD_ENFORCE_PIPELINE_CORRECT", "1")
    result = runner.invoke(app, ["skills", "run", "sdd-correct"])
    assert result.exit_code == 1
    assert "bloqueado" in result.output or "blocked" in result.output.lower()


def test_skills_run_exit_nonzero_on_failed_result(monkeypatch) -> None:
    fake_result = MagicMock()
    fake_result.state = "error"
    fake_result.profile = "default"
    fake_result.skill = "sdd-diagnose"
    fake_result.policy_result = "error"
    fake_result.reason = "failed"
    fake_result.exit_code = 1
    fake_result.governance_footer = "SDD GOVERNANCE: drift=none"
    fake_result.fallback = []
    fake_result.command_results = []
    fake_result.artifacts = {}

    with (
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("sdd_cli.commands.skills.SkillEngine") as mock_engine_cls,
    ):
        mock_engine_cls.return_value.run_skill.return_value = fake_result
        result = runner.invoke(app, ["skills", "run", "sdd-diagnose"])
    assert result.exit_code == 1


def test_skills_export_text_mode_langchain() -> None:
    result = runner.invoke(app, ["skills", "export", "--format", "langchain"])
    assert result.exit_code == 0
    assert "{" in result.output


def test_skills_learning_candidates_text_mode(tmp_path) -> None:
    with (
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
        patch("sdd_cli.commands.skills.SupervisedLearningStore") as mock_store_cls,
    ):
        mock_store_cls.return_value.generate_candidates_from_ledger.return_value = []
        result = runner.invoke(app, ["skills", "learning-candidates"])
    assert result.exit_code == 0
    assert "rule candidates:" in result.output


def test_skills_learning_candidates_text_mode_with_existing(tmp_path) -> None:
    candidates_path = tmp_path / ".sdd" / "runtime" / "rule-candidates.json"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(
        json.dumps({"candidates": [{"candidate_id": "c1", "pattern": "foo.*"}]}),
        encoding="utf-8",
    )
    with (
        patch("sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path),
        patch("sdd_cli.commands.skills.SupervisedLearningStore") as mock_store_cls,
    ):
        mock_store_cls.return_value.generate_candidates_from_ledger.return_value = []
        result = runner.invoke(app, ["skills", "learning-candidates"])
    assert result.exit_code == 0
    assert "c1" in result.output


def test_skills_list_text_mode() -> None:
    result = runner.invoke(app, ["skills", "list"])
    assert result.exit_code == 0, result.output
    assert "Available skills:" in result.output


def test_skills_describe_existing_text_mode() -> None:
    result = runner.invoke(app, ["skills", "describe", "diagnose"])
    assert result.exit_code == 0, result.output
    assert "diagnose" in result.output


def test_skills_describe_missing_text_mode() -> None:
    result = runner.invoke(app, ["skills", "describe", "does-not-exist"])
    assert result.exit_code == 1
    assert (
        "not found" in result.output.lower()
        or "not found" in result.stderr_bytes.decode("utf-8", errors="replace").lower()
        if hasattr(result, "stderr_bytes")
        else True
    )


class TestRunFullBootstrapTextMode:
    def _mock_bootstrap(
        self, tmp_path, monkeypatch, *, regenerate_seeds=False, dry_run=False
    ):
        reconcile_summary = MagicMock()
        reconcile_summary.as_json.return_value = {}
        reconcile_summary.commands = {"added": 2, "removed": 0}
        reconcile_summary.skills = {"added": 3, "removed": 0}

        with (
            patch(
                "sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_cli.commands.skills._validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch("sdd_cli.commands.skills.generate_agent_seeds", return_value=[1, 2]),
            patch("sdd_cli.commands.skills.generate_agent_instruction_files"),
            patch("sdd_cli.commands.skills.generate_agent_prompt_commands"),
            patch(
                "sdd_cli.commands.skills.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.commands.skills.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "sdd_cli.commands.skills.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "sdd_cli.commands.skills.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.commands.skills.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
            patch("sdd_cli.commands.skills._generate_adapters", return_value=(2, None)),
            patch("sdd_cli.commands.skills._run_reconcile", return_value=(1, 2)),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
        ):
            from typer.testing import CliRunner as TCliRunner

            from sdd_cli.commands.skills import app as skills_app

            cli_runner = TCliRunner()
            args = ["full-bootstrap"]
            if regenerate_seeds:
                args += ["--regenerate-seeds"]
            if dry_run:
                args += ["--dry-run"]
            return cli_runner.invoke(skills_app, args)

    def test_text_mode_prints_completion_summary(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        from sdd_cli.commands.skills import _run_full_bootstrap

        reconcile_summary = MagicMock()
        reconcile_summary.as_json.return_value = {}
        reconcile_summary.commands = {"added": 2, "removed": 0}
        reconcile_summary.skills = {"added": 3, "removed": 0}

        with (
            patch(
                "sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_cli.commands.skills._validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch("sdd_cli.commands.skills.generate_agent_seeds", return_value=[1, 2]),
            patch("sdd_cli.commands.skills.generate_agent_instruction_files"),
            patch("sdd_cli.commands.skills.generate_agent_prompt_commands"),
            patch(
                "sdd_cli.commands.skills.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.commands.skills.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "sdd_cli.commands.skills.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "sdd_cli.commands.skills.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.commands.skills.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
            patch("sdd_cli.commands.skills._generate_adapters", return_value=(2, None)),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
        ):
            _run_full_bootstrap(regenerate_seeds=False, dry_run=False)

    def test_text_mode_prints_deleted_seeds_on_regenerate(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        from sdd_cli.commands.skills import _run_full_bootstrap

        reconcile_summary = MagicMock()
        reconcile_summary.as_json.return_value = {}
        reconcile_summary.commands = {"added": 0, "removed": 0}
        reconcile_summary.skills = {"added": 0, "removed": 0}

        with (
            patch(
                "sdd_cli.commands.skills.resolve_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_cli.commands.skills._validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch("sdd_cli.commands.skills.generate_agent_seeds", return_value=[]),
            patch("sdd_cli.commands.skills.generate_agent_instruction_files"),
            patch("sdd_cli.commands.skills.generate_agent_prompt_commands"),
            patch(
                "sdd_cli.commands.skills.generate_skills_registry",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.commands.skills.generate_commands_registry",
                return_value={"command_count": 0},
            ),
            patch(
                "sdd_cli.commands.skills.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "sdd_cli.commands.skills.generate_skill_index",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.commands.skills.generate_cli_commands_index",
                return_value={"command_count": 0},
            ),
            patch("sdd_cli.commands.skills._generate_adapters", return_value=(0, None)),
            patch("sdd_cli.commands.skills._run_reconcile", return_value=(3, 3)),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
        ):
            _run_full_bootstrap(regenerate_seeds=True, dry_run=False)


class TestReadRegistryIds:
    def test_raises_on_non_list_value(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _read_registry_ids

        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({"commands": "not-a-list"}), encoding="utf-8")
        with pytest.raises(ValueError, match=r"invalid registry format for "):
            _read_registry_ids(reg, "commands", "id")

    def test_skips_non_dict_rows(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _read_registry_ids

        reg = tmp_path / "registry.json"
        reg.write_text(
            json.dumps({"commands": ["string-row", {"id": "sdd-ask"}]}),
            encoding="utf-8",
        )
        result = _read_registry_ids(reg, "commands", "id")
        assert result == ["sdd-ask"]


class TestGenerateAdapters:
    def test_returns_zero_on_import_error(self) -> None:
        from sdd_cli.commands.skills import _generate_adapters

        with patch(
            "sdd_adapters.adapter_generator.AdapterGenerator",
            side_effect=ImportError("no adapters"),
        ):
            count, err = _generate_adapters(Path("/tmp"))
        assert count == 0
        assert err is not None

    def test_returns_count_on_success(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _generate_adapters

        with patch("sdd_adapters.adapter_generator.AdapterGenerator") as mock_cls:
            mock_cls.return_value.generate.return_value = [1, 2, 3]
            count, err = _generate_adapters(tmp_path)
        assert count == 3
        assert err is None


class TestHandleAdapterError:
    def test_text_mode_prints_error_and_exits(self) -> None:
        from sdd_cli.commands.skills import _handle_adapter_error

        with (
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _handle_adapter_error("template error")
        assert exc_info.value.exit_code == 1

    def test_json_mode_emits_error_and_exits(self) -> None:
        from sdd_cli.commands.skills import _handle_adapter_error

        with (
            patch("sdd_cli.commands.skills._ctx_json", return_value=True),
            patch("sdd_cli.commands.skills._emit_skills_json") as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            _handle_adapter_error("template error")
        assert exc_info.value.exit_code == 1
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "adapter_generation_failed"


class TestValidateAndLoadGovernance:
    def test_text_mode_exits_on_invalid_path(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _validate_and_load_governance

        with (
            patch(
                "sdd_cli.commands.skills.validate_governance_path", return_value=False
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _validate_and_load_governance(tmp_path / ".sdd" / "compiled")
        assert exc_info.value.exit_code == 1

    def test_json_mode_exits_on_invalid_path(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _validate_and_load_governance

        with (
            patch(
                "sdd_cli.commands.skills.validate_governance_path", return_value=False
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=True),
            patch("sdd_cli.commands.skills._emit_skills_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            _validate_and_load_governance(tmp_path / ".sdd" / "compiled")
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_artifacts"

    def test_text_mode_exits_on_empty_items(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _validate_and_load_governance

        with (
            patch(
                "sdd_cli.commands.skills.validate_governance_path", return_value=True
            ),
            patch(
                "sdd_cli.commands.skills.load_governance_config",
                return_value={"items": []},
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _validate_and_load_governance(tmp_path / ".sdd" / "compiled")
        assert exc_info.value.exit_code == 1

    def test_json_mode_exits_on_empty_items(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _validate_and_load_governance

        with (
            patch(
                "sdd_cli.commands.skills.validate_governance_path", return_value=True
            ),
            patch(
                "sdd_cli.commands.skills.load_governance_config",
                return_value={"items": []},
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=True),
            patch("sdd_cli.commands.skills._emit_skills_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            _validate_and_load_governance(tmp_path / ".sdd" / "compiled")
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_items"


class TestRunReconcile:
    def test_text_mode_exits_on_exception(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _run_reconcile

        with (
            patch(
                "sdd_cli.commands.skills._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=False),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _run_reconcile(tmp_path, dry_run=False)
        assert exc_info.value.exit_code == 1

    def test_json_mode_exits_on_exception(self, tmp_path) -> None:
        from sdd_cli.commands.skills import _run_reconcile

        with (
            patch(
                "sdd_cli.commands.skills._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            patch("sdd_cli.commands.skills._ctx_json", return_value=True),
            patch("sdd_cli.commands.skills._emit_skills_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            _run_reconcile(tmp_path, dry_run=False)
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "seed_reconciliation_failed"
