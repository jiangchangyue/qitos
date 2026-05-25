# Manager-Worker Pattern

A manager agent delegates tasks to specialized worker agents.

## Architecture

```
         ┌──> Researcher
Manager ─┼──> Coder
         └──> Reviewer
```

## Configuration

Define workers and their capabilities in `config.yaml`.

## Handoff Context

- **Manager → Worker**: Summary strategy (task + relevant context)
- **Worker → Manager**: Summary strategy (result + status)
- **SharedMemory**: `task`, `result` fields shared across all agents

## Usage

```python
from qitos.templates.manager_worker.agent import ManagerWorkerConfig, WorkerSpec, build_manager_worker_system

config = ManagerWorkerConfig(
    workers=[
        WorkerSpec(name="researcher", description="Research agent", capabilities=["search"]),
        WorkerSpec(name="coder", description="Code agent", capabilities=["write", "test"]),
    ]
)
system = build_manager_worker_system(config)
```
