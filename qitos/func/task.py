"""@task decorator — wrap functions as composable task units.

A ``@task`` wraps a plain function so it can be:
1. Called directly like a regular function
2. Composed within an ``@agent`` for parallel execution
3. Integrated with retry/timeout policies

Unlike LangGraph's ``@task``, QitOS tasks are simpler: they don't
require a Pregel graph and work directly with the Engine.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Generic, Optional, TypeVar, overload

P = TypeVar("P")
T = TypeVar("T")
F = TypeVar("F", bound=Callable)


class TaskFunction(Generic[P, T]):
    """A function wrapped by @task.

    Can be called directly (sync) or via ``.submit()`` for parallel execution.
    """

    def __init__(
        self,
        func: Callable[..., T],
        *,
        name: Optional[str] = None,
        max_retries: int = 0,
        timeout_s: Optional[float] = None,
    ) -> None:
        self._func = func
        self._name = name or getattr(func, "__name__", "task")
        self._max_retries = max_retries
        self._timeout_s = timeout_s
        self._is_async = asyncio.iscoroutinefunction(func)
        functools.update_wrapper(self, func, updated=())

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_async(self) -> bool:
        return self._is_async

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        """Call the task directly (blocking)."""
        return self._func(*args, **kwargs)

    async def acall(self, *args: Any, **kwargs: Any) -> T:
        """Call the task asynchronously."""
        if self._is_async:
            return await self._func(*args, **kwargs)
        return await asyncio.to_thread(self._func, *args, **kwargs)

    def submit(self, executor: Optional[ThreadPoolExecutor] = None, *args: Any, **kwargs: Any) -> Future:
        """Submit the task for parallel execution.

        Returns a concurrent.futures.Future that can be collected later.
        Only works for sync functions. For async, use acall() with asyncio.gather.
        """
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=1)
        return executor.submit(self._func, *args, **kwargs)

    def __repr__(self) -> str:
        return f"TaskFunction({self._name!r})"


@overload
def task(__func_or_none__: None = None, **kwargs: Any) -> Callable[[F], TaskFunction]: ...


@overload
def task(__func_or_none__: F, **kwargs: Any) -> TaskFunction: ...


def task(
    __func_or_none__: Any = None,
    *,
    name: Optional[str] = None,
    max_retries: int = 0,
    timeout_s: Optional[float] = None,
) -> Any:
    """Decorator to wrap a function as a composable task unit.

    Can be used bare (``@task``) or with keyword arguments
    (``@task(name="search", max_retries=2)``).

    Parameters
    ----------
    name : str, optional
        Name for the task (defaults to function name).
    max_retries : int
        Maximum retry attempts on failure.
    timeout_s : float, optional
        Timeout in seconds for each attempt.
    """

    def decorator(func: F) -> TaskFunction:
        return TaskFunction(
            func,
            name=name,
            max_retries=max_retries,
            timeout_s=timeout_s,
        )

    if __func_or_none__ is not None:
        # Bare usage: @task
        return decorator(__func_or_none__)

    # With arguments: @task(name=..., max_retries=...)
    return decorator


__all__ = ["task", "TaskFunction"]
