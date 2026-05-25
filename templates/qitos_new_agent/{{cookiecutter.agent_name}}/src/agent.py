"""{{cookiecutter.agent_description}} — {{cookiecutter.agent_name}}."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from qitos.core.agent_module import AgentModule
from qitos.core.state import StateSchema


@dataclass
class {{cookiecutter.agent_name | pascalcase}}State(StateSchema):
    """State for the {{cookiecutter.agent_name}} agent."""

    result: str = ""
    steps_taken: int = 0


class {{cookiecutter.agent_name | pascalcase}}Agent(AgentModule[{{cookiecutter.agent_name | pascalcase}}State, Any, Any]):
    """{{cookiecutter.agent_description}}."""

    def init_state(self, task: str, **kwargs: Any) -> {{cookiecutter.agent_name | pascalcase}}State:
        return {{cookiecutter.agent_name | pascalcase}}State(task=task, max_steps={{cookiecutter.max_steps}})

    def build_system_prompt(self, state: {{cookiecutter.agent_name | pascalcase}}State) -> str:
        return (
            "You are {{cookiecutter.agent_name}}, a helpful agent.\n"
            "{{cookiecutter.agent_description}}\n"
            f"Task: {state.task}"
        )

    def prepare(self, state: {{cookiecutter.agent_name | pascalcase}}State) -> dict[str, Any]:
        return {}

    def reduce(self, state: {{cookiecutter.agent_name | pascalcase}}State, decision: Any, results: list[Any]) -> {{cookiecutter.agent_name | pascalcase}}State:
        state.steps_taken += 1
        if results:
            state.result = str(results[-1])[:500]
        return state
