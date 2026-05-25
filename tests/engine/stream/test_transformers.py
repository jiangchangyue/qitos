"""Tests for StreamTransformer protocol and built-in transformers (Task 3.3)."""

from __future__ import annotations

import pytest

from qitos.engine.events import EngineEvent, EngineEventType
from qitos.engine.states import RuntimePhase
from qitos.engine.stream.transformer import (
    StreamTransformer,
    TransformerChain,
    TransformerOutput,
)
from qitos.engine.stream.values import ValuesTransformer
from qitos.engine.stream.messages import MessagesTransformer
from qitos.engine.stream.lifecycle import LifecycleTransformer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(
    event_type: EngineEventType,
    step_id: int = 0,
    payload: dict | None = None,
    error: str | None = None,
) -> EngineEvent:
    return EngineEvent(
        event_type=event_type,
        step_id=step_id,
        payload=payload or {},
        error=error,
    )


# ---------------------------------------------------------------------------
# 3.3.1 StreamTransformer protocol
# ---------------------------------------------------------------------------


class TestTransformerOutput:
    def test_defaults(self):
        out = TransformerOutput()
        assert out.type == "custom"
        assert out.value is None
        assert out.step_id == 0
        assert out.metadata == {}

    def test_custom_values(self):
        out = TransformerOutput(type="values", value={"x": 1}, step_id=5)
        assert out.type == "values"
        assert out.value == {"x": 1}
        assert out.step_id == 5


class TestTransformerChain:
    def test_empty_chain(self):
        chain = TransformerChain()
        result = chain.process(_event(EngineEventType.STEP_START))
        assert result == []

    def test_single_transformer(self):
        class DoubleType(StreamTransformer):
            output_type = "double"

            def transform(self, event):
                return TransformerOutput(
                    type=self.output_type,
                    value=event.step_id * 2,
                    step_id=event.step_id,
                )

        chain = TransformerChain([DoubleType()])
        result = chain.process(_event(EngineEventType.STEP_START, step_id=3))
        assert len(result) == 1
        assert result[0].value == 6

    def test_multiple_transformers_in_order(self):
        """Transformers run in the order they were added."""

        class First(StreamTransformer):
            output_type = "first"

            def transform(self, event):
                return TransformerOutput(type="first", value="A", step_id=event.step_id)

        class Second(StreamTransformer):
            output_type = "second"

            def transform(self, event):
                return TransformerOutput(type="second", value="B", step_id=event.step_id)

        chain = TransformerChain([First(), Second()])
        result = chain.process(_event(EngineEventType.STEP_START))
        assert len(result) == 2
        assert result[0].value == "A"
        assert result[1].value == "B"

    def test_transformer_can_suppress_event(self):
        """Returning None from transform() suppresses the output."""

        class FilterType(StreamTransformer):
            output_type = "filter"

            def transform(self, event):
                if event.step_id % 2 == 0:
                    return TransformerOutput(type="filter", value="even", step_id=event.step_id)
                return None

        chain = TransformerChain([FilterType()])
        r1 = chain.process(_event(EngineEventType.STEP_START, step_id=2))
        r2 = chain.process(_event(EngineEventType.STEP_START, step_id=3))
        assert len(r1) == 1
        assert len(r2) == 0

    def test_add_transformer(self):
        chain = TransformerChain()

        class T(StreamTransformer):
            output_type = "t"

            def transform(self, event):
                return TransformerOutput(type="t", value=1, step_id=0)

        chain.add(T())
        result = chain.process(_event(EngineEventType.STEP_START))
        assert len(result) == 1

    def test_lifecycle_callbacks(self):
        called = {"start": False, "end": False}

        class T(StreamTransformer):
            output_type = "t"

            def transform(self, event):
                return None

            def on_run_start(self):
                called["start"] = True

            def on_run_end(self):
                called["end"] = True

        chain = TransformerChain([T()])
        chain.on_run_start()
        chain.on_run_end()
        assert called["start"]
        assert called["end"]


# ---------------------------------------------------------------------------
# 3.3.2 ValuesTransformer
# ---------------------------------------------------------------------------


class TestValuesTransformer:
    def test_step_end_emits_state(self):
        t = ValuesTransformer()
        event = _event(
            EngineEventType.STEP_END,
            step_id=1,
            payload={"state": {"counter": 5}},
        )
        result = t.transform(event)
        assert result is not None
        assert result.type == "values"
        assert result.value == {"counter": 5}

    def test_non_step_end_suppressed(self):
        t = ValuesTransformer()
        event = _event(EngineEventType.STEP_START, step_id=1)
        result = t.transform(event)
        assert result is None

    def test_no_state_in_payload(self):
        t = ValuesTransformer()
        event = _event(EngineEventType.STEP_END, step_id=1)
        result = t.transform(event)
        assert result is not None
        assert result.value is None  # No state available


# ---------------------------------------------------------------------------
# 3.3.3 MessagesTransformer
# ---------------------------------------------------------------------------


class TestMessagesTransformer:
    def test_step_stream_emits_chunk(self):
        t = MessagesTransformer()
        event = _event(
            EngineEventType.STEP_STREAM,
            step_id=1,
            payload={"text": "Hello"},
        )
        result = t.transform(event)
        assert result is not None
        assert result.type == "messages"
        assert result.value["chunk"] == "Hello"
        assert result.metadata["streaming"] is True

    def test_decide_end_emits_full_message(self):
        t = MessagesTransformer()
        # Buffer some chunks
        t.transform(_event(EngineEventType.STEP_STREAM, step_id=1, payload={"text": "Hi"}))
        t.transform(_event(EngineEventType.STEP_STREAM, step_id=1, payload={"text": " there"}))

        # End of decide
        event = _event(
            EngineEventType.DECIDE,
            step_id=1,
            payload={"stage": "end"},
        )
        result = t.transform(event)
        assert result is not None
        assert result.value["content"] == "Hi there"
        assert result.value["role"] == "assistant"
        assert result.metadata["streaming"] is False

    def test_non_matching_event_suppressed(self):
        t = MessagesTransformer()
        event = _event(EngineEventType.ACT, step_id=1)
        result = t.transform(event)
        assert result is None

    def test_buffer_cleared_after_decide_end(self):
        t = MessagesTransformer()
        t.transform(_event(EngineEventType.STEP_STREAM, step_id=1, payload={"text": "first"}))
        t.transform(_event(EngineEventType.DECIDE, step_id=1, payload={"stage": "end"}))
        t.transform(_event(EngineEventType.STEP_STREAM, step_id=2, payload={"text": "second"}))
        t.transform(_event(EngineEventType.DECIDE, step_id=2, payload={"stage": "end"}))

        # Second decide should only have "second"
        result2 = t.transform(_event(EngineEventType.DECIDE, step_id=2, payload={"stage": "end"}))
        # Buffer was cleared, so this is a fresh start
        # Actually, the second DECIDE end already consumed the buffer.
        # Let's verify by creating a new one properly
        t2 = MessagesTransformer()
        t2.transform(_event(EngineEventType.STEP_STREAM, step_id=1, payload={"text": "A"}))
        r1 = t2.transform(_event(EngineEventType.DECIDE, step_id=1, payload={"stage": "end"}))
        assert r1.value["content"] == "A"
        # Buffer is now cleared
        t2.transform(_event(EngineEventType.STEP_STREAM, step_id=2, payload={"text": "B"}))
        r2 = t2.transform(_event(EngineEventType.DECIDE, step_id=2, payload={"stage": "end"}))
        assert r2.value["content"] == "B"

    def test_delta_key_fallback(self):
        t = MessagesTransformer()
        event = _event(
            EngineEventType.STEP_STREAM,
            step_id=1,
            payload={"delta": "chunk"},
        )
        result = t.transform(event)
        assert result.value["chunk"] == "chunk"


# ---------------------------------------------------------------------------
# 3.3.4 LifecycleTransformer
# ---------------------------------------------------------------------------


class TestLifecycleTransformer:
    def test_interrupt_event(self):
        t = LifecycleTransformer()
        event = _event(
            EngineEventType.INTERRUPT,
            step_id=2,
            payload={"reason": "approval_needed"},
        )
        result = t.transform(event)
        assert result is not None
        assert result.type == "lifecycle"
        assert result.value["event"] == "interrupt"
        assert len(t.interrupts) == 1

    def test_run_start_event(self):
        t = LifecycleTransformer()
        event = _event(
            EngineEventType.RUN_START,
            payload={"task": "hello"},
        )
        result = t.transform(event)
        assert result is not None
        assert result.value["event"] == "run_start"
        assert result.value["task"] == "hello"

    def test_run_end_event(self):
        t = LifecycleTransformer()
        event = _event(
            EngineEventType.RUN_END,
            step_id=5,
            payload={"step_count": 5, "stop_reason": "final"},
        )
        result = t.transform(event)
        assert result is not None
        assert result.value["event"] == "run_end"
        assert result.value["step_count"] == 5

    def test_error_event(self):
        t = LifecycleTransformer()
        event = _event(
            EngineEventType.ERROR,
            step_id=3,
            error="tool failed",
        )
        result = t.transform(event)
        assert result is not None
        assert result.value["event"] == "error"
        assert len(t.errors) == 1

    def test_non_lifecycle_suppressed(self):
        t = LifecycleTransformer()
        event = _event(EngineEventType.ACT, step_id=1)
        result = t.transform(event)
        assert result is None

    def test_multiple_interrupts_tracked(self):
        t = LifecycleTransformer()
        t.transform(_event(EngineEventType.INTERRUPT, step_id=1, payload={"r": "a"}))
        t.transform(_event(EngineEventType.INTERRUPT, step_id=2, payload={"r": "b"}))
        assert len(t.interrupts) == 2


# ---------------------------------------------------------------------------
# Chained composition
# ---------------------------------------------------------------------------


class TestChainedComposition:
    def test_values_and_lifecycle_together(self):
        """Values + Lifecycle transformers can coexist in a chain."""
        chain = TransformerChain([ValuesTransformer(), LifecycleTransformer()])

        # STEP_END → ValuesTransformer emits
        results = chain.process(
            _event(EngineEventType.STEP_END, step_id=1, payload={"state": {"x": 1}})
        )
        types = [r.type for r in results]
        assert "values" in types
        # STEP_END is not a lifecycle event, so LifecycleTransformer returns None
        assert "lifecycle" not in types

        # INTERRUPT → LifecycleTransformer emits
        results = chain.process(
            _event(EngineEventType.INTERRUPT, step_id=2, payload={"reason": "approval"})
        )
        types = [r.type for r in results]
        assert "lifecycle" in types

    def test_all_three_together(self):
        chain = TransformerChain([
            ValuesTransformer(),
            MessagesTransformer(),
            LifecycleTransformer(),
        ])

        events = [
            _event(EngineEventType.RUN_START, payload={"task": "test"}),
            _event(EngineEventType.STEP_STREAM, step_id=1, payload={"text": "Hi"}),
            _event(EngineEventType.STEP_END, step_id=1, payload={"state": {"x": 1}}),
            _event(EngineEventType.INTERRUPT, step_id=2, payload={"reason": "approval"}),
        ]

        all_outputs = []
        for event in events:
            all_outputs.extend(chain.process(event))

        types = [o.type for o in all_outputs]
        assert "lifecycle" in types  # RUN_START + INTERRUPT
        assert "messages" in types  # STEP_STREAM
        assert "values" in types  # STEP_END
