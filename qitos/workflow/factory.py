"""QitosNodeFactory — construct QitOS-specific workflow nodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from qitos_dag.node import NodeConfig, WorkflowNode, create_node
from qitos_dag.schema import NodeSchema

# Import QitOS nodes to register them
from .nodes.tool import ToolNode
from .nodes.agent import AgentNode
from .nodes.human import HumanInputNode


class QitosNodeFactory:
    """Factory for constructing QitOS-specific workflow nodes.

    Extends the base qitos-dag node factory with QitOS-specific
    dependency injection (ToolRegistry, AgentRegistry, SharedMemory,
    LLM, TracingProvider, etc.).
    """

    def __init__(
        self,
        tool_registry: Any = None,
        agent_registry: Any = None,
        tracing_provider: Any = None,
        shared_memory: Any = None,
        llm: Any = None,
        hooks: Optional[List[Any]] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.tracing_provider = tracing_provider
        self.shared_memory = shared_memory
        self.llm = llm
        self.hooks = hooks

    def create(self, schema: NodeSchema) -> WorkflowNode:
        """Construct a WorkflowNode from a NodeSchema, injecting QitOS dependencies."""
        config = NodeConfig(
            id=schema.id,
            type=schema.type,
            title=schema.title,
            description=schema.description,
            position=schema.position,
            data=dict(schema.data),
        )

        # Inject QitOS-specific dependencies based on node type
        if schema.type == "tool" and self.tool_registry is not None:
            config.data["_tool_registry"] = self.tool_registry
        elif schema.type == "agent":
            if self.agent_registry is not None:
                config.data["_agent_registry"] = self.agent_registry
            if self.shared_memory is not None:
                config.data["_shared_memory"] = self.shared_memory
            if self.tracing_provider is not None:
                config.data["_tracing_provider"] = self.tracing_provider
            if self.llm is not None:
                config.data["_llm"] = self.llm
            if self.hooks:
                config.data["_hooks"] = list(self.hooks)

        node = create_node(config)
        return node

    def create_all(
        self, node_schemas: list[NodeSchema]
    ) -> Dict[str, WorkflowNode]:
        """Construct all nodes from a list of NodeSchema objects."""
        nodes = {}
        for schema in node_schemas:
            nodes[schema.id] = self.create(schema)
        return nodes
