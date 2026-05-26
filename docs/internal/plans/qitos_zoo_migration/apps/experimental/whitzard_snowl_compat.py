"""Snowl compatibility adapter for qitos_auditor (Whitzard).

Provides the adapter interface for running the Whitzard security audit
agent under the Snowl evaluation framework, including CyberGym and
OWASP benchmark configuration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Snowl agent factory
# ---------------------------------------------------------------------------

REQUIRED_TOOLS: List[str] = [
    "shell",
    "file_read",
    "file_write",
    "security_audit",
    "report",
]
REQUIRED_ENV: Dict[str, Any] = {
    "type": "host",
    "capabilities": ["filesystem", "command", "network"],
}


def create_snowl_agent(
    *,
    model: Optional[str] = None,
    max_steps: int = 300,
    **kwargs: Any,
) -> Any:
    """Create a qitos_auditor (Whitzard) agent for Snowl evaluation.

    Parameters
    ----------
    model : str | None
        Model identifier. Falls back to family preset resolution.
    max_steps : int
        Maximum steps per audit run.
    **kwargs
        Additional arguments forwarded to the agent constructor.

    Returns
    -------
    WhitzardAgent
        A configured agent instance.
    """
    # Import from experimental until formal migration
    from .whitzard_agent import WhitzardAgent

    return WhitzardAgent(
        model=model,
        max_steps=max_steps,
        **kwargs,
    )


def map_findings_to_owasp(result: Any) -> List[Dict[str, Any]]:
    """Map Whitzard findings to OWASP Top 10 categories.

    Parameters
    ----------
    result : EngineResult
        Result from running the auditor agent.

    Returns
    -------
    list[dict]
        Findings mapped to OWASP categories.
    """
    findings = []
    state = getattr(result, "state", None)
    if state is None:
        return findings

    # Extract confirmed findings from state
    confirmed = getattr(state, "confirmed_findings", [])
    for finding in confirmed:
        if isinstance(finding, dict):
            findings.append({
                "category": finding.get("category", "A01:2021-Broken Access Control"),
                "severity": finding.get("severity", "MEDIUM"),
                "description": finding.get("description", ""),
                "evidence": finding.get("evidence", ""),
                "remediation": finding.get("remediation", ""),
            })
        else:
            findings.append({
                "category": "A01:2021-Broken Access Control",
                "severity": "MEDIUM",
                "description": str(finding),
                "evidence": "",
                "remediation": "",
            })

    return findings


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize an audit result to Snowl-compatible JSON.

    Parameters
    ----------
    result : EngineResult
        Result from running the auditor agent.

    Returns
    -------
    dict
        Snowl-compatible trajectory with mapped findings.
    """
    from qitos.engine.run_state import RunState
    import json

    state = RunState.from_engine_result(result, agent_name="qitos_auditor")
    data = json.loads(state.to_json(pretty=False))
    data["owasp_findings"] = map_findings_to_owasp(result)
    return data


def deserialize_run(raw: str) -> Any:
    """Deserialize a Snowl trajectory back to a RunState.

    Parameters
    ----------
    raw : str
        JSON string from Snowl storage.

    Returns
    -------
    RunState
        Restored run state.
    """
    from qitos.engine.run_state import RunState

    return RunState.from_json(raw)


__all__ = [
    "create_snowl_agent",
    "map_findings_to_owasp",
    "serialize_run",
    "deserialize_run",
    "REQUIRED_TOOLS",
    "REQUIRED_ENV",
]
