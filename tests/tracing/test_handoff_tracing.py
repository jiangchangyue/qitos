"""Tests for Handoff tracing integration — HandoffSpanData and TracingProvider span writing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from qitos.tracing.models import HandoffSpanData, SpanType
from qitos.engine._handoff_runtime import _HandoffRuntime


# ---------------------------------------------------------------------------
# HandoffSpanData
# ---------------------------------------------------------------------------


class TestHandoffSpanData:
    def test_type_is_handoff(self):
        sd = HandoffSpanData(from_agent="a1", to_agent="a2")
        assert sd.type == SpanType.HANDOFF.value

    def test_basic_export(self):
        sd = HandoffSpanData(from_agent="planner", to_agent="coder")
        data = sd.export()
        assert data["from_agent"] == "planner"
        assert data["to_agent"] == "coder"
        assert data["type"] == "handoff"

    def test_export_with_context_strategy(self):
        sd = HandoffSpanData(
            from_agent="a1",
            to_agent="a2",
            context_strategy="summary",
        )
        data = sd.export()
        assert data["context_strategy"] == "summary"

    def test_export_with_messages_passed(self):
        sd = HandoffSpanData(
            from_agent="a1",
            to_agent="a2",
            messages_passed=5,
        )
        data = sd.export()
        assert data["messages_passed"] == 5

    def test_export_omits_none_optional_fields(self):
        sd = HandoffSpanData(from_agent="a1", to_agent="a2")
        data = sd.export()
        assert "context_strategy" not in data
        assert "messages_passed" not in data

    def test_full_export(self):
        sd = HandoffSpanData(
            from_agent="planner",
            to_agent="coder",
            output_content="result",
            context_strategy="full",
            messages_passed=10,
        )
        data = sd.export()
        assert data == {
            "type": "handoff",
            "from_agent": "planner",
            "to_agent": "coder",
            "output_content": "result",
            "context_strategy": "full",
            "messages_passed": 10,
        }


# ---------------------------------------------------------------------------
# _HandoffRuntime._write_handoff_span integration
# ---------------------------------------------------------------------------


class TestHandoffSpanWriting:
    def test_no_span_when_no_provider(self):
        engine = MagicMock()
        engine._tracing_provider = None
        rt = _HandoffRuntime(engine)
        # Should not raise
        rt._write_handoff_span("a1", "a2", "full", 5)

    def test_trace_failure_does_not_raise(self):
        engine = MagicMock()
        engine._tracing_provider = MagicMock()
        engine._tracing_provider.create_trace.side_effect = RuntimeError("trace fail")
        rt = _HandoffRuntime(engine)
        # Should swallow the exception
        rt._write_handoff_span("a1", "a2", "full", 5)

    def test_writes_span_with_real_provider(self):
        """Test _write_handoff_span with a real TracingProvider."""
        from qitos.tracing.provider import TracingProvider
        from qitos.tracing.processor import TraceProcessor

        collected_spans = []

        class SpanCollector(TraceProcessor):
            def on_trace_start(self, trace):
                pass

            def on_trace_end(self, trace):
                for span in trace._spans:
                    collected_spans.append(span)

            def on_span_start(self, span):
                pass

            def on_span_end(self, span):
                pass

        provider = TracingProvider(processors=[SpanCollector()])
        engine = MagicMock()
        engine._tracing_provider = provider

        rt = _HandoffRuntime(engine)
        rt._write_handoff_span("planner", "coder", "summary", 3)

        assert len(collected_spans) == 1
        span = collected_spans[0]
        assert isinstance(span.data, HandoffSpanData)
        assert span.data.from_agent == "planner"
        assert span.data.to_agent == "coder"
        assert span.data.context_strategy == "summary"
        assert span.data.messages_passed == 3


# ---------------------------------------------------------------------------
# HandoffSpanData with TracingProvider end-to-end
# ---------------------------------------------------------------------------


class TestHandoffSpanDataTracingProvider:
    def test_handoff_span_flows_through_processor(self):
        from qitos.tracing.provider import TracingProvider
        from qitos.tracing.processor import TraceProcessor

        events = []

        class Recorder(TraceProcessor):
            def on_trace_start(self, trace):
                events.append(("trace_start", trace.name))

            def on_trace_end(self, trace):
                events.append(("trace_end", trace.name))
                for span in trace._spans:
                    events.append(("span_data", span.data.export()))

            def on_span_start(self, span):
                events.append(("span_start", span.data.type))

            def on_span_end(self, span):
                events.append(("span_end", span.data.type))

        provider = TracingProvider(processors=[Recorder()])
        with provider.create_trace(name="handoff:a->b") as trace:
            span_data = HandoffSpanData(
                from_agent="a",
                to_agent="b",
                context_strategy="summary",
                messages_passed=7,
            )
            span = trace.create_span(SpanType.HANDOFF, span_data)
            span.start()
            span.finish()

        assert ("trace_start", "handoff:a->b") in events
        assert ("trace_end", "handoff:a->b") in events
        assert ("span_start", "handoff") in events
        assert ("span_end", "handoff") in events

        span_exports = [e for e in events if e[0] == "span_data"]
        assert len(span_exports) == 1
        exported = span_exports[0][1]
        assert exported["from_agent"] == "a"
        assert exported["to_agent"] == "b"
        assert exported["context_strategy"] == "summary"
        assert exported["messages_passed"] == 7
