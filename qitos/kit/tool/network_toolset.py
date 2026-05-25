"""Compatibility shim for experimental network tools.

These tools are explicit opt-in and now live under
`qitos.kit.tool.experimental.security_research`.
"""

import warnings

warnings.warn(
    "Importing from qitos.kit.tool.network_toolset is deprecated. "
    "Use qitos.kit.tool.experimental.security_research.network_toolset instead.",
    DeprecationWarning,
    stacklevel=2,
)

from qitos.kit.tool.experimental.security_research.network_toolset import NetworkToolSet

__all__ = ["NetworkToolSet"]
