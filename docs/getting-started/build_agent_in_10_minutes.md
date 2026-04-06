# Build an Agent in 10 Minutes

## Goal

Go from zero to a runnable LLM agent with the smallest useful QiTOS authoring pattern:

1. define state
2. define a system prompt
3. define `prepare`
4. let Engine do model calling + parsing
5. define `reduce`
6. run with `agent.run(...)`

This page intentionally teaches the **blessed path**. You do not need to instantiate `Engine(...)` directly for this workflow.

## Step 1: define state

Keep state small and explicit. Only put in it what the agent needs in order to decide the next step.

```python
from dataclasses import dataclass, field
from qitos import StateSchema

@dataclass
class FixState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"
    test_command: str = 'python -c "import buggy_module; assert buggy_module.add(20, 22) == 42"'
```

Kernel fields such as `task`, `current_step`, `max_steps`, `final_result`, and `stop_reason` already come from `StateSchema`.

## Step 2: define the prompt and parser together

Prompt shape and parser are one contract.

If you want ReAct-style text:

```python
from qitos.kit import ReActTextParser

SYSTEM_PROMPT = """
You are a careful coding agent.

Rules:
- Exactly one tool call per step.
- Inspect before editing.
- Run verification after edits.

Output contract:
Thought: <one concise sentence>
Action: <tool_name>(arg=value, ...)
or
Final Answer: <what changed and what passed>
""".strip()
```

Then pair it with:

```python
parser = ReActTextParser()
```

Do not write a ReAct prompt and then attach a JSON or XML parser.

## Step 3: register tools in the agent constructor

```python
from typing import Any
from qitos import Action, AgentModule, Decision, ToolRegistry
from qitos.kit import EditorToolSet, ReActTextParser, RunCommand

class FixAgent(AgentModule[FixState, dict[str, Any], Action]):
    def __init__(self, llm: Any, workspace_root: str):
        reg = ToolRegistry()
        reg.include(EditorToolSet(workspace_root=workspace_root))
        reg.register(RunCommand(cwd=workspace_root))
        super().__init__(
            tool_registry=reg,
            llm=llm,
            model_parser=ReActTextParser(),
        )
```

This is your executable surface. If the model cannot call a tool here, it cannot use it at runtime.

## Step 4: implement `init_state`, `build_system_prompt`, and `prepare`

```python
    def init_state(self, task: str, **kwargs: Any) -> FixState:
        return FixState(task=task, max_steps=int(kwargs.get("max_steps", 8)))

    def build_system_prompt(self, state: FixState) -> str | None:
        return SYSTEM_PROMPT

    def prepare(self, state: FixState) -> str:
        lines = [
            f"Task: {state.task}",
            f"Target file: {state.target_file}",
            f"Test command: {state.test_command}",
            f"Step: {state.current_step}/{state.max_steps}",
        ]
        if state.scratchpad:
            lines.append("Recent trajectory:")
            lines.extend(state.scratchpad[-6:])
        return "\n".join(lines)
```

`prepare` should stay short. It should help the next decision, not dump the world.

## Step 5: let Engine do the model call

If you return `None` from `decide`, Engine automatically does:

1. `prepare(state)`
2. assemble `system + history + current user message`
3. call `llm(messages)`
4. parse output into `Decision`

```python
    def decide(self, state: FixState, observation: dict[str, Any]):
        return None
```

This is the simplest and most common path in QiTOS.

## Step 6: reduce tool evidence into the next state

```python
    def reduce(
        self,
        state: FixState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> FixState:
        if decision.rationale:
            state.scratchpad.append(f"Thought: {decision.rationale}")
        if decision.actions:
            state.scratchpad.append(f"Action: {decision.actions[0]}")

        results = observation.get("action_results", [])
        if results:
            first = results[0]
            state.scratchpad.append(f"Observation: {first}")
            if isinstance(first, dict) and int(first.get("returncode", 1)) == 0:
                state.final_result = "Bug fixed and verification passed."

        state.scratchpad = state.scratchpad[-30:]
        return state
```

The rule of thumb is simple:

- `prepare` tells the model what it needs to know
- `reduce` turns evidence into the next state

## Step 7: run it with the happy path

```python
# llm = ...
# agent = FixAgent(llm=llm, workspace_root="./playground")

result = agent.run(
    task="Fix buggy_module.py and make the test pass.",
    workspace="./playground",
    max_steps=8,
    return_state=True,
)

print(result.state.final_result)
print(result.state.stop_reason)
```

This is the path we recommend most users start with. Terminal UI and trace are enabled by default.

## When to add more

Add more only when you actually need it:

- `history_policy=...`: change model-facing history selection
- `memory=...`: retrieve task-relevant long-term information inside `prepare`
- `critics=[...]`: add self-reflection / retry policy
- `search=...`: enable branch selection for ToT-like agents
- structured `Task(...)`: use when you need resources, env specs, or benchmark/eval reproducibility

## Mental model

The runtime loop you should keep in mind is:

```text
state -> prepare -> model -> decision -> action/env -> observation -> reduce -> next state
```

QiTOS keeps that loop explicit, typed, and traceable.

## Source Index

- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [qitos/core/state.py](https://github.com/Qitor/qitos/blob/main/qitos/core/state.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [examples/real/coding_agent.py](https://github.com/Qitor/qitos/blob/main/examples/real/coding_agent.py)
