"""Reusable multi-agent pattern templates for QitOS."""

from .manager_worker import ManagerWorkerConfig, build_manager_worker_system
from .planner_executor import PlannerExecutorConfig, build_planner_executor_system
from .proposer_verifier import ProposerVerifierConfig, build_proposer_verifier_system
from .debate import DebateConfig, build_debate_system
from .moa import MoAConfig, build_moa_system
from .workflow import Workflow, WorkflowConfig, build_workflow_system

__all__ = [
    "ManagerWorkerConfig",
    "build_manager_worker_system",
    "PlannerExecutorConfig",
    "build_planner_executor_system",
    "ProposerVerifierConfig",
    "build_proposer_verifier_system",
    "DebateConfig",
    "build_debate_system",
    "MoAConfig",
    "build_moa_system",
    "Workflow",
    "WorkflowConfig",
    "build_workflow_system",
]
