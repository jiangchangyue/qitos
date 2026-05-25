"""Tests for the QitOS hierarchical tracing system (qitos.tracing)."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict

import pytest

from qitos.tracing import (
    TracingProvider,
    Trace,
    Span,
    SpanData,
    SpanType,
    TraceProcessor,
    TracingMode,
    set_trace_processors,
    add_trace_processor,
    set_tracing_disabled,
    set_tracing_mode,
    get_tracing_provider,
    create_trace,
)
from qitos.tracing.models import (
    AgentSpanData,
    StepSpanData,
    DecideSpanData,
    ActSpanData,
    ReduceSpanData,
    CriticSpanData,
    ToolSpanData,
    HandoffSpanData,
    GenerationSpanData,
    MCPSpanData,
    CustomSpanData,
    NoOpSpan,
    NoOpTrace,
    _current_span,
)
from qitos.tracing.processor import (
    SynchronousMultiTraceProcessor,
    NoOpTraceProcessor,
)
from qitos.tracing.console import ConsoleTraceProcessor
from qitos.tracing.json_processor import JsonFileTraceProcessor
from qitos.tracing.config import RedactingSpanData, _redact_dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RecordingProcessor(TraceProcessor):
    """Processor that records every call for assertions."""

    def __init__(self) -> None:
        self.trace_starts: list = []
        self.trace_ends: list = []
        self.span_starts: list = []
        self.span_ends: list = []

    def on_trace_start(self, trace: Trace) -> None:
        self.trace_starts.append(trace)

    def on_trace_end(self, trace: Trace) -> None:
        self.trace_ends.append(trace)

    def on_span_start(self, span: Span) -> None:
        self.span_starts.append(span)

    def on_span_end(self, span: Span) -> None:
        self.span_ends.append(span)


# ---------------------------------------------------------------------------
# 1. SpanData models
# ---------------------------------------------------------------------------


class TestSpanDataModels:
    def test_agent_span_data_export(self) -> None:
        data = AgentSpanData("planner", model="gpt-4", tools=["search"])
        exported = data.export()
        assert exported["type"] == "agent"
        assert exported["name"] == "planner"
        assert exported["model"] == "gpt-4"
        assert exported["tools"] == ["search"]

    def test_tool_span_data_export(self) -> None:
        data = ToolSpanData(tool_name="bash", tool_args={"cmd": "ls"}, output_content="files")
        exported = data.export()
        assert exported["type"] == "tool"
        assert exported["tool_name"] == "bash"
        assert exported["tool_args"] == {"cmd": "ls"}
        assert exported["output_content"] == "files"

    def test_generation_span_data_export(self) -> None:
        data = GenerationSpanData(
            model="claude-3",
            input_content="prompt",
            output_content="response",
            token_usage={"prompt_tokens": 10, "completion_tokens": 20},
        )
        exported = data.export()
        assert exported["model"] == "claude-3"
        assert exported["token_usage"]["prompt_tokens"] == 10

    def test_mcp_span_data_export(self) -> None:
        data = MCPSpanData(server_name="fs_server", tool_name="read_file")
        exported = data.export()
        assert exported["type"] == "mcp"
        assert exported["server_name"] == "fs_server"

    def test_custom_span_data_export(self) -> None:
        data = CustomSpanData(name="my_span", data={"key": "val"})
        exported = data.export()
        assert exported["type"] == "custom"
        assert exported["name"] == "my_span"
        assert exported["data"] == {"key": "val"}

    def test_all_span_data_types_match_enum(self) -> None:
        """Every concrete SpanData subclass .type should match a SpanType."""
        instances = [
            AgentSpanData("a"),
            StepSpanData(1),
            DecideSpanData(),
            ActSpanData(),
            ReduceSpanData(),
            CriticSpanData(),
            ToolSpanData(tool_name="t"),
            HandoffSpanData(),
            GenerationSpanData(),
            MCPSpanData(),
            CustomSpanData(name="c"),
        ]
        enum_values = {e.value for e in SpanType}
        for inst in instances:
            assert inst.type in enum_values, (
                f"{type(inst).__name__}.type={inst.type!r} not in SpanType"
            )

    def test_step_span_data(self) -> None:
        data = StepSpanData(step_number=3, observation="obs", decision="dec")
        exported = data.export()
        assert exported["type"] == "step"
        assert exported["step_number"] == 3
        assert exported["observation"] == "obs"

    def test_decide_span_data(self) -> None:
        data = DecideSpanData(
            input_content="question",
            output_content="answer",
            model_response={"choices": [1]},
        )
        exported = data.export()
        assert exported["type"] == "decide"
        assert exported["model_response"] == {"choices": [1]}

    def test_handoff_span_data(self) -> None:
        data = HandoffSpanData(from_agent="a", to_agent="b")
        exported = data.export()
        assert exported["from_agent"] == "a"
        assert exported["to_agent"] == "b"

    def test_critic_span_data(self) -> None:
        data = CriticSpanData(critic_name="safety", score=0.9)
        exported = data.export()
        assert exported["critic_name"] == "safety"
        assert exported["score"] == 0.9

    def test_act_span_data(self) -> None:
        data = ActSpanData(action_name="run", tool_args={"x": 1}, output_content="done")
        exported = data.export()
        assert exported["action_name"] == "run"
        assert exported["tool_args"] == {"x": 1}

    def test_reduce_span_data(self) -> None:
        data = ReduceSpanData(input_count=5, output_content="merged")
        exported = data.export()
        assert exported["input_count"] == 5
        assert exported["output_content"] == "merged"


# ---------------------------------------------------------------------------
# 2. Span lifecycle
# ---------------------------------------------------------------------------


class TestSpanLifecycle:
    def test_span_start_sets_timestamp(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("t") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            assert span.started_at is not None
            span.finish()

    def test_span_finish_sets_end_and_duration(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("t") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
            assert span.ended_at is not None
            assert span.ended_at >= span.started_at  # type: ignore[operator]

    def test_span_finish_with_error(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("t") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish(error="boom")
            assert span.error == "boom"

    def test_span_set_output(self) -> None:
        span = Span(trace_id="t", span_id="s", data=AgentSpanData("a"))
        span.set_output({"result": 42})
        assert span.output == {"result": 42}

    def test_span_export_roundtrip(self) -> None:
        provider = TracingProvider()
        with provider.create_trace("t") as trace:
            span = trace.create_span(SpanType.TOOL, ToolSpanData(tool_name="bash"))
            span.start()
            span.finish()
            exported = span.export()
            assert exported["trace_id"] == trace.trace_id
            assert exported["data"]["type"] == "tool"
            assert exported["data"]["tool_name"] == "bash"
            assert exported["started_at"] is not None
            assert exported["ended_at"] is not None

    def test_span_repr(self) -> None:
        span = Span(trace_id="t1", span_id="s1", data=AgentSpanData("a"))
        r = repr(span)
        assert "s1" in r
        assert "agent" in r


# ---------------------------------------------------------------------------
# 3. Trace context manager and span nesting
# ---------------------------------------------------------------------------


class TestTraceAndNesting:
    def test_trace_context_manager_calls_processor(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("my-trace") as trace:
            pass
        assert len(rec.trace_starts) == 1
        assert len(rec.trace_ends) == 1
        assert rec.trace_starts[0].name == "my-trace"

    def test_nested_spans_have_parent(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("nested") as trace:
            parent = trace.create_span(SpanType.AGENT, AgentSpanData("parent"))
            parent.start()
            # child is created while parent is the current span
            child = trace.create_span(SpanType.TOOL, ToolSpanData(tool_name="ls"))
            child.start()
            assert child.parent_span_id == parent.span_id
            child.finish()
            parent.finish()

    def test_trace_export_includes_all_spans(self) -> None:
        provider = TracingProvider()
        with provider.create_trace("export-test") as trace:
            s1 = trace.create_span(SpanType.AGENT, AgentSpanData("a1"))
            s1.start()
            s1.finish()
            s2 = trace.create_span(SpanType.TOOL, ToolSpanData(tool_name="t"))
            s2.start()
            s2.finish()
        exported = trace.export()
        assert len(exported["spans"]) == 2
        assert exported["spans"][0]["data"]["name"] == "a1"
        assert exported["spans"][1]["data"]["tool_name"] == "t"

    def test_trace_repr(self) -> None:
        provider = TracingProvider()
        trace = provider.create_trace("repr-test")
        r = repr(trace)
        assert "repr-test" in r

    def test_trace_group_id_and_metadata(self) -> None:
        provider = TracingProvider()
        trace = provider.create_trace(
            "grouped",
            group_id="g1",
            metadata={"env": "test"},
        )
        assert trace.group_id == "g1"
        assert trace.metadata == {"env": "test"}

    def test_sibling_spans_share_parent(self) -> None:
        """Two spans created at the same nesting level share the same parent."""
        rec = _RecordingProcessor()
        provider = TracingProvider(processors=[rec])
        with provider.create_trace("siblings") as trace:
            parent = trace.create_span(SpanType.AGENT, AgentSpanData("root"))
            parent.start()
            child1 = trace.create_span(SpanType.TOOL, ToolSpanData(tool_name="t1"))
            child1.start()
            child1.finish()
            child2 = trace.create_span(SpanType.TOOL, ToolSpanData(tool_name="t2"))
            child2.start()
            child2.finish()
            parent.finish()
        assert child1.parent_span_id == parent.span_id
        assert child2.parent_span_id == parent.span_id


# ---------------------------------------------------------------------------
# 4. NoOp sentinels
# ---------------------------------------------------------------------------


class TestNoOpSentinels:
    def test_noop_span_is_noop(self) -> None:
        span = NoOpSpan()
        result = span.start()
        assert result is span
        span.finish()
        span.set_output("anything")
        assert span.export() == {}

    def test_noop_trace_is_noop(self) -> None:
        trace = NoOpTrace()
        with trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            assert isinstance(span, NoOpSpan)
        assert trace.export() == {}

    def test_disabled_provider_returns_noop(self) -> None:
        provider = TracingProvider(mode=TracingMode.DISABLED)
        trace = provider.create_trace("disabled")
        assert isinstance(trace, NoOpTrace)


# ---------------------------------------------------------------------------
# 5. Processor fan-out and error isolation
# ---------------------------------------------------------------------------


class TestProcessorFanOut:
    def test_multi_processor_fans_out(self) -> None:
        rec1 = _RecordingProcessor()
        rec2 = _RecordingProcessor()
        multi = SynchronousMultiTraceProcessor([rec1, rec2])
        provider = TracingProvider(processors=[multi])
        with provider.create_trace("fanout") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
        assert len(rec1.span_starts) == 1
        assert len(rec2.span_starts) == 1

    def test_error_isolation(self) -> None:
        """A failing processor must not prevent others from being called."""

        class _FailingProcessor(TraceProcessor):
            def on_trace_start(self, trace): raise RuntimeError("fail")
            def on_trace_end(self, trace): raise RuntimeError("fail")
            def on_span_start(self, span): raise RuntimeError("fail")
            def on_span_end(self, span): raise RuntimeError("fail")

        rec = _RecordingProcessor()
        multi = SynchronousMultiTraceProcessor([_FailingProcessor(), rec])
        provider = TracingProvider(processors=[multi])
        with provider.create_trace("error-iso") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
        # The second processor should still have been called
        assert len(rec.span_starts) == 1
        assert len(rec.span_ends) == 1

    def test_noop_processor_does_nothing(self) -> None:
        noop = NoOpTraceProcessor()
        # Should not raise
        noop.on_trace_start(NoOpTrace())
        noop.on_trace_end(NoOpTrace())
        noop.on_span_start(NoOpSpan())
        noop.on_span_end(NoOpSpan())
        noop.shutdown()
        noop.force_flush()

    def test_multi_processor_add_remove(self) -> None:
        rec = _RecordingProcessor()
        multi = SynchronousMultiTraceProcessor()
        multi.add_processor(rec)
        assert len(multi.processors) == 1
        multi.remove_processor(rec)
        assert len(multi.processors) == 0
        # Removing non-existent should not raise
        multi.remove_processor(rec)

    def test_multi_processor_shutdown_and_flush(self) -> None:
        rec = _RecordingProcessor()
        multi = SynchronousMultiTraceProcessor([rec])
        # These should not raise even on a plain RecordingProcessor
        multi.shutdown()
        multi.force_flush()


# ---------------------------------------------------------------------------
# 6. Redaction (ENABLED_WITHOUT_DATA)
# ---------------------------------------------------------------------------


class TestRedaction:
    def test_redacting_span_data_hides_sensitive_fields(self) -> None:
        original = ToolSpanData(
            tool_name="secret_tool",
            tool_args={"password": "hunter2"},
            output_content="sensitive result",
        )
        redacted = RedactingSpanData(original)
        exported = redacted.export()
        assert exported["tool_args"] == "__redacted__"
        assert exported["output_content"] == "__redacted__"
        assert exported["tool_name"] == "secret_tool"  # not redacted

    def test_redacting_span_data_preserves_type(self) -> None:
        original = ToolSpanData(tool_name="t")
        redacted = RedactingSpanData(original)
        assert redacted.type == "tool"

    def test_redact_dict_recursive(self) -> None:
        data = {
            "tool_args": {"a": 1},
            "output_content": "secret",
            "safe_field": "visible",
            "nested": {
                "model_response": {"choices": []},
                "other": 42,
            },
        }
        result = _redact_dict(data)
        assert result["tool_args"] == "__redacted__"
        assert result["output_content"] == "__redacted__"
        assert result["safe_field"] == "visible"
        assert result["nested"]["model_response"] == "__redacted__"
        assert result["nested"]["other"] == 42

    def test_provider_enabled_without_data_redacts(self) -> None:
        rec = _RecordingProcessor()
        provider = TracingProvider(
            processors=[rec],
            mode=TracingMode.ENABLED_WITHOUT_DATA,
        )
        with provider.create_trace("redact-test") as trace:
            span = trace.create_span(
                SpanType.TOOL,
                ToolSpanData(tool_name="t", tool_args={"k": "v"}, output_content="out"),
            )
            span.start()
            span.finish()
        # The span recorded by the processor at on_span_end should be redacted
        ended_span = rec.span_ends[0]
        exported = ended_span.export()
        assert exported["data"]["tool_args"] == "__redacted__"
        assert exported["data"]["output_content"] == "__redacted__"

    def test_redact_with_list_values(self) -> None:
        data = {
            "items": [
                {"tool_args": "x", "name": "ok"},
                {"safe": "yes"},
            ],
        }
        result = _redact_dict(data)
        assert result["items"][0]["tool_args"] == "__redacted__"
        assert result["items"][0]["name"] == "ok"
        assert result["items"][1]["safe"] == "yes"


# ---------------------------------------------------------------------------
# 7. ConsoleTraceProcessor
# ---------------------------------------------------------------------------


class TestConsoleTraceProcessor:
    def test_console_processor_logs_without_error(self) -> None:
        processor = ConsoleTraceProcessor()
        provider = TracingProvider(processors=[processor])
        with provider.create_trace("console-test") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("logger"))
            span.start()
            span.finish()
        # If we reach here without exception, the processor works

    def test_console_processor_duration_calculation(self) -> None:
        provider = TracingProvider()
        with provider.create_trace("dur-test") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
        ms = ConsoleTraceProcessor._duration_ms(span)
        assert isinstance(ms, int)


# ---------------------------------------------------------------------------
# 8. JsonFileTraceProcessor
# ---------------------------------------------------------------------------


class TestJsonFileTraceProcessor:
    def test_batch_mode_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = JsonFileTraceProcessor(output_dir=tmpdir)
            provider = TracingProvider(processors=[processor])
            with provider.create_trace("json-test") as trace:
                span = trace.create_span(
                    SpanType.TOOL,
                    ToolSpanData(tool_name="bash"),
                )
                span.start()
                span.finish()
            path = os.path.join(tmpdir, f"trace_{trace.trace_id}.json")
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["name"] == "json-test"
            assert len(data["spans"]) == 1

    def test_streaming_mode_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = JsonFileTraceProcessor(
                output_dir=tmpdir, streaming=True
            )
            provider = TracingProvider(processors=[processor])
            with provider.create_trace("stream-test") as trace:
                span = trace.create_span(
                    SpanType.AGENT,
                    AgentSpanData("a"),
                )
                span.start()
                span.finish()
            path = os.path.join(tmpdir, f"trace_{trace.trace_id}.jsonl")
            assert os.path.exists(path)
            with open(path) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            # Expect at least 1 span line + 1 trace_end line
            assert len(lines) >= 2
            assert lines[0]["type"] == "span"
            assert lines[-1]["type"] == "trace_end"

    def test_batch_mode_trace_with_multiple_spans(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = JsonFileTraceProcessor(output_dir=tmpdir)
            provider = TracingProvider(processors=[processor])
            with provider.create_trace("multi-span") as trace:
                for i in range(5):
                    span = trace.create_span(
                        SpanType.STEP,
                        StepSpanData(step_number=i),
                    )
                    span.start()
                    span.finish()
            path = os.path.join(tmpdir, f"trace_{trace.trace_id}.json")
            with open(path) as f:
                data = json.load(f)
            assert len(data["spans"]) == 5


# ---------------------------------------------------------------------------
# 9. Global configuration helpers
# ---------------------------------------------------------------------------


class TestGlobalConfig:
    def test_set_trace_processors_replaces(self) -> None:
        rec = _RecordingProcessor()
        set_trace_processors([rec])
        provider = get_tracing_provider()
        # Reset mode in case a previous test disabled it
        set_tracing_mode(TracingMode.ENABLED)
        with create_trace("global-proc") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
        assert len(rec.span_starts) == 1
        # Clean up
        set_trace_processors([])

    def test_set_tracing_disabled(self) -> None:
        set_tracing_disabled(True)
        trace = create_trace("disabled-global")
        assert isinstance(trace, NoOpTrace)
        # Re-enable
        set_tracing_disabled(False)

    def test_add_trace_processor_appends(self) -> None:
        set_trace_processors([])
        rec = _RecordingProcessor()
        add_trace_processor(rec)
        set_tracing_mode(TracingMode.ENABLED)
        with create_trace("add-proc") as trace:
            span = trace.create_span(SpanType.AGENT, AgentSpanData("a"))
            span.start()
            span.finish()
        assert len(rec.span_starts) == 1
        # Clean up
        set_trace_processors([])

    def test_get_tracing_provider_returns_provider(self) -> None:
        provider = get_tracing_provider()
        assert isinstance(provider, TracingProvider)


# ---------------------------------------------------------------------------
# 10. Provider ID generation
# ---------------------------------------------------------------------------


class TestProviderIdGeneration:
    def test_gen_trace_id_unique(self) -> None:
        ids = {TracingProvider.gen_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_gen_span_id_unique(self) -> None:
        ids = {TracingProvider.gen_span_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# 11. TracingMode
# ---------------------------------------------------------------------------


class TestTracingMode:
    def test_mode_values(self) -> None:
        assert TracingMode.ENABLED.value == "enabled"
        assert TracingMode.ENABLED_WITHOUT_DATA.value == "enabled_without_data"
        assert TracingMode.DISABLED.value == "disabled"

    def test_mode_is_str_enum(self) -> None:
        assert isinstance(TracingMode.ENABLED, str)
