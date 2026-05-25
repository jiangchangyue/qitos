"""Workflow pattern — declarative graph-based orchestration (simplified).

Provides a lightweight DAG-based workflow where nodes are functions
or AgentModules and edges define execution order with data flow.

Usage::

    from qitos.kit.patterns import Workflow, WorkflowConfig

    wf = Workflow()
    wf.add_node("search", search_func)
    wf.add_node("analyze", analyze_func)
    wf.add_node("report", report_func)
    wf.add_edge("search", "analyze")
    wf.add_edge("analyze", "report")

    result = wf.run("investigate this topic")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from ...core.state import StateSchema


@dataclass
class WorkflowConfig:
    """Configuration for the workflow pattern."""

    max_node_retries: int = 1
    strict_order: bool = True  # If False, allows partial execution on failure


@dataclass
class _WorkflowNode:
    """A node in the workflow graph."""

    name: str
    func: Callable[..., Any]
    description: str = ""


@dataclass
class _WorkflowEdge:
    """A directed edge between two nodes."""

    source: str
    target: str


@dataclass
class WorkflowState(StateSchema):
    """State for the workflow execution."""

    current_node: str = ""
    completed_nodes: List[str] = field(default_factory=list)
    node_results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)


class Workflow:
    """Declarative graph-based workflow orchestrator.

    Build a DAG of nodes (functions or AgentModules) connected by edges,
    then execute them in topological order with data flowing between nodes.
    """

    def __init__(self, config: Optional[WorkflowConfig] = None) -> None:
        self._config = config or WorkflowConfig()
        self._nodes: Dict[str, _WorkflowNode] = {}
        self._edges: List[_WorkflowEdge] = []
        self._entry_node: Optional[str] = None

    def add_node(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
    ) -> "Workflow":
        """Add a node to the workflow.

        Parameters
        ----------
        name : str
            Unique node name.
        func : callable
            The function to execute. Receives the task and
            a ``context`` dict with results from upstream nodes.
        description : str
            Optional description.

        Returns
        -------
        Workflow
            Self, for chaining.
        """
        self._nodes[name] = _WorkflowNode(
            name=name,
            func=func,
            description=description or getattr(func, "__doc__", "") or "",
        )
        if self._entry_node is None:
            self._entry_node = name
        return self

    def add_edge(self, source: str, target: str) -> "Workflow":
        """Add a directed edge from source to target.

        The target node receives the source node's result as input.

        Returns
        -------
        Workflow
            Self, for chaining.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found")
        self._edges.append(_WorkflowEdge(source=source, target=target))
        return self

    def set_entry(self, name: str) -> "Workflow":
        """Set the entry node for the workflow."""
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        self._entry_node = name
        return self

    def _topological_order(self) -> List[str]:
        """Compute execution order using Kahn's algorithm."""
        in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
        adjacency: Dict[str, List[str]] = {n: [] for n in self._nodes}

        for edge in self._edges:
            adjacency[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._nodes):
            raise ValueError("Workflow contains a cycle")

        return order

    def _get_upstream_results(self, node_name: str) -> Dict[str, Any]:
        """Get results from all nodes that are direct upstream of this node."""
        upstream = {}
        for edge in self._edges:
            if edge.target == node_name:
                upstream[edge.source] = self._node_results.get(edge.source)
        return upstream

    def run(self, task: str, **kwargs: Any) -> WorkflowState:
        """Execute the workflow.

        Parameters
        ----------
        task : str
            The task/input for the workflow.

        Returns
        -------
        WorkflowState
            The final workflow state with results from all nodes.
        """
        state = WorkflowState(task=task, max_steps=len(self._nodes) + 1)
        self._node_results: Dict[str, Any] = {}

        order = self._topological_order()

        for node_name in order:
            node = self._nodes[node_name]
            state.current_node = node_name

            # Build context with upstream results
            context = self._get_upstream_results(node_name)

            try:
                result = node.func(task, context=context, **kwargs)
                state.node_results[node_name] = result
                state.completed_nodes.append(node_name)
                self._node_results[node_name] = result
            except Exception as exc:
                state.errors[node_name] = str(exc)
                if self._config.strict_order:
                    state.set_stop("unrecoverable_error", f"Node '{node_name}' failed: {exc}")
                    break

        if not state.errors:
            state.current_node = ""
            state.set_stop("final", "workflow_completed")

        return state

    @property
    def nodes(self) -> List[str]:
        return list(self._nodes.keys())

    @property
    def edges(self) -> List[tuple[str, str]]:
        return [(e.source, e.target) for e in self._edges]


def build_workflow_system(
    config: Optional[WorkflowConfig] = None,
) -> Workflow:
    """Build a Workflow orchestrator.

    Returns:
        A Workflow instance ready for node/edge configuration.
    """
    return Workflow(config=config)


__all__ = ["Workflow", "WorkflowConfig", "build_workflow_system"]
