# Contracts & Guarantees

## Prompt ↔ Parser Contract

Prompt format and parser must match.

- ReAct text prompt → `ReActTextParser`
- XML prompt → XML parser
- JSON prompt → JSON parser

If you change the prompt output shape without changing the parser, you are breaking the contract.

## AgentModule ↔ Engine Contract

QitOS keeps the runtime loop explicit:

```text
state -> prepare -> model/decide -> action/env -> observation -> reduce -> next state
```

- `AgentModule` defines strategy, state transitions, and model-facing inputs.
- `Engine` drives lifecycle, tool execution, stop checks, tracing, and hooks.
- Returning `None` from `decide` opts into the default Engine model path.

## Tool Input / Output Contract

- Tools should expose explicit parameters with stable names.
- Tool results should be structured dictionaries, not ambiguous free-form strings.
- Agents should reason over observations, not assume tool side effects without reading outputs.

## Trace / Run Artifact Contract

Trace artifacts are first-class outputs, not debugging leftovers.

- `runs/` holds structured run outputs.
- `qita` consumes those outputs for board, replay, and export.
- Benchmarks, examples, and real agents all benefit from the same artifact model.

## Why This Matters

These contracts are what make QitOS comparable, debuggable, and reusable across research, product agents, and evaluation workflows.
