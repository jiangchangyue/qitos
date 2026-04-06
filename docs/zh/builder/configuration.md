# 配置与 API Key

## 目标

用一条最主流、最省心的路径，把 QiTOS 示例在 5 分钟内跑起来。

## 推荐配置方式

现在主示例直接从环境变量读取模型配置：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `QITOS_API_KEY` 作为备用 key 名
- `QITOS_MODEL` 作为可选模型名覆盖

最快配置：

```bash
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1/"
export OPENAI_API_KEY="<your_api_key>"
export QITOS_MODEL="Qwen/Qwen3-8B"
```

然后直接运行示例：

```bash
python examples/patterns/react.py
python examples/real/coding_agent.py
```

## 示例默认值

只要你提供 key 和 endpoint，主示例已经默认使用：

- 模型名：`Qwen/Qwen3-8B`
- temperature：`0.2`
- max tokens：`2048`

这样示例文件本身就能保持自包含、可读、可改。

## 不要把 API Key 提交到 git

不要在示例里硬编码 key，更不要提交到 GitHub。

推荐做法：

- 在 shell 环境变量里导出，或
- 用本地 `.env` 并在 shell 启动时加载，但不要提交该文件

## 快速自检

```bash
python examples/patterns/react.py
```

如果配置正确，你应该看到：

1. 终端 UI 自动渲染
2. 运行中出现模型与工具调用
3. `runs/` 下自动生成 trace 目录

## 常见问题

1. `Set OPENAI_API_KEY or QITOS_API_KEY before running this example.`
- 先导出 `OPENAI_API_KEY` 或 `QITOS_API_KEY`

2. 401/403
- key 无效、过期，或不匹配当前 endpoint

3. 404 / model not found
- 当前 provider 不支持所配置的模型名

4. timeout
- provider 不可达、网络/代理问题，或上游响应过慢

## Source Index

- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [examples/real/coding_agent.py](https://github.com/Qitor/qitos/blob/main/examples/real/coding_agent.py)
- [qitos/models/openai.py](https://github.com/Qitor/qitos/blob/main/qitos/models/openai.py)
