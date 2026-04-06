# Examples

Examples are split into two layers.

## 1. Teaching examples

These are the files users should read first.
They are intentionally short, self-contained, and runnable without CLI plumbing.

- `examples/quickstart/`
- `examples/patterns/`
- `examples/real/` single-task demos

All primary examples follow the same shape:

- top-level constants for task / workspace / model defaults
- direct model setup from environment variables
- one `AgentModule`
- one `agent.run(...)`
- terminal UI and trace on by default

## 2. Benchmark runners

Benchmark/eval runners are allowed to be more operational:

- GAIA
- Tau-Bench
- CyBench

These files may keep benchmark loops, resume logic, JSONL export, and concurrency.

## Required environment variables

Never commit API keys.

```bash
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1/"
export OPENAI_API_KEY="your_api_key"
```

Optional:

```bash
export QITOS_MODEL="Qwen/Qwen3-8B"
```

## Quickstart

```bash
python examples/quickstart/minimal_agent.py
python examples/patterns/react.py
python examples/patterns/planact.py
python examples/patterns/reflexion.py
```

## Real agents

```bash
python examples/real/coding_agent.py
python examples/real/swe_agent.py
python examples/real/computer_use_agent.py
python examples/real/epub_reader_agent.py
```

Notes:

- `examples/real/epub_reader_agent.py` expects a local EPUB at `./playground/epub_reader_agent/book.epub`.
- benchmark/eval runners remain under `examples/real/` because they are full workflows, not teaching-first demos.
