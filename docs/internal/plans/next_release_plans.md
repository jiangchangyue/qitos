# Qitos Month-by-Month Product Plan: v0.3 → v1.0

> Timeline: 2026-04 to 2027-03  
> Goal: move Qitos from a promising research-first agent framework to a clear v1.0 “research OS” for AI agents.

---

## 1. Plan Overview

### Version sequence

- **v0.3** — Reproducible Runs Foundation
- **v0.4** — Optimized Harness / Gold Presets
- **v0.5** — Multimodal Core / Visual-Web Research
- **v0.6** — Computer-Use + qita Visual Replay
- **v0.7** — Native Multi-Agent Core
- **v0.8** — Safety / Judge / Robustness Layer
- **v0.9** — MCP / A2A / Recipes / Community Prep
- **v1.0** — Research OS for AI Agents

### Execution rules

1. Every month must have one clear theme.
2. Every version must have one clear narrative.
3. Every release must ship with code + docs + examples + a report.
4. Benchmark support must always land through the same framework abstractions.
5. New power features should improve the research story, not dilute it.

---

## 2. Monthly Plan

## April 2026 — Scope Freeze for v0.3

### Theme

**Define the research kernel clearly before adding more power.**

### Main goals

- freeze the v0.3 scope,
- define the core run and artifact model,
- eliminate ambiguity in what counts as an official Qitos run,
- align codebase, docs, and examples around one experimental contract.

### Deliverables

#### Product / architecture

- Write and ratify `ExperimentSpec` / `RunSpec`
- Define Artifact Schema v1
- Define benchmark runner contract
- Define official terminology for:
  - run
  - trajectory
  - observation
  - decision
  - action
  - artifact
  - replay
  - benchmark result

#### Engineering

- Refactor any examples that bypass the intended kernel abstractions
- Create a single structured output path for benchmark runs
- Standardize metadata capture:
  - model
  - seed
  - git SHA
  - benchmark split
  - stop criteria
  - cost / latency / tokens

#### Documentation

- Publish a short design doc: “What is an official Qitos run?”
- Publish a glossary page
- Publish a migration page for any config changes

### Exit criteria

- `ExperimentSpec` is stable enough to implement against,
- artifact shape is documented,
- contributors can understand where new benchmark integrations should hook in,
- internal ambiguity about “the right way to run Qitos” is gone.

---

## May 2026 — Ship v0.3: Reproducible Runs Foundation

### Theme

**Every serious run should be replayable, diffable, and exportable.**

### Main goals

- turn reproducibility into a product feature,
- make qita visibly more useful,
- make benchmark outputs consistent and publication-friendly.

### Deliverables

#### Core runtime

- Implement `ExperimentSpec` / `RunSpec`
- Implement Artifact Schema v1 in official runners
- Add deterministic replay hooks
- Standardize benchmark result serialization

#### qita

- Run replay
- HTML export
- First-pass side-by-side diff
- Cost / token / latency comparison
- “first failure step” summary

#### CLI

- `qitos bench run`
- `qitos bench eval`
- `qitos bench replay`
- `qitos bench export`

#### Docs / examples

- “Run a benchmark reproducibly” tutorial
- “Replay and inspect a failed run” tutorial
- one end-to-end example from run → replay → export

### Release narrative

**v0.3 makes reproducible agent runs a first-class product feature.**

### Exit criteria

- official benchmark runs can be replayed from config + seed + git SHA,
- qita diff is good enough to compare two failed runs,
- benchmark outputs feel unified rather than custom per benchmark.

---

## June 2026 — Build the v0.4 Harness Layer

### Theme

**Move from provider adapters to serious model-family presets.**

### Main goals

- define the harness abstraction layer,
- separate provider plumbing from research-quality default behavior,
- make Qitos capable of shipping fairer default baselines.

### Deliverables

#### Harness abstractions

- `ModelAdapter`
- `FamilyPreset`
- `HarnessPolicy`
- `PromptProtocol`
- `ToolPolicy`
- `ContextPolicy`

#### Preset system

- design a benchmark-aware preset layout,
- define inheritance / override rules,
- define how presets register parser, retry, context, and stop policies.

#### Internal benchmarking

- create a small internal evaluation matrix,
- compare raw adapter behavior vs preset behavior,
- record tuning notes for each family.

#### Docs

- “What is a Qitos preset?”
- “How to add a new model-family preset”

### Exit criteria

- harness abstractions are clean enough to support multiple model families,
- presets can encode meaningful policy decisions,
- model-family comparisons no longer require handwritten scaffolding.

---

## July 2026 — Ship v0.4: Optimized Harness / Gold Presets

### Theme

**Qitos should become known for fair, usable, research-quality baselines.**

### Main goals

- ship the first public gold presets,
- prove that Qitos presets are a better research baseline than generic adapters,
- make “switch model families, keep the benchmark constant” a core workflow.

### Deliverables

#### Gold preset release

- ship 3–5 major model-family presets,
- include per-family documentation,
- include recommended benchmark targets,
- include known failure modes and caveats.

#### Benchmark report

- publish the first Harness Benchmark Report,
- compare success / cost / latency across presets,
- publish tuning notes and reproducible configs.

#### qita updates

- preset-aware run display,
- structured comparison panels for family A vs family B,
- config diff visibility.

#### Docs / examples

- “Switch model families with presets” tutorial
- “Build your own preset” tutorial
- one benchmark comparison notebook / report example

### Release narrative

**v0.4 makes Qitos a stronger default baseline framework for agent research.**

### Exit criteria

- researchers can swap model families with minimal code changes,
- Qitos presets are strong enough to cite in blog posts or internal reports,
- baseline quality becomes a visible differentiator for the project.

---

## August 2026 — Build the v0.5 Multimodal Core

### Theme

**Do not add image input as a bolt-on; define a clean multimodal environment model.**

### Main goals

- define unified observation and action abstractions,
- design the environment adapter SDK,
- ensure multimodal support still fits the same Qitos kernel.

### Deliverables

#### Core abstractions

- `ObservationPack`
- `ActionSpace`
- `EnvironmentAdapter`
- `GroundingMetadata`
- `VisualTraceAsset`

#### Observation support

- text
- screenshot
- DOM
- accessibility tree
- UI element candidates
- OCR / grounding metadata

#### Action support

- click
- double click
- type
- hotkey
- scroll
- drag
- region select
- wait
- tool call

#### Docs

- “How multimodal agents fit into the Qitos kernel”
- “How to add a new environment adapter”

### Exit criteria

- multimodal support is represented as clean framework abstractions, not per-benchmark hacks,
- observation and action semantics are stable enough for multiple benchmarks,
- the same trace / artifact model still works for multimodal runs.

---

## September 2026 — Ship v0.5: Multimodal Core / Visual-Web Research

### Theme

**Make Qitos relevant to frontier multimodal and web-agent research.**

### Main goals

- ship the first multimodal benchmark path,
- prove the observation / action abstractions are usable,
- make multimodal traces inspectable enough for researchers.

### Deliverables

#### Benchmark support

- ship the first official multimodal / visual-web environment integration,
- provide a canonical starter baseline,
- unify runner output with the existing artifact schema.

#### Baseline agent

- planner,
- grounding step,
- action selector,
- critic / retry loop.

#### qita

- first visual timeline,
- basic screenshot playback,
- action overlay foundation.

#### Docs / examples

- “Run your first multimodal benchmark” tutorial
- “Inspect a GUI failure in qita” tutorial
- one visual-web baseline example

### Release narrative

**v0.5 makes Qitos a serious starting point for multimodal and visual-web agent research.**

### Exit criteria

- at least one multimodal benchmark path is fully runnable,
- visual traces are inspectable enough to help debug failures,
- Qitos now has a visible story beyond text-only agents.

---

## October 2026 — Ship v0.6: Computer-Use + qita Visual Replay

### Theme

**Turn multimodal support into full computer-use research support.**

### Main goals

- expand from visual-web into broader computer-use workflows,
- make qita a truly differentiated visual debugging tool,
- solidify Qitos as a platform for GUI agent experiments.

### Deliverables

#### Environment expansion

- add a second major GUI / computer-use environment family,
- refine the environment adapter SDK based on real integrations,
- improve action semantics for longer-horizon tasks.

#### qita visual replay

- screenshot timeline,
- action overlay,
- step-by-step observation pack viewer,
- branch comparison,
- grounding failure annotation.

#### Computer-use starter pack

- release a stronger canonical multimodal baseline package,
- add configurable grounding and retry strategies,
- provide visual debugging presets.

#### Docs / examples

- “From visual-web to computer-use” guide
- “How to inspect grounding failures” guide

### Release narrative

**v0.6 makes qita and Qitos meaningfully useful for computer-use agent research.**

### Exit criteria

- the same agent design can operate across at least two multimodal / GUI environment families,
- qita visual replay becomes a visible reason to use Qitos,
- computer-use becomes a real pillar of the framework story.

---

## November 2026 — Ship v0.7: Native Multi-Agent Core

### Theme

**Make multi-agent behavior a first-class research subject.**

### Main goals

- ship a local multi-agent runtime,
- make handoff and delegation traceable,
- provide canonical collaboration templates.

### Deliverables

#### Runtime

- local sub-agent runtime,
- handoff,
- delegation,
- role contracts,
- shared vs private memory,
- stop / timeout / arbitration.

#### Templates

- manager-worker,
- planner-executor,
- proposer-verifier,
- actor-critic,
- debate.

#### qita / evaluation

- handoff timeline,
- per-agent token / cost breakdown,
- loop / conflict detection,
- role-level contribution view.

#### Docs / examples

- “Build your first multi-agent system in Qitos” tutorial
- “When to use shared vs private memory” guide
- one benchmark-style multi-agent example

### Release narrative

**v0.7 turns Qitos from a single-agent framework into a multi-agent research runtime.**

### Exit criteria

- multi-agent traces are inspectable and comparable,
- multi-agent patterns are reusable rather than ad-hoc,
- Qitos has a clear story for studying collaboration strategies.

---

## December 2026 — Ship v0.8: Safety / Judge / Robustness Layer

### Theme

**Expand from “can the agent do the task?” to “how safely and reliably does it behave?”**

### Main goals

- make evaluation more rigorous,
- add judge-based and safety-oriented analysis,
- connect capability benchmarking with robustness research.

### Deliverables

#### Evaluation layer

- `JudgeSpec`
- evaluation hooks in the artifact model,
- support for structured judge outputs,
- run-level safety / robustness tags.

#### Benchmarking

- add one safety / robustness benchmark path,
- support attacker / adversarial environment annotations,
- define a failure taxonomy template.

#### qita

- judge panel,
- failure category summary,
- run-level risk / failure overview.

#### Docs / examples

- “How to evaluate an agent with judges” guide
- “How to tag and analyze failure modes” guide

### Release narrative

**v0.8 makes Qitos a stronger framework for studying not just capability, but agent reliability and robustness.**

### Exit criteria

- judge outputs are first-class artifacts,
- failure analysis feels structured rather than anecdotal,
- Qitos can support public safety / robustness benchmark reports.

---

## January 2027 — Ship v0.9: MCP / A2A / Recipes / Community Prep

### Theme

**Turn Qitos into a platform that other researchers can extend and publish on top of.**

### Main goals

- prepare for ecosystem growth,
- add standards-based interoperability,
- launch the reproduction and recipe layer,
- make outside contributions easier.

### Deliverables

#### Interop

- MCP client,
- MCP server wrapper,
- A2A bridge,
- remote-agent wrapper.

#### Recipes

Launch `qitos-recipes` with:

- canonical single-agent recipes,
- canonical multimodal recipes,
- canonical multi-agent recipes,
- benchmark baseline recipes.

#### Contributor experience

- module-based contribution guide,
- benchmark adapter template,
- preset template,
- environment adapter template,
- recipe template.

#### Docs / examples

- “How to publish a recipe with Qitos” guide
- “How to contribute a benchmark adapter” guide
- “How to wrap a remote agent” guide

### Release narrative

**v0.9 turns Qitos into an extensible research ecosystem, not just a codebase.**

### Exit criteria

- external contributors have clear entry points,
- interop support exists without distorting the core runtime,
- recipes make Qitos easier to learn and easier to cite.

---

## February 2027 — v1.0 Beta / API Freeze Month

### Theme

**Stop expanding the surface area; harden the product.**

### Main goals

- freeze the core public API shape,
- harden docs and migration paths,
- verify that the framework feels coherent end-to-end,
- identify anything that would make a v1.0 release feel premature.

### Deliverables

#### Product hardening

- API audit,
- artifact schema stability audit,
- benchmark runner consistency audit,
- qita UX audit,
- docs completeness audit.

#### Quality

- regression suite expansion,
- example validation suite,
- benchmark smoke tests,
- migration notes for all post-v0.3 breaking changes.

#### Narrative and packaging

- v1.0 positioning page,
- release candidate notes,
- benchmark / harness / multimodal / multi-agent overview pages.

### Exit criteria

- core public abstractions are stable enough for a 1.0 promise,
- docs support a new user from install to benchmark to replay,
- maintainers are confident that new contributions fit the architecture.

---

## March 2027 — Ship v1.0: Research OS for AI Agents

### Theme

**Present Qitos as the default framework for serious agent research.**

### Main goals

- launch a coherent v1.0,
- make the product story unmistakable,
- show that Qitos is not a demo framework but a research platform.

### Deliverables

#### v1.0 release package

- stable core runtime,
- reproducibility layer,
- harness presets,
- multimodal core,
- computer-use support,
- native multi-agent runtime,
- judge / robustness layer,
- MCP / A2A bridges,
- recipes layer,
- qita visual replay and diff.

#### v1.0 supporting assets

- launch blog post,
- “Why Qitos” page,
- benchmark report bundle,
- recipes index,
- contributor roadmap,
- migration guide.

#### Community launch motions

- publish 3 flagship demos,
- publish 3 benchmark / reproduction stories,
- encourage outside recipes and benchmark adapters,
- open a v1.x RFC process.

### Release narrative

**v1.0 makes Qitos the research-first operating system for building, benchmarking, replaying, and studying AI agents.**

### Exit criteria

- new researchers can get from install → example → benchmark → replay → report cleanly,
- the v1.0 message is clear and differentiated,
- Qitos feels opinionated, coherent, and extensible.

---

## 3. Cross-Cutting Monthly Operating System

These tasks should happen every month, regardless of the feature theme.

### 3.1 Release discipline

- one version story,
- one benchmark or evaluation artifact,
- one technical blog post,
- one migration note if needed.

### 3.2 Research communication

- publish one public or internal benchmark comparison,
- publish one failure analysis note,
- collect one “what we learned” memo.

### 3.3 Contributor funnel

- keep “good first issue” current,
- maintain adapter / preset / recipe templates,
- label issues by subsystem.

### 3.4 Quality discipline

- example validation,
- regression tests,
- benchmark smoke tests,
- docs freshness review.

---

## 4. Success Metrics by v1.0

By the time v1.0 ships, Qitos should ideally have:

### Product metrics

- a stable run / artifact model,
- 3–5 strong model-family presets,
- at least 2 multimodal / GUI benchmark paths,
- at least 3 canonical multi-agent templates,
- visual replay and run diff in qita.

### Research metrics

- at least 2 public harness benchmark reports,
- at least 2 multimodal / computer-use reports,
- at least 1 multi-agent methodology report,
- at least 1 safety / robustness evaluation report.

### Ecosystem metrics

- external contributions in presets, adapters, or recipes,
- a visible recipes library,
- a clean contributor story,
- a clear v1.x roadmap.

---

## 5. Final Standard

This plan succeeds if, by v1.0, the answer to the following question is clearly “Qitos” for a meaningful set of researchers:

> “What framework should I use if I want to build, benchmark, replay, and analyze a serious AI agent experiment?”

