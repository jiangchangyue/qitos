# Contributing to QitOS Zoo

QitOS Zoo is the collection of agent applications built on the QitOS framework.
Each agent lives in its own directory under `apps/` with a consistent structure.

## Agent Application Structure

Every agent application should follow this layout:

```
apps/<agent_name>/
  README.md              # Purpose, usage, supported models
  <agent_name>_agent.py  # Main AgentModule implementation
  configs/
    default.yaml         # Default configuration
  prompts/
    system_prompt.py     # Prompt templates
  critic/                # (optional) Agent-specific critics
  tools/                 # (optional) Agent-specific tools
  snowl_compat.py        # Snowl evaluation adapter
  eval_config.yaml       # Benchmark configuration
  tests/
    test_<agent_name>.py # Unit and integration tests
```

## snowl_compat.py Template

Every agent that supports benchmark evaluation should include a
`snowl_compat.py` with this interface:

```python
"""Snowl compatibility adapter for <agent_name>."""

from typing import Any, Dict, List, Optional

REQUIRED_TOOLS: List[str] = [...]  # Tool names the agent needs
REQUIRED_ENV: Dict[str, Any] = {}  # Environment requirements

def create_snowl_agent(**kwargs: Any) -> Any:
    """Create the agent for Snowl evaluation."""
    from .<agent_module> import <AgentClass>
    return <AgentClass>(**kwargs)

def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize EngineResult to Snowl JSON."""
    from qitos.engine.run_state import RunState
    import json
    state = RunState.from_engine_result(result, agent_name="<agent_name>")
    return json.loads(state.to_json(pretty=False))

def deserialize_run(raw: str) -> Any:
    """Deserialize Snowl JSON back to RunState."""
    from qitos.engine.run_state import RunState
    return RunState.from_json(raw)
```

## eval_config.yaml Template

```yaml
agent:
  name: <agent_name>
  factory: qitos_zoo.<agent_name>.snowl_compat.create_snowl_agent
  required_tools: [...]
  required_env: {}

benchmarks:
  <benchmark_name>:
    dataset: <dataset_path>
    split: test
    max_steps: <int>
    eval_metric: <metric>

serialization:
  format: runstate_json
  schema_version: "1.0"
  round_trip: true

defaults:
  model: null
  temperature: 0.0
```

## Safety and Scope Requirements

- Agents must NOT access the network unless explicitly required
- Shell tools must use `needs_approval=True` for destructive commands
- Agent state must be serializable via `StateSchema.to_dict()`
- Critics should use `@critic` decorator when possible
- Never import from other zoo apps directly — use QitOS core APIs

## Shared Code Policy

Code is shared between zoo apps only when **2 or more apps** need it.
In that case, the shared code should be promoted to QitOS core under
the appropriate `kit/` module. Do not create cross-app imports.

## Testing

- Each agent must have at least basic unit tests
- Mock LLM calls in tests — do not require live API access
- Test the `snowl_compat` round-trip: `deserialize_run(serialize_run(result))`
- Run the full QitOS test suite to check for regressions
