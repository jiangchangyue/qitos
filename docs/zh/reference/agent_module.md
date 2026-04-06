# AgentModule（API 参考）

## 职责

`AgentModule` 定义 agent 的策略语义。
`Engine` 负责执行、编排、trace 与 hooks。

对于大多数用户，`AgentModule` 就是主要需要编写的对象。

## 必须实现的方法

- `init_state(task: str, **kwargs) -> State`
- `reduce(state, observation, decision) -> State`

## 可选覆盖的方法

- `build_system_prompt(state) -> str | None`
- `prepare(state) -> str`
- `decide(state, observation) -> Decision | None`
- `should_stop(state) -> bool`

## 决策语义

- 返回 `Decision`：完全自定义策略路径
- 返回 `None`：走 Engine 默认模型路径

默认模型路径是：

```text
prepare -> history assembly -> llm(messages) -> parser -> Decision
```

## 推荐运行方式

普通单次运行，推荐直接实例化 agent 然后调用 `agent.run(...)`：

```python
result = agent.run(
    task="修掉这个 bug",
    workspace="./playground",
    max_steps=8,
    return_state=True,
)
```

现在 `agent.run(...)` 默认会开启：

- 终端渲染
- 写入 `runs/` 的 trace

只有在你明确不需要时，才传 `trace=False` 或 `render=False`。

只有当你要复用一套高级 runtime 配置时，才建议直接使用 `Engine(...)`。

## Memory 与 History 语义

Memory 和 History 是两个不同概念。

- `self.memory`：任务级检索存储，供 agent 在 `prepare` 中主动使用
- `self.history`：消息历史，供 Engine 在 `decide(...)` 返回 `None` 时组装模型输入

推荐理解：

- 长期或选择性检索逻辑放到 memory
- 面向模型的消息历史交给 Engine + `HistoryPolicy`

## 提示词-解析器契约

提示词格式与 parser 必须严格匹配。

例如：

- ReAct 提示词 -> `ReActTextParser`
- XML 决策提示词 -> `XmlDecisionParser`
- JSON 决策提示词 -> `JsonDecisionParser`

这是运行时硬契约，不只是写 prompt 的风格问题。

## 最小骨架

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
- [docs/zh/research/agent_authoring.md](../research/agent_authoring.md)
