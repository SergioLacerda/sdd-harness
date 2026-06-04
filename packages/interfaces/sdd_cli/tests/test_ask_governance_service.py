from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from sdd_cli.services.ask_governance import (
    _compiled_candidates,
    fingerprint_file,
    load_compiled_governance,
    load_governance_via_runtime,
    log_sdd_metadata,
    signature_mode,
    try_sdd_compiled_dir,
    try_sdd_compiled_fallback,
    validate_signature_for_artifact,
)


def _mk_compiled_artifact(compiled_dir: Path) -> None:
    compiled_dir.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": "abcd1234ef", "mandates": [{"id": "M001"}]}
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_compiled_candidates_only_returns_active_dir(tmp_path: Path) -> None:
    active = tmp_path / ".sdd" / "compiled" / "active"
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
    active = tmp_path / ".sdd" / "compiled" / "active"
    _mk_compiled_artifact(active)

    source, fingerprint, mandates_count, *_ = load_compiled_governance(
        tmp_path,
        compiled_active_dir_fn=lambda _: active,
    )
    assert source == "compiled"
    assert fingerprint
    assert mandates_count == 1


# ---------------------------------------------------------------------------
# fingerprint_file
# ---------------------------------------------------------------------------


def test_fingerprint_file_returns_8_char_hex(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"hello")
    fp = fingerprint_file(f)
    assert len(fp) == 8
    assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# signature_mode
# ---------------------------------------------------------------------------


def test_signature_mode_default_is_warn(monkeypatch) -> None:
    monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)
    assert signature_mode() == "warn"


def test_signature_mode_off(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "off")
    assert signature_mode() == "off"


def test_signature_mode_strict(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")
    assert signature_mode() == "strict"


def test_signature_mode_invalid_returns_warn(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "bogus")
    assert signature_mode() == "warn"


# ---------------------------------------------------------------------------
# try_sdd_compiled_dir
# ---------------------------------------------------------------------------


def test_try_sdd_compiled_dir_file_not_exist(tmp_path: Path) -> None:
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_data_not_dict(tmp_path: Path) -> None:
    (tmp_path / "governance-core.json").write_text("[]", encoding="utf-8")
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_mandates_none_with_logger(tmp_path: Path) -> None:
    logger = MagicMock()
    (tmp_path / "governance-core.json").write_text(
        json.dumps({"other": "key"}), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path, logger=logger)
    assert result is None
    logger.debug.assert_called()


def test_try_sdd_compiled_dir_mandates_not_list(tmp_path: Path) -> None:
    (tmp_path / "governance-core.json").write_text(
        json.dumps({"mandates": "bad"}), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_exception_with_logger(tmp_path: Path) -> None:
    logger = MagicMock()
    (tmp_path / "governance-core.json").write_bytes(b"\xff\xfe invalid json")
    result = try_sdd_compiled_dir(tmp_path, logger=logger)
    assert result is None
    logger.debug.assert_called()


def test_try_sdd_compiled_dir_success_with_fingerprint_in_data(tmp_path: Path) -> None:
    payload = {
        "fingerprint": "aabbccdd1122",
        "mandates": [{"id": "M001"}, {"id": "M002"}],
    }
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    source, fp, count = result
    assert source == "compiled"
    assert fp == "aabbccd"[:8] or len(fp) == 8
    assert count == 2


def test_try_sdd_compiled_dir_success_fallback_fingerprint(tmp_path: Path) -> None:
    payload = {"mandates": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    source, fp, count = result
    assert source == "compiled"
    assert len(fp) == 8
    assert count == 1


def test_try_sdd_compiled_dir_uses_items_key(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    assert result[2] == 1


# ---------------------------------------------------------------------------
# validate_signature_for_artifact
# ---------------------------------------------------------------------------


def test_validate_signature_off_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    auth, deg, reason, trust = validate_signature_for_artifact(
        f, signature_mode_value="off"
    )
    assert auth is True
    assert deg is False
    assert trust == "none"


def test_validate_signature_exception_strict_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    with patch.dict(sys.modules, {"sdd_runtime": None, "sdd_runtime.signatures": None}):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="strict"
        )
    assert auth is False
    assert deg is False
    assert "signature validation failed" in reason


def test_validate_signature_exception_warn_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    with patch.dict(sys.modules, {"sdd_runtime": None, "sdd_runtime.signatures": None}):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is True
    assert "warn mode" in reason


def test_validate_signature_result_ok(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = True
    result.blocking = False
    result.deprecation_warning = ""
    result.trust_source = "signed"
    with patch("sdd_cli.services.ask_governance.validate_signature_for_artifact") as mp:
        mp.return_value = (True, False, "", "signed")
        auth, deg, reason, trust = mp(f, signature_mode_value="warn")
    assert auth is True


def test_validate_signature_result_ok_with_deprecation(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    result = MagicMock()
    result.ok = True
    result.blocking = False
    result.deprecation_warning = "old key"
    result.trust_source = "signed"
    mock_validate = MagicMock(return_value=result)
    with (
        patch.dict(
            sys.modules,
            {
                "sdd_runtime": MagicMock(
                    signatures=MagicMock(validate_artifact_signature=mock_validate)
                )
            },
        ),
        patch("sdd_runtime.signatures.validate_artifact_signature", mock_validate),
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is True


def test_validate_signature_result_blocking(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = False
    result.blocking = True
    result.code = "ERR001"
    result.reason = "expired"
    result.trust_source = "none"
    mock_validate = MagicMock(return_value=result)
    with patch("sdd_runtime.signatures.validate_artifact_signature", mock_validate):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is False
    assert "ERR001" in reason


def test_validate_signature_result_non_blocking(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = False
    result.blocking = False
    result.code = "WARN001"
    result.reason = "degraded key"
    result.trust_source = "partial"
    mock_validate = MagicMock(return_value=result)
    with patch("sdd_runtime.signatures.validate_artifact_signature", mock_validate):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is True


# ---------------------------------------------------------------------------
# load_governance_via_runtime
# ---------------------------------------------------------------------------


def test_load_governance_via_runtime_dir_not_dir(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = load_governance_via_runtime(
        tmp_path,
        compiled_active_dir_fn=lambda _: missing,
    )
    assert result is None


def test_load_governance_via_runtime_exception_returns_none(tmp_path: Path) -> None:
    logger = MagicMock()
    import sys

    with patch.dict(sys.modules, {"sdd_runtime": None}):
        result = load_governance_via_runtime(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
            logger=logger,
        )
    assert result is None
    logger.debug.assert_called()


def test_load_governance_via_runtime_injector_loads(tmp_path: Path) -> None:
    injector_result = MagicMock()
    injector_result.loaded = True
    injector_result.artifact_fingerprint = "deadbeef1234"
    injector_result.total_loaded = 5
    injector_result.auth_state = "verified"
    injector_result.trust_source = "signed"
    injector = MagicMock()
    injector.inject_from_path.return_value = injector_result

    import sys

    mock_sdd_runtime = MagicMock()
    mock_sdd_runtime.GovernanceInjector.return_value = injector
    with patch.dict(sys.modules, {"sdd_runtime": mock_sdd_runtime}):
        result = load_governance_via_runtime(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    assert result is not None
    source, fp, count, auth_state, trust_source = result
    assert source == "compiled"
    assert count == 5


# ---------------------------------------------------------------------------
# try_sdd_compiled_fallback
# ---------------------------------------------------------------------------


def test_try_sdd_compiled_fallback_not_dir(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = try_sdd_compiled_fallback(missing, "warn")
    assert result is None


def test_try_sdd_compiled_fallback_try_sdd_returns_none(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is None


def test_try_sdd_compiled_fallback_artifact_exists(tmp_path: Path, monkeypatch) -> None:
    payload = {"mandates": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(
        "sdd_cli.services.ask_governance.validate_signature_for_artifact",
        lambda *a, **kw: (True, False, "", "signed"),
    )
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is not None
    assert result[0] == "compiled"
    assert result[3] is True


def test_try_sdd_compiled_fallback_strict_no_artifact(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-client.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_fallback(tmp_path, "strict")
    assert result is not None
    assert result[3] is False
    assert "strict mode" in result[5]


def test_try_sdd_compiled_fallback_warn_no_artifact(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-client.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is not None
    assert result[4] is True


# ---------------------------------------------------------------------------
# log_sdd_metadata
# ---------------------------------------------------------------------------


def test_log_sdd_metadata_file_not_exists(tmp_path: Path) -> None:
    logger = MagicMock()
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_not_called()


def test_log_sdd_metadata_valid_file(tmp_path: Path) -> None:
    logger = MagicMock()
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"version": "3.0", "item_count": 12}), encoding="utf-8"
    )
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_called()


def test_log_sdd_metadata_invalid_json(tmp_path: Path) -> None:
    logger = MagicMock()
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_bytes(b"\xff\xfe invalid")
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_called()


def test_log_sdd_metadata_no_logger(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"version": "3.0"}), encoding="utf-8"
    )
    log_sdd_metadata(tmp_path, logger=None)


# ---------------------------------------------------------------------------
# load_compiled_governance — runtime_result not None path
# ---------------------------------------------------------------------------


def test_load_compiled_governance_runtime_verified(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.services.ask_governance.load_governance_via_runtime",
        lambda *a, **kw: ("compiled", "abcd1234", 7, "verified", "signed"),
    )
    source, fp, count, authenticated, degraded, reason, trust = (
        load_compiled_governance(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    )
    assert source == "compiled"
    assert authenticated is True
    assert degraded is False


def test_load_compiled_governance_runtime_degraded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sdd_cli.services.ask_governance.load_governance_via_runtime",
        lambda *a, **kw: ("compiled", "abcd1234", 3, "degraded", "partial"),
    )
    source, fp, count, authenticated, degraded, reason, trust = (
        load_compiled_governance(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    )
    assert degraded is True
    assert authenticated is False
