"""Tests for _EngineProtocol type safety."""
from __future__ import annotations

from unittest.mock import MagicMock

from qitos import AgentModule, StateSchema
from qitos.engine._protocol import _EngineProtocol
from qitos.engine.engine import Engine


class _MinimalAgent(AgentModule):
    name = "test_protocol"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init_state(self, task, **kwargs):
        return StateSchema(task=task, max_steps=3)

    def build_system_prompt(self, state):
        return "You are a test agent."

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        return state


def test_engine_satisfies_protocol():
    """Engine instances satisfy _EngineProtocol at runtime."""
    agent = _MinimalAgent(llm=MagicMock())
    engine = Engine(agent=agent)
    assert isinstance(engine, _EngineProtocol)


def test_protocol_has_required_attributes():
    """_EngineProtocol requires key attributes that Engine provides."""
    agent = _MinimalAgent(llm=MagicMock())
    engine = Engine(agent=agent)
    # Check a sample of protocol attributes
    assert hasattr(engine, "agent")
    assert hasattr(engine, "budget")
    assert hasattr(engine, "context_config")
    assert hasattr(engine, "records")
    assert hasattr(engine, "auto_approve")
    assert hasattr(engine, "_critic_modified_prompt")
    assert hasattr(engine, "_critic_instruction_patch")


def test_protocol_has_required_methods():
    """_EngineProtocol requires key methods that Engine provides."""
    agent = _MinimalAgent(llm=MagicMock())
    engine = Engine(agent=agent)
    assert callable(getattr(engine, "_dispatch_hook", None))
    assert callable(getattr(engine, "_hook_context", None))
    assert callable(getattr(engine, "_emit", None))
    assert callable(getattr(engine, "_memory_append", None))
    assert callable(getattr(engine, "_history_append", None))


def test_runtime_classes_accept_engine():
    """Runtime mixin classes accept Engine instances via _EngineProtocol."""
    from qitos.engine._action_runtime import _ActionRuntime
    from qitos.engine._control_runtime import _ControlRuntime
    from qitos.engine._context_runtime import _ContextRuntime

    agent = _MinimalAgent(llm=MagicMock())
    engine = Engine(agent=agent)

    # These should not raise type errors
    action_rt = _ActionRuntime(engine)
    control_rt = _ControlRuntime(engine)
    context_rt = _ContextRuntime(engine)

    assert action_rt.engine is engine
    assert control_rt.engine is engine
    assert context_rt.engine is engine


def test_stream_bridge_hook_typed_parameters():
    """_StreamBridgeHook methods have properly typed parameters."""
    from qitos.engine.async_engine import _StreamBridgeHook
    from qitos.engine.events import EventStream
    import inspect

    hook = _StreamBridgeHook(EventStream())

    # Verify on_run_start signature uses Engine, not Any
    sig = inspect.signature(hook.on_run_start)
    params = list(sig.parameters.values())
    assert params[2].name == "engine"

    # Verify on_event signature uses RuntimeEvent and StepRecord
    sig = inspect.signature(hook.on_event)
    params = list(sig.parameters.values())
    assert params[0].name == "event"
    assert params[2].name == "record"
    assert params[3].name == "engine"


def test_stream_bridge_hook_emits_events():
    """_StreamBridgeHook emits EngineEvents when hooks fire."""
    from qitos.engine.async_engine import _StreamBridgeHook
    from qitos.engine.events import EventStream, EngineEventType

    stream = EventStream()
    hook = _StreamBridgeHook(stream)

    # Simulate on_run_start
    hook.on_run_start("test task", None, MagicMock())

    # Check event was emitted
    events = list(stream._queue._queue)
    assert len(events) >= 1
    assert events[0].event_type == EngineEventType.RUN_START
