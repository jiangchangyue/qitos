"""Private action execution helpers for Engine."""

from __future__ import annotations

from typing import Any, Dict, Generic, List, TypeVar, cast

from ..core.action import Action
from ..core.decision import Decision
from .states import RuntimePhase, StepRecord


StateT = TypeVar("StateT")
ActionT = TypeVar("ActionT")


class _ActionRuntime(Generic[StateT, ActionT]):
    def __init__(self, engine: Any):
        self.engine = engine

    def run_act(
        self, state: StateT, decision: Decision[ActionT], record: StepRecord
    ) -> List[Any]:
        engine = self.engine
        engine._dispatch_hook(
            "on_before_act",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.ACT,
                state=state,
                decision=decision,
                record=record,
            ),
        )
        engine._emit(record.step_id, RuntimePhase.ACT, payload={"stage": "start"})

        if decision.mode != "act":
            engine._emit(
                record.step_id,
                RuntimePhase.ACT,
                payload={"stage": "skipped", "reason": "decision_not_act"},
            )
            return []
        if engine.executor is None:
            raise RuntimeError("No tool registry configured for action execution")

        actions: List[Action] = []
        for action in decision.actions:
            if isinstance(action, Action):
                actions.append(action)
                continue
            payload = (
                action if isinstance(action, dict) else cast(Dict[str, Any], action)
            )
            actions.append(Action.from_dict(payload))
        for normalized_action in actions:
            engine._memory_append("action", normalized_action, record.step_id)

        execution = engine.executor.execute(actions, env=engine.env, state=state)
        record.tool_invocations = [
            {
                "tool_name": item.name,
                "toolset_name": item.metadata.get("toolset_name"),
                "toolset_version": item.metadata.get("toolset_version"),
                "source": item.metadata.get("source"),
                "attempts": item.attempts,
                "latency_ms": item.latency_ms,
                "status": item.status.value,
                "error_category": item.metadata.get("error_category"),
                "error": item.error,
            }
            for item in execution
        ]
        results = [
            r.output if r.status.value == "success" else {"error": r.error}
            for r in execution
        ]
        if engine.env is not None:
            env_result = engine._run_env_step(decision=decision, action_results=results)
            if env_result is not None:
                results.append({"env": engine._env_step_result_to_dict(env_result)})
        record.action_results = results
        for item in results:
            engine._memory_append("action_result", item, record.step_id)
        engine._emit(
            record.step_id,
            RuntimePhase.ACT,
            payload={
                "stage": "action_results",
                "tool_invocations": record.tool_invocations,
                "action_results": results,
            },
        )
        engine._dispatch_hook(
            "on_after_act",
            engine._hook_context(
                step_id=record.step_id,
                phase=RuntimePhase.ACT,
                state=state,
                decision=decision,
                action_results=results,
                record=record,
            ),
        )
        return results
