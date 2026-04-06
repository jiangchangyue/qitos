# AgentModule (API Reference)

## Role

`AgentModule` defines agent semantics.
`Engine` owns execution, orchestration, trace, and hooks.

For most users, `AgentModule` is the main object to author.

## Required methods

- `init_state(task: str, **kwargs) -> State`
- `reduce(state, observation, decision) -> State`

## Optional methods

- `build_system_prompt(state) -> str | None`
- `prepare(state) -> str`
- `decide(state, observation) -> Decision | None`
- `should_stop(state) -> bool`

## Decision semantics

- return a `Decision`: fully custom policy path
- return `None`: default Engine model path

Default Engine model path:

```text
prepare -> history assembly -> llm(messages) -> parser -> Decision
```

## Preferred run path

For normal single-run workflows, instantiate the agent and call `agent.run(...)`.

```python
result = agent.run(
    task="fix the bug",
    workspace="./playground",
    max_steps=8,
    return_state=True,
)
```

By default, `agent.run(...)` now enables:

- terminal rendering
- trace writing into `runs/`

Use `trace=False` or `render=False` only when you explicitly want to turn them off.

Use `Engine(...)` directly only when you want a reusable advanced runtime configuration.

## Memory and History semantics

Memory and history are different on purpose.

- `self.memory`: task-level retrieval store used by your agent inside `prepare`
- `self.history`: message history used by Engine to assemble model input when `decide(...)` returns `None`

Typical usage:

- put long-term or selective retrieval logic in memory
- let Engine manage message history with `HistoryPolicy`

## Prompt-parser contract

Prompt format and parser must agree.

Examples:

- ReAct prompt -> `ReActTextParser`
- XML decision prompt -> `XmlDecisionParser`
- JSON decision prompt -> `JsonDecisionParser`

This is a hard runtime contract.

## Minimal skeleton

```python
from dataclasses import dataclass, field
from typing import Any

from qitos import Action, AgentModule, Decision, StateSchema, ToolRegistry, tool
from qitos.kit import ReActTextParser

@dataclass
class S(StateSchema):
    scratchpad: list[str] = field(default_factory=list)

@tool(name="add")
def add(a: int, b: int) -> int:
    return a + b

class A(AgentModule[S, dict[str, Any], Action]):
    def __init__(self, llm: Any):
        reg = ToolRegistry()
        reg.register(add)
        super().__init__(tool_registry=reg, llm=llm, model_parser=ReActTextParser())

    def init_state(self, task: str, **kwargs: Any) -> S:
        return S(task=task, max_steps=6)

    def build_system_prompt(self, state: S) -> str | None:
        return "Use ReAct and return one action or Final Answer."

    def prepare(self, state: S) -> str:
        return f"Task: {state.task}\nRecent: {state.scratchpad[-6:]}"

    def decide(self, state: S, observation: dict[str, Any]):
        return None

    def reduce(self, state: S, observation: dict[str, Any], decision: Decision[Action]) -> S:
        if decision.rationale:
            state.scratchpad.append(f"Thought: {decision.rationale}")
        if decision.actions:
            state.scratchpad.append(f"Action: {decision.actions[0]}")
        results = observation.get("action_results", [])
        if results:
            state.scratchpad.append(f"Observation: {results[0]}")
        return state
```

## Source Index

- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [docs/research/agent_authoring.md](../research/agent_authoring.md)
