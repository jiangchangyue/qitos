"""Compatibility shim for experimental web testing tools.

These tools are explicit opt-in and now live under
`qitos.kit.tool.experimental.security_research`.
"""

import warnings

warnings.warn(
    "Importing from qitos.kit.tool.web_test_toolset is deprecated. "
    "Use qitos.kit.tool.experimental.security_research.web_test_toolset instead.",
    DeprecationWarning,
    stacklevel=2,
)

from qitos.kit.tool.experimental.security_research.web_test_toolset import WebTestToolSet

__all__ = ["WebTestToolSet"]
