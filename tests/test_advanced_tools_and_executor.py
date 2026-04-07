from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from qitos import (
    Action,
    StateSchema,
    ToolPermissionContext,
    ToolPermissionRule,
    ToolRegistry,
)
from qitos.core.action import ActionStatus
from qitos.core.tool import BaseTool, ToolPermission, ToolSpec, ToolValidationResult
from qitos.engine.action_executor import ActionExecutor
from qitos.kit.tool.tools import advanced_coding_tools
from qitos.kit.tool import (
    AskUserChoiceTool,
    BashV2,
    FileEditV2,
    FileReadV2,
    LSPQueryTool,
    MCPListResourcesTool,
    MCPReadResourceTool,
    TodoWriteTool,
    ToolSearchTool,
    WebFetchV2,
)


class _EchoTool(BaseTool):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="echo_tool",
                description="demo tool",
                parameters={"value": {"type": "string"}},
                required=["value"],
                permissions=ToolPermission(),
                result_max_chars=8,
            )
        )

    def validate_input(self, args, runtime_context=None):
        _ = runtime_context
        if str(args.get("value", "")) == "bad":
            return ToolValidationResult.fail("bad input", code="bad_input")
        return ToolValidationResult.ok()

    def run(self, value: str, runtime_context=None):
        _ = runtime_context
        return {"result": value}


@dataclass
class _ExecutorState(StateSchema):
    pass


def test_action_executor_applies_validation_permission_and_truncation():
    registry = ToolRegistry().register(_EchoTool())
    executor = ActionExecutor(registry)
    state = _ExecutorState(task="demo")

    ok = executor.execute(
        [Action(name="echo_tool", args={"value": "1234567890"})], state=state
    )[0]
    assert ok.status == ActionStatus.SUCCESS
    assert ok.output["result"].endswith("[truncated]")

    invalid = executor.execute(
        [Action(name="echo_tool", args={"value": "bad"})], state=state
    )[0]
    assert invalid.status == ActionStatus.ERROR
    assert invalid.metadata["error_category"] == "bad_input"

    state.metadata["tool_permission_context"] = ToolPermissionContext(
        deny_rules=[
            ToolPermissionRule(effect="deny", tool_name="echo_tool", message="blocked")
        ]
    )
    denied = executor.execute(
        [Action(name="echo_tool", args={"value": "ok"})], state=state
    )[0]
    assert denied.status == ActionStatus.SKIPPED
    assert denied.output["status"] == "denied"

    state.metadata["tool_permission_context"] = ToolPermissionContext(
        ask_rules=[
            ToolPermissionRule(
                effect="ask", tool_name="echo_tool", message="need approval"
            )
        ]
    )
    ask = executor.execute(
        [Action(name="echo_tool", args={"value": "ok"})], state=state
    )[0]
    assert ask.status == ActionStatus.SKIPPED
    assert ask.output["status"] == "needs_user_input"


def test_bash_v2_supports_read_only_and_background(tmp_path):
    tool = BashV2(workspace_root=str(tmp_path))
    valid = tool.validate_input({"command": "rg --files .", "read_only": True})
    assert valid.valid

    destructive = tool.validate_input(
        {"command": "rm -rf tmp", "allow_destructive": False}
    )
    assert not destructive.valid

    bg = tool.run(command="sleep 0.1; echo hi", run_in_background=True)
    assert bg["status"] == "success"
    assert Path(bg["stdout_path"]).exists()
    time.sleep(0.2)


def test_file_read_and_edit_v2_preserve_line_endings_and_detect_conflicts(tmp_path):
    path = tmp_path / "demo.txt"
    path.write_bytes(b"hello\r\nworld\r\n")

    reader = FileReadV2(workspace_root=str(tmp_path))
    read_out = reader.run(path="demo.txt")
    assert read_out["status"] == "success"
    assert read_out["line_ending"] == "\r\n"

    editor = FileEditV2(workspace_root=str(tmp_path))
    edit_out = editor.run(
        path="demo.txt",
        action="str_replace",
        old_text="world",
        new_text="qitos",
        expected_mtime=path.stat().st_mtime,
    )
    assert edit_out["status"] == "success"
    assert b"\r\n" in path.read_bytes()

    stale = editor.run(
        path="demo.txt",
        action="str_replace",
        old_text="qitos",
        new_text="again",
        expected_mtime=0.0,
    )
    assert stale["status"] == "error"
    assert "modified" in stale["message"]


def test_web_fetch_v2_handles_redirect_and_prompt_extraction(monkeypatch):
    tool = WebFetchV2()

    def _redirect(
        url: str,
        params=None,
        headers=None,
        timeout=None,
        verify_tls=True,
        allow_redirects: bool = False,
    ):
        _ = params
        _ = headers
        _ = timeout
        _ = verify_tls
        _ = allow_redirects
        return {
            "status": "success",
            "url": "https://redirected.example.com/doc",
            "status_code": 302,
            "content": "",
            "headers": {"Location": "https://redirected.example.com/doc"},
        }

    monkeypatch.setattr(tool._impl.http_get, "run", _redirect)
    redirect = tool.run(url="https://example.com/doc", prompt="summarize")
    assert redirect["redirect_url"] == "https://redirected.example.com/doc"

    def _content(
        url: str,
        params=None,
        headers=None,
        timeout=None,
        verify_tls=True,
        allow_redirects: bool = False,
    ):
        _ = url
        _ = params
        _ = headers
        _ = timeout
        _ = verify_tls
        _ = allow_redirects
        return {
            "status": "success",
            "url": "https://github.com/openai/example",
            "status_code": 200,
            "content": "<html><body><p>QitOS adds advanced coding tools.</p><p>Advanced tools include bash, file edit, and tool search.</p></body></html>",
            "headers": {},
        }

    monkeypatch.setattr(tool._impl.http_get, "run", _content)
    out = tool.run(
        url="https://github.com/openai/example", prompt="advanced tool search"
    )
    assert out["status"] == "success"
    assert "tool search" in out["result"].lower()
    assert out["auth_hint"]


def test_session_tools_and_tool_search(tmp_path):
    registry = advanced_coding_tools(str(tmp_path), enable_lsp=False, enable_web=False)
    state = _ExecutorState(task="advanced")
    ctx = {"state": state, "tool_registry": registry}

    todo = TodoWriteTool().run(
        todos=[{"content": "ship", "status": "pending"}], runtime_context=ctx
    )
    assert todo["count"] == 1

    plan_enter = registry.get("enter_plan_mode").run(
        reason="decompose", runtime_context=ctx
    )
    assert plan_enter["current_mode"] == "plan"

    create = registry.get("task_create").run(
        subject="Implement", description="Do the work", runtime_context=ctx
    )
    listed = registry.get("task_list").run(runtime_context=ctx)
    assert create["status"] == "success"
    assert listed["count"] == 1

    search = ToolSearchTool().run(query="plan", runtime_context=ctx)
    assert search["count"] >= 1


def test_lsp_query_and_mcp_resource_tools():
    class _FakeLSP:
        def query(self, **kwargs):
            return {"status": "success", "kwargs": kwargs}

    lsp = LSPQueryTool()
    out = lsp.run(
        operation="definition",
        symbol="demo",
        runtime_context={"ops": {"lsp": _FakeLSP()}},
    )
    assert out["status"] == "success"
    assert out["kwargs"]["operation"] == "definition"

    resources = {
        "docs": [
            {"uri": "memo://one", "text": "alpha"},
            {"uri": "memo://two", "text": "beta"},
        ]
    }
    listed = MCPListResourcesTool().run(runtime_context={"mcp_resources": resources})
    assert "docs" in listed["resources"]

    read = MCPReadResourceTool().run(
        server="docs", uri="memo://two", runtime_context={"mcp_resources": resources}
    )
    assert read["resource"]["text"] == "beta"


def test_ask_user_choice_returns_needs_input_without_answers():
    tool = AskUserChoiceTool()
    out = tool.run(
        questions=[
            {
                "header": "Mode",
                "question": "Which mode?",
                "options": [{"label": "A"}, {"label": "B"}],
            }
        ]
    )
    assert out["status"] == "needs_user_input"
