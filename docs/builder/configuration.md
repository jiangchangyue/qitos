# Configuration & API Keys

## Goal

Make QiTOS examples runnable in under 5 minutes with one mainstream setup path.

## Recommended setup

Primary examples now read model configuration directly from environment variables:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `QITOS_API_KEY` as a fallback key name
- `QITOS_MODEL` as an optional model name override

Fastest setup:

```bash
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1/"
export OPENAI_API_KEY="<your_api_key>"
export QITOS_MODEL="Qwen/Qwen3-8B"
```

Then run any teaching example directly:

```bash
python examples/patterns/react.py
python examples/real/coding_agent.py
```

## Default example values

If you only set the key and endpoint, the primary examples already default to:

- model name: `Qwen/Qwen3-8B`
- temperature: `0.2`
- max tokens: `2048`

That keeps the example files self-contained and easy to read.

## Keep your API key out of git

Do not hardcode keys in examples or commit them to Git.

Recommended:

- export them in your shell profile, or
- load them from a local `.env` in your shell startup, without committing that file

## Quick verification

```bash
python examples/patterns/react.py
```

If configuration is correct, you should see:

1. terminal UI rendered automatically
2. model/tool activity in the run
3. a trace folder created under `runs/`

## Common errors

1. `Set OPENAI_API_KEY or QITOS_API_KEY before running this example.`
- export one of those keys

2. request 401/403
- the key is invalid or rejected by the endpoint

3. request 404 / model not found
- the provider does not serve the configured model name

4. timeout
- provider unavailable, network/proxy issue, or upstream latency

## Source Index

- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [examples/real/coding_agent.py](https://github.com/Qitor/qitos/blob/main/examples/real/coding_agent.py)
- [qitos/models/openai.py](https://github.com/Qitor/qitos/blob/main/qitos/models/openai.py)
