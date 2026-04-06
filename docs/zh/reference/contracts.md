# Contracts & Guarantees

## Prompt ↔ Parser 契约

提示词输出格式和 parser 必须匹配。

- ReAct 文本提示词 → `ReActTextParser`
- XML 提示词 → XML parser
- JSON 提示词 → JSON parser

如果你改了输出格式却没改 parser，就破坏了契约。

## AgentModule ↔ Engine 契约

QitOS 把运行循环保持为显式结构：

```text
state -> prepare -> model/decide -> action/env -> observation -> reduce -> next state
```

- `AgentModule` 定义策略、状态转移和模型输入。
- `Engine` 负责生命周期、工具执行、停止判定、trace 与 hooks。
- 当 `decide` 返回 `None` 时，就进入默认的 Engine 模型路径。

## Tool 输入 / 输出契约

- 工具应暴露清晰且稳定的参数名。
- 工具结果应优先返回结构化字典，而不是模糊文本。
- agent 应基于 observation 推理，而不是假设工具已经完成了某种副作用。

## Trace / Run Artifact 契约

trace 工件是正式输出，不是临时调试垃圾。

- `runs/` 保存结构化运行结果。
- `qita` 基于这些结果做 board、replay 与 export。
- benchmark、examples 和 real agents 共享同一套 artifact 模型。

## 为什么重要

正是这些契约，让 QitOS 能同时服务研究、真实 agent 和评测工作流，而且保持可比较、可调试、可复用。
