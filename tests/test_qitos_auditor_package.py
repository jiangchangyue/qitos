"""Tests for qitos_auditor package."""
from __future__ import annotations

import pytest


def test_auditor_package_imports():
    from qitos_zoo.qitos_auditor import AuditAgent, AuditState

    assert AuditAgent is not None
    assert AuditState is not None


def test_auditor_agent_instantiation(tmp_path):
    from qitos_zoo.qitos_auditor import AuditAgent
    from examples._support import SequenceModel

    agent = AuditAgent(
        llm=SequenceModel(["Final Answer: No issues found."]),
        workspace_root=str(tmp_path),
    )
    assert agent is not None
    assert agent.tool_registry is not None


def test_auditor_tools_have_correct_markers():
    from qitos_zoo.qitos_auditor.tools.audit_toolset import AuditToolSet

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ts = AuditToolSet(workspace_root=tmp)
        tools = ts.tools()
        assert len(tools) == 11
        needs_approval_names = {
            "audit_report_findings",
            "audit_generate_report",
            "audit_track_remediation",
            "audit_index_knowledge",
        }
        for tool in tools:
            from qitos.core.tool import FunctionTool

            assert isinstance(tool, FunctionTool)
            if tool.spec.name in needs_approval_names:
                assert tool.spec.needs_approval is True
            else:
                assert tool.spec.read_only is True


def test_audit_state_defaults():
    from qitos_zoo.qitos_auditor import AuditState

    state = AuditState(task="test", max_steps=5)
    assert state.mode == "code_audit"
    assert state.findings == []
    assert state.scanned_files == []


def test_auditor_modes():
    from qitos_zoo.qitos_auditor import AuditAgent
    from examples._support import SequenceModel

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        agent_security = AuditAgent(
            llm=SequenceModel(["Final Answer: done."]),
            workspace_root=tmp,
            mode="security_audit",
        )
        assert agent_security._mode == "security_audit"


def test_snowl_compat():
    from qitos_zoo.qitos_auditor.snowl_compat import get_eval_config

    config = get_eval_config()
    assert config["agent_name"] == "qitos_auditor"
    assert "metrics" in config


def test_auditor_tool_registry_has_audit_tools():
    from qitos_zoo.qitos_auditor import AuditAgent
    from examples._support import SequenceModel

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        agent = AuditAgent(
            llm=SequenceModel(["Final Answer: done."]),
            workspace_root=tmp,
        )
        tool_names = agent.tool_registry.list_tools()
        assert "audit_scan_patterns" in tool_names
        assert "audit_check_compliance" in tool_names
        assert "audit_report_findings" in tool_names
        assert "audit_suggest_fix" in tool_names
        assert "audit_generate_report" in tool_names
        assert "audit_check_compliance_template" in tool_names
        assert "audit_ci_summary" in tool_names
        assert "audit_deduplicate_findings" in tool_names
        assert "audit_track_remediation" in tool_names
