# Self-Refine Template Notes

## Source idea
Self-Refine (Madaan et al. 2023) iterates: generate → critique → refine until quality meets a threshold:

1. **Generate**: The agent produces an initial draft.
2. **Critique**: A critic evaluates the draft, identifying weaknesses.
3. **Refine**: The agent produces an improved version addressing the critique.
4. **Loop**: Steps 2-3 repeat until quality threshold or max refinements.

Key insight: LLMs can effectively critique and improve their own outputs when given structured feedback.

## Mapping in QitOS
- `SelfRefineAgent` manages the generate-refine cycle with `build_system_prompt()` including refinement round context.
- `SelfRefineCritic` drives the loop: heuristic scoring on draft quality, `retry` with `instruction_patch` when below threshold.
- `SelfRefineState` tracks draft, refinement count, and critique history.

## Key differences from the paper
- The paper uses LLM-based scoring for evaluation. QitOS uses heuristic scoring (draft length + refinement count) by default.
- Override `SelfRefineCritic.evaluate()` to plug in LLM-based scoring for production use.

## Scope in this template
This template provides the core generate-critique-refine loop. For production use, replace heuristic scoring with LLM-based evaluation.
