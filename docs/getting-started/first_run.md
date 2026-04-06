# First Run (Minimal + LLM)

## Goal

Get two end-to-end runs working:

1. a minimal run without an LLM, just to validate the kernel loop
2. an LLM-backed ReAct run, to validate model + parser + tools + trace

## 0) Configure the model once

Primary QiTOS examples read:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `QITOS_API_KEY` as a fallback

Fastest setup:

```bash
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1/"
export OPENAI_API_KEY="<your_api_key>"
```

## 1) Run the minimal agent

```bash
python examples/quickstart/minimal_agent.py
```

What to check:

1. the script completes with a final result
2. the stop reason is explicit
3. a trace run appears under `runs/`

## 2) Run an LLM-backed agent

```bash
python examples/patterns/react.py
```

This exercises the default Engine path:

- `decide(...) -> None`
- Engine assembles `system + history + prepared user input`
- Engine calls `llm(messages)`
- parser turns model text into `Decision`
- Engine executes the action and reduces back into state

What to check:

1. terminal render appears automatically
2. tool calls and observations are visible in the run
3. `runs/` contains the trace artifacts

## Why this matters

The same happy path scales from teaching demos to real agents:

- author the policy in `AgentModule`
- run through `agent.run(...)`
- get trace + terminal UI by default

## Next

- Model setup details: [Configuration & API Keys](../builder/configuration.md)
- Inspect runs with qita: [qita Guide](../builder/qita.md)

## Source Index

- [examples/quickstart/minimal_agent.py](https://github.com/Qitor/qitos/blob/main/examples/quickstart/minimal_agent.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
