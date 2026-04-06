# Start Here

## 第一次使用 QitOS？

先按你的当前目标选一条路径。

## 我想先跑通一个 demo

1. [安装 QitOS](getting-started/installation.md)
2. [运行最小 agent](getting-started/first_run.md)
3. [用 qita 查看运行](builder/qita.md)

## 我想开始写 agent

1. [理解推荐主线](getting-started/build_agent_in_10_minutes.md)
2. [查看 canonical examples](tutorials/examples/index.md)
3. [阅读 walkthroughs](tutorials/examples/index.md)

## 我想理解内核

1. [内核架构](research/kernel.md)
2. [Engine 循环深度拆解](research/kernel_deep_dive.md)
3. [Contracts & Guarantees](reference/contracts.md)

## 我想跑 benchmark

1. [GAIA Benchmark 指南](builder/benchmark_gaia.md)
2. [Tau-Bench 指南](builder/benchmark_tau.md)
3. [Use Cases](use-cases.md)

## 最短 happy path

在仓库根目录执行：

```bash
pip install qitos
export OPENAI_API_KEY="<your_key>"
python examples/quickstart/minimal_agent.py
qita board --logdir runs
```
