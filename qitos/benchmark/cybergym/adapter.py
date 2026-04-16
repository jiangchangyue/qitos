"""CyberGym benchmark task adapter."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from qitos.core import Task, TaskBudget

from ..base import BenchmarkAdapter, BenchmarkSource


def task_slug(task_id: str) -> str:
    return str(task_id).replace(":", "_")


class CyberGymBenchmarkAdapter(BenchmarkAdapter):
    """Convert CyberGym task ids into QitOS Task objects."""

    def __init__(self, *, difficulty: str = "level1") -> None:
        self.source = BenchmarkSource(name="cybergym", split=str(difficulty))
        self.difficulty = str(difficulty)

    def load_records(
        self,
        *,
        task_ids: Iterable[str],
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for raw_task_id in task_ids:
            task_id = str(raw_task_id).strip()
            if not task_id:
                continue
            records.append({"task_id": task_id})
            if limit is not None and len(records) >= int(limit):
                break
        return records

    def to_task(
        self,
        record: Mapping[str, Any],
        *,
        split: str | None = None,
        idx: int = 0,
    ) -> Task:
        task_id = str(record.get("task_id") or record.get("id") or "").strip()
        if not task_id:
            raise ValueError("CyberGym record requires task_id")
        difficulty = str(split or record.get("difficulty") or self.difficulty)
        return Task(
            id=task_id,
            objective=f"Solve CyberGym task {task_id}.",
            inputs={"task_id": task_id, "difficulty": difficulty},
            budget=TaskBudget(max_steps=int(record.get("max_steps", 30))),
            metadata={
                "benchmark": "cybergym",
                "split": difficulty,
                "task_index": int(idx),
                "raw_record": dict(record),
            },
        )

    def to_tasks(
        self,
        records: Iterable[Mapping[str, Any]],
        split: str,
        limit: Optional[int] = None,
    ) -> list[Task]:
        tasks: list[Task] = []
        for idx, record in enumerate(records):
            tasks.append(self.to_task(record, split=split, idx=idx))
            if limit is not None and len(tasks) >= int(limit):
                break
        return tasks


def load_cybergym_tasks(
    *,
    task_ids: Iterable[str],
    difficulty: str = "level1",
    limit: Optional[int] = None,
) -> list[Task]:
    adapter = CyberGymBenchmarkAdapter(difficulty=difficulty)
    records = adapter.load_records(task_ids=task_ids, limit=limit)
    return adapter.to_tasks(records, split=difficulty, limit=limit)
