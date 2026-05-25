"""Functional API for QitOS — @task and @agent decorators.

Provides a lightweight, decorator-driven way to create agents and tasks
without subclassing AgentModule.

Usage::

    from qitos.func import task, agent

    @task
    def search(query: str) -> list[str]:
        ...

    @agent
    def research_agent(topic: str) -> str:
        results = search(topic)
        return summarize(results)

    # Run directly
    result = research_agent("quantum computing")
"""

from .task import task, TaskFunction
from .agent import agent, AgentFunction
from .compose import compose

__all__ = [
    "task",
    "TaskFunction",
    "agent",
    "AgentFunction",
    "compose",
]
