"""WorkflowRunner — high-level API for running QitOS workflows."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from qitos_dag.graph_engine import EngineConfig, GraphEngine, GraphRunResult
from qitos_dag.schema import WorkflowSchema

from .factory import QitosNodeFactory
from .layers import CheckpointLayer, ExecutionLimitsLayer, QitaTracingLayer


class WorkflowRunner:
    """High-level API for running QitOS workflows.

    Handles schema compilation, node construction with dependency
    injection, layer setup, and execution.
    """

    def __init__(
        self,
        tool_registry: Any = None,
        agent_registry: Any = None,
        tracing_provider: Any = None,
        shared_memory: Any = None,
        llm: Any = None,
        hooks: Optional[List[Any]] = None,
        engine_config: Optional[EngineConfig] = None,
    ) -> None:
        self.factory = QitosNodeFactory(
            tool_registry=tool_registry,
            agent_registry=agent_registry,
            tracing_provider=tracing_provider,
            shared_memory=shared_memory,
            llm=llm,
            hooks=hooks,
        )
        self.tracing_provider = tracing_provider
        self.shared_memory = shared_memory
        self.engine_config = engine_config or EngineConfig()

    async def run(
        self,
        schema: WorkflowSchema,
        inputs: Optional[Dict[str, Any]] = None,
        checkpoint_dir: Optional[str] = None,
    ) -> GraphRunResult:
        """Execute a workflow from a schema.

        Parameters
        ----------
        schema : WorkflowSchema
            The workflow definition.
        inputs : dict
            Input values for the Start node.
        checkpoint_dir : str
            Optional directory for checkpoint persistence.

        Returns
        -------
        GraphRunResult
        """
        # Build nodes with QitOS dependency injection
        node_overrides = self.factory.create_all(schema.nodes)

        # Set up layers
        layers: List = []
        if self.tracing_provider:
            layers.append(QitaTracingLayer(
                tracing_provider=self.tracing_provider,
                graph_id=schema.title,
            ))
        layers.append(ExecutionLimitsLayer(
            max_steps=self.engine_config.max_execution_steps,
            max_time_ms=self.engine_config.max_execution_time_ms,
        ))
        if checkpoint_dir:
            layers.append(CheckpointLayer(checkpoint_dir=checkpoint_dir))

        # Create and run engine
        engine = GraphEngine(
            schema=schema,
            config=self.engine_config,
            layers=layers,
            node_overrides=node_overrides,
        )
        engine.compile()

        result = await engine.run(inputs=inputs)

        # Sync VariablePool state to SharedMemory after execution
        if self.shared_memory is not None:
            from .adapter import SharedMemoryAdapter
            # Use the engine's pool if available, else skip
            pool = getattr(engine, 'variable_pool', None)
            if pool is not None:
                adapter = SharedMemoryAdapter(pool, self.shared_memory)
                adapter.sync_to_shared_memory()

        return result

    async def run_from_json(
        self,
        json_str: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> GraphRunResult:
        """Execute a workflow from a JSON schema string."""
        schema = WorkflowSchema.from_json(json_str)
        return await self.run(schema, inputs)

    async def run_from_file(
        self,
        path: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> GraphRunResult:
        """Execute a workflow from a JSON schema file."""
        with open(path) as f:
            json_str = f.read()
        return await self.run_from_json(json_str, inputs)

    def run_sync(
        self,
        schema: WorkflowSchema,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> GraphRunResult:
        """Synchronous wrapper for use from Engine tools (WorkflowTool)."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already inside an event loop — run in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run, self.run(schema, inputs)
                )
                return future.result(timeout=300)
        else:
            return asyncio.run(self.run(schema, inputs))
