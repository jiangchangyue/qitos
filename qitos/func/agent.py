"""@agent decorator — wrap functions as lightweight Agents.

An ``@agent`` wraps a plain function into an AgentModule-compatible
agent that can be run by the Engine. It auto-configures state,
tools, and model from the function signature.

Usage::

    @agent
    def research_agent(topic: str) -> str:
        '''Research a topic and return findings.'''
        results = search(topic)
        return summarize(results)

    # Run directly
    result = research_agent("quantum computing")

    # Or with Engine
    from qitos.engine import Engine
    engine = Engine(research_agent._as_agent_module())
    result = engine.run("quantum computing")
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar, overload

from ..core.agent_module import AgentModule
from ..core.decision import Decision
from ..core.state import StateSchema
from .task import TaskFunction

F = TypeVar("F", bound=Callable)
StateT = TypeVar("StateT", bound=StateSchema)


@dataclass
class _AgentState(StateSchema):
    """Default state for @agent-decorated functions."""

    result: Optional[str] = None
    steps_taken: int = 0


class _FunctionAgent(AgentModule[_AgentState, Any, Any]):
    """AgentModule backed by a plain function.

    The function receives the task as its first argument and optionally
    a ``state`` parameter for accessing/modifying state.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        name: str,
        max_steps: int = 10,
        llm: Any = None,
        **config: Any,
    ):
        self._func = func
        self._agent_name = name
        self._max_steps = max_steps
        self._is_async = asyncio.iscoroutinefunction(func)
        # Inspect if function accepts state parameter
        sig = inspect.signature(func)
        self._accepts_state = "state" in sig.parameters
        super().__init__(llm=llm, **config)

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._agent_name

    def init_state(self, task: str, **kwargs: Any) -> _AgentState:
        return _AgentState(task=task, max_steps=self._max_steps)

    def build_system_prompt(self, state: _AgentState) -> str | None:
        doc = getattr(self._func, "__doc__", "") or ""
        return doc.strip() if doc.strip() else f"Agent: {self._agent_name}"

    def reduce(
        self,
        state: _AgentState,
        observation: Any,
        decision: Decision[Any],
    ) -> _AgentState:
        # The function result is handled in run() directly
        return state

    def should_stop(self, state: _AgentState) -> bool:
        return state.result is not None or state.steps_taken >= state.max_steps

    def _run_function(self, task: str, state: Optional[_AgentState] = None) -> Any:
        """Execute the wrapped function."""
        kwargs: dict[str, Any] = {}
        if self._accepts_state and state is not None:
            kwargs["state"] = state
        return self._func(task, **kwargs)


class AgentFunction:
    """A function wrapped by @agent.

    Can be called directly to run the agent, or converted to an
    AgentModule for Engine integration.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        name: Optional[str] = None,
        max_steps: int = 10,
    ) -> None:
        self._func = func
        self._name = name or getattr(func, "__name__", "agent")
        self._max_steps = max_steps
        self._agent_module: Optional[_FunctionAgent] = None
        functools.update_wrapper(self, func, updated=())

    @property
    def name(self) -> str:
        return self._name

    def __call__(self, task: str, **kwargs: Any) -> Any:
        """Run the agent function directly."""
        return self._func(task, **kwargs)

    async def acall(self, task: str, **kwargs: Any) -> Any:
        """Run the agent function asynchronously."""
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(task, **kwargs)
        return await asyncio.to_thread(self._func, task, **kwargs)

    def _as_agent_module(self, **kwargs: Any) -> _FunctionAgent:
        """Convert to an AgentModule for Engine integration."""
        return _FunctionAgent(
            func=self._func,
            name=self._name,
            max_steps=self._max_steps,
            **kwargs,
        )

    def __repr__(self) -> str:
        return f"AgentFunction({self._name!r})"


@overload
def agent(__func_or_none__: None = None, **kwargs: Any) -> Callable[[F], AgentFunction]: ...


@overload
def agent(__func_or_none__: F, **kwargs: Any) -> AgentFunction: ...


def agent(
    __func_or_none__: Any = None,
    *,
    name: Optional[str] = None,
    max_steps: int = 10,
) -> Any:
    """Decorator to wrap a function as a lightweight Agent.

    Can be used bare (``@agent``) or with keyword arguments
    (``@agent(name="researcher", max_steps=5)``).

    Parameters
    ----------
    name : str, optional
        Name for the agent (defaults to function name).
    max_steps : int
        Maximum execution steps.
    """

    def decorator(func: F) -> AgentFunction:
        return AgentFunction(func, name=name, max_steps=max_steps)

    if __func_or_none__ is not None:
        # Bare usage: @agent
        return decorator(__func_or_none__)

    # With arguments: @agent(name=..., max_steps=...)
    return decorator


__all__ = ["agent", "AgentFunction", "_FunctionAgent", "_AgentState"]
