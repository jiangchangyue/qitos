"""Bridge processor that routes TracingProvider events to the legacy TraceWriter.

When an Engine is configured with a TracingProvider, this processor
converts Span events into the flat RuntimeEvent format that the old
TraceWriter expects, maintaining backward compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import Span, SpanData, SpanType, Trace
from .processor import TraceProcessor


class LegacyTraceWriterProcessor(TraceProcessor):
    """Bridge from new TracingProvider spans to legacy TraceWriter events.

    Usage::

        from qitos.tracing import LegacyTraceWriterProcessor

        processor = LegacyTraceWriterProcessor(trace_writer)
        provider.add_processor(processor)
    """

    def __init__(self, trace_writer: Any) -> None:
        self._writer = trace_writer
        self._trace_map: Dict[str, Dict[str, Any]] = {}

    def on_trace_start(self, trace: Trace) -> None:
        self._trace_map[trace.trace_id] = {
            "trace_id": trace.trace_id,
            "name": trace.name,
            "group_id": trace.group_id,
            "metadata": trace.metadata,
        }

    def on_trace_end(self, trace: Trace) -> None:
        self._trace_map.pop(trace.trace_id, None)

    def on_span_start(self, span: Span) -> None:
        pass  # Legacy writer doesn't have a start concept

    def on_span_end(self, span: Span) -> None:
        """Convert span to a flat event and write to legacy TraceWriter."""
        if self._writer is None:
            return

        from ..engine.states import RuntimePhase

        # Map span data type to RuntimePhase
        span_type_str = span.data.type if span.data else "custom"
        phase = _span_type_str_to_phase(span_type_str)

        payload = {
            "run_id": span.trace_id,
            "step_id": 0,
            "phase": phase.value if phase else "unknown",
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
        }

        # Add span data details to payload
        if span.data is not None:
            try:
                exported = span.data.export()
                payload["span_data"] = exported
            except Exception:
                pass

        if span.error:
            payload["error"] = span.error

        # Use legacy writer's write_event method
        try:
            from ..trace.events import TraceEvent
            event = TraceEvent(
                run_id=self._writer.run_id,
                step_id=0,
                phase=phase.value if phase else "unknown",
                payload=payload,
                ok=span.error is None,
                error=span.error,
            )
            self._writer.write_event(event)
        except Exception:
            # Graceful degradation: if conversion fails, skip
            pass

    def shutdown(self) -> None:
        if self._writer is not None and hasattr(self._writer, "flush"):
            try:
                self._writer.flush()
            except Exception:
                pass

    def force_flush(self) -> None:
        self.shutdown()


def _span_type_str_to_phase(span_type_str: str) -> Any:
    """Map a span type string to a RuntimePhase for legacy compatibility."""
    from ..engine.states import RuntimePhase

    mapping = {
        "agent": RuntimePhase.DECIDE,
        "step": RuntimePhase.DECIDE,
        "decide": RuntimePhase.DECIDE,
        "act": RuntimePhase.ACT,
        "reduce": RuntimePhase.REDUCE,
        "critic": RuntimePhase.CRITIC,
        "tool": RuntimePhase.ACT,
        "handoff": RuntimePhase.ACT,
        "generation": RuntimePhase.DECIDE,
        "mcp": RuntimePhase.ACT,
    }
    return mapping.get(span_type_str, RuntimePhase.ACT)
