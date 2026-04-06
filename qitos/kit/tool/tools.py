"""Tool registry builders backed by concrete tool implementations."""

from __future__ import annotations

from qitos.core.tool import tool
from qitos.core.tool_registry import ToolRegistry
from qitos.kit.tool.codebase import CodebaseToolSet
from qitos.kit.tool.coding import CodingToolSet
from qitos.kit.tool.editor import EditorToolSet
from qitos.kit.tool.file import ListFiles, ReadFile, WriteFile
from qitos.kit.tool.notebook import NotebookToolSet
from qitos.kit.tool.shell import RunCommand
from qitos.kit.tool.taskboard import TaskToolSet
from qitos.kit.tool.web import HTTPGet, HTTPPost, HTTPRequest, HTMLExtractText, WebFetch


def math_tools() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(name="add")
    def add(a: int, b: int) -> int:
        return a + b

    @tool(name="multiply")
    def multiply(a: int, b: int) -> int:
        return a * b

    registry.register(add)
    registry.register(multiply)
    return registry


def editor_tools(workspace_root: str) -> ToolRegistry:
    registry = ToolRegistry()
    registry.include(EditorToolSet(workspace_root=workspace_root))
    return registry


def codebase_tools(workspace_root: str) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_toolset(CodebaseToolSet(workspace_root=workspace_root))
    registry.register(ListFiles(root_dir=workspace_root))
    registry.register(ReadFile(root_dir=workspace_root))
    registry.register(WriteFile(root_dir=workspace_root))
    return registry


def notebook_tools(workspace_root: str) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_toolset(NotebookToolSet(workspace_root=workspace_root))
    return registry


def web_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(HTTPRequest())
    registry.register(HTTPGet())
    registry.register(HTTPPost())
    registry.register(HTMLExtractText())
    registry.register(WebFetch())
    return registry


def coding_tools(workspace_root: str, shell_timeout: int = 30, include_notebook: bool = True) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_toolset(
        CodingToolSet(
            workspace_root=workspace_root,
            shell_timeout=shell_timeout,
            include_notebook=include_notebook,
        ),
        namespace="",
    )
    return registry


def task_tools(workspace_root: str, board_relpath: str = ".qitos/task_board.json") -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_toolset(TaskToolSet(workspace_root=workspace_root, board_relpath=board_relpath), namespace="")
    return registry


__all__ = [
    "math_tools",
    "editor_tools",
    "codebase_tools",
    "notebook_tools",
    "web_tools",
    "coding_tools",
    "task_tools",
]
