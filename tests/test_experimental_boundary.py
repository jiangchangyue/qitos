"""Test that shim files emit DeprecationWarning when imported."""

import warnings


class TestNetworkToolsetShim:
    def test_import_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Force re-import by using importlib
            import importlib
            import qitos.kit.tool.network_toolset as mod
            importlib.reload(mod)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Expected at least one DeprecationWarning"
            msg = str(deprecation_warnings[0].message)
            assert "deprecated" in msg.lower()
            assert "network_toolset" in msg

    def test_network_toolset_accessible(self):
        """Backward compat: NetworkToolSet is importable from the shim."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from qitos.kit.tool.network_toolset import NetworkToolSet
        assert NetworkToolSet is not None

    def test_network_toolset_matches_experimental(self):
        """Shim re-exports the same class from the experimental package."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from qitos.kit.tool.network_toolset import NetworkToolSet as ShimClass
        from qitos.kit.tool.experimental.security_research.network_toolset import (
            NetworkToolSet as ExpClass,
        )
        assert ShimClass is ExpClass


class TestWebTestToolsetShim:
    def test_import_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import importlib
            import qitos.kit.tool.web_test_toolset as mod
            importlib.reload(mod)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Expected at least one DeprecationWarning"
            msg = str(deprecation_warnings[0].message)
            assert "deprecated" in msg.lower()
            assert "web_test_toolset" in msg

    def test_web_test_toolset_accessible(self):
        """Backward compat: WebTestToolSet is importable from the shim."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from qitos.kit.tool.web_test_toolset import WebTestToolSet
        assert WebTestToolSet is not None

    def test_web_test_toolset_matches_experimental(self):
        """Shim re-exports the same class from the experimental package."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from qitos.kit.tool.web_test_toolset import WebTestToolSet as ShimClass
        from qitos.kit.tool.experimental.security_research.web_test_toolset import (
            WebTestToolSet as ExpClass,
        )
        assert ShimClass is ExpClass


class TestSecurityAuditAgentShim:
    def test_import_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import importlib
            import qitos.kit.agent.security_audit_agent as mod
            importlib.reload(mod)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Expected at least one DeprecationWarning"
            msg = str(deprecation_warnings[0].message)
            assert "deprecated" in msg.lower()
            assert "security_audit_agent" in msg
