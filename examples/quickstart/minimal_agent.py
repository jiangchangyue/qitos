"""Quickstart: smallest runnable AgentModule + Engine flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qitos import Action, AgentModule, Decision, StateSchema, ToolRegistry, tool

TASK = "compute 40 + 2"
WORKSPACE = Path("./playground/minimal_agent")
MAX_STEPS = 2


@dataclass
class CalcState(StateSchema):
    pass


class MinimalAgent(AgentModule[CalcState, dict[str, Any], Action]):
    def __init__(self):
        registry = ToolRegistry()

        @tool(name="add")
        def add(a: int, b: int) -> int:
            return a + b

        registry.register(add)
        super().__init__(tool_registry=registry)

    def init_state(self, task: str, **kwargs: Any) -> CalcState:
        return CalcState(task=task, max_steps=int(kwargs.get("max_steps", MAX_STEPS)))

    def decide(self, state: CalcState, observation: dict[str, Any]) -> Decision[Action]:
        if state.current_step == 0:
            return Decision.act([Action(name="add", args={"a": 40, "b": 2})], rationale="compute_answer")
        return Decision.final("42")

    def reduce(self, state: CalcState, observation: dict[str, Any], decision: Decision[Action]) -> CalcState:
        action_results = observation.get("action_results", []) if isinstance(observation, dict) else []
        if action_results:
            state.final_result = str(action_results[0])
        return state


def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    agent = MinimalAgent()
    result = agent.run(
        task=TASK,
        workspace=str(WORKSPACE),
        max_steps=MAX_STEPS,
        return_state=True,
    )
    print("workspace:", WORKSPACE)
    print("final_result:", result.state.final_result)
    print("stop_reason:", result.state.stop_reason)


if __name__ == "__main__":
    main()
