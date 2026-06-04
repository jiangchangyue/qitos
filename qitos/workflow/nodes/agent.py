"""Agent Node — delegate to a QitOS AgentModule via Engine.

Unifies LLMNode and AgentNode: every intelligent workflow node IS an agent.
Supports two modes:
  - Pre-registered agent from AgentRegistry (via resolve)
  - Auto-created _WorkflowAgent from config (prompt_template, system_prompt, etc.)

Both run through the Engine's observe→decide→act→reduce loop.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos_dag.node import NodeCategory, NodeConfig, WorkflowNode, register_node_type
from qitos_dag.variable_pool import VariablePool


@register_node_type
class AgentNode(WorkflowNode):
    """Delegate execution to a QitOS AgentModule via Engine.

    Supports two delegation modes:
    - delegate: Nested Engine.run() (synchronous delegation)
    - handoff: Control transfer via _source_handle signal

    Config data:
        agent_name: str — registered agent name in AgentRegistry (optional if prompt_template provided)
        prompt_template: str — for auto-creating a simple agent
        system_prompt: str — system prompt for auto-created agent
        mode: str — "delegate" | "handoff" (default "delegate")
        task_template: str — task text with template references
        max_steps: int — max steps for the delegated agent (default 10)
        context_strategy: str — "FULL" | "SUMMARY" | "ISOLATED" (for handoff)
        _agent_registry: Any — injected at runtime
        _llm: Any — injected LLM for auto-created agents
        _shared_memory: Any — injected SharedMemory instance
        _tracing_provider: Any — injected TracingProvider
        _hooks: list — injected Engine hooks
    """

    node_type = "agent"
    category = NodeCategory.EXECUTABLE

    def validate_config(self) -> None:
        has_name = bool(self.config.data.get("agent_name"))
        has_template = bool(self.config.data.get("prompt_template"))
        if not has_name and not has_template:
            raise ValueError(
                f"AgentNode '{self.id}': need agent_name or prompt_template"
            )

    async def run(self, inputs: Dict[str, Any], pool: VariablePool) -> Dict[str, Any]:
        agent_name = self.config.data.get("agent_name", "")
        mode = self.config.data.get("mode", "delegate")
        task_template = self.config.data.get("task_template", "")
        max_steps = self.config.data.get("max_steps", 10)

        # Resolve task template
        if task_template:
            task = pool.resolve_template(task_template)
        else:
            task = inputs.get("task", inputs.get("query", ""))

        # Resolve agent: try registry first, fall back to auto-created
        agent, spec = self._resolve_agent(agent_name)

        if agent is None:
            return {"error": f"Could not resolve agent '{agent_name}' and no prompt_template provided"}

        if mode == "handoff" and spec is not None:
            return await self._handoff(agent, task, spec, pool)

        return await self._delegate(agent, task, max_steps, pool)

    def _resolve_agent(self, agent_name: str) -> tuple[Any, Optional[Any]]:
        """Resolve agent from registry or create from config.

        Returns (agent, spec) — spec is None for auto-created agents.
        """
        agent_registry = self.config.data.get("_agent_registry")
        if agent_registry is not None and agent_name:
            try:
                spec = agent_registry.resolve(agent_name)
                return spec.agent, spec
            except KeyError:
                pass

        # Fall back to auto-created agent
        prompt_template = self.config.data.get("prompt_template", "")
        system_prompt = self.config.data.get("system_prompt", "")
        if prompt_template or system_prompt:
            agent = _WorkflowAgent(
                system_prompt=system_prompt,
                prompt_template=prompt_template,
                llm=self.config.data.get("_llm"),
            )
            return agent, None

        return None, None

    async def _delegate(
        self, agent: Any, task: str, max_steps: int, pool: VariablePool
    ) -> Dict[str, Any]:
        """Delegate via nested Engine.run() with full context injection."""
        from qitos.engine.engine import Engine
        from qitos.engine.states import RuntimeBudget

        budget = RuntimeBudget(max_steps=max_steps)

        # Build Engine with full injected context
        engine_kwargs: Dict[str, Any] = {
            "agent": agent,
            "budget": budget,
        }

        # Pass through injected observability and state dependencies
        shared_memory = self.config.data.get("_shared_memory")
        if shared_memory is not None:
            engine_kwargs["shared_memory"] = shared_memory

        tracing_provider = self.config.data.get("_tracing_provider")
        if tracing_provider is not None:
            engine_kwargs["tracing_provider"] = tracing_provider

        agent_registry = self.config.data.get("_agent_registry")
        if agent_registry is not None:
            engine_kwargs["agent_registry"] = agent_registry

        hooks = self.config.data.get("_hooks")
        if hooks:
            engine_kwargs["hooks"] = list(hooks)

        # Install event bridge hook to surface Engine events in DAG
        event_emitter = self.config.data.get("_event_emitter")
        if event_emitter is not None:
            from ..event_bridge import EngineToDagHook
            bridge = EngineToDagHook(emit_callback=event_emitter, node_id=self.id)
            engine_kwargs.setdefault("hooks", []).append(bridge.as_engine_hook())

        # Inject conversation history from pool into the agent
        history = pool.read_optional(("conversation", "_conversation_history"))
        if history is not None and hasattr(agent, "history"):
            agent.history = history

        engine = Engine(**engine_kwargs)
        result = engine.run(task=task)

        # Sync Engine result to VariablePool for downstream nodes
        result_data = {
            "result": result.state.final_result or "",
            "stop_reason": result.state.stop_reason or "",
            "steps": result.state.current_step,
        }
        pool.write(self.id, "result", result_data["result"])
        pool.write(self.id, "stop_reason", result_data["stop_reason"])
        pool.write(self.id, "steps", result_data["steps"])

        # Sync SharedMemory writes from Engine back to VariablePool
        if shared_memory is not None:
            from ..adapter import SharedMemoryAdapter
            adapter = SharedMemoryAdapter(pool, shared_memory)
            adapter.sync_from_shared_memory(namespace=f"agent_{self.id}")

        # Persist conversation history for next AgentNode
        engine_history = getattr(engine, "_runtime_history", None)
        if engine_history is not None:
            items = getattr(engine_history, "_items", None)
            if items is not None:
                pool.set_conversation_variable(
                    "_conversation_history", list(items)
                )

        return result_data

    async def _handoff(
        self, agent: Any, task: str, spec: Any, pool: VariablePool
    ) -> Dict[str, Any]:
        """Handoff — signal control transfer via _source_handle."""
        handoff_payload = self.config.data.get("handoff_payload", {})
        for key, value in handoff_payload.items():
            if isinstance(value, str):
                resolved = pool.resolve_template(value)
            else:
                resolved = value
            pool.set_conversation_variable(f"_handoff_{key}", resolved)

        return {
            "_source_handle": f"handoff:{spec.name}",
            "handoff_target": spec.name,
            "task": task,
        }


class _WorkflowAgent:
    """Lightweight agent for workflow AgentNode.

    Implements the AgentModule interface (init_state, build_system_prompt,
    prepare, reduce) so it can run through Engine. Does NOT override
    decide() — Engine handles LLM calls by default.
    """

    name = "workflow_agent"

    def __init__(
        self,
        system_prompt: str = "",
        prompt_template: str = "",
        llm: Any = None,
        **kwargs: Any,
    ) -> None:
        self._system_prompt = system_prompt
        self._prompt_template = prompt_template
        self.llm = llm
        self.tool_registry = None
        self.model_parser = None
        self.model_protocol = None
        self.memory = None
        self.history = None
        self.mcp_servers = []
        self.config = kwargs

    # -- AgentModule abstract methods --

    def init_state(self, task: str, **kwargs: Any):
        from qitos.core.state import StateSchema

        return StateSchema(task=task, max_steps=kwargs.get("max_steps", 1))

    def reduce(self, state: Any, observation: Any, decision: Any):
        mode = decision.mode
        if mode == "final" or getattr(mode, "value", None) == "final":
            state.final_result = decision.final_answer or ""
        return state

    # -- AgentModule overridable methods --

    def build_system_prompt(self, state: Any) -> str | None:
        return self._system_prompt or "You are a helpful AI assistant."

    def prepare(self, state: Any) -> str:
        if self._prompt_template:
            return self._prompt_template.format(task=state.task)
        return state.task

    def build_engine(self, **engine_kwargs: Any):
        from qitos.engine.engine import Engine

        return Engine(agent=self, **engine_kwargs)
