"""Predefined coding-oriented toolset."""

from __future__ import annotations

from typing import Any, List

from qitos.core.tool import get_tool_meta
from qitos.kit.tool.codebase import CodebaseToolSet
from qitos.kit.tool.editor import EditorToolSet
from qitos.kit.tool.file import ListFiles, ReadFile, WriteFile
from qitos.kit.tool.notebook import NotebookToolSet
from qitos.kit.tool.shell import RunCommand


def _collect_object_tools(obj: Any) -> List[Any]:
    items: List[Any] = []
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue
        attr = getattr(obj, attr_name)
        if callable(attr) and get_tool_meta(attr) is not None:
            items.append(attr)
    return items


class CodingToolSet:
    """A batteries-included toolset for coding agents."""

    name = "coding"
    version = "1"

    def __init__(self, workspace_root: str = ".", shell_timeout: int = 30, include_notebook: bool = True):
        self._editor = EditorToolSet(workspace_root=workspace_root)
        self._codebase = CodebaseToolSet(workspace_root=workspace_root)
        self._notebook = NotebookToolSet(workspace_root=workspace_root) if include_notebook else None
        self._shell = RunCommand(timeout=shell_timeout, cwd=workspace_root)
        self._read = ReadFile(root_dir=workspace_root)
        self._write = WriteFile(root_dir=workspace_root)
        self._list = ListFiles(root_dir=workspace_root)

    def setup(self, context: dict[str, Any]) -> None:
        _ = context

    def teardown(self, context: dict[str, Any]) -> None:
        _ = context

    def tools(self) -> list[Any]:
        tools: List[Any] = []
        tools.extend(_collect_object_tools(self._editor))
        tools.extend(self._codebase.tools())
        if self._notebook is not None:
            tools.extend(self._notebook.tools())
        tools.extend([self._shell, self._read, self._write, self._list])
        return tools


__all__ = ["CodingToolSet"]
