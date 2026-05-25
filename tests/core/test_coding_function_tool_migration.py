"""Tests for @function_tool migration of coding tools."""
from __future__ import annotations
import pytest
from qitos.core.function_tool_decorator import function_tool
from qitos.core.tool import FunctionTool
from qitos.kit.tool.internal.coding_impl import CodingToolSet

class TestCodingFunctionToolMigration:
    def test_all_tools_are_function_tools(self):
        """Every @tool method should now be a FunctionTool instance."""
        cts = CodingToolSet(workspace_root="/tmp", include_notebook=False, enable_lsp=False, enable_tasks=False, enable_web=False)
        # Get all tool methods
        for name in dir(cts):
            attr = getattr(cts, name)
            if hasattr(attr, 'spec') and hasattr(attr, 'func'):
                assert isinstance(attr, FunctionTool), f"{name} is not a FunctionTool"

    def test_destructive_tools_need_approval(self):
        """Tools with side effects should have needs_approval=True."""
        cts = CodingToolSet(workspace_root="/tmp", include_notebook=False, enable_lsp=False, enable_tasks=False, enable_web=False)
        destructive_tools = ["shell", "file_write", "file_edit", "replace_lines", "create_file", "delete_file", "mkdir"]
        for tool_name in destructive_tools:
            attr = getattr(cts, tool_name, None)
            if attr and hasattr(attr, 'meta'):
                assert attr.meta.needs_approval is True, f"{tool_name} should need approval"

    def test_read_tools_are_read_only(self):
        """Read-only tools should have read_only=True."""
        cts = CodingToolSet(workspace_root="/tmp", include_notebook=False, enable_lsp=False, enable_tasks=False, enable_web=False)
        read_tools = ["file_read", "view", "grep", "glob", "find_files", "list_dir", "get_cwd"]
        for tool_name in read_tools:
            attr = getattr(cts, tool_name, None)
            if attr and hasattr(attr, 'meta'):
                assert attr.meta.read_only is True, f"{tool_name} should be read_only"

    def test_tools_have_rich_schema(self):
        """FunctionTool should produce richer parameter schemas than @tool."""
        cts = CodingToolSet(workspace_root="/tmp", include_notebook=False, enable_lsp=False, enable_tasks=False, enable_web=False)
        for name in ["file_read", "shell"]:
            attr = getattr(cts, name, None)
            if attr and hasattr(attr, 'spec'):
                assert attr.spec.parameters is not None
                assert len(attr.spec.parameters) > 0
