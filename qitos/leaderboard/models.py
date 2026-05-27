"""Leaderboard submission data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping


@dataclass
class LeaderboardSubmission:
    """One row in the leaderboard — a benchmark task result tied to a RunSpec."""

    submission_id: str
    benchmark: str
    split: str
    task_id: str
    model_name: str = ""
    model_family: str = ""
    prompt_protocol: str = ""
    parser_name: str = ""
    success: bool = False
    stop_reason: str = ""
    steps: int = 0
    latency_seconds: float = 0.0
    token_usage: int = 0
    cost: float = 0.0
    is_official: bool = False
    run_spec_json: str = "{}"
    result_json: str = "{}"
    trace_artifacts_dir: str = ""
    git_sha: str = ""
    package_version: str = ""
    submitted_at: str = ""
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_value(cls, value: Mapping[str, Any]) -> LeaderboardSubmission:
        known = {k: v for k, v in dict(value).items() if k in cls.__dataclass_fields__}
        # Fill missing required fields with empty defaults
        for fname in cls.__dataclass_fields__:
            if fname not in known:
                known[fname] = ""
        return cls(**known)
