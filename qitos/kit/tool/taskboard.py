"""External task board tools for planning, decomposition, and progress tracking."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qitos.core.tool import BaseTool, ToolPermission, ToolSpec
from qitos.kit.tool.codebase import _resolve_workspace_path

TASK_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskNote:
    created_at: str
    text: str
    kind: str = "note"


@dataclass
class TaskRecord:
    id: str
    subject: str
    description: str
    status: str = "pending"
    active_form: str = ""
    owner: str = ""
    blocks: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    notes: List[TaskNote] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["notes"] = [asdict(note) for note in self.notes]
        return data


class TaskBoardStore:
    def __init__(self, workspace_root: str = ".", board_relpath: str = ".qitos/task_board.json"):
        self._workspace_root = os.path.abspath(workspace_root)
        self._board_path = Path(_resolve_workspace_path(self._workspace_root, board_relpath))
        self._lock = threading.Lock()

    @property
    def board_path(self) -> str:
        return str(self._board_path)

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self._board_path.exists():
                return {"version": 1, "tasks": []}
            with self._board_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Task board must be a JSON object")
            data.setdefault("version", 1)
            data.setdefault("tasks", [])
            return data

    def save(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._board_path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(prefix="task_board_", suffix=".json", dir=str(self._board_path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                os.replace(temp_path, self._board_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def list_tasks(self) -> List[TaskRecord]:
        payload = self.load()
        return [self._from_dict(item) for item in payload.get("tasks", [])]

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        for task in self.list_tasks():
            if task.id == task_id:
                return task
        return None

    def upsert(self, task: TaskRecord) -> TaskRecord:
        payload = self.load()
        tasks = [self._from_dict(item) for item in payload.get("tasks", [])]
        for idx, item in enumerate(tasks):
            if item.id == task.id:
                tasks[idx] = task
                payload["tasks"] = [entry.to_dict() for entry in tasks]
                self.save(payload)
                return task
        tasks.append(task)
        payload["tasks"] = [entry.to_dict() for entry in tasks]
        self.save(payload)
        return task

    def _from_dict(self, data: Dict[str, Any]) -> TaskRecord:
        notes = [TaskNote(**note) for note in list(data.get("notes", []) or [])]
        return TaskRecord(
            id=str(data.get("id", "")),
            subject=str(data.get("subject", "")),
            description=str(data.get("description", "")),
            status=str(data.get("status", "pending")),
            active_form=str(data.get("active_form", "")),
            owner=str(data.get("owner", "")),
            blocks=list(data.get("blocks", []) or []),
            blocked_by=list(data.get("blocked_by", []) or []),
            notes=notes,
            metadata=dict(data.get("metadata", {}) or {}),
            created_at=str(data.get("created_at", _utc_now())),
            updated_at=str(data.get("updated_at", _utc_now())),
        )


class CreateTask(BaseTool):
    def __init__(self, store: TaskBoardStore):
        self._store = store
        super().__init__(
            ToolSpec(
                name="task_create",
                description="Create a task in the external task board",
                parameters={
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "active_form": {"type": "string"},
                    "metadata": {"type": "object"},
                    "status": {"type": "string"},
                },
                required=["subject", "description"],
                permissions=ToolPermission(filesystem_write=True, filesystem_read=True),
            )
        )

    def run(
        self,
        subject: str,
        description: str,
        active_form: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        normalized = str(status or "pending").strip()
        if normalized not in TASK_STATUSES:
            return {"status": "error", "message": f"Unsupported status: {normalized}"}
        task = TaskRecord(
            id=uuid4().hex[:10],
            subject=subject,
            description=description,
            active_form=active_form,
            metadata=dict(metadata or {}),
            status=normalized,
        )
        self._store.upsert(task)
        return {"status": "success", "task": task.to_dict(), "board_path": self._store.board_path}


class ListTaskBoard(BaseTool):
    def __init__(self, store: TaskBoardStore):
        self._store = store
        super().__init__(
            ToolSpec(
                name="task_list",
                description="List tasks from the external task board",
                parameters={
                    "status": {"type": "string"},
                    "include_completed": {"type": "boolean"},
                },
                required=[],
                permissions=ToolPermission(filesystem_read=True),
            )
        )

    def run(
        self,
        status: str = "",
        include_completed: bool = True,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        tasks = self._store.list_tasks()
        if status:
            tasks = [task for task in tasks if task.status == status]
        if not include_completed:
            tasks = [task for task in tasks if task.status != "completed"]
        return {
            "status": "success",
            "tasks": [task.to_dict() for task in tasks],
            "count": len(tasks),
            "board_path": self._store.board_path,
        }


class GetTask(BaseTool):
    def __init__(self, store: TaskBoardStore):
        self._store = store
        super().__init__(
            ToolSpec(
                name="task_get",
                description="Get one task from the external task board",
                parameters={"task_id": {"type": "string"}},
                required=["task_id"],
                permissions=ToolPermission(filesystem_read=True),
            )
        )

    def run(self, task_id: str, runtime_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = runtime_context
        task = self._store.get_task(task_id)
        if task is None:
            return {"status": "error", "message": f"Task not found: {task_id}"}
        return {"status": "success", "task": task.to_dict(), "board_path": self._store.board_path}


class UpdateTask(BaseTool):
    def __init__(self, store: TaskBoardStore):
        self._store = store
        super().__init__(
            ToolSpec(
                name="task_update",
                description="Update task fields, status, or dependency links",
                parameters={
                    "task_id": {"type": "string"},
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "active_form": {"type": "string"},
                    "status": {"type": "string"},
                    "owner": {"type": "string"},
                    "add_blocks": {"type": "array"},
                    "remove_blocks": {"type": "array"},
                    "add_blocked_by": {"type": "array"},
                    "remove_blocked_by": {"type": "array"},
                    "metadata": {"type": "object"},
                },
                required=["task_id"],
                permissions=ToolPermission(filesystem_write=True, filesystem_read=True),
            )
        )

    def run(
        self,
        task_id: str,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        active_form: Optional[str] = None,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        add_blocks: Optional[List[str]] = None,
        remove_blocks: Optional[List[str]] = None,
        add_blocked_by: Optional[List[str]] = None,
        remove_blocked_by: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        task = self._store.get_task(task_id)
        if task is None:
            return {"status": "error", "message": f"Task not found: {task_id}"}
        if status is not None:
            normalized = str(status).strip()
            if normalized not in TASK_STATUSES:
                return {"status": "error", "message": f"Unsupported status: {normalized}"}
            task.status = normalized
        if subject is not None:
            task.subject = subject
        if description is not None:
            task.description = description
        if active_form is not None:
            task.active_form = active_form
        if owner is not None:
            task.owner = owner
        if add_blocks:
            task.blocks = sorted({*task.blocks, *[str(x) for x in add_blocks if str(x).strip()]})
        if remove_blocks:
            remove_set = {str(x) for x in remove_blocks}
            task.blocks = [x for x in task.blocks if x not in remove_set]
        if add_blocked_by:
            task.blocked_by = sorted({*task.blocked_by, *[str(x) for x in add_blocked_by if str(x).strip()]})
        if remove_blocked_by:
            remove_set = {str(x) for x in remove_blocked_by}
            task.blocked_by = [x for x in task.blocked_by if x not in remove_set]
        if metadata:
            merged = dict(task.metadata)
            for key, value in metadata.items():
                if value is None:
                    merged.pop(key, None)
                else:
                    merged[key] = value
            task.metadata = merged
        task.updated_at = _utc_now()
        self._store.upsert(task)
        return {"status": "success", "task": task.to_dict(), "board_path": self._store.board_path}


class AppendTaskNote(BaseTool):
    def __init__(self, store: TaskBoardStore):
        self._store = store
        super().__init__(
            ToolSpec(
                name="task_append_note",
                description="Append a note or progress update to a task",
                parameters={
                    "task_id": {"type": "string"},
                    "text": {"type": "string"},
                    "kind": {"type": "string"},
                },
                required=["task_id", "text"],
                permissions=ToolPermission(filesystem_write=True, filesystem_read=True),
            )
        )

    def run(
        self,
        task_id: str,
        text: str,
        kind: str = "note",
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        task = self._store.get_task(task_id)
        if task is None:
            return {"status": "error", "message": f"Task not found: {task_id}"}
        task.notes.append(TaskNote(created_at=_utc_now(), text=text, kind=str(kind or "note")))
        task.updated_at = _utc_now()
        self._store.upsert(task)
        return {
            "status": "success",
            "task_id": task_id,
            "note_count": len(task.notes),
            "board_path": self._store.board_path,
        }


class TaskToolSet:
    name = "task"
    version = "1"

    def __init__(self, workspace_root: str = ".", board_relpath: str = ".qitos/task_board.json"):
        self.store = TaskBoardStore(workspace_root=workspace_root, board_relpath=board_relpath)
        self.task_create = CreateTask(self.store)
        self.task_list = ListTaskBoard(self.store)
        self.task_get = GetTask(self.store)
        self.task_update = UpdateTask(self.store)
        self.task_append_note = AppendTaskNote(self.store)

    def setup(self, context: dict[str, Any]) -> None:
        _ = context

    def teardown(self, context: dict[str, Any]) -> None:
        _ = context

    def tools(self) -> list[Any]:
        return [
            self.task_create,
            self.task_list,
            self.task_get,
            self.task_update,
            self.task_append_note,
        ]


__all__ = [
    "TaskRecord",
    "TaskNote",
    "TaskBoardStore",
    "TaskToolSet",
    "CreateTask",
    "ListTaskBoard",
    "GetTask",
    "UpdateTask",
    "AppendTaskNote",
]
