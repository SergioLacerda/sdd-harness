import os

try:
    import pytest
except ImportError:
    pytest = None
from pathlib import Path

from sdd_core.utils.environment import detect_repo_root, find_workspace_root
from sdd_wizard.orchestration.phase5_source_writer import SddSourceWriter
from sdd_wizard.orchestration.phase6_ide_deployer import IdeTemplateDeployer
from sdd_wizard.orchestration.seedlings.base_generator import BaseSeedlingGenerator


def _get_repo_root() -> Path:
    """Get the actual repo root for the current environment."""
    return find_workspace_root() or detect_repo_root()


def test_ide_deployer_blocks_root_mutation(monkeypatch):
    """
    Verify that IdeTemplateDeployer blocks root mutation during initialization
    while SDD_TEST_OUTPUT_DIR is set.
    """
    repo_root = _get_repo_root()
    output_base = repo_root  # DANGER: pointing to root

    # Enable test isolation mode
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-isolated-test")

    if pytest:
        with pytest.raises(PermissionError) as excinfo:
            IdeTemplateDeployer(
                repo_root=repo_root, output_base=output_base, verbose=True
            )
        assert "SDD_ISOLATION_ERROR" in str(excinfo.value)
    print("✅ IdeTemplateDeployer safety guard successfully blocked root mutation!")


def test_instruction_files_blocks_root_mutation(monkeypatch):
    """
    Verify that generate_agent_instruction_files blocks root mutation in tests.
    """
    from sdd_cli.generators._instruction_files import generate_agent_instruction_files

    repo_root = _get_repo_root()

    # Enable test isolation mode
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-isolated-test")

    if pytest:
        with pytest.raises(PermissionError) as excinfo:
            generate_agent_instruction_files(output_dir=repo_root, config={"items": []})
        assert "SDD_ISOLATION_ERROR" in str(excinfo.value)
    print("✅ Agent instruction files safety guard successfully blocked root mutation!")


def test_source_writer_blocks_root_mutation(monkeypatch):
    """Verify that SddSourceWriter blocks root mutation in tests."""
    repo_root = _get_repo_root()
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-isolated-test")

    if pytest:
        with pytest.raises(PermissionError) as excinfo:
            SddSourceWriter(
                output_base=repo_root,
                source_dir=repo_root / ".sdd" / "source",
                runtime_dir=repo_root / ".sdd" / "runtime",
                mandates_dir=repo_root / ".sdd" / "source" / "mandates",
                guidelines_dir=repo_root / ".sdd" / "source" / "guidelines",
                mandates=[],
                guidelines={},
                guidelines_by_category={},
                config={},
                verbose=True,
            )
        assert "SDD_ISOLATION_ERROR" in str(excinfo.value)
    print("✅ SddSourceWriter safety guard successfully blocked root mutation!")


def test_base_seedling_generator_blocks_root_mutation(monkeypatch):
    """Verify that BaseSeedlingGenerator blocks root mutation in tests."""
    repo_root = _get_repo_root()
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-isolated-test")

    if pytest:
        with pytest.raises(PermissionError) as excinfo:
            BaseSeedlingGenerator(
                output_base=repo_root,
                seedlings_dir=repo_root / ".sdd" / "seedlings",
                config={},
                spec_fingerprint="fp",
                mandate_ids=[],
                active_categories=[],
                generated_at="now",
                verbose=True,
            )
        assert "SDD_ISOLATION_ERROR" in str(excinfo.value)
    print("✅ BaseSeedlingGenerator safety guard successfully blocked root mutation!")


if __name__ == "__main__":
    # If run as a script, we need to mock monkeypatch
    class MockMonkeypatch:
        def setenv(self, name, value):
            os.environ[name] = value

    mp = MockMonkeypatch()
    try:
        test_ide_deployer_blocks_root_mutation(mp)
        test_instruction_files_blocks_root_mutation(mp)
        test_source_writer_blocks_root_mutation(mp)
        test_base_seedling_generator_blocks_root_mutation(mp)
    except Exception as e:
        print(f"\n❌ Caught unexpected error: {type(e).__name__}: {e}")
        import sys
        import traceback

        traceback.print_exc()
        sys.exit(1)
