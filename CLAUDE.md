# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Installation (development mode)
pip install -e .
pip install -e ".[models,yaml,benchmarks]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_architecture_layout.py

# Run specific test
pytest tests/test_architecture_layout.py::test_kit_has_only_package_root_file

# Run with coverage
pytest --cov=qitos

# Build package
python -m build

# CLI tools
qita board --logdir runs    # View run overview
qita view <run_id>          # Inspect trajectory
qita replay <run_id>        # Playback execution
```

## Single Kernel Rule (Critical Architecture Constraint)

The **only** execution mainline is: `AgentModule + Engine + Trace`

There is no parallel runtime model and no alternative execution abstraction in the public API. Extensions (parsers, critics, memory adapters, toolkits) must attach to this pipeline but may not introduce a second orchestrator.

## Core Architecture Separation

| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
| **AgentModule** | Strategy layer: state, prompts, decision policy, reduction logic | `qitos/core/agent_module.py` |
| **Engine** | Execution layer: lifecycle, tool execution, stop checks, tracing | `qitos/engine/engine.py` |
| **Kit** | Reusable concrete implementations | `qitos/kit/{tool,memory,parser,planning,critic}/` |

AgentModule provides hooks: `init_state()`, `build_system_prompt()`, `prepare()`, `decide()`, `reduce()`, `should_stop()`. The Engine owns `phase loop → action execution → recovery → stop criteria → trace writing`.

## Task + Env Abstraction

As of the current milestone, two first-class abstractions unify agent workflows:

- **Task** (`qitos/core/task.py`): Defines objective, budget (steps/time), resources, and success criteria
- **Env** (`qitos/core/env.py`): Provides `reset/observe/step/is_terminal/close` lifecycle

Engine supports `Engine.run(task: str | Task)` with automatic resource staging and env lifecycle orchestration.

## Key Execution Flow

```
Task → Engine.run()
     → prepare → decide → act → reduce → check_stop → ...
     → hooks + trace + replay
```

The `Decision` class has canonical modes: `act`, `wait`, `final`, `branch`. Use `Decision.act()`, `Decision.final()` etc. rather than constructing directly.

## Prompt-Parser Contract

Prompt format and parser must match exactly:

- ReAct text prompt → `ReActTextParser` (expects `Thought:` + `Action:`)
- XML prompt → XML parser (expects `<thought>` + `<action>`)
- JSON prompt → JSON parser (expects `{"thought": ..., "action": ...}`)

Changing output format requires changing the parser.

## Template Contract

Templates in `templates/` must include:
- `agent.py` (subclasses AgentModule)
- `config.yaml`
- `paper.md`
- `__init__.py`

They must run through `Engine` or `agent.run(...)`.

## Trace Reproducibility

Required artifacts per run: `manifest.json`, `events.jsonl`, `steps.jsonl`. Mandatory fields include `task_id`, `task_hash`, `model_name`, `config_hash`, `tool_manifest`.

## Repository Layout Rules

- `qitos/core/`: Only contracts and types (no implementations)
- `qitos/kit/`: Top-level must only have `__init__.py`; implementations go in subpackages
- `examples/`: Runnable model-connected agents
- `tests/`: Includes architecture consistency tests enforcing the single-kernel rule
