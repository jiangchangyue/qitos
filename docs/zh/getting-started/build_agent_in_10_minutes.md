# 10 分钟搭一个 Agent

## 目标

用 QiTOS 最小但实用的主线，从零搭出一个可运行的大模型 Agent：

1. 定义 state
2. 定义 system prompt
3. 定义 `prepare`
4. 让 Engine 自动完成模型调用与解析
5. 定义 `reduce`
6. 用 `agent.run(...)` 跑起来

这篇文档只讲 **推荐主线**。对于这个工作流，你不需要手动实例化 `Engine(...)`。

## 第 1 步：定义 state

state 要小、清楚、只放下一步决策真正需要的东西。

```python
from dataclasses import dataclass, field
from qitos import StateSchema

@dataclass
class FixState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"
    test_command: str = 'python -c "import buggy_module; assert buggy_module.add(20, 22) == 42"'
```

`task`、`current_step`、`max_steps`、`final_result`、`stop_reason` 这些内核字段已经由 `StateSchema` 提供。

## 第 2 步：提示词和 parser 一起设计

提示词格式和 parser 是同一个契约。

如果你想用 ReAct 文本格式：

```python
from qitos.kit import ReActTextParser

SYSTEM_PROMPT = """
你是一个谨慎的代码修复 Agent。

规则：
- 每一步只能调用一个工具。
- 修改前先阅读。
- 修改后要跑验证。

输出契约：
Thought: <一句简洁推理>
Action: <tool_name>(arg=value, ...)
或
Final Answer: <改了什么，以及什么验证通过了>
""".strip()
```

就应该配：

```python
parser = ReActTextParser()
```

不要写 ReAct 提示词，却挂一个 JSON 或 XML parser。

## 第 3 步：在构造函数里注册工具

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

这里就是 Agent 的可执行表面。模型如果不能从这里调用工具，运行时就不能用。

## 第 4 步：实现 `init_state`、`build_system_prompt` 和 `prepare`

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

`prepare` 要短。它的任务是帮助模型做出下一步决策，而不是把整个世界塞进去。

## 第 5 步：让 Engine 自动走模型路径

当 `decide` 返回 `None` 时，Engine 会自动执行：

1. `prepare(state)`
2. 组装 `system + history + 当前 user message`
3. 调用 `llm(messages)`
4. 解析成 `Decision`

```python
    def decide(self, state: FixState, observation: dict[str, Any]):
        return None
```

这是 QiTOS 里最简单、最常见的路径。

## 第 6 步：把工具证据 reduce 回 state

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

可以记一个很简单的原则：

- `prepare` 负责把 state 变成模型输入
- `reduce` 负责把证据变成下一轮 state

## 第 7 步：直接用 happy path 跑起来

```python
# llm = ...
# agent = FixAgent(llm=llm, workspace_root="./playground")

result = agent.run(
    task="修复 buggy_module.py，并让测试通过。",
    workspace="./playground",
    max_steps=8,
    return_state=True,
)

print(result.state.final_result)
print(result.state.stop_reason)
```

这就是我们推荐大多数用户起步的方式。终端 UI 和 trace 默认就是开启的。

## 什么时候再加别的

只有真的需要时再加：

- `history_policy=...`：改模型看到的历史窗口
- `memory=...`：在 `prepare` 里检索长期任务记忆
- `critics=[...]`：加自反思/重试控制
- `search=...`：给 ToT 这类分支 Agent 加选择器
- 结构化 `Task(...)`：当你需要 resources、env_spec、benchmark/eval 可复现性时再用

## 心智模型

你应该始终记住的运行链是：

```text
state -> prepare -> model -> decision -> action/env -> observation -> reduce -> next state
```

QiTOS 的设计目标，就是把这条链做得显式、可组合、可追踪。

## 下一步看什么

建议按这条 canonical 顺序继续：

- `examples/quickstart/minimal_agent.py`
- `examples/patterns/react.py`
- `examples/patterns/planact.py`
- `examples/real/coding_agent.py`

之后再进入其它 `examples/real/` 示例；当你需要批量评测与恢复运行时，再看 `examples/benchmarks/`。

## Source Index

- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [qitos/core/state.py](https://github.com/Qitor/qitos/blob/main/qitos/core/state.py)
- [examples/quickstart/minimal_agent.py](https://github.com/Qitor/qitos/blob/main/examples/quickstart/minimal_agent.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [examples/real/coding_agent.py](https://github.com/Qitor/qitos/blob/main/examples/real/coding_agent.py)
