import json
from pathlib import Path

from sdd_cli.commands._ask_backend import _render_context_output, _try_sdd_compiled_dir


def test_loader_rejects_unknown_json_schema(tmp_path: Path):
    # Setup: a random JSON file in compiled dir
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    random_file = compiled_dir / "random.json"
    random_file.write_text(json.dumps({"some": "data"}), encoding="utf-8")

    # Setup: a canonical file with WRONG schema (missing items/mandates)
    bad_gov = compiled_dir / "governance-core.json"
    bad_gov.write_text(json.dumps({"fingerprint": "fake"}), encoding="utf-8")

    # Act
    result = _try_sdd_compiled_dir(compiled_dir)

    # Assert
    assert result is None


def test_loader_accepts_canonical_schema(tmp_path: Path):
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    good_gov = compiled_dir / "governance-core.json"
    good_gov.write_text(
        json.dumps({"fingerprint": "real-fp", "items": []}), encoding="utf-8"
    )

    # Act
    result = _try_sdd_compiled_dir(compiled_dir)

    # Assert
    assert result is not None
    assert result[1] == "real-fp"


def test_degraded_output_shows_warning():
    # Act
    output = _render_context_output(
        query="test",
        context_source="compiled",
        fingerprint="fp123",
        mandates_count=5,
        degraded=True,
        degrade_reason="invalid signature",
        trust_source="none",
    )

    # Assert
    assert "⚠ Governance loaded in DEGRADED mode" in output
    assert "degraded        : yes" in output
    assert "degraded_reason : invalid signature" in output
    assert "Governance is active" not in output


def test_verified_output_shows_active():
    # Act
    output = _render_context_output(
        query="test",
        context_source="compiled",
        fingerprint="fp123",
        mandates_count=5,
        degraded=False,
        degrade_reason="",
        trust_source="canonical",
    )

    # Assert
    assert "Governance is active" in output
    assert "degraded        : no" in output
    assert "⚠ Governance loaded in DEGRADED mode" not in output
