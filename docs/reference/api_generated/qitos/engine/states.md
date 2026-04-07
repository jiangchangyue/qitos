# `qitos.engine.states`

- Module Group: `qitos.engine`
- Source: [qitos/engine/states.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/states.py)

## Quick Jump

- [Classes](#classes)
- [Functions](#functions)
- [Class: `ContextConfig`](#class-contextconfig)
- [Class: `ContextTelemetry`](#class-contexttelemetry)
- [Class: `RuntimeBudget`](#class-runtimebudget)
- [Class: `RuntimeEvent`](#class-runtimeevent)
- [Class: `RuntimePhase`](#class-runtimephase)
- [Class: `StepRecord`](#class-steprecord)

## Classes

<a id="class-contextconfig"></a>
???+ note "Class: `ContextConfig(self, enabled: 'bool' = True, warning_ratio: 'float' = 0.8, compact_ratio: 'float' = 0.85, safety_reserve_tokens: 'Optional[int]' = None, safety_reserve_ratio: 'float' = 0.05, min_safety_reserve_tokens: 'int' = 1024, default_context_window: 'int' = 128000, strict_overflow: 'bool' = True, show_ui: 'bool' = True) -> None`"
    ContextConfig(enabled: 'bool' = True, warning_ratio: 'float' = 0.8, compact_ratio: 'float' = 0.85, safety_reserve_tokens: 'Optional[int]' = None, safety_reserve_ratio: 'float' = 0.05, min_safety_reserve_tokens: 'int' = 1024, default_context_window: 'int' = 128000, strict_overflow: 'bool' = True, show_ui: 'bool' = True)

<a id="class-contexttelemetry"></a>
???+ note "Class: `ContextTelemetry(self, context_window: 'Optional[int]' = None, available_input_budget: 'Optional[int]' = None, system_prompt_tokens: 'int' = 0, history_tokens: 'int' = 0, prepared_tokens: 'int' = 0, input_tokens_total: 'int' = 0, output_tokens: 'int' = 0, occupancy_ratio: 'float' = 0.0, warning_threshold_ratio: 'float' = 0.8, counting_mode: 'str' = 'disabled', prompt_tokens_total: 'int' = 0, completion_tokens_total: 'int' = 0, tokens_total: 'int' = 0, peak_input_tokens: 'int' = 0, peak_occupancy_ratio: 'float' = 0.0, history_message_count: 'int' = 0, compact_events: 'List[Dict[str, Any]]' = <factory>, reserve_tokens: 'int' = 0, max_output_tokens: 'int' = 0, history_budget: 'Optional[int]' = None) -> None`"
    ContextTelemetry(context_window: 'Optional[int]' = None, available_input_budget: 'Optional[int]' = None, system_prompt_tokens: 'int' = 0, history_tokens: 'int' = 0, prepared_tokens: 'int' = 0, input_tokens_total: 'int' = 0, output_tokens: 'int' = 0, occupancy_ratio: 'float' = 0.0, warning_threshold_ratio: 'float' = 0.8, counting_mode: 'str' = 'disabled', prompt_tokens_total: 'int' = 0, completion_tokens_total: 'int' = 0, tokens_total: 'int' = 0, peak_input_tokens: 'int' = 0, peak_occupancy_ratio: 'float' = 0.0, history_message_count: 'int' = 0, compact_events: 'List[Dict[str, Any]]' = <factory>, reserve_tokens: 'int' = 0, max_output_tokens: 'int' = 0, history_budget: 'Optional[int]' = None)

<a id="class-runtimebudget"></a>
???+ note "Class: `RuntimeBudget(self, max_steps: 'int' = 20, max_runtime_seconds: 'Optional[float]' = None, max_tokens: 'Optional[int]' = None) -> None`"
    RuntimeBudget(max_steps: 'int' = 20, max_runtime_seconds: 'Optional[float]' = None, max_tokens: 'Optional[int]' = None)

<a id="class-runtimeevent"></a>
???+ note "Class: `RuntimeEvent(self, step_id: 'int', phase: 'RuntimePhase', ok: 'bool' = True, payload: 'Dict[str, Any]' = <factory>, error: 'Optional[str]' = None, ts: 'str' = <factory>) -> None`"
    RuntimeEvent(step_id: 'int', phase: 'RuntimePhase', ok: 'bool' = True, payload: 'Dict[str, Any]' = <factory>, error: 'Optional[str]' = None, ts: 'str' = <factory>)

<a id="class-runtimephase"></a>
???+ note "Class: `RuntimePhase(self, *args, **kwds)`"
    str(object='') -> str

<a id="class-steprecord"></a>
???+ note "Class: `StepRecord(self, step_id: 'int', phase_events: 'List[RuntimeEvent]' = <factory>, observation: 'Any' = None, decision: 'Any' = None, actions: 'List[Any]' = <factory>, action_results: 'List[Any]' = <factory>, tool_invocations: 'List[Any]' = <factory>, critic_outputs: 'List[Any]' = <factory>, state_diff: 'Dict[str, Any]' = <factory>, context: 'Dict[str, Any]' = <factory>) -> None`"
    StepRecord(step_id: 'int', phase_events: 'List[RuntimeEvent]' = <factory>, observation: 'Any' = None, decision: 'Any' = None, actions: 'List[Any]' = <factory>, action_results: 'List[Any]' = <factory>, tool_invocations: 'List[Any]' = <factory>, critic_outputs: 'List[Any]' = <factory>, state_diff: 'Dict[str, Any]' = <factory>, context: 'Dict[str, Any]' = <factory>)

## Functions

- _None_

## Source Index

- [qitos/engine/states.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/states.py)
