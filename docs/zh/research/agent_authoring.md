# 编写新 AgentModule

## 目标

只实现策略代码，把运行时编排留给 Engine。

## 最小必需方法

1. `init_state(task, **kwargs)`
2. `reduce(state, observation, decision)`

## 常用可选方法

1. `build_system_prompt(state)`
2. `prepare(state)`
3. `decide(state, observation)`
4. `should_stop(state)`

## 推荐实现路径

大多数新 Agent，推荐按下面这条主线来：

1. 定义一个小而清楚的 `StateSchema` 子类
2. 把提示词和 parser 一起设计
3. 实现 `prepare`
4. 让 `decide` 返回 `None`
5. 实现 `reduce`
6. 用 `agent.run(...)` 跑起来

这样可以把策略代码留在 agent 里，同时把 runtime 配置放在调用侧，而不需要你手动去拼 `Engine(...)`。

## 模板

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

## 实战建议

- `prepare` 要短、要有界。
- `reduce` 只做状态转移，不做 I/O。
- 所有外部操作都放在 tool/env，不要放进 `reduce`。
- 提示词格式和 parser 必须成对设计。
- 用 `agent.run(..., history_policy=...)` 控制模型看到的 history。
- memory 检索逻辑始终显式写在 `prepare` 里，通过 `self.memory` 访问。

## Happy Path 运行方式

```python
result = agent.run(
    task="完成这个任务",
    workspace="./playground",
    max_steps=8,
    trace=True,
    render=True,
    return_state=True,
)
```
