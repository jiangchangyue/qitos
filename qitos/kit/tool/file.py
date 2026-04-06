"""File-oriented concrete tool objects."""

from __future__ import annotations

import os
from typing import Any, Dict

from qitos.core.tool import BaseTool, ToolPermission, ToolSpec


class WriteFile(BaseTool):
    """Write UTF-8 text to a workspace file, creating parent directories when needed.

    Use this tool when the agent needs to create or fully overwrite a file. The
    path is resolved relative to the configured workspace root and is rejected if
    it escapes that boundary.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="write_file",
                description="Write content to a file under workspace",
                parameters={"filename": {"type": "string"}, "content": {"type": "string"}},
                required=["filename", "content"],
                permissions=ToolPermission(filesystem_write=True),
                required_ops=["file"],
            )
        )

    def run(self, filename: str, content: str, runtime_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Write text content to a file under the workspace root.

        :param filename: Path relative to the workspace root.
        :param content: Full text content to write into the file.
        :param runtime_context: Optional runtime ops injected by the engine.

        Creates parent directories automatically. Rejects paths that escape the
        configured workspace boundary.
        """
        runtime_context = runtime_context or {}
        ops = runtime_context.get("ops", {})
        file_ops = ops.get("file")
        if file_ops is not None and hasattr(file_ops, "write_text"):
            try:
                file_ops.write_text(filename, content)
                return {"status": "success", "path": filename, "size": len(content)}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        if not filename:
            return {"status": "error", "message": "Filename cannot be empty"}
        safe_path = os.path.abspath(os.path.join(self._root_dir, filename))
        if not safe_path.startswith(self._root_dir):
            return {"status": "error", "message": "Access to files outside directory is prohibited"}
        try:
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "path": safe_path, "size": len(content)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ReadFile(BaseTool):
    """Read the full UTF-8 text content of a workspace file.

    Use this tool to inspect a specific file before editing, summarizing, or
    reasoning over its contents. The tool returns both the raw text and basic
    metadata such as the path and size.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="read_file",
                description="Read file content under workspace",
                parameters={"filename": {"type": "string"}},
                required=["filename"],
                permissions=ToolPermission(filesystem_read=True),
                required_ops=["file"],
            )
        )

    def run(self, filename: str, runtime_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Read the full text content of a file under the workspace root.

        :param filename: Path relative to the workspace root.
        :param runtime_context: Optional runtime ops injected by the engine.

        Returns the file content together with path and size metadata.
        """
        runtime_context = runtime_context or {}
        ops = runtime_context.get("ops", {})
        file_ops = ops.get("file")
        if file_ops is not None and hasattr(file_ops, "read_text"):
            try:
                content = file_ops.read_text(filename)
                return {"status": "success", "content": content, "path": filename, "size": len(content)}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        if not filename:
            return {"status": "error", "message": "Filename cannot be empty"}
        safe_path = os.path.abspath(os.path.join(self._root_dir, filename))
        if not safe_path.startswith(self._root_dir):
            return {"status": "error", "message": "Access to files outside directory is prohibited"}
        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "content": content, "path": safe_path, "size": len(content)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ListFiles(BaseTool):
    """List files and directories under a workspace-relative path.

    Use this tool to discover what exists in the current workspace before
    deciding which files to inspect or edit. The output distinguishes files from
    directories and includes file sizes when available.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="list_files",
                description="List files and directories under workspace",
                parameters={"path": {"type": "string"}},
                required=[],
                permissions=ToolPermission(filesystem_read=True),
                required_ops=["file"],
            )
        )

    def run(self, path: str = ".", runtime_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        List files and directories under a workspace-relative path.

        :param path: Directory path relative to the workspace root.
        :param runtime_context: Optional runtime ops injected by the engine.

        Returns one entry per file or directory, including type information and
        file sizes where available.
        """
        runtime_context = runtime_context or {}
        ops = runtime_context.get("ops", {})
        file_ops = ops.get("file")
        if file_ops is not None and hasattr(file_ops, "list_files"):
            try:
                files = file_ops.list_files(path=path)
                return {"status": "success", "path": path, "count": len(files), "files": files}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        target_path = os.path.abspath(os.path.join(self._root_dir, path))
        if not target_path.startswith(self._root_dir):
            return {"status": "error", "message": "Access to files outside directory is prohibited"}
        try:
            items = []
            for item in os.listdir(target_path):
                item_path = os.path.join(target_path, item)
                items.append(
                    {
                        "name": item,
                        "type": "directory" if os.path.isdir(item_path) else "file",
                        "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None,
                    }
                )
            items.sort(key=lambda x: (x["type"] == "file", x["name"]))
            return {"status": "success", "path": target_path, "count": len(items), "files": items}
        except Exception as e:
            return {"status": "error", "message": str(e)}


__all__ = ["WriteFile", "ReadFile", "ListFiles"]
