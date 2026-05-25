"""Minimal protocol for Engine references in runtime helper classes.

This avoids circular imports while providing type safety for the
private runtime mixins that need access to Engine internals.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..core.action import Action
    from ..core.decision import Decision
    from ..core.tool_result import ToolResult
    from .states import ContextConfig, RuntimeBudget, RuntimePhase, StepRecord


@runtime_checkable
class _EngineProtocol(Protocol):
    """Subset of Engine attributes/methods used by runtime helper classes."""

    # -- core attributes --
    agent: Any
    budget: Any  # RuntimeBudget
    context_config: Any  # ContextConfig
    executor: Any  # ActionExecutor
    env: Optional[Any]
    records: List[Any]  # List[StepRecord]
    auto_approve: bool

    # -- internal state --
    _active_run_id: str
    _last_system_prompt: str
    _last_prompt_metadata: Dict[str, Any]
    _token_usage: int
    _last_context_telemetry: Dict[str, Any]
    _critic_modified_prompt: Optional[str]
    _critic_instruction_patch: Optional[str]
    _tool_loop_detector: Any
    _handoff_history: List[str]

    # -- methods used by runtime mixins --
    def _dispatch_hook(self, method_name: str, ctx: Any) -> None: ...
    def _hook_context(self, **kwargs: Any) -> Any: ...
    def _emit(self, step_id: int, phase: Any, payload: Optional[Dict[str, Any]] = None) -> None: ...
    def _memory_append(self, category: str, item: Any, step_id: int) -> None: ...
    def _history_append(self, role: str, content: str, step_id: int, **kwargs: Any) -> None: ...
    def _intercept_handoff_action(self, action: Any) -> Optional[Any]: ...
    def _run_env_step(self, **kwargs: Any) -> Optional[Any]: ...
    def _env_step_result_to_dict(self, result: Any) -> Dict[str, Any]: ...
