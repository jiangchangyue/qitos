# History

## 目标

明确 QitOS 中消息历史（History）的归属和用法。

## 归属

History 归属于 `AgentModule`（`self.history`），未设置时使用 Engine 运行时 history。

## 契约

`History` 提供：

- `append(message)`
- `retrieve(query, state, observation)`
- `summarize(max_items)`
- `reset(run_id)`

## Engine 使用方式

默认模型路径（`decide -> None`）下，Engine 按如下顺序组装消息：

1. `system`（可选）
2. 按 `history_policy` 选择的 history 消息
3. 当前 `prepare(state)` 生成的 `user` 消息

Engine 会把当前轮 user/assistant 消息写入 history。

典型 history 序列：

- `system`
- `user`
- `assistant`
- `user`
- `assistant`
- ...

## HistoryPolicy

在运行时调用上配置：

- `roles`
- `max_messages`
- `step_window`
- `max_tokens`
- 以及 `pending_content`、`model_name`、`phase`、`query_kind` 这类 history 可消费的查询上下文

典型 happy path：

```python
agent.run(
    task="做点什么",
    workspace="./playground",
    history_policy=HistoryPolicy(max_messages=12),
)
```

## CompactHistory

当你希望框架自动压缩面向模型的上下文，而不是只靠简单滑动窗口时，可以使用 `CompactHistory`。

`CompactHistory` 是显式 opt-in 的预设，包含：

- 接近预算时的 compact warning 元数据
- 对旧长消息 / tool-heavy 内容的 microcompact
- 对更早轮次的 continuation summary compact
- 通过 Engine 正常事件写入 trace/qita 的 compact 事件

典型用法：

```python
from qitos import HistoryPolicy
from qitos.kit import CompactHistory

agent.history = CompactHistory(llm=llm, max_tokens=2200, keep_last_rounds=2)

agent.run(
    task="修复 bug",
    workspace="./playground",
    history_policy=HistoryPolicy(max_messages=16, max_tokens=2200),
)
```

可直接参考：

- `examples/real/react_compact_agent.py`

## Source Index

- [qitos/core/history.py](https://github.com/Qitor/qitos/blob/main/qitos/core/history.py)
- [qitos/engine/engine.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/engine.py)
- [qitos/kit/history/window_history.py](https://github.com/Qitor/qitos/blob/main/qitos/kit/history/window_history.py)
- [qitos/kit/history/compact_history.py](https://github.com/Qitor/qitos/blob/main/qitos/kit/history/compact_history.py)
