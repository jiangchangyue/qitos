"""QitOS Layers — cross-cutting concerns for workflow execution."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from qitos_dag.events import (
    EventType,
    NodeRunFailedEvent,
    NodeRunStartedEvent,
    NodeRunSucceededEvent,
    WorkflowEvent,
)
from qitos_dag.graph_engine import GraphEngineLayer
from qitos_dag.schema import WorkflowSchema


class QitaTracingLayer(GraphEngineLayer):
    """Layer that creates qita-compatible trace spans for workflow events.

    Uses the correct Trace/Span API:
      - provider.create_trace() returns a Trace object
      - trace.create_span(SpanType, SpanData) creates a child Span
      - span.start() / span.finish() manage lifecycle
      - Trace is a context manager (__enter__/__exit__)
    """

    def __init__(self, tracing_provider: Any = None, graph_id: str = "") -> None:
        self.tracing_provider = tracing_provider
        self.graph_id = graph_id
        self._trace: Optional[Any] = None
        self._spans: Dict[str, Any] = {}

    def on_graph_start(self, schema: WorkflowSchema, inputs: Dict[str, Any]) -> None:
        if self.tracing_provider is None:
            return
        self._trace = self.tracing_provider.create_trace(
            name=f"workflow:{schema.title or self.graph_id}",
            metadata={"node_count": len(schema.nodes), "edge_count": len(schema.edges)},
        )
        self._trace.__enter__()

    def on_node_run_start(self, node: Any) -> None:
        if self.tracing_provider is None or self._trace is None:
            return
        from qitos.tracing.models import CustomSpanData, SpanType

        span = self._trace.create_span(
            SpanType.CUSTOM,
            CustomSpanData(name=node.id, data={"node_type": node.node_type}),
        )
        span.start()
        self._spans[node.id] = span

    def on_node_run_end(self, node: Any, error: Optional[Exception] = None) -> None:
        span = self._spans.pop(node.id, None)
        if span is not None:
            span.finish(error=str(error) if error else None)

    def on_event(self, event: WorkflowEvent) -> None:
        """Handle events — create child spans for engine step events."""
        if self._trace is None:
            return
        # Surface child Engine events as sub-spans under the current node span
        if event.data.get("_engine_event"):
            from qitos.tracing.models import CustomSpanData, SpanType

            node_id = event.data.get("node_id", "unknown")
            parent_span = self._spans.get(node_id)
            if parent_span is not None:
                child_span = self._trace.create_span(
                    SpanType.CUSTOM,
                    CustomSpanData(
                        name=f"engine_step:{event.data.get('step_id', '?')}",
                        data=event.data,
                    ),
                )
                child_span.start()
                # Immediately finish — each engine step is instantaneous in DAG time
                child_span.finish()

    def on_graph_end(self, error: Optional[Exception] = None) -> None:
        if self._trace is not None:
            self._trace.__exit__(
                type(error) if error else None,
                error,
                getattr(error, "__traceback__", None),
            )
            self._trace = None


class ExecutionLimitsLayer(GraphEngineLayer):
    """Layer that enforces step and time limits on workflow execution."""

    def __init__(
        self, max_steps: int = 500, max_time_ms: int = 300_000
    ) -> None:
        self.max_steps = max_steps
        self.max_time_ms = max_time_ms
        self._step_count = 0
        self._start_time: float = 0

    def on_graph_start(self, schema: WorkflowSchema, inputs: Dict[str, Any]) -> None:
        self._step_count = 0
        self._start_time = time.monotonic()

    def on_node_run_start(self, node: Any) -> None:
        self._step_count += 1
        elapsed = (time.monotonic() - self._start_time) * 1000

        if self._step_count > self.max_steps:
            raise RuntimeError(
                f"Workflow exceeded max steps ({self.max_steps})"
            )
        if elapsed > self.max_time_ms:
            raise RuntimeError(
                f"Workflow exceeded max time ({self.max_time_ms}ms)"
            )


class CheckpointLayer(GraphEngineLayer):
    """Layer that checkpoints workflow state for pause/resume."""

    def __init__(self, checkpoint_dir: Optional[str] = None) -> None:
        self.checkpoint_dir = checkpoint_dir
        self._snapshot: Optional[Dict[str, Any]] = None

    def on_event(self, event: WorkflowEvent) -> None:
        # After each node success, we could persist a snapshot
        if event.event_type == EventType.NODE_RUN_SUCCEEDED:
            # Snapshot logic would go here
            pass
