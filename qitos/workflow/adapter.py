"""SharedMemory Adapter — bridge VariablePool ↔ SharedMemory."""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos_dag.variable_pool import VariablePool


class SharedMemoryAdapter:
    """Bidirectional adapter between qitos-dag VariablePool and
    qitos SharedMemory.

    Uses SharedMemoryNamespace for namespaced access, since
    SharedMemory.write() only accepts (key, value) without a
    namespace parameter.
    """

    def __init__(self, pool: VariablePool, shared_memory: Any = None) -> None:
        self.pool = pool
        self.shared_memory = shared_memory

    def sync_to_shared_memory(self, namespace: str = "workflow") -> None:
        """Write VariablePool contents to SharedMemory via SharedMemoryNamespace."""
        if self.shared_memory is None:
            return

        from qitos.core.shared_memory import SharedMemoryNamespace

        ns = SharedMemoryNamespace(self.shared_memory, namespace)
        snapshot = self.pool.debug_dump()
        for node_id, vars_ in snapshot.items():
            for var_name, value in vars_.items():
                ns.write(f"{node_id}.{var_name}", value)

    def sync_from_shared_memory(self, namespace: str = "workflow") -> None:
        """Read SharedMemory contents into VariablePool via SharedMemoryNamespace."""
        if self.shared_memory is None:
            return

        from qitos.core.shared_memory import SharedMemoryNamespace

        ns = SharedMemoryNamespace(self.shared_memory, namespace)
        for key in ns.list_keys():
            value = ns.read(key)
            parts = key.split(".", 1)
            if len(parts) == 2:
                node_id, var_name = parts
                self.pool.write(node_id, var_name, value)

    @staticmethod
    def sync_engine_result(
        pool: VariablePool, node_id: str, engine_result: Any
    ) -> None:
        """Write Engine result fields into VariablePool for downstream nodes.

        Extracts final_result, stop_reason, current_step from EngineResult.state
        and writes them as node outputs so downstream DAG nodes can access them
        via selectors like {{#agent1.result#}}.
        """
        state = getattr(engine_result, "state", engine_result)
        pool.write(node_id, "result", getattr(state, "final_result", "") or "")
        pool.write(node_id, "stop_reason", getattr(state, "stop_reason", "") or "")
        pool.write(node_id, "steps", getattr(state, "current_step", 0))

    def write_handoff_payload(
        self, target_agent: str, payload: Dict[str, Any]
    ) -> None:
        """Write handoff payload to SharedMemory for a target agent."""
        if self.shared_memory is None:
            # Fallback: write to conversation variables
            for key, value in payload.items():
                self.pool.set_conversation_variable(
                    f"_handoff_{target_agent}_{key}", value
                )
            return

        from qitos.core.shared_memory import SharedMemoryNamespace

        ns = SharedMemoryNamespace(self.shared_memory, target_agent)
        for key, value in payload.items():
            ns.write(key, value)
