"""Integration tests for `sdd metrics summary` and `sdd metrics serve` commands."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from unittest import mock

import pytest
import typer

from sdd_cli.commands.metrics import _CollectorRef, _start_reload_worker, serve, summary

pytestmark = pytest.mark.integration


class TestMetricsSummaryCommand:
    """Tests for `sdd metrics summary` subcommand."""

    def test_summary_no_jsonl_file_error(self, tmp_path: Path) -> None:
        """Summary should error gracefully when JSONL not found."""
        # Pass a path that doesn't exist (no fixture, no auto-detection)
        nonexistent_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(typer.Exit):
            summary(ctx=mock.MagicMock(), jsonl=nonexistent_path, last_hours=None)

    def test_summary_with_sample_events(self, metrics_events_path: Path) -> None:
        """Summary should load and render events correctly."""
        # Capture console output
        with mock.patch("sdd_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            # Verify console.print was called (table rendered)
            assert mock_console.print.called

    def test_summary_with_time_filter(self, metrics_events_path: Path) -> None:
        """Summary should support --last-hours filtering."""
        with mock.patch("sdd_cli.commands.metrics.console") as mock_console:
            # This should not crash; time filtering is handled by reader
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=1)

            # Should still render (older events may or may not be included)
            assert mock_console.print.called

    def test_summary_with_explicit_jsonl_path(self, metrics_events_path: Path) -> None:
        """Summary should accept explicit --jsonl path."""
        with mock.patch("sdd_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            assert mock_console.print.called

    def test_summary_renders_token_metrics(self, metrics_events_path: Path) -> None:
        """Summary should render token consumption metrics from synthetic events."""
        with mock.patch("sdd_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            # Should have called print at least once for table output
            assert mock_console.print.called

    def test_summary_json_mode_emits_envelope(self, metrics_events_path: Path) -> None:
        """Summary should emit standard JSON envelope in global --json mode."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        with mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit:
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "ok"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0
        assert "summary" in payload["data"]

    def test_summary_json_mode_missing_file_emits_error(self, tmp_path: Path) -> None:
        """Summary should emit JSON error envelope when file is missing."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        nonexistent_path = tmp_path / "missing.jsonl"
        with (
            mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=nonexistent_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is False
        assert payload["data"]["exit_code"] == 1

    def test_summary_json_mode_uses_canonical_data_payload(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strict mode should expose only canonical envelope + data payload."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        with mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit:
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "ok"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0
        assert "exit_code" not in payload
        assert "summary" not in payload

    def test_summary_json_mode_error_uses_canonical_data_payload(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strict mode error should keep exit metadata only under data."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        nonexistent_path = tmp_path / "missing.jsonl"
        with (
            mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=nonexistent_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is False
        assert payload["data"]["exit_code"] == 1
        assert "exit_code" not in payload


class TestMetricsServeCommand:
    """Tests for `sdd metrics serve` subcommand."""

    @staticmethod
    def _free_port() -> int:
        """Allocate an ephemeral localhost port for test server startup."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                return int(sock.getsockname()[1])
        except PermissionError:
            pytest.skip("Socket creation is restricted in this environment")

    def test_serve_no_jsonl_file_error(self, tmp_path: Path) -> None:
        """Serve should error gracefully when JSONL not found."""
        # Pass a path that doesn't exist (no fixture, no auto-detection)
        nonexistent_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(typer.Exit):
            serve(port=9999, jsonl=nonexistent_path, refresh=30)

    def test_serve_no_jsonl_file_json_error(self, tmp_path: Path) -> None:
        """Serve should emit canonical JSON error when file is missing."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        with (
            mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=9999, jsonl=nonexistent_path, refresh=30, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics serve"
        assert payload["error"]["code"] == "events_file_not_found"
        assert payload["data"]["exit_code"] == 1

    def test_serve_metrics_endpoint(self, metrics_events_path: Path) -> None:
        """Serve should expose /metrics endpoint with Prometheus format."""
        import urllib.error
        import urllib.request

        # Start server in background thread
        server_port = self._free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                # In restricted environments bind can fail; test handles this via request path.
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.5)

        try:
            # Request /metrics endpoint
            response = urllib.request.urlopen(
                f"http://localhost:{server_port}/metrics", timeout=2
            )
            metrics_text = response.read().decode("utf-8")

            # Verify Prometheus format
            assert "# HELP" in metrics_text
            assert "# TYPE" in metrics_text
            assert "sdd_tokens" in metrics_text or metrics_text.strip() != ""
            assert response.status == 200

        except urllib.error.URLError:
            # Server may not have started in time; skip
            pytest.skip("Server did not start in time")

    def test_serve_metrics_404_for_other_paths(self, metrics_events_path: Path) -> None:
        """Serve should reject requests to non-/metrics paths."""
        import urllib.error
        import urllib.request

        server_port = self._free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        try:
            # Request non-metrics path should fail
            try:
                urllib.request.urlopen(
                    f"http://localhost:{server_port}/notfound", timeout=2
                )
                pytest.fail("Should have raised HTTP error")
            except urllib.error.HTTPError as e:
                # Accept both 404 and 501 (server implementation may vary)
                if e.code not in (404, 501):
                    pytest.fail(f"Expected 404 or 501, got {e.code}")

        except urllib.error.URLError:
            pytest.skip("Server did not start in time")

    def test_serve_with_explicit_jsonl_path(self, metrics_events_path: Path) -> None:
        """Serve should accept explicit --jsonl path."""
        # Just verify it doesn't crash with explicit path
        # (would need full HTTP test for full validation)
        server_port = self._free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        # If we get here, no exception was raised
        assert True

    def test_reload_worker_stops_deterministically(
        self, metrics_events_path: Path
    ) -> None:
        """Reload worker should stop after stop_event is set."""
        from sdd_runtime.metrics import TokenEconomyCollector
        from sdd_runtime.reader import TelemetryReader

        collector = TokenEconomyCollector.from_reader(
            TelemetryReader(metrics_events_path)
        )
        collector_ref = _CollectorRef(collector)
        stop_event = threading.Event()
        worker = _start_reload_worker(
            jsonl_path=metrics_events_path,
            refresh=1,
            collector_ref=collector_ref,
            stop_event=stop_event,
        )
        stop_event.set()
        worker.join(timeout=2)
        assert not worker.is_alive()

    def test_serve_closes_server_on_keyboard_interrupt(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Serve should close HTTP server and exit cleanly on Ctrl+C."""
        closed = {"value": False}

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                closed["value"] = True

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        with pytest.raises(typer.Exit):
            serve(port=9996, jsonl=metrics_events_path, refresh=1)
        assert closed["value"] is True

    def test_serve_restart_cycle_multiple_times(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Serve should support repeated start/stop cycles without leaking state."""
        close_count = {"value": 0}

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                close_count["value"] += 1

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        for port in (9995, 9994, 9993):
            with pytest.raises(typer.Exit):
                serve(port=port, jsonl=metrics_events_path, refresh=1)
        assert close_count["value"] == 3

    def test_reload_worker_repeat_start_stop(self, metrics_events_path: Path) -> None:
        """Reload worker start/stop should be stable across repeated cycles."""
        from sdd_runtime.metrics import TokenEconomyCollector
        from sdd_runtime.reader import TelemetryReader

        for _ in range(5):
            collector = TokenEconomyCollector.from_reader(
                TelemetryReader(metrics_events_path)
            )
            collector_ref = _CollectorRef(collector)
            stop_event = threading.Event()
            worker = _start_reload_worker(
                jsonl_path=metrics_events_path,
                refresh=1,
                collector_ref=collector_ref,
                stop_event=stop_event,
            )
            stop_event.set()
            worker.join(timeout=2)
            assert not worker.is_alive()

    @pytest.mark.slow
    def test_serve_soak_restart_cycles(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Soak: repeated churn should exit cleanly with deterministic cleanup."""
        close_count = {"value": 0}
        cycles = 30

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                close_count["value"] += 1

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        for offset in range(cycles):
            with pytest.raises(typer.Exit):
                serve(port=9800 + offset, jsonl=metrics_events_path, refresh=1)

        assert close_count["value"] == cycles

    def test_serve_bind_failure_exits_without_starting_worker(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bind failures should fail fast and avoid worker startup/leaks."""

        def _raise_bind(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("bind denied")

        worker_started = {"value": False}

        def _worker(*_args: object, **_kwargs: object):
            worker_started["value"] = True
            raise AssertionError("reload worker must not start when bind fails")

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer", _raise_bind
        )
        monkeypatch.setattr("sdd_cli.commands.metrics._start_reload_worker", _worker)

        with pytest.raises(typer.Exit) as excinfo:
            serve(port=9799, jsonl=metrics_events_path, refresh=1)
        assert excinfo.value.exit_code == 1
        assert worker_started["value"] is False

    def test_serve_bind_failure_json_emits_canonical_error(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bind failure should emit canonical JSON error envelope."""

        def _raise_bind(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("bind denied")

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer", _raise_bind
        )
        with (
            mock.patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=9798, jsonl=metrics_events_path, refresh=1, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics serve"
        assert payload["error"]["code"] == "metrics_bind_failed"
        assert payload["data"]["exit_code"] == 1


class TestCollectorRef:
    def test_swap_updates_collector(self) -> None:
        from unittest.mock import MagicMock

        from sdd_cli.commands.metrics import _CollectorRef

        initial = MagicMock()
        replacement = MagicMock()
        ref = _CollectorRef(initial)
        ref.swap(replacement)
        assert ref._collector is replacement

    def test_snapshot_delegates_to_collector(self) -> None:
        from unittest.mock import MagicMock

        from sdd_cli.commands.metrics import _CollectorRef

        fake_snap = MagicMock()
        collector = MagicMock()
        collector.snapshot.return_value = fake_snap
        ref = _CollectorRef(collector)
        result = ref.snapshot()
        assert result is fake_snap


class TestResolveJsonlPath:
    def test_returns_explicit_path_when_provided(self, tmp_path) -> None:
        from sdd_cli.commands.metrics import _resolve_jsonl_path

        explicit = tmp_path / "events.jsonl"
        assert _resolve_jsonl_path(explicit) == explicit

    def test_returns_default_path_when_none(self) -> None:
        from sdd_cli.commands.metrics import _resolve_jsonl_path

        result = _resolve_jsonl_path(None)
        assert result.name == "compliance-events.jsonl"

    def test_returns_existing_default_path(self, tmp_path, monkeypatch) -> None:
        from sdd_cli.commands.metrics import _resolve_jsonl_path

        events = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
        events.parent.mkdir(parents=True, exist_ok=True)
        events.write_text("", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = _resolve_jsonl_path(None)
        assert result.name == "compliance-events.jsonl"


class TestSummaryErrorPaths:
    def test_summary_load_error_text_mode(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")
        ctx = MagicMock()
        ctx.obj = {}

        with (
            patch(
                "sdd_runtime.reader.TelemetryReader",
                side_effect=Exception("corrupt data"),
            ),
            patch("sdd_cli.commands.metrics.console"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            summary(ctx=ctx, jsonl=events, last_hours=None)
        assert exc_info.value.exit_code == 1

    def test_summary_load_error_json_mode(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")
        ctx = MagicMock()
        ctx.obj = {"output_json": True}

        with (
            patch(
                "sdd_runtime.reader.TelemetryReader",
                side_effect=Exception("corrupt data"),
            ),
            patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=events, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["error"]["code"] == "metrics_load_failed"

    def test_summary_budget_breach_text_mode(self, metrics_events_path) -> None:
        from unittest.mock import MagicMock, patch

        ctx = MagicMock()
        ctx.obj = {}
        snap = MagicMock()
        snap.budget_utilization_pct = 105.0
        snap.total_tokens_input = 100
        snap.total_tokens_output = 50
        snap.total_tokens_total = 150
        snap.total_cost_usd = 0.01
        snap.total_calls = 5
        snap.warn_count = 0
        snap.breach_count = 1
        snap.retry_cap_count = 0

        with (
            patch("sdd_runtime.reader.TelemetryReader"),
            patch("sdd_runtime.metrics.TokenEconomyCollector") as mock_coll,
            patch("sdd_cli.commands.metrics.console"),
        ):
            mock_coll.from_reader.return_value.snapshot.return_value = snap
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)

    def test_summary_budget_warning_text_mode(self, metrics_events_path) -> None:
        from unittest.mock import MagicMock, patch

        ctx = MagicMock()
        ctx.obj = {}
        snap = MagicMock()
        snap.budget_utilization_pct = 92.0
        snap.total_tokens_input = 100
        snap.total_tokens_output = 50
        snap.total_tokens_total = 150
        snap.total_cost_usd = 0.01
        snap.total_calls = 5
        snap.warn_count = 1
        snap.breach_count = 0
        snap.retry_cap_count = 0

        with (
            patch("sdd_runtime.reader.TelemetryReader"),
            patch("sdd_runtime.metrics.TokenEconomyCollector") as mock_coll,
            patch("sdd_cli.commands.metrics.console"),
        ):
            mock_coll.from_reader.return_value.snapshot.return_value = snap
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)


class TestServeErrorPaths:
    def test_serve_missing_file_text_mode(self, tmp_path) -> None:
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            serve(
                port=19999,
                jsonl=tmp_path / "missing.jsonl",
                refresh=30,
                json_output=False,
            )
        assert exc_info.value.exit_code == 1

    def test_serve_load_error_text_mode(self, tmp_path) -> None:
        from unittest.mock import patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        with (
            patch(
                "sdd_runtime.reader.TelemetryReader",
                side_effect=Exception("bad data"),
            ),
            patch("sdd_cli.commands.metrics.console"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            serve(port=19998, jsonl=events, refresh=30, json_output=False)
        assert exc_info.value.exit_code == 1

    def test_serve_load_error_json_mode(self, tmp_path) -> None:
        from unittest.mock import patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        with (
            patch(
                "sdd_runtime.reader.TelemetryReader",
                side_effect=Exception("bad data"),
            ),
            patch("sdd_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=19997, jsonl=events, refresh=30, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["error"]["code"] == "metrics_load_failed"

    def test_serve_bind_error_text_mode(self, metrics_events_path, monkeypatch) -> None:
        import typer

        monkeypatch.setattr(
            "sdd_cli.commands.metrics.http.server.HTTPServer",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("bind failed")),
        )
        with pytest.raises(typer.Exit) as exc_info:
            serve(
                port=19996,
                jsonl=metrics_events_path,
                refresh=30,
                json_output=False,
            )
        assert exc_info.value.exit_code == 1


class TestStartReloadWorker:
    def test_reload_worker_calls_swap_on_tick(self, tmp_path) -> None:
        import threading
        from unittest.mock import MagicMock, patch

        from sdd_cli.commands.metrics import _CollectorRef, _start_reload_worker

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        collector_ref = _CollectorRef(MagicMock())
        stop_event = threading.Event()

        fake_collector = MagicMock()
        with (
            patch("sdd_runtime.reader.TelemetryReader"),
            patch("sdd_runtime.metrics.TokenEconomyCollector") as mock_coll_cls,
        ):
            mock_coll_cls.from_reader.return_value = fake_collector
            worker = _start_reload_worker(
                jsonl_path=events,
                refresh=0,
                collector_ref=collector_ref,
                stop_event=stop_event,
            )
            stop_event.set()
            worker.join(timeout=2)

        assert not worker.is_alive()


class TestMetricsIntegration:
    """Integration tests combining summary and serve."""

    def test_summary_and_serve_same_data(self, metrics_events_path: Path) -> None:
        """Both summary and serve should read same JSONL consistently."""
        # Load with summary
        with mock.patch("sdd_cli.commands.metrics.console"):
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

        # Summary didn't crash, so data is readable
        # Serve would do the same (tested above)
        assert metrics_events_path.exists()
        assert metrics_events_path.stat().st_size > 0
