"""Tests for the qitos_zoo package structure and imports."""

import pytest


class TestQitOSZooPackage:
    """Test the qitos_zoo top-level package."""

    def test_version(self):
        from qitos_zoo import __version__

        assert __version__ == "0.1.0"

    def test_package_importable(self):
        import qitos_zoo

        assert qitos_zoo is not None


class TestQitOSCoder:
    """Test the qitos_coder sub-package."""

    def test_sub_package_importable(self):
        import qitos_zoo.qitos_coder

        assert qitos_zoo.qitos_coder is not None

    def test_claude_code_agent_from_init(self):
        from qitos_zoo.qitos_coder import ClaudeCodeAgent, ClaudeCodeState

        assert ClaudeCodeAgent is not None
        assert ClaudeCodeState is not None

    def test_claude_code_agent_from_module(self):
        from qitos_zoo.qitos_coder.claude_code.agent import ClaudeCodeAgent

        assert ClaudeCodeAgent is not None

    def test_claude_code_state_from_module(self):
        from qitos_zoo.qitos_coder.claude_code.agent import ClaudeCodeState

        assert ClaudeCodeState is not None

    def test_claude_code_sub_package_importable(self):
        from qitos_zoo.qitos_coder.claude_code import ClaudeCodeAgent, ClaudeCodeState

        assert ClaudeCodeAgent is not None
        assert ClaudeCodeState is not None

    def test_claude_code_main_importable(self):
        from qitos_zoo.qitos_coder.claude_code import main

        assert callable(main)


class TestQitOSCyber:
    """Test the qitos_cyber sub-package."""

    def test_sub_package_importable(self):
        import qitos_zoo.qitos_cyber

        assert qitos_zoo.qitos_cyber is not None

    def test_security_audit_agent_importable(self):
        from qitos_zoo.qitos_cyber.code_security_audit_agent import (
            CodeSecurityAuditAgent,
        )

        assert CodeSecurityAuditAgent is not None

    def test_pentagi_runner_importable(self):
        from qitos_zoo.qitos_cyber.pentagi.runner import PentAGIRunner

        assert PentAGIRunner is not None

    def test_snowl_compat_importable(self):
        from qitos_zoo.qitos_cyber.snowl_compat import create_snowl_agent

        assert callable(create_snowl_agent)

    def test_code_security_audit_agent_from_init(self):
        from qitos_zoo.qitos_cyber import CodeSecurityAuditAgent, SecurityAuditState

        assert CodeSecurityAuditAgent is not None
        assert SecurityAuditState is not None

    def test_pentagi_classes_from_init(self):
        from qitos_zoo.qitos_cyber import (
            PentAGIConfig,
            PentAGIRunner,
            PentAGIFlow,
            PentAGIResult,
            PentAGIMemory,
            PrimaryPentestAgent,
            ReflectorCritic,
        )

        assert PentAGIConfig is not None
        assert PentAGIRunner is not None
        assert PentAGIFlow is not None
        assert PentAGIResult is not None
        assert PentAGIMemory is not None
        assert PrimaryPentestAgent is not None
        assert ReflectorCritic is not None

    def test_snowl_compat_from_init(self):
        from qitos_zoo.qitos_cyber import create_snowl_agent, map_results_to_trajectory

        assert callable(create_snowl_agent)
        assert callable(map_results_to_trajectory)

    def test_all_completeness(self):
        import qitos_zoo.qitos_cyber as cyber

        assert hasattr(cyber, "__all__")
        for name in cyber.__all__:
            assert hasattr(cyber, name), f"{name} in __all__ but not in module"
        # Verify every public name from __all__ is importable
        for name in cyber.__all__:
            obj = getattr(cyber, name)
            assert obj is not None, f"{name} is None"


class TestQitOSResearcher:
    """Test the qitos_researcher sub-package."""

    def test_sub_package_importable(self):
        import qitos_zoo.qitos_researcher

        assert qitos_zoo.qitos_researcher is not None

    def test_researcher_from_init(self):
        from qitos_zoo.qitos_researcher import QitOSResearcher, ResearcherState

        assert QitOSResearcher is not None
        assert ResearcherState is not None

    def test_researcher_from_module(self):
        from qitos_zoo.qitos_researcher.agent import QitOSResearcher

        assert QitOSResearcher is not None

    def test_snowl_compat_importable(self):
        from qitos_zoo.qitos_researcher.snowl_compat import create_snowl_agent

        assert callable(create_snowl_agent)


class TestQitOSSWE:
    """Test the qitos_swe sub-package."""

    def test_sub_package_importable(self):
        import qitos_zoo.qitos_swe

        assert qitos_zoo.qitos_swe is not None

    def test_swe_agent_from_init(self):
        from qitos_zoo.qitos_swe import QitOSSWEAgent, SWEState

        assert QitOSSWEAgent is not None
        assert SWEState is not None

    def test_swe_agent_from_module(self):
        from qitos_zoo.qitos_swe.agent import QitOSSWEAgent

        assert QitOSSWEAgent is not None

    def test_snowl_compat_importable(self):
        from qitos_zoo.qitos_swe.snowl_compat import create_snowl_agent

        assert callable(create_snowl_agent)
