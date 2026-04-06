# Author New Agent Modules

## Goal

Build a new agent by implementing only policy code, while keeping runtime behavior in Engine.

## Minimal required methods

1. `init_state(task, **kwargs)`
2. `reduce(state, observation, decision)`

## Common optional methods

1. `build_system_prompt(state)`
2. `prepare(state)`
3. `decide(state, observation)`
4. `should_stop(state)`

## Recommended authoring path

For most new agents, use this path:

1. define a small `StateSchema` subclass
2. define prompt + parser together
3. implement `prepare`
4. let `decide` return `None`
5. implement `reduce`
6. run with `agent.run(...)`

This keeps policy code in the agent and runtime configuration in the call site, without forcing you to manually wire `Engine(...)`.

## Template

```python
from dataclasses import dataclass, field
from typing import Any

from qitos import Action, AgentModule, Decision, StateSchema

@dataclass
class MyState(StateSchema):
    notes: list[str] = field(default_factory=list)

class MyAgent(AgentModule[MyState, dict[str, Any], Action]):
    def init_state(self, task: str, **kwargs: Any) -> MyState:
        return MyState(task=task, max_steps=int(kwargs.get("max_steps", 8)))

    def prepare(self, state: MyState) -> str:
        return f"Task: {state.task}\nStep: {state.current_step}"

    def decide(self, state: MyState, observation: dict[str, Any]):
        return None

    def reduce(self, state: MyState, observation: dict[str, Any], decision: Decision[Action]) -> MyState:
        state.notes.append(f"mode={decision.mode}")
        results = observation.get("action_results", [])
        if results:
            state.notes.append(f"result={results[0]}")
        state.notes = state.notes[-30:]
        return state
```

## Practical guidance

- Keep `prepare` concise and bounded.
- Let `reduce` be state transition only.
- Put all I/O in tools/env, not in `reduce`.
- Keep stop logic explicit (`final`, `should_stop`, criteria).
- Treat prompt format and parser as one contract.
- Use `history_policy=...` on `agent.run(...)` to control model-facing history.
- Keep memory retrieval explicit inside `prepare`, via `self.memory`.

## Happy-path run

```python
result = agent.run(
    task="solve the task",
    workspace="./playground",
    max_steps=8,
    trace=True,
    render=True,
    return_state=True,
)
```

## Source Index

- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [qitos/engine/engine.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/engine.py)
