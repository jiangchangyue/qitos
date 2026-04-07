"""Tool registry builders backed by concrete tool implementations."""

from __future__ import annotations

from qitos.core.tool import tool
from qitos.core.tool_registry import ToolRegistry
from qitos.kit.tool.advanced import AdvancedCodingToolSet
from qitos.kit.tool.coding import CodingToolSet
from qitos.kit.tool.notebook import NotebookToolSet
from qitos.kit.tool.report_toolset import ReportToolSet
from qitos.kit.tool.security_audit import SecurityAuditToolSet
from qitos.kit.tool.taskboard import TaskToolSet


def math_tools() -> ToolRegistry:
    """Build a tiny registry of arithmetic example tools."""
    registry = ToolRegistry()

    @tool(name="add")
    def add(a: int, b: int) -> int:
        """
        Return the sum of two integers.

        :param a: First integer.
        :param b: Second integer.
        """
        return a + b

    @tool(name="multiply")
    def multiply(a: int, b: int) -> int:
        """
        Return the product of two integers.

        :param a: First integer.
        :param b: Second integer.
        """
        return a * b

    registry.register(add)
    registry.register(multiply)
    return registry


def editor_tools(workspace_root: str) -> ToolRegistry:
    """Build a registry containing only the editor toolset."""
    registry = ToolRegistry()
    registry.register_toolset(
        CodingToolSet(
            workspace_root=workspace_root,
            include_notebook=False,
            enable_lsp=False,
            enable_tasks=False,
            enable_web=False,
            expose_legacy_aliases=True,
            expose_modern_names=False,
            profile="editor",
        ),
        namespace="",
    )
    return registry


def codebase_tools(workspace_root: str) -> ToolRegistry:
    """Build a registry for code search plus basic file read and write tools."""
    registry = ToolRegistry()
    registry.register_toolset(
        CodingToolSet(
            workspace_root=workspace_root,
            include_notebook=False,
            enable_lsp=False,
            enable_tasks=False,
            enable_web=False,
            expose_legacy_aliases=True,
            expose_modern_names=False,
            profile="codebase",
        ),
        namespace="codebase",
    )
    registry.register_toolset(
        CodingToolSet(
            workspace_root=workspace_root,
            include_notebook=False,
            enable_lsp=False,
            enable_tasks=False,
            enable_web=False,
            expose_legacy_aliases=True,
            expose_modern_names=False,
            profile="files",
        ),
        namespace="",
    )
    return registry


def notebook_tools(workspace_root: str) -> ToolRegistry:
    """Build a registry containing notebook-specific tools."""
    registry = ToolRegistry()
    registry.register_toolset(NotebookToolSet(workspace_root=workspace_root))
    return registry


def web_tools() -> ToolRegistry:
    """Build a registry containing HTTP and HTML extraction tools."""
    registry = ToolRegistry()
    registry.register_toolset(
        CodingToolSet(
            include_notebook=False,
            enable_lsp=False,
            enable_tasks=False,
            enable_web=True,
            expose_legacy_aliases=True,
            expose_modern_names=True,
            profile="web",
            include_http_tools=True,
        ),
        namespace="",
    )
    return registry


def coding_tools(
    workspace_root: str, shell_timeout: int = 30, include_notebook: bool = True
) -> ToolRegistry:
    """Build a registry with the standard coding-oriented tool bundle."""
    registry = ToolRegistry()
    registry.register_toolset(
        CodingToolSet(
            workspace_root=workspace_root,
            shell_timeout=shell_timeout,
            include_notebook=include_notebook,
            enable_lsp=True,
            enable_tasks=True,
            enable_web=True,
            expose_legacy_aliases=True,
            expose_modern_names=True,
            profile="full",
        ),
        namespace="",
    )
    return registry


def task_tools(
    workspace_root: str, board_relpath: str = ".qitos/task_board.json"
) -> ToolRegistry:
    """Build a registry containing the external task-board tools."""
    registry = ToolRegistry()
    registry.register_toolset(
        TaskToolSet(workspace_root=workspace_root, board_relpath=board_relpath),
        namespace="",
    )
    return registry


def report_tools(workspace_root: str) -> ToolRegistry:
    """Build a registry containing the assessment reporting toolset."""
    registry = ToolRegistry()
    registry.register_toolset(
        ReportToolSet(workspace_root=workspace_root), namespace=""
    )
    return registry


def security_audit_tools(
    workspace_root: str,
    *,
    include_external: bool = False,
    external_timeout: int = 120,
    max_matches: int = 200,
) -> ToolRegistry:
    """Build a registry containing the codebase security audit toolset."""
    registry = ToolRegistry()
    registry.register_toolset(
        SecurityAuditToolSet(
            workspace_root=workspace_root,
            include_external=include_external,
            external_timeout=external_timeout,
            max_matches=max_matches,
        ),
        namespace="",
    )
    return registry


def advanced_coding_tools(
    workspace_root: str,
    *,
    enable_lsp: bool = True,
    enable_tasks: bool = True,
    enable_web: bool = True,
) -> ToolRegistry:
    """Build a Claude-style advanced registry on top of the canonical coding toolset."""
    registry = ToolRegistry()
    registry.register_toolset(
        AdvancedCodingToolSet(
            workspace_root=workspace_root,
            enable_lsp=enable_lsp,
            enable_tasks=enable_tasks,
            enable_web=enable_web,
        ),
        namespace="",
    )
    return registry


__all__ = [
    "math_tools",
    "editor_tools",
    "codebase_tools",
    "notebook_tools",
    "web_tools",
    "coding_tools",
    "task_tools",
    "report_tools",
    "security_audit_tools",
    "advanced_coding_tools",
]
