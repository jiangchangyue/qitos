"""Task composition — call @task functions within @agent with parallelism.

Provides helpers for composing multiple @task calls within an @agent,
including parallel execution via futures.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, List, Optional, Sequence, TypeVar

from .task import TaskFunction

T = TypeVar("T")


def compose(
    *tasks: TaskFunction,
    executor: Optional[ThreadPoolExecutor] = None,
) -> _Composer:
    """Create a composer for parallel task execution.

    Usage::

        @task
        def search(query: str) -> list[str]:
            ...

        @task
        def summarize(texts: list[str]) -> str:
            ...

        composer = compose(search, summarize)
        results = composer.run("quantum computing")
    """
    return _Composer(tasks, executor=executor)


class _Composer:
    """Compose multiple TaskFunctions for parallel execution."""

    def __init__(
        self,
        tasks: Sequence[TaskFunction],
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self._tasks = list(tasks)
        self._executor = executor or ThreadPoolExecutor(max_workers=max(len(tasks), 1))

    def run(self, *args: Any, **kwargs: Any) -> List[Any]:
        """Run all tasks in parallel and return results.

        Each task receives the same args/kwargs.
        """
        futures = [
            t.submit(self._executor, *args, **kwargs)
            for t in self._tasks
        ]
        return [f.result() for f in futures]

    async def arun(self, *args: Any, **kwargs: Any) -> List[Any]:
        """Run all tasks asynchronously and return results."""
        coros = [t.acall(*args, **kwargs) for t in self._tasks]
        return list(await asyncio.gather(*coros))

    def map(self, items: Sequence[Any]) -> List[Any]:
        """Run each task with one item from items (1:1 mapping)."""
        if len(items) != len(self._tasks):
            raise ValueError(
                f"Expected {len(self._tasks)} items, got {len(items)}"
            )
        futures = [
            t.submit(self._executor, item)
            for t, item in zip(self._tasks, items)
        ]
        return [f.result() for f in futures]


__all__ = ["compose", "_Composer"]
