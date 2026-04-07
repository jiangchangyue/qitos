from __future__ import annotations

from pathlib import Path
from typing import List

from examples.real.whitzard_agent import WhitzardAgent
from qitos.core import TerminalCapability
from qitos.core.tool_registry import ToolRegistry
from qitos.kit import SecurityAuditToolSet, TmuxEnv


class FakeTerminal(TerminalCapability):
    def __init__(self):
        self.alive = True
        self.screen = "$ "
        self.buffer = "$ "
        self.previous = None
        self.sent: list[str] = []
        self.waits: list[float] = []
        self.closed = False
        self.ts = 0.0

    def reset_session(self, cwd: str | None = None) -> None:
        self.screen = "$ "
        self.buffer = "$ "
        self.previous = None
        self.alive = True

    def close_session(self) -> None:
        self.closed = True
        self.alive = False

    def send_keys(
        self,
        keys: str | list[str],
        min_timeout_sec: float = 0.0,
        block: bool = False,
        max_timeout_sec: float = 180.0,
    ) -> dict:
        text = "".join(keys) if isinstance(keys, list) else str(keys)
        self.sent.append(text)
        self.waits.append(float(min_timeout_sec))
        self.ts += 1.0
        update = f"executed: {text.strip()}\n$ " if text.strip() else self.screen
        self.buffer += update
        self.screen = update
        return {
            "status": "success",
            "keys": text,
            "waited_seconds": min_timeout_sec,
            "block": block,
        }

    def capture_screen(self) -> str:
        return self.screen

    def capture_buffer(self) -> str:
        return self.buffer

    def get_incremental_output(self) -> str:
        current = self.buffer
        if self.previous is None:
            self.previous = current
            return f"Current Terminal Screen:\n{self.screen}"
        if self.previous in current:
            idx = current.index(self.previous) + len(self.previous)
            delta = current[idx:].lstrip("\n")
        else:
            delta = self.screen
        self.previous = current
        return (
            f"New Terminal Output:\n{delta}"
            if delta.strip()
            else f"Current Terminal Screen:\n{self.screen}"
        )

    def is_session_alive(self) -> bool:
        return self.alive

    def get_timestamp(self) -> float | None:
        return self.ts


class DummyModel:
    def __init__(self, outputs: List[str]):
        self.outputs = list(outputs)
        self.calls: list[list[dict[str, str]]] = []
        self.model = "dummy-whitzard"

    def __call__(self, messages):
        self.calls.append(list(messages))
        return self.outputs.pop(0)


def _seed_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text(
        "from flask import Flask, request\n"
        "import subprocess\n\n"
        "app = Flask(__name__)\n"
        "SECRET_KEY = 'hardcoded-secret-123456'\n\n"
        "@app.route('/run')\n"
        "def run():\n"
        "    subprocess.run(request.args.get('cmd'), shell=True)\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("flask\n", encoding="utf-8")


def test_security_audit_toolset_is_available_from_flat_surface(tmp_path: Path) -> None:
    toolset = SecurityAuditToolSet(workspace_root=str(tmp_path), include_external=False)
    registry = ToolRegistry().register_toolset(toolset, namespace="")
    names = registry.list_tools()
    assert "audit_inventory" in names
    assert "audit_hotspots" in names


def test_whitzard_agent_roundtrip_collects_findings_and_requires_double_completion(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    llm = DummyModel(
        outputs=[
            "not valid json",
            '{"analysis":"Inventory the repository","plan":"Run inventory and entrypoint scans","tools":[{"name":"audit_inventory","args":{}},{"name":"audit_entrypoints","args":{}}]}',
            '{"analysis":"Rank hotspots","plan":"Run hotspot analysis","tools":[{"name":"audit_hotspots","args":{}}]}',
            '{"analysis":"Record confirmed issue","plan":"Add a finding for the command injection sink","tools":[{"name":"finding_add","args":{"title":"Potential command injection via subprocess shell","severity":"high","description":"User-controlled command reaches subprocess.run(..., shell=True).","evidence":"app.py:8 subprocess.run(request.args.get(\'cmd\'), shell=True)","affected_component":"app.py","remediation":"Avoid shell=True and validate/allowlist commands."}}]}',
            '{"analysis":"Write the audit report","plan":"Generate a markdown report","tools":[{"name":"generate_report","args":{"format":"markdown","output_file":"security_report.md"}}]}',
            '{"analysis":"The report is written and findings are ranked","plan":"Request completion","task_complete":true}',
            '{"analysis":"Confirmed completion","plan":"Finish","task_complete":true}',
        ]
    )
    terminal = FakeTerminal()
    env = TmuxEnv(
        workspace_root=str(tmp_path),
        session_name="whitzard-loop",
        terminal=terminal,
        auto_kill=False,
    )
    agent = WhitzardAgent(llm=llm, workspace_root=str(tmp_path))

    result = agent.run(
        task="Audit this repository and write a report.",
        workspace=str(tmp_path),
        env=env,
        protocol="terminus_json_v1",
        max_steps=10,
        parser_format="json",
        render=False,
        trace=False,
        return_state=True,
    )

    assert result.state.stop_reason == "success"
    assert "security_report.md" in result.state.final_result
    assert result.state.final_report_path == "security_report.md"
    assert any(
        "subprocess" in str(item.get("evidence", "")) for item in result.state.findings
    )
    assert any(item.get("file") == "app.py" for item in result.state.hotspots)
    assert len(llm.calls) == 7
    assert "Parser feedback" in llm.calls[1][-1]["content"]
    assert (
        "Are you sure you want to mark the task as complete?"
        in llm.calls[6][-1]["content"]
    )
