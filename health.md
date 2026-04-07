# QitOS 项目健康审计

审计时间：2026-04-07

## 审计范围

本轮审计基于仓库当前工作区完成，遵循“不修改任何现有代码”的要求，仅阅读代码、配置、文档、测试与 CI 配置，并执行了以下验证：

- `pytest -q`
- `python -m compileall qitos tests`
- `flake8 qitos tests`
- `flake8 qitos tests --ignore=E501,W293,W391`
- `mypy qitos --hide-error-context --no-error-summary`

说明：

- 当前工作区本身存在较多未提交改动，本报告尽量只评价“仓库当前整体状态”，不把这些本地变更简单视为缺陷。
- 下面的“问题”更偏向维护者视角的架构健康、工程治理和长期演进风险，而不是单纯“能不能跑”。

## 总结判断

一句话结论：

**这是一个方向正确、核心抽象已经成形、测试完成度明显高于静态工程治理完成度的项目。**

如果用维护者视角打分，我会给出下面的判断：

| 维度 | 评价 |
| --- | --- |
| 架构方向 | 好，且有清晰的内核意识 |
| 运行正确性 | 较好，当前测试面证明核心可用 |
| 项目结构 | 中上，分层清楚，但边界开始膨胀 |
| 测试健康度 | 好 |
| 静态健康度 | 一般偏弱 |
| 发布/CI 治理 | 偏弱 |
| 长期可维护性 | 中等，需要尽快做一次治理收口 |

更具体地说：

- `core + engine + trace + render + qita` 这条主链路已经有“框架骨架”的样子。
- `kit/tool` 和部分 benchmark/skill 子系统开始承担过多职责，是当前维护成本的主要来源。
- 项目已经具备“研究型开源框架”的可见度，但还没完全达到“稳定维护型开源项目”的工程守门线。

## 事实快照

- `qitos` 下约 `204` 个 Python 文件，约 `49,136` 行 Python 代码。
- `tests` 下约 `27` 个 Python 文件，约 `3,145` 行测试代码。
- `docs` 下约 `504` 个 Markdown 文件，文档体量很充足。
- 代码量集中区：
  - `qitos/benchmark`: `22,821` LOC
  - `qitos/kit`: `15,661` LOC
  - `qitos/engine`: `3,287` LOC
  - `qitos/qita`: `1,475` LOC

验证结果：

- `pytest -q`：`109 passed`
- `compileall`：通过
- `flake8 qitos tests`：`4783` 条，其中 `4406` 条是 `E501` 行长问题
- `flake8 --ignore=E501,W293,W391`：仍有 `130` 条有效问题
- `mypy qitos ...`：`180` 个类型错误

问题分布最集中的区域：

- `flake8` 有效问题最多：`qitos/kit/tool`（`51` 条）
- `mypy` 错误最多：`qitos/kit/tool`（`78` 条）
- 当前 `.github/workflows/` 只有：
  - `docs.yml`
  - `pypi.yml`

这意味着：

- 运行健康度明显好于静态健康度
- 文档和发布有流程，但缺少“日常开发守门 CI”

## 项目结构审计

### 结构上的优点

1. 顶层分层是清晰的

- `qitos/core`：协议与核心抽象
- `qitos/engine`：统一执行内核
- `qitos/models`：模型适配层
- `qitos/trace` / `qitos/render` / `qitos/qita`：可观测性与展示层
- `qitos/kit`：高阶能力、工具、记忆、规划、技能、环境

这说明项目不是“功能堆砌”起家的，而是有意识地围绕 `AgentModule + Engine` 去组织。

2. 核心 API 面向内核，而不是面向杂项能力

- `qitos/__init__.py`
- `qitos/engine/__init__.py`

对外导出的确以 `Engine / AgentModule / StateSchema / Decision / Action` 为中心，这个方向是对的。

3. 有结构冻结意识

测试里已经存在：

- `tests/test_architecture_layout.py`
- `tests/test_p0_freeze_guards.py`

这类测试说明你已经在主动保护“公开表面”和“包布局”，这是很多开源项目早期最容易忽略、后期最难补的能力。

4. 文档和示例建设明显超前

- README 和中文 README 都比较完整
- docs 体量很大
- examples / templates / benchmarks 比较齐全

这对开源 adoption 很关键。

### 结构上的隐患

1. `qitos/kit` 已经成为事实上的“大杂烩层”

`kit` 当前包含：

- critic
- env
- evaluate
- history
- memory
- metric
- parser
- planning
- prompts
- skill
- state
- tool

这本身不一定错，但现在的问题是：**`kit` 已经不再只是“辅助能力层”，而是在承担大量产品化、实验性、兼容层、扩展层职责。**

建议把 `kit` 重新定义为“受支持扩展层”，并进一步划清：

- 稳定扩展
- 实验扩展
- 安全研究/高风险扩展
- 兼容适配扩展

2. `qitos/kit/tool` 边界过宽

当前这里既有：

- coding/editor/file/notebook/taskboard 这类通用开发工具
- web/network/report 这类集成型工具
- recon/exploit/password/vuln_scan 这类高风险安全研究工具
- advanced 这类兼容导出层

这会带来三个问题：

- 所有权不清晰
- 包的“默认认知”被安全研究能力拉偏
- 静态治理和文档治理难度陡增

3. benchmark 数据以 Python 源码形式占用大量主体代码体积

例如：

- `qitos/benchmark/tau_bench/port/envs/retail/tasks_train.py`
- `qitos/benchmark/tau_bench/port/envs/retail/tasks.py`
- `qitos/benchmark/tau_bench/port/envs/airline/tasks.py`

这些文件极大抬高了仓库 LOC、lint 噪音和阅读成本，但并不等于“框架复杂度”。
建议后续迁移成数据文件、构建产物，或拆为可选 benchmark 包。

4. `qita` 和 render 层出现单文件膨胀

代表性文件：

- `qitos/qita/cli.py`：`1467` 行
- `qitos/render/hooks.py`：`609` 行
- `qitos/render/cli_render.py`：`497` 行

这说明“观测产品层”已从小工具成长为独立子系统，但代码组织还停留在早期阶段。

## 代码健康度审计

### 1. 运行健康度：好

这是这次审计里最积极的一点。

- 全量测试通过：`109 passed`
- `compileall` 通过
- 核心引擎、hook、tool registry、history、context、qita CLI、examples layout 都有覆盖

这说明当前仓库不是“看起来完整、实际上脆弱”的状态，而是**核心行为已经被一定程度固定住了**。

### 2. 静态健康度：明显落后

这是当前最需要尽快补上的短板。

#### flake8

默认 flake8 的 `4783` 条问题里，大部分是行长；如果忽略行长和空白问题，仍然还有 `130` 条有效问题，主要包括：

- 未使用 import
- 未定义名字
- 无占位的 f-string
- 局部变量未使用
- 裸 `except`
- 一些格式与布局问题

这里面不是简单的“代码风格之争”，已经出现了真实缺陷信号。

#### mypy

`mypy` 报 `180` 个错误，且集中在框架关键区：

- `qitos/kit/tool`
- `qitos/engine/_control_runtime.py`
- `qitos/engine/engine.py`
- `qitos/trace/writer.py`
- `qitos/render/cli_render.py`

这说明项目的**类型设计还没有跟上架构演进**。
对一个智能体框架来说，这会直接影响：

- 重构速度
- API 演化安全性
- 新贡献者理解成本
- 兼容层稳定性

### 3. 发现的代表性问题

下面这些不是“风格建议”，而是我认为值得优先处理的真实健康问题。

#### P1：工具抽象层发生了接口漂移

根因：

- `BaseTool.run(self, **kwargs)` 是极宽泛接口
- 具体工具子类普遍使用强签名 `run(...)`
- `FunctionTool` / `BaseTool` / `ActionExecutor` / `runtime_context` 注入逻辑形成了动态约定

直接表现：

- 大量 `mypy override` 错误
- 工具调用语义更多依赖运行时约定，而不是类型系统表达

典型影响文件：

- `qitos/core/tool.py`
- `qitos/engine/action_executor.py`
- `qitos/kit/tool/file.py`
- `qitos/kit/tool/notebook.py`
- `qitos/kit/tool/web.py`
- `qitos/kit/tool/text_web_browser.py`
- `qitos/kit/tool/taskboard.py`

我的判断：

这不是单点 bug，而是**当前框架最大的抽象债**。

#### P1：存在至少一处明显的潜在运行时缺陷

文件：

- `qitos/kit/tool/exploit_toolset.py:264`

问题：

- 代码里引用了未定义变量 `target`

这意味着即使测试目前不覆盖这条路径，运行到 bind payload 分支时很可能直接失败。

#### P1：skill 子系统有未闭环信号

文件：

- `qitos/kit/skill/injector.py:134`
- `qitos/kit/skill/injector.py:158`

问题：

- `SkillRegistry` 只作为字符串注解出现，但静态分析认为名字未定义

这类问题本身不大，但它暴露出一个更重要的事实：
**skill 子系统目前像是“已经进入公共表面”，但内部契约和类型边界还没有完全收口。**

#### P1：异常吞掉过多，削弱可观测性

仓库中有大量：

- `except Exception: pass`
- 宽泛兜底后静默降级

集中区域包括：

- `qitos/engine/engine.py`
- `qitos/engine/_env_runtime.py`
- `qitos/engine/_trace_runtime.py`
- `qitos/render/*`
- `qitos/kit/tool/coding.py`

我理解这些写法很多是出于“框架尽量不崩”的善意，但副作用是：

- 故障被吞掉
- 调试路径变长
- 线上回归更难定位
- 用户误以为功能正常，只是“结果奇怪”

#### P2：渲染/观测层已经长成子系统，但还没被当子系统治理

表现：

- `qita` CLI 是大单文件
- HTML 模板、HTTP handler、数据装载、视图逻辑混在一起
- render hooks 与 content renderer 的职责重叠度开始变高

短期内这还能维护，长期会拖累：

- UI 迭代
- 回放功能扩展
- trace schema 兼容
- 测试颗粒度

#### P2：安全研究工具与核心框架强耦合

例如：

- `qitos/kit/tool/exploit_toolset.py`
- `qitos/kit/tool/password_toolset.py`
- `qitos/kit/tool/recon_toolset.py`
- `qitos/kit/tool/vuln_scan_toolset.py`

从“能不能做”角度看，这些能力不一定有问题；
但从开源框架维护角度看，它们会放大：

- 包的认知复杂度
- 审查复杂度
- 合规/平台信任成本
- 依赖扩散和测试面

更合适的形态通常是：

- 独立可选插件
- 单独 extra
- 独立仓库或单独 namespace

#### P2：工程治理缺失日常守门 CI

当前 CI 只有：

- 文档构建
- PyPI 发布

缺少：

- PR / push 自动测试
- lint
- 类型检查
- 最低打包校验矩阵

这意味着项目现在更多依赖维护者自觉，而不是流程守门。

## 我认为你现在最值得保留的东西

这些是项目最有价值、最不该在治理过程中被误伤的部分：

1. `AgentModule + Engine` 这个核心叙事

这是项目最清晰、最能被外界记住的部分，不要被外围能力冲淡。

2. core-first 的公开 API 表面

现在的导出策略是正确的，建议继续保持“核心稳定、外围渐进”。

3. 测试里对结构和公开表面的保护意识

很多框架到后期才意识到要补这种测试，你这里已经提前做了。

4. qita / trace / replay 的可观测性方向

这条线很有辨识度，也很容易形成项目差异化。

## 优先级建议

### 第一阶段：一周内完成的治理动作

1. 建立真正的开发守门 CI

- 新增 `test` workflow
- 至少跑 `pytest -q`
- 增加一个“宽松模式”的 lint / mypy 工作流
- 先允许 baseline，后续再逐步收紧

2. 修掉确定性的真实缺陷

- 未定义名字
- 明显无效变量
- 裸 `except`
- 明显错误的 f-string

3. 给静态检查设边界

建议先只强约束：

- `qitos/core`
- `qitos/engine`
- `qitos/models`
- `qitos/trace`

不要一上来要求整个 `kit` 和 benchmark 全绿，否则治理成本会过高。

### 第二阶段：两到四周内完成的结构治理

1. 重构工具抽象

目标：

- 明确 `BaseTool` 的契约
- 明确 `runtime_context` 注入方式
- 减少动态鸭子类型
- 让 `ActionExecutor` 的约定能被类型系统表达

2. 拆分大文件

优先顺序建议：

- `qitos/qita/cli.py`
- `qitos/kit/tool/coding.py`
- `qitos/render/hooks.py`

3. 收口 `kit/tool`

按领域重新分包，例如：

- `kit/tool/coding`
- `kit/tool/productivity`
- `kit/tool/web`
- `kit/tool/security_research`
- `kit/tool/compat`

### 第三阶段：版本化治理

1. 给模块打稳定性标签

例如：

- stable
- provisional
- experimental
- deprecated

2. 迁移 benchmark 大数据文件

把任务语料从 `.py` 迁走，降低：

- 包体积
- lint 噪音
- 审阅压力

3. 现代化打包配置

当前 `pyproject.toml` 只有 build-system，项目实际配置主要还在 `setup.py`。
建议逐步迁移到 `pyproject.toml` 的标准声明式配置，并统一：

- 依赖
- extras
- 工具配置
- lint/type/format 配置

## 最后结论

从开源维护者视角看，QitOS 现在最像一个：

**已经跨过“想法验证期”，正在进入“平台治理期”的项目。**

这不是坏消息，恰恰相反，这说明你的项目已经不再是“先活下来再说”的状态，而是开始出现典型的成功项目问题：

- 核心很好，外围扩张太快
- 功能很多，边界开始变松
- 测试已经跟上，静态与流程治理还没完全跟上

我的最终判断是：

- **短期可用性：好**
- **中期维护风险：中**
- **长期演进潜力：高**

如果你只做一件事，我最推荐的是：

**先用 CI + 类型边界，把 `core/engine/tool abstraction` 这三层钉牢。**

一旦这三层稳定下来，QitOS 后面的 examples、skills、qita、benchmarks 才会真正成为资产，而不是持续扩大的维护负担。
