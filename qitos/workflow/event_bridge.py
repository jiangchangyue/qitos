"""Event Bridge — bidirectional event surfacing between DAG and Engine.

When a child Engine runs inside an AgentNode, its EngineEvents need to
surface in the parent GraphEngine's event stream. Conversely, when a
WorkflowTool triggers a DAG from inside Engine, the DAG's WorkflowEvents
need to surface in the parent Engine's event stream.

This module provides two bridge classes:
- EngineToDagBridge: EngineHook that forwards EngineEvents as synthetic
  WorkflowEvents into the parent GraphEngine's event queue.
- DagToEngineBridge: GraphEngineLayer that forwards WorkflowEvents as
  EngineEvents into the parent Engine's EventStream.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from qitos_dag.events import EventType, WorkflowEvent


class EngineToDagHook:
    """EngineHook that forwards Engine events to a DAG callback.

    Install this hook on a child Engine (inside AgentNode._delegate)
    to surface Engine step/phase events as synthetic WorkflowEvents
    in the parent GraphEngine's event stream.

    Usage:
        hook = EngineToDagHook(emit_callback=my_emit, node_id="agent1")
        engine = Engine(agent=..., hooks=[hook.as_engine_hook()])
    """

    def __init__(
        self,
        emit_callback: Callable[[WorkflowEvent], None],
        node_id: str,
    ) -> None:
        self._emit = emit_callback
        self._node_id = node_id

    def as_engine_hook(self) -> Any:
        """Return an EngineHook instance that forwards events."""
        hook = self

        class _BridgeHook:
            """Minimal EngineHook that forwards on_after_step."""

            def on_after_step(self, ctx: Any, engine: Any) -> None:
                from qitos_dag.events import NodeRunSucceededEvent

                step_id = getattr(ctx, "step_id", 0)
                phase = getattr(ctx, "phase", None)
                phase_str = getattr(phase, "value", str(phase)) if phase else ""

                event = NodeRunSucceededEvent(
                    graph_id="",
                    data={
                        "_engine_event": True,
                        "node_id": hook._node_id,
                        "step_id": step_id,
                        "phase": phase_str,
                    },
                )
                hook._emit(event)

            def on_run_end(self, result: Any, engine: Any) -> None:
                from qitos_dag.events import NodeRunSucceededEvent

                state = getattr(result, "state", None)
                event = NodeRunSucceededEvent(
                    graph_id="",
                    data={
                        "_engine_event": True,
                        "node_id": hook._node_id,
                        "event": "engine_run_end",
                        "stop_reason": getattr(state, "stop_reason", None),
                        "final_result": getattr(state, "final_result", None),
                    },
                )
                hook._emit(event)

        return _BridgeHook()


class DagToEngineLayer:
    """GraphEngineLayer that forwards DAG events to an Engine EventStream.

    Install this layer on a child GraphEngine (inside WorkflowTool)
    to surface DAG node events as EngineEvents in the parent Engine's
    event stream.

    Usage:
        layer = DagToEngineLayer(event_stream=engine_event_stream)
        engine = GraphEngine(schema=..., layers=[layer])
    """

    def __init__(self, event_stream: Any = None) -> None:
        self._event_stream = event_stream

    def on_event(self, event: WorkflowEvent) -> None:
        """Forward WorkflowEvent as a synthetic EngineEvent."""
        if self._event_stream is None:
            return

        from qitos.engine.events import EngineEvent, EngineEventType

        # Map DAG event types to Engine event types
        dag_type = event.event_type
        node_id = event.data.get("node_id", "")

        if dag_type == EventType.GRAPH_RUN_STARTED:
            engine_type = EngineEventType.RUN_START
        elif dag_type == EventType.GRAPH_RUN_SUCCEEDED:
            engine_type = EngineEventType.RUN_END
        elif dag_type == EventType.GRAPH_RUN_FAILED:
            engine_type = EngineEventType.RUN_END
        elif dag_type == EventType.NODE_RUN_STARTED:
            engine_type = EngineEventType.STEP_START
        elif dag_type == EventType.NODE_RUN_SUCCEEDED:
            engine_type = EngineEventType.STEP_END
        elif dag_type == EventType.NODE_RUN_FAILED:
            engine_type = EngineEventType.STEP_END
        else:
            engine_type = EngineEventType.CUSTOM if hasattr(EngineEventType, "CUSTOM") else EngineEventType.ERROR

        engine_event = EngineEvent(
            event_type=engine_type,
            agent_id=node_id,
            ok=dag_type not in (EventType.GRAPH_RUN_FAILED, EventType.NODE_RUN_FAILED),
            payload={
                "_dag_event": True,
                "dag_event_type": dag_type.value if hasattr(dag_type, "value") else str(dag_type),
                "data": event.data,
            },
        )
        self._event_stream.emit(engine_event)
