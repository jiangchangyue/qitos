# 第一次运行（最小示例 + LLM 示例）

## 目标

跑通两个完整闭环：

1. 不调用 LLM 的最小示例，用来确认内核主线没问题
2. 调用大模型的 ReAct 示例，用来确认 model + parser + tool + trace 全链路

## 0）先配置一次模型

主示例默认读取：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `QITOS_API_KEY` 作为备用

最快配置：

```bash
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1/"
export OPENAI_API_KEY="<your_api_key>"
```

## 1）运行最小 Agent

```bash
python examples/quickstart/minimal_agent.py
```

你需要确认：

1. 脚本顺利结束并给出 final result
2. stop reason 是明确的
3. `runs/` 下出现 trace run 目录

## 2）运行一个 LLM 驱动的 Agent

```bash
python examples/patterns/react.py
```

这一步会经过默认 Engine 主线：

- `decide(...) -> None`
- Engine 组装 `system + history + prepare 后的 user 输入`
- Engine 调用 `llm(messages)`
- parser 把模型输出解析成 `Decision`
- Engine 执行动作，再 reduce 回 state

你需要确认：

1. 终端 UI 会自动出现
2. 工具调用和 Observation 在运行过程中可见
3. `runs/` 里包含本次运行的 trace 工件

## 为什么这很重要

这条 happy path 会一直延续到真实 Agent：

- 用 `AgentModule` 写策略
- 用 `agent.run(...)` 跑起来
- 默认就带 trace 和 terminal UI

## 下一步

- 模型配置细节：见 [配置与 API Key](../builder/configuration.md)
- 用 qita 复盘运行：见 [qita 使用指南](../builder/qita.md)

## Source Index

- [examples/quickstart/minimal_agent.py](https://github.com/Qitor/qitos/blob/main/examples/quickstart/minimal_agent.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
