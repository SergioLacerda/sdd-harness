from sdd_telemetry.otel.protocol import OtelExporter


class _MinimalExporter:
    def export_event(self, attributes, *, trace_id=None, span_id=None) -> None:
        pass

    def shutdown(self) -> None:
        pass


class _MissingShutdown:
    def export_event(self, attributes, *, trace_id=None, span_id=None) -> None:
        pass


class _MissingExportEvent:
    def shutdown(self) -> None:
        pass


def test_minimal_exporter_satisfies_protocol() -> None:
    assert isinstance(_MinimalExporter(), OtelExporter)


def test_missing_shutdown_fails_protocol() -> None:
    assert not isinstance(_MissingShutdown(), OtelExporter)


def test_missing_export_event_fails_protocol() -> None:
    assert not isinstance(_MissingExportEvent(), OtelExporter)


def test_plain_object_fails_protocol() -> None:
    assert not isinstance(object(), OtelExporter)


def test_protocol_is_runtime_checkable() -> None:
    exporter = _MinimalExporter()
    result = isinstance(exporter, OtelExporter)
    assert result is True
