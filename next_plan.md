# QitOS Next Plan: Path to World-Class Framework

This document outlines the critical gaps between the current state and a world-class open-source agent framework, with prioritized action items.

## Current Assessment

**Maturity Level:** Research prototype → Production beta (70% per plans.md)

**Core Strengths:**
- Clean `AgentModule + Engine` architecture with good separation of concerns
- Well-designed Task/Env abstraction with proper validation
- Multiple benchmark adapters (GAIA, Tau-Bench, CyBench)
- Reproducibility focus with trace system
- PyPI packaging ready

**Critical Gaps Preventing World-Class Status:**

---

## Phase 1: Production Readiness (P0 - Blockers for 1.0)

### 1.1 CI/CD and Quality Gates
**Status:** Missing automated testing and release gates

**Actions:**
```yaml
# .github/workflows/ci.yml (to create)
- Run full test suite on Python 3.9-3.12 matrix
- Enforce >80% code coverage with pytest-cov
- Run architecture tests (test_architecture_layout.py must pass)
- Benchmark smoke tests (tiny dataset, fixed seed)
- Lint checks (black, flake8, mypy)
- Secret scanning (detect API keys in commits)
```

**Verification:** CI passes on main branch for 7 consecutive days before release

### 1.2 Async Engine Support
**Status:** Engine is synchronous only

**Problem:** Real-world agents need concurrent tool execution, background operations, and streaming responses.

**Actions:**
- Add `AsyncEngine` class in `qitos/engine/async_engine.py`
- Support async `AgentModule.decide()` hook
- Concurrent tool execution for independent actions
- Streaming response support for real-time rendering

**API Target:**
```python
result = await AsyncEngine(agent=agent, env=env).run(task)
```

### 1.3 Model Provider Diversity
**Status:** Only OpenAI-compatible API in examples

**Actions:**
- First-class `AnthropicModel` adapter (Claude native)
- First-class `GeminiModel` adapter
- `OLLAMAModel` for local inference
- `VLLMModel` for self-hosted
- Unified response schema across providers (tool calls, reasoning, content)

**Location:** `qitos/models/anthropic.py`, `qitos/models/gemini.py`, etc.

### 1.4 Community Infrastructure
**Status:** Missing contributor experience

**Actions:**
- `CONTRIBUTING.md` with development setup, PR process, commit conventions
- `CHANGELOG.md` following Keep a Changelog format
- `.github/ISSUE_TEMPLATE/` (bug report, feature request, research question)
- `.github/PULL_REQUEST_TEMPLATE.md`
- `CODE_OF_CONDUCT.md`

---

## Phase 2: Competitive Differentiation (P1 - Release Critical)

### 2.1 Production-Grade Tool Ecosystem
**Status:** Basic toolset (editor, shell, web)

**Competition Comparison:**
- LangChain: 100+ tools
- Smolagents: Rich tool ecosystem
- QitOS: ~5 tools

**Priority Tool Additions:**
```
Browser:
  - BrowserUseTool (existing?), PlaywrightTool, ScreenshotTool

Code Execution:
  - DockerSandboxTool (isolated code execution)
  - JupyterTool (IPython notebook integration)

Data Processing:
  - CSVTool, SQLTool, DataFrameTool

Communication:
  - EmailTool, SlackTool, CalendarTool

AI-Native:
  - EmbeddingsTool (RAG support)
  - VectorSearchTool
  - ImageGenerationTool
```

**Architecture Decision:** Tools should leverage `Env` capabilities for isolation and reproducibility

### 2.2 Comprehensive Benchmark Runner
**Status:** Adapters exist but no unified runner

**Actions:**
- Implement `qitos bench run` CLI command
- Dataset-level execution with resume capability
- Standardized output format: success rate, latency, step count, cost proxy, failure taxonomy
- Built-in evaluators (exact match, LLM-as-judge, test-based)
- Comparison mode: `qitos bench compare run_a/ run_b/`

**Example:**
```bash
qitos bench run gaia --level validation --model gpt-4o --output runs/gaia_gpt4/
qitos bench report runs/gaia_gpt4/ --format markdown
```

### 2.3 Real Multi-Step Replays and Debugging
**Status:** Basic trace exists but limited debugging tools

**Actions:**
- `qita step <run_id> <step_num>` - Inspect single step with full context
- `qita diff <run_a> <run_b>` - Compare two trajectories
- `qita rerun <run_id> --from-step 5` - Resume from middle with same state
- Inspector breakpoints: `debugger.break_on_step(3)` or `debugger.break_on_tool("execute")`

### 2.4 Environment Implementations
**Status:** Only HostEnv exists

**Actions:**
- `DockerEnv` - Isolated containerized execution (security + reproducibility)
- `BrowserEnv` - Full browser automation with state persistence
- `RepoEnv` - Git-native environment for SWE tasks (branches, commits, diff tracking)
- `DocumentEnv` - PDF/EPUB with page-level navigation and annotations

---

## Phase 3: Research and Scale (P2 - Post-Release Roadmap)

### 3.1 Multi-Agent Orchestration
**Status:** Single agent only

**Design:** Parent/child task delegation pattern
- Parent agent creates sub-tasks via `Task.create_child()`
- Shared env instances for collaboration
- Agent-as-tool pattern for modularity

### 3.2 Distributed/Batch Execution
**Status:** Single-process only

**Actions:**
- `qitos bench distribute` with Ray/Dask integration
- Parallel benchmark execution with result aggregation
- Checkpointing for resumable long runs
- Cost tracking across distributed workers

### 3.3 Fine-Tuning and Distillation Pipeline
**Unique Differentiator:** Most frameworks ignore post-hoc improvement

**Actions:**
- `qitos train export --from-runs runs/ --format openai` - Export successful trajectories
- SFT dataset generation from traces
- Reward model training on preference pairs
- Distilled small model evaluation

### 3.4 Streaming Frontend Events
**Status:** Render hooks exist but schema not frozen

**Actions:**
- Freeze event schema v1.0
- WebSocket server for real-time agent visualization
- React/Vue component library for custom UIs
- Shareable trace URLs with embedded viewer

---

## Open Questions Requiring Research

1. **Memory Architecture:** Current memory is too simplistic for long-running agents
   - Consider: episodic vs semantic memory, vector DB integration, memory summarization

2. **Planning Beyond ToT:** Tree of Thoughts is basic
   - Consider: MCTS integration, learned value functions, reflexion variants

3. **Tool Learnability:** Hard-coded tools don't scale
   - Consider: tool creation from documentation, tool composition

4. **Evaluation Standard:** Each benchmark has different evaluators
   - Consider: unified `Evaluator` interface with registry

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep on env implementations | High | Medium | Keep core env minimal, push to kit |
| Benchmark non-determinism | Medium | High | Record seeds, prompts, model versions |
| Schema churn breaks users | Medium | High | Freeze v1.0 schema, maintain adapters |
| Competition from larger frameworks | High | Medium | Focus on reproducibility + research workflow differentiation |

---

## Success Metrics for World-Class Status

1. **Adoption:** 100+ GitHub stars, 10+ external contributors
2. **Benchmark Performance:** Top-3 results on at least one public benchmark (GAIA, etc.)
3. **Stability:** 30 days CI green, no breaking changes in patch releases
4. **Documentation:** Complete API coverage, 5+ end-to-end tutorials
5. **Ecosystem:** 3+ community-contributed tools or environments
