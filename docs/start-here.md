# Start Here

## First Time Using QitOS?

Pick the path that matches what you need right now.

## I want to run a demo

1. [Install QitOS](getting-started/installation.md)
2. [Run the minimal agent](getting-started/first_run.md)
3. [Inspect the run with qita](builder/qita.md)

## I want to build an agent

1. [Understand the blessed path](getting-started/build_agent_in_10_minutes.md)
2. [Browse canonical examples](tutorials/examples/index.md)
3. [Read example walkthroughs](tutorials/examples/index.md)

## I want to understand the kernel

1. [Kernel Architecture](research/kernel.md)
2. [Engine Loop Deep Dive](research/kernel_deep_dive.md)
3. [Contracts & Guarantees](reference/contracts.md)

## I want to run benchmarks

1. [GAIA Benchmark Guide](builder/benchmark_gaia.md)
2. [Tau-Bench Guide](builder/benchmark_tau.md)
3. [Use Cases](use-cases.md)

## Fastest Happy Path

From the repository root:

```bash
pip install qitos
export OPENAI_API_KEY="<your_key>"
python examples/quickstart/minimal_agent.py
qita board --logdir runs
```
