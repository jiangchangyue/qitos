# Reflexion Template Notes

## Source idea
Reflexion (Shinn et al. 2023) iterates: act → evaluate → reflect → retry with memory:

1. **Act**: The agent takes an action toward the task.
2. **Evaluate**: Check if the action succeeded or failed.
3. **Reflect**: On failure, generate a verbal reflection describing what went wrong and how to improve.
4. **Retry**: The agent tries again, with previous reflections injected into its context.

Key insight: Storing and re-injecting reflections allows LLMs to learn from their own mistakes within a single session.

## Mapping in QitOS
- `ReflexionAgent` manages the act-reflect cycle with `build_system_prompt()` including previous reflections.
- `ReflexionCritic` detects failures (errors, non-zero return codes, empty results) and generates reflections as `instruction_patch`.
- `ReflexionState` tracks reflections, reflection count, and attempt number.

## Key differences from the paper
- The paper uses a separate evaluation model. QitOS uses tool result signals (error, returncode) for failure detection.
- The paper stores reflections in long-term memory across episodes. QitOS stores them in per-run state.
- For production use, override `_generate_reflection()` to use LLM-based reflection generation.

## Scope in this template
This template provides the core act-reflect-retry loop with reflection storage. For production use, enhance reflection generation with LLM prompts.
