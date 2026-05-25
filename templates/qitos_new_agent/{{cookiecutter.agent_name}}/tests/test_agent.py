"""Tests for {{cookiecutter.agent_name}} agent."""

from __future__ import annotations

from {{cookiecutter.agent_name}}.src.agent import (
    {{cookiecutter.agent_name | pascalcase}}Agent,
    {{cookiecutter.agent_name | pascalcase}}State,
)


class Test{{cookiecutter.agent_name | pascalcase}}State:
    def test_init_state(self):
        agent = {{cookiecutter.agent_name | pascalcase}}Agent()
        state = agent.init_state("test task")
        assert state.task == "test task"
        assert state.result == ""
        assert state.steps_taken == 0

    def test_build_system_prompt(self):
        agent = {{cookiecutter.agent_name | pascalcase}}Agent()
        state = agent.init_state("test task")
        prompt = agent.build_system_prompt(state)
        assert len(prompt) > 0
        assert "test task" in prompt
