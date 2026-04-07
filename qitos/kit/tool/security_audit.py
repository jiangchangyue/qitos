"""Stable public export surface for the curated defensive security audit toolset."""

from __future__ import annotations

from typing import Any

from qitos.kit.tool.experimental.security_research import (
    security_audit_tools as _security_audit_tools,
)
from qitos.kit.tool.experimental.security_research.security_audit import (
    SecurityAuditToolSet as _SecurityAuditToolSet,
)


class SecurityAuditToolSet(_SecurityAuditToolSet):
    """Public defensive code-security audit toolset."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)


def security_audit_tools(*args: Any, **kwargs: Any):
    """Build a registry containing the defensive code-security audit toolset."""
    return _security_audit_tools(*args, **kwargs)


__all__ = ["SecurityAuditToolSet", "security_audit_tools"]
