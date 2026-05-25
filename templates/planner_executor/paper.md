# Planner-Executor Pattern

A planner decomposes a task into subtasks, and an executor carries out each step.

## Architecture

```
Planner ──handoff──> Executor ──handoff──> Planner
   ^                                        |
   └──────────────── (loop until done) ─────┘
```

## Key Design

- **Planner** uses `FULL` context strategy — sees the complete plan and all results
- **Executor** uses `ISOLATED` context strategy — only receives the current subtask
- **SharedMemory**: `plan`, `step_result`, `overall_result` fields

## Configuration

Adjust `max_subtasks` and agent names in `config.yaml`.

## Usage

```python
from qitos.templates.planner_executor.agent import PlannerExecutorConfig, build_planner_executor_system

config = PlannerExecutorConfig(max_subtasks=3)
system = build_planner_executor_system(config)
```
