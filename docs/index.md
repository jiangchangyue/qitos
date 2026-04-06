# QitOS

<div class="qitos-hero">

QitOS is a research-first **agent framework** for modular, reproducible LLM agent workflows.

- Clean kernel: `AgentModule + Engine`
- Canonical loop: `prepare -> decide -> act -> reduce -> check_stop`
- Built-in observability: `qita` board, replay, export, and traces

<div class="qitos-actions">
  <a class="qitos-btn qitos-btn-glow" href="start-here.md">Start Here</a>
  <a class="qitos-btn" href="getting-started/build_agent_in_10_minutes.md">Build an Agent in 10 Minutes</a>
  <a class="qitos-btn" href="tutorials/examples/index.md">Open Examples</a>
</div>

</div>

## Choose Your Path

<div class="qitos-grid">
  <div class="qitos-card">
    <h3>I want to run a demo</h3>
    <p>Install QitOS, run the minimal agent, and inspect the run with qita.</p>
    <p><a href="getting-started/index.md">Go to Getting Started</a></p>
  </div>
  <div class="qitos-card">
    <h3>I want to build an agent</h3>
    <p>Follow the canonical authoring path from state to <code>agent.run(...)</code>.</p>
    <p><a href="getting-started/build_agent_in_10_minutes.md">Open 10-Minute Tutorial</a></p>
  </div>
  <div class="qitos-card">
    <h3>I want to study the kernel</h3>
    <p>Understand the runtime contracts behind decisions, tools, state, and traces.</p>
    <p><a href="research/kernel.md">Open Kernel Docs</a></p>
  </div>
  <div class="qitos-card">
    <h3>I want benchmarks</h3>
    <p>Run GAIA and Tau-Bench on the same kernel used by practical agents.</p>
    <p><a href="builder/benchmark_gaia.md">Open Benchmark Guides</a></p>
  </div>
</div>

## Run In 2 Minutes

From the repository root:

```bash
pip install qitos
export OPENAI_API_KEY="<your_key>"
python examples/quickstart/minimal_agent.py
qita board --logdir runs
```

<div class="qitos-actions">
  <a class="qitos-btn qitos-btn-glow" href="getting-started/first_run.md">First Run Guide</a>
  <a class="qitos-btn" href="builder/configuration.md">Configure Model</a>
  <a class="qitos-btn" href="builder/qita.md">Inspect with qita</a>
</div>

## Product Snapshot

### QitOS CLI

![QitOS CLI](assets/qitos_cli_snapshot.png)

### qita board

![qita board](assets/qita_board_snapshot.png)

### qita trajectory view

![qita trajectory view](assets/qita_traj_snapshot.png)

## What To Read Next

- Need a fast orientation: [Start Here](start-here.md)
- Need concrete scenarios: [Use Cases](use-cases.md)
- Need framework guarantees: [Contracts & Guarantees](reference/contracts.md)
- Need examples: [Example Walkthroughs](tutorials/examples/index.md)

## Source Index

- [examples/quickstart/minimal_agent.py](https://github.com/Qitor/qitos/blob/main/examples/quickstart/minimal_agent.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [qitos/engine/engine.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/engine.py)
- [qitos/qita/cli.py](https://github.com/Qitor/qitos/blob/main/qitos/qita/cli.py)
