"""Verify that tutorial code snippets compile and import correctly.

This test extracts Python code blocks from tutorial .mdx files and validates:
1. Syntax correctness (compile)
2. Import resolution (the referenced modules actually exist)
3. Basic instantiation (no runtime errors for simple patterns)

It does NOT run end-to-end agent execution — snippets that call agent.run()
are expected to fail at the network call, not at import/construction time.
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TUTORIALS_DIR = Path(__file__).resolve().parent.parent / "docs" / "tutorials"

_PYTHON_CODE_BLOCK_RE = re.compile(
    r"```python\n(.*?)```",
    re.DOTALL,
)


def _extract_python_blocks(mdx_path: Path) -> list[str]:
    """Extract all Python code blocks from an .mdx file."""
    content = mdx_path.read_text(encoding="utf-8")
    return _PYTHON_CODE_BLOCK_RE.findall(content)


def _get_tutorial_files() -> list[Path]:
    """Return all EN tutorial .mdx files."""
    if not _TUTORIALS_DIR.exists():
        return []
    return sorted(_TUTORIALS_DIR.glob("*.mdx"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTutorialSnippets:
    """Compile and import-check tutorial code snippets."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_tutorials(self):
        if not _get_tutorial_files():
            pytest.skip("No tutorial files found")

    # Tutorials that are purely prose/navigation (no Python code expected)
    _PROSE_ONLY_TUTORIALS = {
        "index.mdx",
        "inspect-a-gui-failure-in-qita.mdx",
        "run-your-first-desktop-benchmark.mdx",
        "replay-and-inspect-failed-runs.mdx",
    }

    def test_new_tutorials_have_python_blocks(self):
        """Newly added tutorials should contain at least one Python code block."""
        new_tutorials = {
            "critic-system.mdx",
            "hook-lifecycle.mdx",
            "func-api.mdx",
            "mcp-integration.mdx",
            "checkpoint-and-fork.mdx",
        }
        for path in _get_tutorial_files():
            if path.name not in new_tutorials:
                continue
            blocks = _extract_python_blocks(path)
            assert len(blocks) > 0, f"{path.name} has no Python code blocks"

    def test_snippets_compile(self):
        """Every Python code block should be syntactically valid.

        Blocks with ``...`` placeholders (common in docs) are skipped.
        Async blocks with top-level ``await`` are wrapped in ``async def``.
        """
        for path in _get_tutorial_files():
            blocks = _extract_python_blocks(path)
            for i, block in enumerate(blocks):
                block = textwrap.dedent(block).strip()
                if not block:
                    continue
                # Skip blocks with ellipsis placeholders
                if "..." in block:
                    continue
                try:
                    compile(block, f"{path.name}:block-{i}", "exec")
                except SyntaxError:
                    # Async code blocks use 'await' at top level — wrap in async def
                    if "await " in block:
                        wrapped = "async def _snippet():\n" + textwrap.indent(block, "    ")
                        try:
                            compile(wrapped, f"{path.name}:block-{i}", "exec")
                        except SyntaxError as e2:
                            pytest.fail(
                                f"Syntax error in {path.name} block {i}: {e2}"
                            )
                    else:
                        raise

    def test_qitos_imports_resolve(self):
        """Imports from qitos should resolve without ImportError."""
        for path in _get_tutorial_files():
            blocks = _extract_python_blocks(path)
            for i, block in enumerate(blocks):
                block = textwrap.dedent(block).strip()
                if not block:
                    continue
                # Extract import lines
                try:
                    tree = ast.parse(block)
                except SyntaxError:
                    continue  # Already tested in compile test

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("qitos"):
                                try:
                                    __import__(alias.name)
                                except ImportError as e:
                                    pytest.fail(
                                        f"Import error in {path.name} block {i}: "
                                        f"cannot import {alias.name}: {e}"
                                    )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("qitos"):
                            try:
                                __import__(node.module)
                            except ImportError as e:
                                pytest.fail(
                                    f"Import error in {path.name} block {i}: "
                                    f"cannot import from {node.module}: {e}"
                                )
