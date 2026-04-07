from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qitos import AgentModule, Decision, StateSchema, ToolRegistry
from qitos.core.tool import tool
from qitos.engine import Engine
from qitos.kit import MiniMaxToolCallParser
from qitos.models.profile_registry import infer_default_protocol, infer_model_profile
from qitos.protocols import get_protocol


def test_model_profile_registry_infers_minimax_protocol() -> None:
    profile = infer_model_profile("MiniMax-M2.5")
    assert profile is not None
    assert profile.default_protocol == "minimax_tool_call_v1"
    assert infer_default_protocol("unknown-model") == "react_text_v1"


def test_tool_registry_renders_minimax_schema() -> None:
    registry = ToolRegistry()

    @tool(name="send_terminal_keys")
    def send_terminal_keys(keystrokes: str, duration_sec: float = 0.1) -> dict[str, Any]:
        """
        Send keystrokes to the terminal.

        :param keystrokes: Raw terminal input.
        :param duration_sec: Time to wait after sending input.
        """

        return {"ok": True}

    registry.register(send_terminal_keys)
    rendered = registry.get_tool_descriptions(protocol="minimax_tool_call_v1")
    assert "<invoke name=\"send_terminal_keys\">" in rendered
    assert "<parameter name=\"keystrokes\"" in rendered


def test_minimax_parser_handles_wrapped_tool_call() -> None:
    parser = MiniMaxToolCallParser()
    decision = parser.parse(
        """I will call the tool now.
<minimax:tool_call>
  <invoke name="send_terminal_keys">
    <parameter name="keystrokes">pwd\n</parameter>
    <parameter name="duration_sec">0.5</parameter>
  </invoke>
</minimax:tool_call>
Done."""
    )
    assert decision.mode == "act"
    assert decision.actions[0]["name"] == "send_terminal_keys"
    assert decision.meta["parser_diagnostics"]["salvage_applied"] is True


@dataclass
class _ProtocolState(StateSchema):
    last_rationale: str = ""


class _DummyModel:
    def __init__(self, model: str, output: str):
        self.model = model
        self.output = output
        self.calls: list[list[dict[str, str]]] = []

    def __call__(self, messages):
        self.calls.append(list(messages))
        return self.output


class _ProtocolAgent(AgentModule[_ProtocolState, dict[str, Any], dict[str, Any]]):
    name = "protocol_demo"

    def __init__(self, llm: Any):
        super().__init__(tool_registry=ToolRegistry(), llm=llm)

    def init_state(self, task: str, **kwargs: Any) -> _ProtocolState:
        return _ProtocolState(task=task, max_steps=int(kwargs.get("max_steps", 3)))

    def build_system_prompt(self, state: _ProtocolState) -> str | None:
        _ = state
        return self.compose_system_prompt("Return one completion or tool action.", protocol=self.active_protocol())

    def reduce(
        self,
        state: _ProtocolState,
        observation: dict[str, Any],
        decision: Decision[dict[str, Any]],
    ) -> _ProtocolState:
        _ = observation
        if decision.meta.get("task_complete_requested"):
            state.final_result = decision.rationale or "done"
            state.stop_reason = "success"
        state.last_rationale = decision.rationale or ""
        return state


def test_engine_uses_protocol_fallback_chain() -> None:
    llm = _DummyModel(
        model="MiniMax-M2.5",
        output='{"analysis":"done","plan":"finish","commands":[],"task_complete":true}',
    )
    result = Engine(agent=_ProtocolAgent(llm=llm)).run("finish the task")
    assert result.state.stop_reason == "success"
    assert result.records[0].protocol_id == "terminus_json_v1"
    assert result.records[0].parser_selected == "TerminusJsonParser"
    assert result.records[0].parser_fallback_used is True
    assert any(
        item.get("protocol") == "minimax_tool_call_v1" and item.get("result") == "error"
        for item in result.records[0].parser_attempts
    )
    assert any(
        item.get("protocol") == "terminus_json_v1" and item.get("result") == "success"
        for item in result.records[0].parser_attempts
    )


def test_get_protocol_returns_builtin_protocol() -> None:
    protocol = get_protocol("minimax_tool_call_v1")
    assert protocol is not None
    assert protocol.id == "minimax_tool_call_v1"
    assert protocol.supports_native_tool_call_markup is True
