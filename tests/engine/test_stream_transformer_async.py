"""Tests for StreamTransformer async support."""
from __future__ import annotations
import asyncio
import pytest
from qitos.engine.stream.transformer import (
    StreamTransformer,
    TransformerChain,
    TransformerOutput,
)
from qitos.engine.events import EngineEvent, EngineEventType


class SyncTransformer(StreamTransformer):
    """A simple sync transformer for testing."""
    output_type = "sync"

    def transform(self, event: EngineEvent):
        if event.event_type == EngineEventType.RUN_START:
            return TransformerOutput(type="sync", value=event.payload)
        return None


class AsyncTransformer(StreamTransformer):
    """A transformer with custom async implementation."""
    output_type = "async_custom"

    def transform(self, event: EngineEvent):
        return TransformerOutput(type="sync_fallback", value="sync")

    async def atransform(self, event: EngineEvent):
        if event.event_type == EngineEventType.RUN_START:
            return TransformerOutput(type="async_custom", value=event.payload)
        return None


def _make_event(event_type=EngineEventType.RUN_START, payload=None):
    return EngineEvent(event_type=event_type, payload=payload or {})


def test_default_atransform_delegates_to_transform():
    """Default atransform() delegates to sync transform()."""
    t = SyncTransformer()
    event = _make_event(payload={"task": "test"})
    result = asyncio.run(t.atransform(event))
    assert result is not None
    assert result.type == "sync"
    assert result.value == {"task": "test"}


def test_custom_atransform_overrides_default():
    """Subclass atransform() overrides the default delegation."""
    t = AsyncTransformer()
    event = _make_event(payload={"task": "async"})

    # Sync transform returns different value
    sync_result = t.transform(event)
    assert sync_result.type == "sync_fallback"

    # Async transform returns custom value
    result = asyncio.run(t.atransform(event))
    assert result.type == "async_custom"
    assert result.value == {"task": "async"}


def test_atransform_returns_none_for_suppressed_events():
    """atransform returns None for events that transform returns None for."""
    t = SyncTransformer()
    event = _make_event(event_type=EngineEventType.RUN_END)
    result = asyncio.run(t.atransform(event))
    assert result is None


def test_transformer_chain_aprocess():
    """TransformerChain.aprocess() runs all transformers asynchronously."""
    chain = TransformerChain([SyncTransformer(), AsyncTransformer()])
    event = _make_event(payload={"task": "chain"})
    results = asyncio.run(chain.aprocess(event))
    assert len(results) == 2
    assert results[0].type == "sync"
    assert results[1].type == "async_custom"


def test_transformer_chain_aprocess_suppresses_none():
    """TransformerChain.aprocess() filters out None results."""
    class SelectiveAsync(StreamTransformer):
        output_type = "selective"
        def transform(self, event):
            return None
        async def atransform(self, event):
            if event.event_type == EngineEventType.RUN_START:
                return TransformerOutput(type="selective", value="yes")
            return None

    chain = TransformerChain([SelectiveAsync()])
    start_event = _make_event(event_type=EngineEventType.RUN_START)
    end_event = _make_event(event_type=EngineEventType.RUN_END)

    results_start = asyncio.run(chain.aprocess(start_event))
    results_end = asyncio.run(chain.aprocess(end_event))

    assert len(results_start) == 1
    assert len(results_end) == 0


def test_chain_process_still_works_sync():
    """Sync TransformerChain.process() still works after adding aprocess."""
    chain = TransformerChain([SyncTransformer()])
    event = _make_event(payload={"task": "sync"})
    results = chain.process(event)
    assert len(results) == 1
    assert results[0].type == "sync"
