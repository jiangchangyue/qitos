"""Tests for LegacyTraceWriterProcessor bridge."""

from __future__ import annotations

from unittest.mock import MagicMock

from qitos.tracing.legacy_processor import LegacyTraceWriterProcessor
from qitos.tracing.models import Span, SpanType, Trace, ActSpanData, ToolSpanData


class TestLegacyTraceWriterProcessor:
    def test_on_trace_start_end(self):
        writer = MagicMock()
        processor = LegacyTraceWriterProcessor(writer)
        trace = Trace(trace_id="t1", name="test_run")
        processor.on_trace_start(trace)
        assert "t1" in processor._trace_map
        processor.on_trace_end(trace)
        assert "t1" not in processor._trace_map

    def test_on_span_end_writes_event(self):
        writer = MagicMock()
        writer.run_id = "run_1"
        processor = LegacyTraceWriterProcessor(writer)

        trace = Trace(trace_id="t1", name="test_run")
        processor.on_trace_start(trace)

        data = ActSpanData(action_name="read_file")
        span = Span(
            trace_id="t1",
            span_id="s1",
            data=data,
        )
        span.started_at = "2026-01-01T00:00:00Z"
        span.finish()

        processor.on_span_end(span)
        writer.write_event.assert_called_once()

    def test_on_span_end_no_writer(self):
        processor = LegacyTraceWriterProcessor(None)
        data = ToolSpanData(tool_name="bash", tool_args={"cmd": "ls"})
        span = Span(
            trace_id="t1",
            span_id="s1",
            data=data,
        )
        span.finish()
        # Should not raise
        processor.on_span_end(span)

    def test_on_span_end_with_error(self):
        writer = MagicMock()
        writer.run_id = "run_1"
        processor = LegacyTraceWriterProcessor(writer)

        data = ActSpanData(action_name="write_file")
        span = Span(
            trace_id="t1",
            span_id="s1",
            data=data,
        )
        span.error = "test error"
        span.finish()
        processor.on_span_end(span)
        writer.write_event.assert_called_once()

    def test_shutdown_flushes_writer(self):
        writer = MagicMock()
        processor = LegacyTraceWriterProcessor(writer)
        processor.shutdown()
        writer.flush.assert_called_once()

    def test_shutdown_no_writer(self):
        processor = LegacyTraceWriterProcessor(None)
        # Should not raise
        processor.shutdown()

    def test_force_flush_delegates_to_shutdown(self):
        writer = MagicMock()
        processor = LegacyTraceWriterProcessor(writer)
        processor.force_flush()
        writer.flush.assert_called_once()
