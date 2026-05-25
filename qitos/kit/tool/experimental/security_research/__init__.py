"""Explicit opt-in security research tools and registry builders."""

from __future__ import annotations

from typing import Any

from qitos.core.tool import FunctionTool, get_tool_meta
from qitos.core.tool_registry import ToolRegistry

from .exploit_toolset import ExploitToolSet
from .password_toolset import PasswordToolSet
from .recon_toolset import ReconToolSet
from .security_audit import SecurityAuditToolSet
from .vuln_scan_toolset import VulnScanToolSet


def _register_explicit_toolset(registry: ToolRegistry, toolset: Any) -> None:
    tools = getattr(toolset, "tools", None)
    if callable(tools):
        registry.register_toolset(toolset, namespace="")
        return
    for attr_name in dir(toolset):
        if attr_name.startswith("_"):
            continue
        attr = getattr(toolset, attr_name)
        # Support both @tool (marker: __qitos_tool_meta__) and @function_tool (FunctionTool instance)
        if isinstance(attr, FunctionTool):
            registry.register(attr)
        elif callable(attr) and get_tool_meta(attr) is not None:
            registry.register(attr)


def security_research_tools(
    workspace_root: str,
    *,
    include_external: bool = False,
    external_timeout: int = 120,
    max_matches: int = 200,
    include_authorized_ops: bool = False,
    authorized_targets: list[str] | None = None,
) -> ToolRegistry:
    """Build an explicit opt-in registry for security research workflows."""
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
    if include_authorized_ops:
        _register_explicit_toolset(
            registry,
            ReconToolSet(
                authorized_targets=authorized_targets, workspace_root=workspace_root
            ),
        )
        _register_explicit_toolset(
            registry,
            ExploitToolSet(
                authorized_targets=authorized_targets, workspace_root=workspace_root
            ),
        )
        _register_explicit_toolset(
            registry,
            PasswordToolSet(
                authorized_targets=authorized_targets, workspace_root=workspace_root
            ),
        )
        _register_explicit_toolset(
            registry,
            VulnScanToolSet(
                authorized_targets=authorized_targets, workspace_root=workspace_root
            ),
        )
    return registry


def security_audit_tools(
    workspace_root: str,
    *,
    include_external: bool = False,
    external_timeout: int = 120,
    max_matches: int = 200,
) -> ToolRegistry:
    """Build an opt-in registry containing only the static security audit toolset."""
    return security_research_tools(
        workspace_root=workspace_root,
        include_external=include_external,
        external_timeout=external_timeout,
        max_matches=max_matches,
        include_authorized_ops=False,
    )


__all__ = [
    "ExploitToolSet",
    "PasswordToolSet",
    "ReconToolSet",
    "SecurityAuditToolSet",
    "VulnScanToolSet",
    "security_audit_tools",
    "security_research_tools",
]
