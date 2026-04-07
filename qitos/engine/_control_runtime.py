"""Private control-flow helpers for Engine."""

from __future__ import annotations

import time
from typing import Any, Dict, Generic, List, Optional, TypeVar

from ..core.decision import Decision
from ..core.errors import StopReason
from ..core.state import StateSchema
from ._context_runtime import ContextOverflowError
from .states import RuntimePhase, StepRecord


StateT = TypeVar("StateT", bound=StateSchema)
ObservationT = TypeVar("ObservationT")
ActionT = TypeVar("ActionT")


class _ControlRuntime(Generic[StateT, ObservationT, ActionT]):
    def __init__(self, engine: Any):
        self.engine = engine

    def run_reduce(
        self,
        state: StateT,
        observation: ObservationT,
        decision: Decision[ActionT],
        record: StepRecord,
    ) -> None:
        engine = self.engine
        engine._dispatch_hook(
            "on_before_reduce",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.REDUCE,
                state=state,
                observation=observation,
                decision=decision,
                action_results=(record.action_results if record is not None else []),
                record=record,
            ),
        )
        engine._emit(record.step_id, RuntimePhase.REDUCE, payload={"stage": "start"})
        before = state.to_dict()
        new_state = engine.agent.reduce(state, observation, decision)
        if new_state is not state:
            state.__dict__.update(new_state.__dict__)
        after = state.to_dict()
        engine._memory_append("next_state", after, record.step_id)
        record.state_diff = engine._compute_state_diff(before, after)
        engine._emit(
            record.step_id,
            RuntimePhase.REDUCE,
            payload={"stage": "state_reduced", "state_diff": record.state_diff},
        )
        engine._dispatch_hook(
            "on_after_reduce",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.REDUCE,
                state=state,
                observation=observation,
                decision=decision,
                action_results=(record.action_results if record is not None else []),
                record=record,
                payload={"state_diff": record.state_diff},
            ),
        )

    def apply_critics(self, state: StateT, record: StepRecord) -> str:
        engine = self.engine
        if not engine.critics:
            return "continue"
        engine._dispatch_hook(
            "on_before_critic",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.CRITIC,
                state=state,
                decision=record.decision,
                action_results=record.action_results,
                record=record,
            ),
        )
        engine._emit(
            record.step_id,
            RuntimePhase.CRITIC,
            payload={"stage": "start", "critic_count": len(engine.critics)},
        )
        outputs: List[Dict[str, Any]] = []
        for critic in engine.critics:
            out = critic.evaluate(state, record.decision, record.action_results)
            outputs.append(
                out
                if isinstance(out, dict)
                else {"action": "continue", "reason": "invalid_critic_output"}
            )
        record.critic_outputs = outputs
        engine._emit(
            record.step_id,
            RuntimePhase.CRITIC,
            payload={"stage": "outputs", "critic_outputs": outputs},
        )
        for output in outputs:
            action = str(output.get("action", "continue"))
            if action == "stop":
                engine._emit(
                    record.step_id,
                    RuntimePhase.CRITIC,
                    payload={"stage": "stop", "reason": output.get("reason")},
                )
                engine._dispatch_hook(
                    "on_after_critic",
                    engine._hook_context(
                        step_id=record.step_id,
                        phase=RuntimePhase.CRITIC,
                        state=state,
                        decision=record.decision,
                        action_results=record.action_results,
                        record=record,
                        payload={"critic_outputs": outputs, "result": "stop"},
                    ),
                )
                return "stop"
            if action == "retry":
                engine._emit(
                    record.step_id,
                    RuntimePhase.CRITIC,
                    payload={"stage": "retry", "reason": output.get("reason")},
                )
                engine._dispatch_hook(
                    "on_after_critic",
                    engine._hook_context(
                        step_id=record.step_id,
                        phase=RuntimePhase.CRITIC,
                        state=state,
                        decision=record.decision,
                        action_results=record.action_results,
                        record=record,
                        payload={"critic_outputs": outputs, "result": "retry"},
                    ),
                )
                return "retry"
        engine._emit(record.step_id, RuntimePhase.CRITIC, payload={"stage": "pass"})
        engine._dispatch_hook(
            "on_after_critic",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.CRITIC,
                state=state,
                decision=record.decision,
                action_results=record.action_results,
                record=record,
                payload={"critic_outputs": outputs, "result": "continue"},
            ),
        )
        return "continue"

    def run_check_stop(
        self,
        state: StateT,
        decision: Decision[ActionT],
        step_id: int,
        started_at: float,
    ) -> bool:
        engine = self.engine
        engine._dispatch_hook(
            "on_before_check_stop",
            engine._hook_context(
                step_id=step_id,
                phase=RuntimePhase.CHECK_STOP,
                state=state,
                decision=decision,
            ),
        )
        engine._emit(
            state.current_step, RuntimePhase.CHECK_STOP, payload={"stage": "start"}
        )

        if decision.mode == "final":
            state.set_stop(StopReason.FINAL, decision.final_answer)
            self._finish_check_stop(
                step_id=step_id, state=state, decision=decision, stop=True
            )
            return True
        if engine.agent.should_stop(state):
            if state.stop_reason is None:
                state.set_stop(StopReason.AGENT_CONDITION)
            self._finish_check_stop(
                step_id=step_id, state=state, decision=decision, stop=True
            )
            return True
        if engine.env is not None and engine.env.is_terminal(
            state=state, last_result=engine._last_env_result
        ):
            if state.stop_reason is None:
                state.set_stop(StopReason.ENV_TERMINAL)
            self._finish_check_stop(
                step_id=step_id,
                state=state,
                decision=decision,
                stop=True,
                extra_payload={"env_terminal": True},
            )
            return True

        elapsed = time.monotonic() - started_at
        should_stop, reason, detail = self.should_stop_by_criteria(
            state, step_id, elapsed
        )
        if should_stop:
            if state.stop_reason is None:
                state.set_stop(reason or StopReason.UNRECOVERABLE_ERROR)
            self._finish_check_stop(
                step_id=step_id,
                state=state,
                decision=decision,
                stop=True,
                extra_payload={"stop_detail": detail},
            )
            return True

        self._finish_check_stop(
            step_id=step_id, state=state, decision=decision, stop=False
        )
        return False

    def _finish_check_stop(
        self,
        step_id: int,
        state: StateT,
        decision: Decision[ActionT],
        stop: bool,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        engine = self.engine
        if stop:
            payload: Dict[str, Any] = {
                "stage": "stop",
                "stop_reason": state.stop_reason,
                "final_result": state.final_result,
            }
            if extra_payload:
                payload.update(extra_payload)
            engine._emit(state.current_step, RuntimePhase.CHECK_STOP, payload=payload)
        else:
            engine._emit(
                state.current_step,
                RuntimePhase.CHECK_STOP,
                payload={"stage": "continue"},
            )
        engine._dispatch_hook(
            "on_after_check_stop",
            engine._hook_context(
                step_id=step_id,
                phase=RuntimePhase.CHECK_STOP,
                state=state,
                decision=decision,
                stop_reason=state.stop_reason if stop else None,
                payload={"result": "stop" if stop else "continue"},
            ),
        )

    def should_stop_by_criteria(
        self,
        state: StateT,
        step_id: int,
        elapsed_seconds: float,
    ) -> tuple[bool, Optional[StopReason], Optional[str]]:
        engine = self.engine
        for criteria in engine.stop_criteria:
            hit, reason, detail = criteria.should_stop(
                state,
                step_id,
                runtime_info={
                    "elapsed_seconds": elapsed_seconds,
                    "budget_max_steps": engine.budget.max_steps,
                    "budget_max_runtime_seconds": engine.budget.max_runtime_seconds,
                    "budget_max_tokens": engine.budget.max_tokens,
                },
            )
            if hit:
                return True, reason, detail
        return False, None, None

    def budget_exhausted(self, step_id: int, started_at: float, state: StateT) -> bool:
        engine = self.engine
        if step_id >= engine.budget.max_steps:
            state.set_stop(StopReason.BUDGET_STEPS)
            return True
        if engine.budget.max_runtime_seconds is not None:
            elapsed = time.monotonic() - started_at
            if elapsed > engine.budget.max_runtime_seconds:
                state.set_stop(StopReason.BUDGET_TIME)
                return True
        if engine.budget.max_tokens is not None and engine._token_usage >= int(
            engine.budget.max_tokens
        ):
            state.set_stop(StopReason.BUDGET_TOKENS)
            return True
        return False

    def recover(self, state: StateT, phase: RuntimePhase, exc: Exception) -> bool:
        engine = self.engine
        step_id = state.current_step
        engine._dispatch_hook(
            "on_recover",
            engine._hook_context(
                step_id=step_id,
                phase=phase,
                state=state,
                error=exc,
                stop_reason=state.stop_reason,
            ),
        )
        if phase == RuntimePhase.DECIDE:
            engine._emit(step_id, RuntimePhase.DECIDE_ERROR, ok=False, error=str(exc))
        elif phase == RuntimePhase.ACT:
            engine._emit(step_id, RuntimePhase.ACT_ERROR, ok=False, error=str(exc))
        engine._emit(step_id, RuntimePhase.RECOVER, ok=False, error=str(exc))

        if engine.recovery_handler is not None:
            engine.recovery_handler(state, phase, exc)

        if isinstance(exc, ContextOverflowError):
            state.set_stop(StopReason.CONTEXT_OVERFLOW)
            return False

        decision = engine.recovery_policy.handle(state, phase.value, step_id, exc)
        if decision.stop_reason:
            state.set_stop(decision.stop_reason)
        if not decision.continue_run and state.stop_reason is None:
            state.set_stop(StopReason.UNRECOVERABLE_ERROR)
        return decision.continue_run

    def infer_failed_phase(self, record: StepRecord) -> RuntimePhase:
        if not record.phase_events:
            return RuntimePhase.RECOVER
        latest = record.phase_events[-1].phase
        if latest == RuntimePhase.DECIDE:
            return RuntimePhase.DECIDE
        if latest == RuntimePhase.ACT:
            return RuntimePhase.ACT
        return RuntimePhase.RECOVER
