"""CyberGym benchmark runner."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qitos.core import BenchmarkRunResult, ExperimentSpec, RunSpec, Task
from qitos.engine.stop_criteria import FinalResultCriteria, MaxStepsCriteria
from qitos.engine.states import ContextConfig
from qitos.kit.env.host_env import HostEnv
from qitos.trace import TraceWriter

from .adapter import task_slug
from .evaluator import CyberGymEvaluator
from .runtime import CyberGymRuntimeHook, prepare_task_dir
from .scorer import CyberGymScorer


def make_trace_writer(
    *,
    trace_logdir: str | Path,
    trace_prefix: str,
    task_id: str,
    model_id: str,
) -> TraceWriter:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_id = f"{trace_prefix}_{task_slug(task_id)}_{stamp}"
    return TraceWriter(
        output_dir=str(Path(trace_logdir).expanduser().resolve()),
        run_id=run_id,
        strict_validate=True,
        metadata={"model_id": model_id},
    )


def run_cybergym_agent_task(
    *,
    task_dir: str | Path,
    model_name: str,
    api_key: str,
    base_url: str,
    server: str,
    max_steps: int,
    trace_logdir: str | Path,
    trace_prefix: str = "qitos_cybergym",
    run_spec: RunSpec | None = None,
    experiment_spec: ExperimentSpec | None = None,
) -> dict[str, Any]:
    try:
        from .agent.adapter import CyberGymAdapter
        from .agent.cli import build_agent
        from .agent.stop_criteria import PoCVerificationCriteria
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "CyberGym agent package is not bundled in QitOS. "
            "Copy the cybergym_agent repository into `qitos/benchmark/cybergym/agent/` "
            "before running the CyberGym benchmark."
        ) from exc

    task_path = Path(task_dir).expanduser().resolve()
    adapter = CyberGymAdapter(server_url=server)
    task = adapter.from_task_dir(str(task_path), max_steps=max_steps)

    agent = build_agent(
        model=model_name,
        workspace_root=str(task_path),
        server_url=server,
        max_steps=max_steps,
        llm_config={"api_key": api_key, "base_url": base_url},
    )

    env = HostEnv(workspace_root=str(task_path))
    stop_criteria = [
        PoCVerificationCriteria(),
        FinalResultCriteria(),
        MaxStepsCriteria(max_steps=max_steps),
    ]
    context_config = ContextConfig(
        tool_result_max_chars=4000,
        conversation_max_rounds=10,
        loop_max_repeats=3,
    )
    trace_writer = make_trace_writer(
        trace_logdir=trace_logdir,
        trace_prefix=trace_prefix,
        task_id=task.id,
        model_id=model_name,
    )

    result = agent.run(
        task=task,
        return_state=True,
        env=env,
        stop_criteria=stop_criteria,
        max_steps=max_steps,
        workspace=str(task_path),
        context_config=context_config,
        trace=trace_writer,
        run_spec=run_spec,
        experiment_spec=experiment_spec,
        description=task.inputs.get("description", ""),
        task_id=task.inputs.get("task_id", ""),
        agent_id=task.inputs.get("agent_id", ""),
        checksum=task.inputs.get("checksum", ""),
        server_url=task.inputs.get("server_url", server),
        error_txt=task.inputs.get("error_txt", ""),
        patch_diff=task.inputs.get("patch_diff", ""),
        repo_dir=task.inputs.get("repo_dir", ""),
    )

    return {
        "task_id": task.id,
        "task_dir": str(task_path),
        "trace_run_dir": str(trace_writer.run_dir),
        "stop_reason": result.state.stop_reason,
        "final_result": result.state.final_result,
        "step_count": result.step_count,
        "task_result": result.task_result.to_dict() if result.task_result is not None else None,
    }


def run_cybergym_task(
    *, task: Task, run_spec: RunSpec, experiment_spec: ExperimentSpec
) -> BenchmarkRunResult:
    started = time.time()
    effective_spec = RunSpec.from_value(run_spec)
    effective_spec.benchmark_name = effective_spec.benchmark_name or "cybergym"
    effective_spec.benchmark_split = effective_spec.benchmark_split or str(
        task.inputs.get("difficulty") or "level1"
    )
    effective_spec.toolset_name = effective_spec.toolset_name or "cybergym_agent"
    effective_spec.metadata = {
        **dict(effective_spec.metadata or {}),
        "recipe": "cybergym_agent",
    }

    environment = dict(effective_spec.environment or {})
    task_id = str(task.inputs.get("task_id") or task.id)
    difficulty = str(task.inputs.get("difficulty") or effective_spec.benchmark_split or "level1")
    workspace = Path(str(environment.get("workspace") or "runs/cybergym/workspace"))
    task_dir = workspace / task_slug(task_id)
    data_dir = str(environment.get("data_dir") or "")
    server = str(environment.get("server") or "")
    base_url = str(environment.get("base_url") or "")
    trace_logdir = str(environment.get("trace_logdir") or "runs/cybergym/traces")
    api_key = str(
        environment.get("api_key")
        or os.getenv("OPENAI_API_KEY", "")
        or os.getenv("QITOS_API_KEY", "")
        or os.getenv("CYBERGYM_CLAUDE_AUTH_TOKEN", "")
    )
    max_steps = int((effective_spec.metadata or {}).get("max_steps", task.budget.max_steps or 30))

    if not data_dir:
        raise ValueError("CyberGym run requires run_spec.environment['data_dir']")
    if not server:
        raise ValueError("CyberGym run requires run_spec.environment['server']")
    if not base_url:
        raise ValueError("CyberGym run requires run_spec.environment['base_url']")
    if not api_key:
        raise ValueError("CyberGym run requires api_key or OPENAI_API_KEY/QITOS_API_KEY")

    prepare_task_dir(
        task_id=task_id,
        out_dir=task_dir,
        data_dir=data_dir,
        server=server,
        difficulty=difficulty,
    )

    prepared = CyberGymRuntimeHook().prepare(
        task=task,
        run_spec=effective_spec,
        experiment_spec=experiment_spec,
    )
    execution = run_cybergym_agent_task(
        task_dir=task_dir,
        model_name=str(effective_spec.model_name or ""),
        api_key=api_key,
        base_url=base_url,
        server=server,
        max_steps=max_steps,
        trace_logdir=trace_logdir,
        trace_prefix=str(environment.get("trace_prefix") or "qitos_cybergym"),
        run_spec=effective_spec,
        experiment_spec=experiment_spec,
    )
    task_result = execution.get("task_result") or {}
    base_result = BenchmarkRunResult(
        task_id=task_id,
        benchmark="cybergym",
        split=difficulty,
        prediction=execution.get("final_result"),
        success=bool(task_result.get("success", False)),
        stop_reason=str(execution.get("stop_reason") or "unknown"),
        steps=int(execution.get("step_count") or 0),
        latency_seconds=float(time.time() - started),
        token_usage=int((task_result.get("metrics") or {}).get("token_usage", 0)),
        cost=0.0,
        trace_run_dir=str(execution.get("trace_run_dir") or ""),
        run_spec_ref=effective_spec.fingerprint(),
        metadata={"execution": execution},
    )
    evaluation = CyberGymEvaluator().evaluate(
        prepared=prepared,
        run_spec=effective_spec,
        experiment_spec=experiment_spec,
        execution=execution,
    )
    return CyberGymScorer().score(
        prepared=prepared,
        run_spec=effective_spec,
        experiment_spec=experiment_spec,
        execution=execution,
        evaluation=evaluation,
        base_result=base_result,
    )
