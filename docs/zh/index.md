# QitOS（气）

<div class="qitos-hero">

QitOS 是一个面向研究与工程落地的 **LLM Agent 框架**。

- 清晰内核：`AgentModule + Engine`
- canonical 主线：`prepare -> decide -> act -> reduce -> check_stop`
- 内建可观测：`qita` board、replay、export 与 traces

<div class="qitos-actions">
  <a class="qitos-btn qitos-btn-glow" href="start-here.md">Start Here</a>
  <a class="qitos-btn" href="getting-started/build_agent_in_10_minutes.md">10 分钟搭一个 Agent</a>
  <a class="qitos-btn" href="tutorials/examples/index.md">查看示例</a>
</div>

</div>

## 选择你的路径

<div class="qitos-grid">
  <div class="qitos-card">
    <h3>我想先跑通一个 demo</h3>
    <p>安装 QitOS，运行最小 agent，再用 qita 查看运行结果。</p>
    <p><a href="getting-started/index.md">打开快速上手</a></p>
  </div>
  <div class="qitos-card">
    <h3>我想自己写 agent</h3>
    <p>沿着从 state 到 <code>agent.run(...)</code> 的 canonical 主线开始。</p>
    <p><a href="getting-started/build_agent_in_10_minutes.md">打开 10 分钟教程</a></p>
  </div>
  <div class="qitos-card">
    <h3>我想理解内核</h3>
    <p>理解 decision、tool、state、trace 背后的运行时契约。</p>
    <p><a href="research/kernel.md">打开内核文档</a></p>
  </div>
  <div class="qitos-card">
    <h3>我想跑 benchmark</h3>
    <p>在与真实 agent 相同的内核上运行 GAIA 与 Tau-Bench。</p>
    <p><a href="builder/benchmark_gaia.md">打开 benchmark 指南</a></p>
  </div>
</div>

## 2 分钟跑通

在仓库根目录执行：

```bash
pip install qitos
export OPENAI_API_KEY="<your_key>"
python examples/quickstart/minimal_agent.py
qita board --logdir runs
```

<div class="qitos-actions">
  <a class="qitos-btn qitos-btn-glow" href="getting-started/first_run.md">第一次运行</a>
  <a class="qitos-btn" href="builder/configuration.md">配置模型</a>
  <a class="qitos-btn" href="builder/qita.md">用 qita 复盘</a>
</div>

## 产品界面截图

### QitOS CLI

![QitOS CLI](../assets/qitos_cli_snapshot.png)

### qita board

![qita board](../assets/qita_board_snapshot.png)

### qita 轨迹视图

![qita trajectory view](../assets/qita_traj_snapshot.png)

## 接下来读什么

- 想快速定向： [Start Here](start-here.md)
- 想看典型场景： [Use Cases](use-cases.md)
- 想理解框架保证： [Contracts & Guarantees](reference/contracts.md)
- 想看 walkthrough： [Example Walkthroughs](tutorials/examples/index.md)

## Source Index

- [examples/quickstart/minimal_agent.py](https://github.com/Qitor/qitos/blob/main/examples/quickstart/minimal_agent.py)
- [examples/patterns/react.py](https://github.com/Qitor/qitos/blob/main/examples/patterns/react.py)
- [qitos/core/agent_module.py](https://github.com/Qitor/qitos/blob/main/qitos/core/agent_module.py)
- [qitos/engine/engine.py](https://github.com/Qitor/qitos/blob/main/qitos/engine/engine.py)
- [qitos/qita/cli.py](https://github.com/Qitor/qitos/blob/main/qitos/qita/cli.py)
