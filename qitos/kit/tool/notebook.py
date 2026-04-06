"""Atomic Jupyter notebook tools."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from qitos.core.tool import BaseTool, ToolPermission, ToolSpec
from qitos.kit.tool.codebase import _resolve_workspace_path


def _load_notebook(root_dir: str, path: str) -> tuple[Path, Dict[str, Any]]:
    resolved = Path(_resolve_workspace_path(root_dir, path))
    with resolved.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "cells" not in data or not isinstance(data["cells"], list):
        raise ValueError(f"Invalid notebook format: {path}")
    return resolved, data


def _dump_notebook(resolved: Path, data: Dict[str, Any]) -> None:
    with resolved.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _normalize_source(source: Any) -> str:
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return str(source or "")


class ReadNotebook(BaseTool):
    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="read_notebook",
                description="Read notebook cells from a .ipynb file under workspace",
                parameters={
                    "path": {"type": "string"},
                    "cell_start": {"type": "integer"},
                    "cell_limit": {"type": "integer"},
                },
                required=["path"],
                permissions=ToolPermission(filesystem_read=True),
            )
        )

    def run(
        self,
        path: str,
        cell_start: int = 0,
        cell_limit: int = 20,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        try:
            resolved, data = _load_notebook(self._root_dir, path)
            cells = data.get("cells", [])
            start = max(0, int(cell_start))
            limit = max(1, int(cell_limit))
            selected = cells[start : start + limit]
            rendered = []
            for idx, cell in enumerate(selected, start=start):
                rendered.append(
                    {
                        "index": idx,
                        "cell_type": str(cell.get("cell_type", "")),
                        "source": _normalize_source(cell.get("source")),
                    }
                )
            return {
                "status": "success",
                "path": os.path.relpath(str(resolved), self._root_dir),
                "total_cells": len(cells),
                "cell_start": start,
                "cell_limit": limit,
                "cells": rendered,
                "has_more": start + limit < len(cells),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ReplaceNotebookCell(BaseTool):
    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="replace_notebook_cell",
                description="Replace the source of one notebook cell",
                parameters={
                    "path": {"type": "string"},
                    "cell_index": {"type": "integer"},
                    "source": {"type": "string"},
                },
                required=["path", "cell_index", "source"],
                permissions=ToolPermission(filesystem_write=True, filesystem_read=True),
            )
        )

    def run(
        self,
        path: str,
        cell_index: int,
        source: str,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        try:
            resolved, data = _load_notebook(self._root_dir, path)
            cells = data["cells"]
            idx = int(cell_index)
            if idx < 0 or idx >= len(cells):
                return {"status": "error", "message": f"Cell index out of range: {idx}"}
            cells[idx]["source"] = source.splitlines(keepends=True)
            _dump_notebook(resolved, data)
            return {
                "status": "success",
                "path": os.path.relpath(str(resolved), self._root_dir),
                "cell_index": idx,
                "cell_type": str(cells[idx].get("cell_type", "")),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class InsertNotebookCell(BaseTool):
    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="insert_notebook_cell",
                description="Insert a notebook cell at a given index",
                parameters={
                    "path": {"type": "string"},
                    "cell_type": {"type": "string"},
                    "source": {"type": "string"},
                    "index": {"type": "integer"},
                },
                required=["path", "cell_type", "source"],
                permissions=ToolPermission(filesystem_write=True, filesystem_read=True),
            )
        )

    def run(
        self,
        path: str,
        cell_type: str,
        source: str,
        index: int = -1,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = runtime_context
        normalized_type = str(cell_type or "").strip().lower()
        if normalized_type not in {"code", "markdown", "raw"}:
            return {"status": "error", "message": f"Unsupported cell_type: {normalized_type}"}
        try:
            resolved, data = _load_notebook(self._root_dir, path)
            cells = data["cells"]
            new_cell = {
                "cell_type": normalized_type,
                "metadata": {},
                "source": source.splitlines(keepends=True),
            }
            if normalized_type == "code":
                new_cell["execution_count"] = None
                new_cell["outputs"] = []
            insert_at = len(cells) if int(index) < 0 else min(max(0, int(index)), len(cells))
            cells.insert(insert_at, new_cell)
            _dump_notebook(resolved, data)
            return {
                "status": "success",
                "path": os.path.relpath(str(resolved), self._root_dir),
                "cell_index": insert_at,
                "cell_type": normalized_type,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class NotebookToolSet:
    name = "notebook"
    version = "1"

    def __init__(self, workspace_root: str = "."):
        self.read_notebook = ReadNotebook(root_dir=workspace_root)
        self.replace_notebook_cell = ReplaceNotebookCell(root_dir=workspace_root)
        self.insert_notebook_cell = InsertNotebookCell(root_dir=workspace_root)

    def setup(self, context: dict[str, Any]) -> None:
        _ = context

    def teardown(self, context: dict[str, Any]) -> None:
        _ = context

    def tools(self) -> list[Any]:
        return [
            self.read_notebook,
            self.replace_notebook_cell,
            self.insert_notebook_cell,
        ]


__all__ = [
    "ReadNotebook",
    "ReplaceNotebookCell",
    "InsertNotebookCell",
    "NotebookToolSet",
]
