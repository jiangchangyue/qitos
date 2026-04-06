"""Atomic codebase tools inspired by code-assistant search/edit workflows."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from qitos.core.tool import BaseTool, ToolPermission, ToolSpec


def _resolve_workspace_path(root_dir: str, path: str) -> str:
    root = Path(root_dir).expanduser().resolve()
    target = (root / (path or ".")).resolve()
    if target != root and root not in target.parents:
        raise PermissionError(f"Access denied: '{path}' is outside workspace '{root}'")
    return str(target)


def _iter_files(base_dir: str, include_hidden: bool = False) -> Iterable[Path]:
    base = Path(base_dir)
    for root, dirs, files in os.walk(base):
        if not include_hidden:
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"__pycache__", "node_modules", ".venv"}
            ]
            files = [f for f in files if not f.startswith(".")]
        for name in files:
            yield Path(root) / name


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


class GlobFiles(BaseTool):
    """Find workspace files whose names or relative paths match a glob pattern.

    Use this tool to quickly discover candidate files, such as all test files,
    source files, or configuration files that match a naming pattern.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="glob_files",
                description="Find files under workspace matching a glob pattern",
                parameters={
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "include_hidden": {"type": "boolean"},
                    "limit": {"type": "integer"},
                },
                required=["pattern"],
                permissions=ToolPermission(filesystem_read=True),
                required_ops=["file"],
            )
        )

    def run(
        self,
        pattern: str,
        path: str = ".",
        include_hidden: bool = False,
        limit: int = 100,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Find files under the workspace that match a glob pattern.

        :param pattern: Glob pattern such as `*.py` or `src/**/*.md`.
        :param path: Directory path, relative to the workspace root, to search in.
        :param include_hidden: Whether to include hidden files and directories.
        :param limit: Maximum number of matching files to return.
        :param runtime_context: Optional runtime ops injected by the engine.

        Matches both relative paths and file basenames, and reports whether the
        result list was truncated by the requested limit.
        """
        _ = runtime_context
        if not pattern.strip():
            return {"status": "error", "message": "Pattern cannot be empty"}
        try:
            target_dir = _resolve_workspace_path(self._root_dir, path)
            max_results = max(1, int(limit))
            matches: List[str] = []
            truncated = False
            for file_path in _iter_files(target_dir, include_hidden=include_hidden):
                rel = os.path.relpath(str(file_path), self._root_dir)
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    if len(matches) >= max_results:
                        truncated = True
                        break
                    matches.append(rel)
            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "num_files": len(matches),
                "files": sorted(matches),
                "truncated": truncated,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class GrepFiles(BaseTool):
    """Search workspace files for a regex or plain-text pattern.

    Use this tool to locate symbols, error messages, TODOs, or repeated strings
    across many files. It can return either line-level matches or only the file
    paths that contain at least one match.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="grep_files",
                description="Search file contents under workspace with regex or plain text",
                parameters={
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "case_sensitive": {"type": "boolean"},
                    "regex": {"type": "boolean"},
                    "files_with_matches": {"type": "boolean"},
                    "limit": {"type": "integer"},
                },
                required=["pattern"],
                permissions=ToolPermission(filesystem_read=True),
                required_ops=["file"],
            )
        )

    def run(
        self,
        pattern: str,
        path: str = ".",
        glob: Optional[str] = None,
        case_sensitive: bool = False,
        regex: bool = True,
        files_with_matches: bool = False,
        limit: int = 100,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search workspace files for a regex or plain-text pattern.

        :param pattern: Regex or literal text to search for.
        :param path: Directory path, relative to the workspace root, to search in.
        :param glob: Optional glob filter applied before reading candidate files.
        :param case_sensitive: Whether matching should preserve case.
        :param regex: Whether `pattern` should be interpreted as a regex.
        :param files_with_matches: If true, return only one entry per matching file.
        :param limit: Maximum number of returned matches.
        :param runtime_context: Optional runtime ops injected by the engine.

        Returns either line-level matches or matching file paths, depending on
        `files_with_matches`.
        """
        _ = runtime_context
        if not pattern.strip():
            return {"status": "error", "message": "Pattern cannot be empty"}
        try:
            target_dir = _resolve_workspace_path(self._root_dir, path)
            flags = 0 if case_sensitive else re.IGNORECASE
            matcher = re.compile(pattern if regex else re.escape(pattern), flags)
            max_results = max(1, int(limit))
            entries: List[Dict[str, Any]] = []
            seen_files: set[str] = set()
            truncated = False
            for file_path in _iter_files(target_dir):
                rel = os.path.relpath(str(file_path), self._root_dir)
                if glob and not (fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(file_path.name, glob)):
                    continue
                try:
                    content = _read_text(file_path)
                except Exception:
                    continue
                for line_no, line in enumerate(content.splitlines(), 1):
                    if not matcher.search(line):
                        continue
                    if files_with_matches:
                        if rel in seen_files:
                            break
                        seen_files.add(rel)
                        if len(entries) >= max_results:
                            truncated = True
                            break
                        entries.append({"path": rel})
                        break
                    if len(entries) >= max_results:
                        truncated = True
                        break
                    entries.append({"path": rel, "line": line_no, "text": line})
                if truncated:
                    break
            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "matches": entries,
                "num_matches": len(entries),
                "truncated": truncated,
            }
        except re.error as e:
            return {"status": "error", "message": f"Invalid regex: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ReadFileRange(BaseTool):
    """Read a bounded line range from one workspace file.

    Use this tool when the full file would be too large or when the agent only
    needs a localized code or text snippet around a known region.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="read_file_range",
                description="Read a line range from a file under workspace",
                parameters={
                    "filename": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                required=["filename"],
                permissions=ToolPermission(filesystem_read=True),
                required_ops=["file"],
            )
        )

    def run(
        self,
        filename: str,
        offset: int = 0,
        limit: int = 200,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Read a bounded line range from one workspace file.

        :param filename: File path relative to the workspace root.
        :param offset: Zero-based starting line offset.
        :param limit: Maximum number of lines to return.
        :param runtime_context: Optional runtime ops injected by the engine.

        Returns both the concatenated text chunk and a structured per-line view.
        """
        _ = runtime_context
        try:
            resolved = Path(_resolve_workspace_path(self._root_dir, filename))
            lines = _read_text(resolved).splitlines()
            start = max(0, int(offset))
            size = max(1, int(limit))
            end = start + size
            chunk = lines[start:end]
            return {
                "status": "success",
                "path": os.path.relpath(str(resolved), self._root_dir),
                "offset": start,
                "limit": size,
                "total_lines": len(lines),
                "content": "\n".join(chunk),
                "lines": [{"line": start + i + 1, "text": text} for i, text in enumerate(chunk)],
                "has_more": end < len(lines),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class AppendFile(BaseTool):
    """Append new text to the end of a workspace file.

    Use this tool for additive updates such as log notes, generated snippets, or
    report sections when replacing the whole file would be unnecessary.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="append_file",
                description="Append content to a file under workspace",
                parameters={"filename": {"type": "string"}, "content": {"type": "string"}},
                required=["filename", "content"],
                permissions=ToolPermission(filesystem_write=True),
                required_ops=["file"],
            )
        )

    def run(
        self,
        filename: str,
        content: str,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append text to the end of a workspace file.

        :param filename: File path relative to the workspace root.
        :param content: Text to append.
        :param runtime_context: Optional runtime ops injected by the engine.

        Creates the file and any missing parent directories when needed.
        """
        _ = runtime_context
        try:
            resolved = Path(_resolve_workspace_path(self._root_dir, filename))
            resolved.parent.mkdir(parents=True, exist_ok=True)
            with resolved.open("a", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "path": os.path.relpath(str(resolved), self._root_dir),
                "appended_size": len(content),
                "size": resolved.stat().st_size,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class MakeDirectory(BaseTool):
    """Create a directory tree inside the workspace if it does not already exist.

    Use this tool before writing files into a new folder structure or preparing
    output locations for generated artifacts.
    """

    def __init__(self, root_dir: str = "."):
        self._root_dir = os.path.abspath(root_dir)
        super().__init__(
            ToolSpec(
                name="make_directory",
                description="Create a directory under workspace",
                parameters={"path": {"type": "string"}},
                required=["path"],
                permissions=ToolPermission(filesystem_write=True),
            )
        )

    def run(self, path: str, runtime_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a directory inside the workspace.

        :param path: Directory path relative to the workspace root.
        :param runtime_context: Optional runtime ops injected by the engine.

        Creates parent directories automatically and succeeds if the directory
        already exists.
        """
        _ = runtime_context
        try:
            resolved = Path(_resolve_workspace_path(self._root_dir, path))
            resolved.mkdir(parents=True, exist_ok=True)
            return {"status": "success", "path": os.path.relpath(str(resolved), self._root_dir)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class CodebaseToolSet:
    """Bundle common code-search and lightweight file-mutation tools for coding agents."""

    name = "codebase"
    version = "1"

    def __init__(self, workspace_root: str = "."):
        self.glob_files = GlobFiles(root_dir=workspace_root)
        self.grep_files = GrepFiles(root_dir=workspace_root)
        self.read_file_range = ReadFileRange(root_dir=workspace_root)
        self.append_file = AppendFile(root_dir=workspace_root)
        self.make_directory = MakeDirectory(root_dir=workspace_root)

    def setup(self, context: dict[str, Any]) -> None:
        _ = context

    def teardown(self, context: dict[str, Any]) -> None:
        _ = context

    def tools(self) -> list[Any]:
        return [
            self.glob_files,
            self.grep_files,
            self.read_file_range,
            self.append_file,
            self.make_directory,
        ]


__all__ = [
    "GlobFiles",
    "GrepFiles",
    "ReadFileRange",
    "AppendFile",
    "MakeDirectory",
    "CodebaseToolSet",
]
